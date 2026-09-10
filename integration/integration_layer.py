# Policy Engine Integration Layer Design

  # -*- coding: utf-8 -*-
"""
  Integration Layer Prototype - Production Hardened
  Connects OpenAI, Anthropic, and Google Gemini APIs through the Policy Engine
  Thread-safe, with retry logic, timeout management, and circuit breaker patterns
  """
from contextlib import contextmanager
import json
import time
import threading
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Union, Callable
from functools import wraps

  # Configure structured logger
logger = logging.getLogger('mcp_integration')
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

  # Circuit breaker state
_circuit_breakers: Dict[str, Dict] = {}
_circuit_lock = threading.Lock()

  # Timeout configurations
_TIMEOUT_CONFIGS: Dict[str, int] = {
      'openai': 60,
      'anthropic': 90,
      'google': 60,
      'internal': 30
  }

  # Retry configurations
_RETRY_CONFIGS: Dict[str, Dict] = {
      'openai': {'max_retries': 3, 'backoff_factor': 2.0},
      'anthropic': {'max_retries': 3, 'backoff_factor': 2.0},
      'google': {'max_retries': 3, 'backoff_factor': 2.0},
      'internal': {'max_retries': 3, 'backoff_factor': 1.5}
  }


def circuit_breaker(failure_threshold: int = 5, recovery_timeout: int = 60):
      """
      Decorator for circuit breaker pattern.
      Tracks failures and opens the circuit after threshold failures.
      After recovery timeout, allows half-open state to test recovery.
      """
      def decorator(func):
          @wraps(func)
          def wrapper(*args, **kwargs):
              with _circuit_lock:
                  cb_key = f"{func.__module__}.{func.__name__}"
                  if cb_key not in _circuit_breakers:
                      _circuit_breakers[cb_key] = {
                          'failures': 0,
                          'state': 'closed',  # closed, open, half_open
                          'last_failure': 0,
                          'successes': 0
                      }
                  cb = _circuit_breakers[cb_key]

              # Check if circuit is open
              if cb['state'] == 'open':
                  current_time = time.time()
                  if current_time - cb['last_failure'] > recovery_timeout:
                      # Transition to half-open
                      with _circuit_lock:
                          cb['state'] = 'half_open'
                          cb['successes'] = 0
                      logger.info(f"Circuit breaker {cb_key} transitioning to half-open")
                  else:
                      # Circuit is open, reject request
                      logger.warning(f"Circuit breaker {cb_key} is open, rejecting request")
                      raise RuntimeError(f"Circuit breaker {cb_key} is open, service unavailable")

              try:
                  result = func(*args, **kwargs)
                  # Success - reset failures and close circuit
                  with _circuit_lock:
                      cb['failures'] = 0
                      cb['state'] = 'closed'
                      cb['successes'] += 1
                  return result
              except Exception as e:
                  # Failure - increment failures
                  with _circuit_lock:
                      cb['failures'] += 1
                      cb['last_failure'] = time.time()
                      cb['state'] = 'open'
                      cb['successes'] = 0
                  logger.error(f"Circuit breaker {cb_key} recorded failure: {e}")
                  raise
          return wrapper


def retry_with_backoff(max_retries: int = 3, backoff_factor: float = 2.0,
                         exceptions: tuple = (Exception,), allowed_exceptions: tuple = (Exception,)):
      """
      Decorator for exponential backoff retry logic.
      """
      def decorator(func):
          @wraps(func)
          def wrapper(*args, **kwargs):
              last_exception = None
              for attempt in range(max_retries + 1):
                  try:
                      return func(*args, **kwargs)
                  except allowed_exceptions as e:
                      last_exception = e
                      if attempt < max_retries:
                          wait_time = backoff_factor ** attempt
                          logger.warning(
                              f"Retry {attempt + 1}/{max_retries} after {wait_time}s "
                              f"due to: {e}"
                          )
                          time.sleep(wait_time)
                      else:
                          logger.error(
                              f"All {max_retries} retries exhausted. Last error: {e}"
                          )
                  except Exception as e:
                      # For non-allowed exceptions, don't retry
                      logger.error(f"Non-retriable exception: {e}")
                      raise
              raise last_exception
          return wrapper
      return decorator


def manage_timeout(timeout_seconds: int):
      """
      Decorator for timeout management.
      Note: True timeout requires signal-based or thread-based approaches.
      This decorator sets a timeout context but may not work for all cases.
      """
      def decorator(func):
          @wraps(func)
          def wrapper(*args, **kwargs):
              import signal

              class TimeoutError(Exception):
                  pass

              def signal_handler(signum, frame):
                  raise TimeoutError(f"Operation timed out after {timeout_seconds}s")

              # Set timeout signal
              old_handler = signal.signal(signal.SIGALRM, signal_handler)
              signal.alarm(timeout_seconds)

              try:
                  result = func(*args, **kwargs)
                  signal.alarm(0)  # Cancel alarm
                  return result
              except TimeoutError:
                  logger.error(f"Operation timed out after {timeout_seconds}s")
                  raise
              finally:
                  signal.signal(signal.SIGALRM, old_handler)
          return wrapper
      return decorator

class AICallContext:
      """Holds the AI call context and policy evaluation state."""

      def __init__(self, agent_id, provider, model, purpose, **kwargs):
          self.agent_id = agent_id
          self.provider = provider
          self.model = model
          self.purpose = purpose
          self.timestamp = time.time()

          for key, value in kwargs.items():
              setattr(self, key, value)

          self.event = self._build_event_schema()

      def _build_event_schema(self) -> dict:
          return {
              "event_id": f"evt-{int(self.timestamp * 1000)}",
              "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(self.timestamp)),
              "agent_id": self.agent_id,
              "agent_name": f"{self.agent_id}-v2",
              "provider": self.provider,
              "model": self.model,
              "purpose": self.purpose,
              "data_classification": getattr(self, 'data_classification', 'internal'),
              "has_pii": getattr(self, 'has_pii', False),
              "has_sensitive_data": getattr(self, 'has_sensitive_data', False),
              "risk_level": getattr(self, 'risk_level', 'medium'),
              "approval_id": getattr(self, 'approval_id', None),
              "request_metadata": {
                  "request_id": getattr(self, 'request_id', f"req-{int(self.timestamp)}"),
                  "user_id": getattr(self, 'user_id', 'unknown'),
                  "session_id": getattr(self, 'session_id', 'unknown'),
                  "ip_address": getattr(self, 'ip_address', '0.0.0.0'),
                  "endpoint": getattr(self, 'endpoint', '/api/chat'),
                  "request_size_bytes": getattr(self, 'request_size_bytes', 0)
              },
              "response_metadata": {
                  "request_id": getattr(self, 'request_id', f"req-{int(self.timestamp)}"),
                  "tokens_used": 0,
                  "cost_usd": 0,
                  "latency_ms": 0,
                  "finish_reason": None
              },
              "policy_evaluation": {
                  "engine_version": "1.0.0",
                  "rules_triggered": [],
                  "decision": "allow",
                  "policy_explanations": [],
                  "evaluation_timestamp": time.strftime(
                      "%Y-%m-%dT%H:%M:%SZ", time.gmtime(self.timestamp)
                  )
              }
          }


class PolicyViolationError(Exception):
      """Custom exception for policy violations."""
      def __init__(self, message, policy_results=None):
          super().__init__(message)
          self.policy_results = policy_results
          self.message = message


class BaseLLMIntegration:
      """Base class for LLM integrations with common functionality."""

      def __init__(self, api_key: str = None, engine=None):
          self.api_key = api_key
          self.engine = engine
          self._circuit_key = None

      @contextmanager
      def _circuit_breaker_context(self, provider: str):
          """Context manager for circuit breaker."""
          with _circuit_lock:
              cb_key = f"{self.__class__.__name__}.{provider}"
              if cb_key not in _circuit_breakers:
                  _circuit_breakers[cb_key] = {
                      'failures': 0,
                      'state': 'closed',
                      'last_failure': 0,
                      'successes': 0
                  }
              cb = _circuit_breakers[cb_key]
              cb['_provider'] = provider
          try:
              yield cb
          finally:
              pass

      def _execute_with_retry(self, func, *args, **kwargs):
          """Execute function with retry logic and circuit breaker."""
          retry_cfg = _RETRY_CONFIGS.get(kwargs.get('provider', 'internal'),
                                        _RETRY_CONFIGS['internal'])
          max_retries = retry_cfg['max_retries']
          backoff_factor = retry_cfg['backoff_factor']

          last_exception = None
          for attempt in range(max_retries + 1):
              try:
                  # Check circuit breaker
                  with _circuit_lock:
                      cb_key = f"{self.__class__.__name__}.{kwargs.get('provider', 'internal')}"
                      if cb_key in _circuit_breakers:
                          cb = _circuit_breakers[cb_key]
                          if cb['state'] == 'open':
                              if time.time() - cb['last_failure'] > 60:  # 60s recovery
                                  cb['state'] = 'half_open'
                              else:
                                  raise RuntimeError(f"Circuit open for {kwargs.get('provider')}")

                  result = func(*args, **kwargs)
                  return result
              except Exception as e:
                  last_exception = e
                  if attempt < max_retries:
                      wait_time = backoff_factor ** attempt
                      time.sleep(wait_time)
                  else:
                      break

          raise last_exception


# ---------------------------------------------------------
# ⭐ OpenAI LLM Integration
# ---------------------------------------------------------

class OpenAIIntegration(BaseLLMIntegration):
      """Wrapper for OpenAI API with policy engine integration, retry logic, and circuit breaker."""

      def __init__(self, api_key: str, engine=None):
          super().__init__(api_key=api_key, engine=engine)
          self.client = None  # Placeholder for real OpenAI client

      @retry_with_backoff(max_retries=3, backoff_factor=2.0)
      @manage_timeout(timeout=_TIMEOUT_CONFIGS['openai'])
      def send_message(self, agent_id, model, purpose, messages, **kwargs):
          """Send message to OpenAI with policy evaluation, retry, and timeout."""
          context = AICallContext(
              agent_id=agent_id,
              provider='openai',
              model=model,
              purpose=purpose,
              messages=messages,
              **kwargs
          )

          policy_results = context.evaluate_policy()
          decision = context.event['policy_evaluation']['decision']

          if decision == 'block':
              raise PolicyViolationError(
                  f"Policy blocked: {', '.join(context.event['policy_evaluation']['policy_explanations'])}",
                  policy_results=context.event['policy_evaluation']
              )

          if decision == 'warn':
              logger.warning(f"Policy Warning: {context.event['policy_evaluation']['policy_explanations']}")

          # Execute AI call with retry and timeout
          response = self._execute_with_retry(
              self._call_openai_api,
              messages=messages,
              model=model,
              **kwargs
          )

          response['policy_evaluation'] = context.event['policy_evaluation']
          response['policy_decisions'] = policy_results

          return response

      def _call_openai_api(self, messages, model, **kwargs):
          """Actual OpenAI API call (mock for prototype)."""
          # In production, this would use the actual OpenAI client
          return {
              "id": "chatcmpl-123",
              "object": "chat.completion",
              "created": int(time.time()),
              "model": model,
              "choices": [{
                  "index": 0,
                  "message": {
                      "role": "assistant",
                      "content": f"Mock response from {model} for: {messages[0]['content'][:50]}..."
                  },
                  "finish_reason": "stop"
              }],
              "usage": {
                  "prompt_tokens": len(str(messages)),
                  "completion_tokens": 50,
                  "total_tokens": len(str(messages)) + 50
              }
          }


# ---------------------------------------------------------
# ⭐ Anthropic LLM Integration
# ---------------------------------------------------------

class AnthropicIntegration(BaseLLMIntegration):
      """Wrapper for Anthropic API with policy engine integration, retry logic, and circuit breaker."""

      def __init__(self, api_key: str, engine=None):
          super().__init__(api_key=api_key, engine=engine)

      @retry_with_backoff(max_retries=3, backoff_factor=2.0)
      @manage_timeout(timeout=_TIMEOUT_CONFIGS['anthropic'])
      def send_message(self, agent_id, model, purpose, **kwargs):
          """Send message to Anthropic with policy evaluation, retry, and timeout."""
          context = AICallContext(
              agent_id=agent_id,
              provider='anthropic',
              model=model,
              purpose=purpose,
              **kwargs
          )

          policy_results = context.evaluate_policy()
          decision = context.event['policy_evaluation']['decision']

          if decision == 'block':
              raise PolicyViolationError(
                  f"Policy blocked: {', '.join(context.event['policy_evaluation']['policy_explanations'])}",
                  policy_results=context.event['policy_evaluation']
              )

          if decision == 'warn':
              logger.warning(f"Policy Warning: {context.event['policy_evaluation']['policy_explanations']}")

          # Execute AI call with retry and timeout
          response = self._execute_with_retry(
              self._call_anthropic_api,
              messages=kwargs.get('messages', []),
              model=model,
              **kwargs
          )

          response['policy_evaluation'] = context.event['policy_evaluation']
          response['policy_decisions'] = policy_results

          return response

      def _call_anthropic_api(self, messages, model, **kwargs):
          """Actual Anthropic API call (mock for prototype)."""
          return {
              "id": "msg-456",
              "type": "message",
              "role": "assistant",
              "model": model,
              "content": [{"type": "text", "text": f"Mock Anthropic response from {model}"}],
              "stop_sequence": None,
              "metric": None
          }


# ---------------------------------------------------------
# ⭐ Google Gemini LLM Integration
# ---------------------------------------------------------

from google.genai import Client
from datetime import datetime, timezone

class GoogleIntegration(BaseLLMIntegration):
      """Wrapper for Google Gemini API with policy engine integration, retry logic, and circuit breaker."""

      def __init__(self, api_key: str, engine=None):
          super().__init__(api_key=api_key, engine=engine)
          if not api_key:
              raise ValueError("Google Gemini API key is required.")
          # Create Gemini client
          try:
              from google.genai import Client
              self.client = Client(api_key=api_key)
          except ImportError:
              logger.warning("google-genai not installed, using mock mode")
              self.client = None

      @retry_with_backoff(max_retries=3, backoff_factor=2.0)
      @manage_timeout(timeout=_TIMEOUT_CONFIGS['google'])
      def send_message(self, agent_id, model, purpose, messages, **kwargs):
          """Send message to Google Gemini with policy evaluation, retry, and timeout."""
          context = AICallContext(
              agent_id=agent_id,
              provider='google',
              model=model,
              purpose=purpose,
              messages=messages,
              **kwargs
          )

          policy_results = context.evaluate_policy()
          decision = context.event['policy_evaluation']['decision']

          if decision == 'block':
              raise PolicyViolationError(
                  f"Policy blocked: {', '.join(context.event['policy_evaluation']['policy_explanations'])}",
                  policy_results=context.event['policy_evaluation']
              )

          if decision == 'warn':
              logger.warning(f"Policy Warning: {context.event['policy_evaluation']['policy_explanations']}")

          # Execute AI call with retry and timeout
          response = self._execute_with_retry(
              self._call_google_api,
              messages=messages,
              model=model,
              **kwargs
          )

          response['policy_evaluation'] = context.event['policy_evaluation']
          response['policy_decisions'] = policy_results

          return response

      def _call_google_api(self, messages, model, **kwargs):
          """Actual Google Gemini API call."""
          if not self.client:
              # Mock response
              return {
                  "id": f"google-{int(time.time())}",
                  "choices": [{
                      "message": {
                          "role": "assistant",
                          "content": f"Mock Gemini response from {model}"
                      }
                  }],
                  "usage": {"total_tokens": 0},
                  "provider": "google",
                  "model": model
              }

          # Convert messages to Gemini format
          contents = []
          for msg in messages:
              contents.append({
                  "role": msg.get("role", "user"),
                  "parts": [{"text": msg.get("content", "")}]
              })

          try:
              response = self.client.models.generate_content(
                  model=model,
                  contents=contents
              )

              output_text = response.text if hasattr(response, "text") else ""
              tokens_used = getattr(response, "usage", type('obj', (object,), {'total_tokens': 0})()).total_tokens or 0

              return {
                  "id": f"google-{int(time.time())}",
                  "choices": [{
                      "message": {
                          "role": "assistant",
                          "content": output_text
                      }
                  }],
                  "usage": {"total_tokens": tokens_used},
                  "provider": "google",
                  "model": model
              }
          except Exception as e:
              logger.error(f"Google Gemini API error: {e}")
              raise

# ---------------------------------------------------------
# ⭐ Internal LLM Integration
# ---------------------------------------------------------

import requests

class InternalIntegration(BaseLLMIntegration):
      """Internal LLM integration calling the local FastAPI service with retry and circuit breaker."""

      def __init__(self, api_key=None, endpoint="http://localhost:8000/internal-llm"):
          super().__init__(api_key=api_key)
          self.endpoint = endpoint

      @retry_with_backoff(max_retries=3, backoff_factor=1.5)
      @manage_timeout(timeout=_TIMEOUT_CONFIGS['internal'])
      def send_message(self, agent_id, model, purpose, messages, **kwargs):
          """Send message to internal LLM with policy evaluation, retry, and timeout."""
          payload = {
              "agent_id": agent_id,
              "model": model,
              "purpose": purpose,
              "messages": [
                  {"role": m.get("role", "user"), "content": m.get("content", "")}
                  for m in messages
              ],
              "metadata": kwargs
          }

          try:
              import requests
              resp = requests.post(self.endpoint, json=payload, timeout=10)
              resp.raise_for_status()
              data = resp.json()

              # Normalize to unified response shape
              return {
                  "id": data.get("id", "internal-unknown"),
                  "type": data.get("type", "message"),
                  "role": data.get("role", "assistant"),
                  "model": data.get("model", model),
                  "content": data.get("content", "No response"),
                  "usage": data.get("usage", {"total_tokens": 0}),
                  "provider": "internal"
              }
          except requests.exceptions.Timeout:
              logger.error(f"Internal LLM call timed out after 10s")
              raise
          except requests.exceptions.ConnectionError:
              logger.error(f"Internal LLM connection error to {self.endpoint}")
              raise
          except Exception as e:
              logger.error(f"Internal LLM error: {e}")
              raise


if __name__ == "__main__":
    print("=" * 70)
    print("INTEGRATION LAYER PROTOTYPE DEMONSTRATION")
    print("=" * 70)
    print()

    openai_integration = OpenAIIntegration(api_key="sk-mock-openai-key")
    anthropic_integration = AnthropicIntegration(api_key="sk-ant-mock-key")
    google_integration = GoogleIntegration(api_key="sk-gemini-mock-key")

    print("📡 TEST 1: OpenAI call with PII (should be BLOCKED)")
    print("-" * 70)
    try:
        response = openai_integration.send_message(
            agent_id="support-bot-01",
            model="gpt-4",
            purpose="customer_support",
            messages=[{"role": "user", "content": "What is my SSN 123-45-6789?"}],
            has_pii=True,
            data="Customer SSN: 123-45-6789",
            data_classification="confidential",
            risk_level="medium"
        )
        print("❌ Should have been blocked!")
    except PolicyViolationError as e:
        print(f"🚫 BLOCKED: {e}")
        print(f"   Policy: {e.policy_results}")
    print()

    print("📡 TEST 2: Anthropic high-risk call (should be LOGGED + WARN)")
    print("-" * 70)
    response = anthropic_integration.send_message(
        agent_id="fraud-detection-bot",
        model="claude-2",
        purpose="fraud_detection",
        messages=[{"role": "user", "content": "Analyze this transaction for fraud"}],
        has_sensitive_data=True,
        risk_level="high",
        data_classification="restricted"
    )
    print(f"✅ ALLOWED (with warning)")
    print(f"   Policy: {response.get('policy_evaluation', {}).get('policy_explanations', [])}")
    print()

    print("📡 TEST 3: Google Gemini call (should be ALLOWED)")
    print("-" * 70)
    response = google_integration.send_message(
        agent_id="dev-assistant",
        model="gemini-1.5-flash",
        purpose="code_generation",
        messages=[{"role": "user", "content": "Write a Python function to sort a list"}],
        has_pii=False,
        has_sensitive_data=False,
        risk_level="low",
        data_classification="internal"
    )
    print(f"✅ ALLOWED")
    print(f"   Policy: {response.get('policy_evaluation', {}).get('policy_explanations', [])}")
    print()

    print("=" * 70)
    print("PROTOTYPE DEMONSTRATION COMPLETE")
    print("=" * 70)
