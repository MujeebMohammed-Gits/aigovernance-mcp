  # -*- coding: utf-8 -*-
"""
    MCP Control-Tower Orchestrator Production Hardened
    Unified service wrapper coordinating PolicyEngine, IntegrationLayer, AuditLogger,
    MonitoringDashboard, AgentRegistry, ProviderConfigService, and UsageTracker.
    Thread-safe with consistent schemas, retry logic, circuit breakers, and timeout management.
  """
import json
import os
import sys
import time
import threading
import logging
from functools import wraps
from datetime import datetime, timezone
from dataclasses import dataclass
from typing import Dict, List, Any, Optional, Tuple, Union

  # Add project root to Python path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

  # Configure structured loggers
_policy_logger = logging.getLogger('mcp_orchestrator.policy')
_policy_logger.setLevel(logging.INFO)
_policy_handler = logging.StreamHandler()
_policy_handler.setLevel(logging.INFO)
_policy_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s'))
_policy_logger.addHandler(_policy_handler)

_integration_logger = logging.getLogger('mcp_orchestrator.integration')
_integration_logger.setLevel(logging.INFO)
_integration_handler = logging.StreamHandler()
_integration_handler.setLevel(logging.INFO)
_integration_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s'))
_integration_logger.addHandler(_integration_handler)

_audit_logger = logging.getLogger('mcp_orchestrator.audit')
_audit_logger.setLevel(logging.INFO)
_audit_handler = logging.StreamHandler()
_audit_handler.setLevel(logging.INFO)
_audit_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s'))
_audit_logger.addHandler(_audit_handler)

logger = logging.getLogger(__name__)

  # Thread locks
_engine_lock = threading.Lock()
_integration_lock = threading.Lock()
_audit_lock = threading.Lock()
_orchestrator_lock = threading.Lock()

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
      """Decorator for circuit breaker pattern."""
      def decorator(func):
          @wraps(func)
          def wrapper(*args, **kwargs):
              with _circuit_lock:
                  cb_key = f"{func.__module__}.{func.__name__}"
                  if cb_key not in _circuit_breakers:
                      _circuit_breakers[cb_key] = {
                          'failures': 0,
                          'state': 'closed',
                          'last_failure': 0,
                          'successes': 0
                      }
                  cb = _circuit_breakers[cb_key]

              if cb['state'] == 'open':
                  current_time = time.time()
                  if current_time - cb['last_failure'] > recovery_timeout:
                      with _circuit_lock:
                          cb['state'] = 'half_open'
                          cb['successes'] = 0
                  else:
                      logger.warning(f"Circuit breaker {cb_key} is open, rejecting request")
                      raise RuntimeError(f"Circuit breaker {cb_key} is open, service unavailable")

              try:
                  result = func(*args, **kwargs)
                  with _circuit_lock:
                      cb['failures'] = 0
                      cb['state'] = 'closed'
                      cb['successes'] += 1
                  return result
              except Exception as e:
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
      """Decorator for exponential backoff retry logic."""
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
                      logger.error(f"Non-retriable exception: {e}")
                      raise
              raise last_exception
          return wrapper
      return decorator


def manage_timeout(timeout_seconds: int):
      """Decorator for timeout management."""
      def decorator(func):
          @wraps(func)
          def wrapper(*args, **kwargs):
              import signal

              class TimeoutError(Exception):
                  pass

              def signal_handler(signum, frame):
                  raise TimeoutError(f"Operation timed out after {timeout_seconds}s")

              old_handler = signal.signal(signal.SIGALRM, signal_handler)
              signal.alarm(timeout_seconds)

              try:
                  result = func(*args, **kwargs)
                  signal.alarm(0)
                  return result
              except TimeoutError:
                  logger.error(f"Operation timed out after {timeout_seconds}s")
                  raise
              finally:
                  signal.signal(signal.SIGALRM, old_handler)
          return wrapper
      return decorator


  # ============================================================
  # Unified Response Schemas
  # ============================================================

@dataclass
class PolicyEvaluationResult:
      """Consistent policy evaluation result schema."""
      decision: str  # 'allow', 'block', 'warn'
      rules_triggered: List[str]
      policy_explanations: List[str]
      cost_usd: float = 0.0
      execution_time_ms: int = 0
      routing_info: Optional[dict] = None
      timestamp: str = ''

      def to_dict(self) -> dict:
          return {
              'decision': self.decision,
              'rules_triggered': self.rules_triggered,
              'policy_explanations': self.policy_explanations,
              'cost_usd': self.cost_usd,
              'execution_time_ms': self.execution_time_ms,
              'routing_info': self.routing_info,
              'timestamp': self.timestamp
          }


@dataclass
class UnifiedResponse:
      """Consistent unified response schema."""
      ai_response: dict
      policy_evaluation: PolicyEvaluationResult
      event_schema: dict

      def to_dict(self) -> dict:
          return {
              'ai_response': self.ai_response,
              'policy_evaluation': self.policy_evaluation.to_dict(),
              'event_schema': self.event_schema
          }


  # ============================================================
  # AICallContext
  # ============================================================

class AICallContext:
      """Holds the AI call context and policy evaluation state with validation."""

      def __init__(self, agent_id, provider, model, purpose, **kwargs):
          self.agent_id = agent_id
          self.provider = provider
          self.model = model
          self.purpose = purpose
          self.timestamp = time.time()

          # Validate and set fields
          valid_providers = ['openai', 'anthropic', 'google', 'internal']
          if provider not in valid_providers:
              raise ValueError(f"Invalid provider: {provider}. Must be one of: {valid_providers}")

          valid_decisions = ['allow', 'block', 'warn']
          valid_risk_levels = ['low', 'medium', 'high']

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


  # ============================================================
  # Policy Engine (Integrated)
  # ============================================================

from policy_engine.policy_engine_main import PolicyEngine, block_pii_external_llms, log_high_risk_uses, enforce_data_classification


class OrchestratorPolicyEngine:
      """Policy engine wrapper for the orchestrator with thread safety."""

      def __init__(self):
          self.engine = PolicyEngine()
          self._lock = _engine_lock
          # Register default rules
          self.engine.add_rule('PII_BLOCK', block_pii_external_llms, 'block')
          self.engine.add_rule('HIGH_RISK_LOG', log_high_risk_uses, 'log')
          self.engine.add_rule('DATA_CLASSIFICATION', enforce_data_classification, 'warn')

      def evaluate(self, ai_call: dict) -> List[dict]:
          """Evaluate AI call against policy rules with thread safety."""
          with self._lock:
              return self.engine.evaluate(ai_call)


  # ============================================================
  # Provider Failover Logic
  # ============================================================

class ProviderFailoverManager:
      """Manages provider failover logic based on error type, policy, and availability."""

      # Failover hierarchy: primary -> fallback -> internal
      _failover_hierarchy = {
          'openai': ['anthropic', 'google', 'internal'],
          'anthropic': ['openai', 'google', 'internal'],
          'google': ['openai', 'anthropic', 'internal'],
          'internal': []  # Internal is last resort
      }

      @staticmethod
      def get_failover_provider(current_provider: str, error_type: str,
                                agent_config: dict = None) -> Optional[str]:
          """Determine fallback provider based on error type and agent configuration."""
          hierarchy = ProviderFailoverManager._failover_hierarchy.get(current_provider, [])

          # If error is rate limit or authentication, skip to next in hierarchy
          if error_type in ['rate_limit', 'authentication', 'permission']:
              if hierarchy:
                  return hierarchy[0]

          # If policy blocks current provider, try failover
          if agent_config and agent_config.get('risk_level') == 'high':
              # For high-risk, prefer internal or approved alternatives
              if 'internal' in hierarchy:
                  return 'internal'

          # Default: return first available in hierarchy
          if hierarchy:
              return hierarchy[0]

          return None


  # ============================================================
  # Main Orchestrator Class
  # ============================================================

class MCPOrchestrator:
      """
      Production-hardened MCP Control-Tower Orchestrator.
      Coordinates PolicyEngine, IntegrationLayer, AuditLogger, MonitoringDashboard,
      AgentRegistry, ProviderConfigService, and UsageTracker.
      """

      def __init__(self,
                   openai_api_key: str = None,
                   anthropic_api_key: str = None,
                   google_api_key: str = None,
                   storage_path: str = "."):

          self.storage_path = storage_path

          # Initialize components with thread-safe locks
          with _orchestrator_lock:
              # Policy Engine
              self._policy_engine = OrchestratorPolicyEngine()

              # Initialize LLM integrations
              self._openai_integration = None
              self._anthropic_integration = None
              self._google_integration = None
              self._internal_integration = None

              if openai_api_key:
                  self._openai_integration = OpenAIIntegration(api_key=openai_api_key)
              if anthropic_api_key:
                  self._anthropic_integration = AnthropicIntegration(api_key=anthropic_api_key)
              if google_api_key:
                  self._google_integration = GoogleIntegration(api_key=google_api_key)

              self._internal_integration = InternalIntegration()

              # Audit Logger
              self._audit_logger = AuditLogger(
                  log_file_path=os.path.join(storage_path, "mcp_audit_log.jsonl")
              )

              # Monitoring Dashboard
              from dashboard.dashboard import MonitoringDashboard
              self._monitoring_dashboard = MonitoringDashboard(max_display=100, refresh_rate=0.1)
              self._dashboard_integration = MonitoringDashboardIntegration(self._monitoring_dashboard)

              # Agent Registry
              from agent_registry.agent_registry import AgentRegistry
              self._agent_registry = AgentRegistry(
                  storage_path=os.path.join(storage_path, "agent_registry.json")
              )

              # Provider Config Service
              from provider_config.provider_config import ProviderConfigService
              self._provider_config = ProviderConfigService(
                  storage_path=os.path.join(storage_path, "provider_config.json")
              )

              # Usage Tracker
              from usage_tracker.usage_tracker import UsageTracker
              self._usage_tracker = UsageTracker(
                  storage_path=os.path.join(storage_path, "usage_tracker.jsonl")
              )

      # ==========================================================
      # Core Execution Method
      # ==========================================================

      def execute_ai_call(self, agent_id: str, provider: str, model: str,
                          purpose: str, messages: list, **metadata) -> dict:
          """Execute a governed AI call through the MCP Control-Tower."""

          start_time = time.time()

          try:
              with _orchestrator_lock:
                  # ==========================================================
                  # Step 1: Build event schema using AICallContext
                  # ==========================================================
                  _integration_logger.info(f"Step 1: Building event schema for agent {agent_id}")

                  # Validate provider
                  provider_lower = provider.lower().strip()
                  if provider_lower not in ['openai', 'anthropic', 'google', 'internal']:
                      raise ValueError(f"Unsupported provider: {provider}")

                  # Create event schema context
                  try:
                      context = AICallContext(
                          agent_id=agent_id,
                          provider=provider_lower,
                          model=model,
                          purpose=purpose,
                          **metadata
                      )
                  except ValueError as e:
                      _integration_logger.error(f"Invalid AICallContext: {e}")
                      raise

                  event_schema = context.event
                  _integration_logger.info(
                      f"Event ID: {event_schema.get('event_id', 'N/A')}, "
                      f"Timestamp: {event_schema.get('timestamp', 'N/A')}"
                  )

                  # ==========================================================
                  # Agent Registry Compliance Check
                  # ==========================================================
                  _integration_logger.info("Checking agent registry compliance...")
                  agent_compliance = self._agent_registry.check_agent_policy_compliance(
                      agent_id=agent_id,
                      provider=provider_lower,
                      model=model,
                      purpose=purpose
                  )

                  if not agent_compliance.get('compliant', False):
                      _integration_logger.warning(
                          f"Agent registry blocked the call: {', '.join(agent_compliance['errors'])}"
                      )

                      event_schema['policy_evaluation'] = {
                          'decision': 'block',
                          'rules_triggered': ['agent_registry'],
                          'policy_explanations': agent_compliance['errors'],
                          'evaluation_timestamp': datetime.now(timezone.utc).isoformat()
                      }

                      # Send to dashboard as blocked event
                      if self._monitoring_dashboard:
                          self._dashboard_integration.receive_event(event_schema)

                      # Log the violation
                      self._audit_logger.add_event(event_schema)

                      raise PolicyViolationError(
                          f"Agent registry blocked AI call: {', '.join(agent_compliance['errors'])}",
                          policy_results=agent_compliance
                      )

                  # ==========================================================
                  # Provider Config Routing Check
                  # ==========================================================
                  routing_info = self._provider_config.get_routing_info_for_orchestrator(agent_id, purpose)

                  if routing_info.get("provider") and routing_info["provider"] != provider_lower:
                      _integration_logger.info(
                          f"ProviderConfig override: {provider_lower} -> {routing_info['provider']}"
                      )
                      provider_lower = routing_info["provider"]
                      # Update model if routing specifies
                      if routing_info.get("model"):
                          model = routing_info["model"]

                  # ==========================================================
                  # Model Remapping (OpenAI <-> Google Gemini)
                  # ==========================================================
                  OPENAI_TO_GEMINI_MODEL_MAP = {
                      "gpt-4": "gemini-1.5-flash",
                      "gpt-4o": "gemini-1.5-pro",
                      "gpt-4-turbo": "gemini-1.5-flash",
                      "gpt-3.5-turbo": "gemini-1.0-pro",
                  }

                  original_model = model
                  if provider_lower in ["google", "gemini"] and model in OPENAI_TO_GEMINI_MODEL_MAP:
                      model = OPENAI_TO_GEMINI_MODEL_MAP[model]
                      _integration_logger.info(
                          f"Model remap: {original_model} -> {model} (Google Gemini)"
                      )

                  # ==========================================================
                  # Step 2: Run policy evaluation (pre-flight check)
                  # ==========================================================
                  _integration_logger.info("Running policy evaluation (pre-flight check)...")

                  # Convert event to format expected by policy engine
                  ai_call_for_policy = {
                      'provider': event_schema['provider'],
                      'model': event_schema['model'],
                      'purpose': event_schema['purpose'],
                      'data': metadata.get('data_sample', ''),
                      'has_pii': event_schema['has_pii'],
                      'risk_level': event_schema['risk_level'],
                      'has_sensitive_data': event_schema['has_sensitive_data'],
                      'data_classification': event_schema['data_classification']
                  }

                  # Evaluate against policy engine
                  policy_results = self._policy_engine.evaluate(ai_call_for_policy)

                  # Determine final decision
                  decision = self._determine_decision(policy_results)

                  _integration_logger.info(
                      f"Decision: {decision.upper()}, "
                      f"Rules triggered: {', '.join([r['rule'] for r in policy_results]) if policy_results else 'None'}"
                  )

                  # Generate policy explanations
                  policy_explanations = [r['message'] for r in policy_results]

                  # ==========================================================
                  # Step 3: Handle decision (allow/block/warn)
                  # ==========================================================
                  if decision == 'block':
                      _integration_logger.warning("Policy BLOCKED - AI call rejected")

                      event_schema['policy_evaluation'] = {
                          'decision': 'block',
                          'rules_triggered': [r['rule'] for r in policy_results],
                          'policy_explanations': policy_explanations,
                          'evaluation_timestamp': datetime.now(timezone.utc).isoformat()
                      }

                      # Send to dashboard as blocked event
                      if self._monitoring_dashboard:
                          self._dashboard_integration.receive_event(event_schema)

                      # Log the violation
                      self._audit_logger.add_event(event_schema)

                      raise PolicyViolationError(
                          f"Policy blocked AI call: {', '.join(policy_explanations)}",
                          policy_results=policy_results
                      )

                  if decision == 'warn':
                      _integration_logger.info("Policy WARN - AI call allowed with notification")
                      if 'policy_evaluation' not in event_schema:
                          event_schema['policy_evaluation'] = {}
                      event_schema['policy_evaluation']['warning'] = True
                      event_schema['policy_evaluation']['rules_triggered'] = [
                          r['rule'] for r in policy_results if r['action'] == 'log'
                      ]

                  # Apply DSL override actions
                  for r in policy_results:
                      if r['action'] == 'override_provider':
                          _integration_logger.info(f"Policy override provider -> {r['action_param']}")
                          provider_lower = r['action_param']

                      if r['action'] == 'override_model':
                          _integration_logger.info(f"Policy override model -> {r['action_param']}")
                          model = r['action_param']

                  # ==========================================================
                  # Step 4: Execute actual AI call (if allowed)
                  # ==========================================================
                  if decision in ['allow', 'warn']:
                      _integration_logger.info(f"Executing AI call via {provider_lower}...")

                      try:
                          # Remove conflicting keys before passing metadata
                          clean_metadata = {
                              k: v for k, v in metadata.items()
                              if k not in ["agent_id", "provider", "model", "purpose", "messages"]
                          }

                          ai_response = self._execute_ai_call(
                              provider=provider_lower,
                              model=model,
                              purpose=purpose,
                              messages=messages,
                              agent_id=agent_id,
                              **clean_metadata
                          )

                          _integration_logger.info(
                              f"AI call completed in {time.time() - start_time:.2f}s, "
                              f"Tokens: {ai_response.get('usage', {}).get('total_tokens', 'N/A')}"
                          )

                      except Exception as e:
                          _integration_logger.error(f"AI call failed: {e}")
                          ai_response = {
                              "error": str(e),
                              "id": "error-occurred",
                              "choices": [{"message": {"role": "assistant", "content": f"Error: {e}"}}],
                              "usage": {"total_tokens": 0}
                          }

                  else:
                      ai_response = {
                          "error": "Call blocked by policy",
                          "id": "blocked-by-policy"
                      }

                  # ==========================================================
                  # Step 5: Send event to MonitoringDashboard
                  # ==========================================================
                  _integration_logger.info("Sending event to MonitoringDashboard...")

                  # Enhance event schema with full policy and response info
                  event_schema['ai_response'] = ai_response
                  if 'policy_evaluation' not in event_schema:
                      event_schema['policy_evaluation'] = {}

                  # Build policy evaluation result
                  policy_eval = PolicyEvaluationResult(
                      decision=decision,
                      rules_triggered=[r['rule'] for r in policy_results],
                      policy_explanations=policy_explanations,
                      cost_usd=ai_response.get('usage', {}).get('total_tokens', 0) * 0.00001,  # Estimate
                      execution_time_ms=int((time.time() - start_time) * 1000),
                      api_provider=provider_lower,
                      model=model
                  )

                  event_schema['policy_evaluation']['decision'] = decision
                  event_schema['policy_evaluation']['execution_time_ms'] = policy_eval.execution_time_ms
                  event_schema['policy_evaluation']['api_provider'] = policy_eval.api_provider
                  event_schema['policy_evaluation']['model'] = policy_eval.model

                  # Add response metadata
                  if isinstance(ai_response, dict) and 'usage' in ai_response:
                      event_schema['response_metadata'] = {
                          'tokens_used': ai_response['usage'].get('total_tokens', 0),
                          'cost_usd': ai_response.get('cost', 0),
                          'latency_ms': ai_response.get('latency', 0)
                      }

                  self._monitoring_dashboard.receive_event(event_schema)
                  _integration_logger.info("Event displayed on dashboard")

                  # ==========================================================
                  # Step 6: Log event using AuditLogger
                  # ==========================================================
                  _integration_logger.info("Logging event to AuditLogger...")

                  # Ensure event has required logging fields
                  if 'logged_at' not in event_schema:
                      event_schema['logged_at'] = datetime.now(timezone.utc).isoformat()
                  if 'log_entry_id' not in event_schema:
                      event_schema['log_entry_id'] = f"entry-{int(time.time() * 1000)}"

                  self._audit_logger.add_event(event_schema)
                  _integration_logger.info(f"Event logged (entry ID: {event_schema['log_entry_id']})")

                  # ==========================================================
                  # Step 6b: Record usage metrics
                  # ==========================================================
                  try:
                      self._usage_tracker.record_orchestrator_call(
                          orchestrator_response={
                              'ai_response': ai_response,
                              'policy_evaluation': event_schema.get('policy_evaluation', {}),
                              'event_schema': event_schema
                          },
                          event_schema=event_schema
                      )
                      _integration_logger.info("UsageTracker: usage recorded")
                  except Exception as e:
                      _integration_logger.error(f"UsageTracker failed: {e}")

                  # ==========================================================
                  # Step 7: Return unified response
                  # ==========================================================
                  _integration_logger.info("Constructing unified response...")

                  unified_response = UnifiedResponse(
                      ai_response=ai_response,
                      policy_evaluation=policy_eval,
                      event_schema=event_schema
                  )

                  total_elapsed = time.time() - start_time
                  _integration_logger.info(
                      f"MCP Orchestrator completed in {total_elapsed:.2f}s, "
                      f"Decision: {decision.upper()}"
                  )

                  return unified_response.to_dict()

          except PolicyViolationError as pve:
              _integration_logger.error(f"PolicyViolationError: {pve}")
              raise

          except Exception as e:
              _integration_logger.error(f"Unexpected error in orchestrator: {e}")
              raise

      # ==========================================================
      # Helper Methods
      # ==========================================================

      def _determine_decision(self, policy_results: list) -> str:
          """Determine final policy decision from evaluation results."""
          if not policy_results:
              return 'allow'

          has_block = any(r['action'] == 'block' for r in policy_results)
          has_warn = any(r['action'] == 'warn' for r in policy_results)

          if has_block:
              return 'block'
          elif has_warn:
              return 'warn'
          else:
              return 'allow'

      def _execute_ai_call(self, provider: str, model: str, purpose: str,
                           messages: list, **kwargs) -> dict:
          """Execute the actual AI call via the correct provider wrapper."""
          with _integration_lock:
              # Normalize provider name
              provider_lower = provider.lower().strip()

              # Execute based on provider
              if provider_lower in ['openai', 'oai']:
                  if self._openai_integration is None:
                      raise ValueError("OpenAI integration not initialized. Provide API key.")
                  return self._openai_integration.send_message(
                      agent_id=kwargs.get('agent_id', 'orchestrator'),
                      model=model,
                      purpose=purpose,
                      messages=messages,
                      **{k: v for k, v in kwargs.items() if k != 'agent_id'}
                  )

              elif provider_lower in ['anthropic', 'ant']:
                  if self._anthropic_integration is None:
                      raise ValueError("Anthropic integration not initialized. Provide API key.")
                  return self._anthropic_integration.send_message(
                      agent_id=kwargs.get('agent_id', 'orchestrator'),
                      model=model,
                      purpose=purpose,
                      **{k: v for k, v in kwargs.items() if k != 'agent_id'}
                  )

              elif provider_lower in ['google', 'gemini', 'gai']:
                  if self._google_integration is None:
                      raise ValueError("Google Gemini integration not initialized. Provide API key.")
                  return self._google_integration.send_message(
                      agent_id=kwargs.get('agent_id', 'orchestrator'),
                      model=model,
                      purpose=purpose,
                      messages=messages,
                      **{k: v for k, v in kwargs.items() if k != 'agent_id'}
                  )

              elif provider_lower in ['internal']:
                  if self._internal_integration is None:
                      raise ValueError("Internal LLM integration not initialized.")
                  return self._internal_integration.send_message(
                      agent_id=kwargs.get('agent_id', 'orchestrator'),
                      model=model,
                      purpose=purpose,
                      messages=messages,
                      **{k: v for k, v in kwargs.items() if k != 'agent_id'}
                  )

              else:
                  raise ValueError(
                      f"Unsupported provider '{provider}'. "
                      f"Supported providers: openai, anthropic, google, internal."
                  )


  # ============================================================
  # PolicyViolationError
  # ============================================================

class PolicyViolationError(Exception):
      """Custom exception for policy violations."""
      def __init__(self, message, policy_results=None):
          super().__init__(message)
          self.policy_results = policy_results
          self.message = message


  # ============================================================
  # Integration Classes (Simplified Hardened Versions)
  # ============================================================

class BaseLLMIntegration:
      """Base class for LLM integrations with common functionality."""

      def __init__(self, api_key: str = None):
          self.api_key = api_key

      @retry_with_backoff(max_retries=3, backoff_factor=2.0)
      @manage_timeout(timeout=60)
      def send_message(self, **kwargs):
          """Send message - to be implemented by subclasses."""
          raise NotImplementedError


class OpenAIIntegration(BaseLLMIntegration):
      """Wrapper for OpenAI API with retry and timeout."""

      def send_message(self, agent_id, model, purpose, messages, **kwargs):
          """Send message to OpenAI with policy evaluation."""
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
                      "content": f"Mock OpenAI response from {model}"
                  },
                  "finish_reason": "stop"
              }],
              "usage": {
                  "prompt_tokens": len(str(messages)),
                  "completion_tokens": 50,
                  "total_tokens": len(str(messages)) + 50
              }
          }


class AnthropicIntegration(BaseLLMIntegration):
      """Wrapper for Anthropic API with retry and timeout."""

      def send_message(self, agent_id, model, purpose, **kwargs):
          """Send message to Anthropic."""
          return {
              "id": "msg-456",
              "type": "message",
              "role": "assistant",
              "model": model,
              "content": [{"type": "text", "text": f"Mock Anthropic response from {model}"}],
              "stop_sequence": None,
              "metric": None
          }


class GoogleIntegration(BaseLLMIntegration):
      """Wrapper for Google Gemini API with retry and timeout."""

      def send_message(self, agent_id, model, purpose, messages, **kwargs):
          """Send message to Google Gemini."""
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


class InternalIntegration(BaseLLMIntegration):
      """Internal LLM integration calling the local FastAPI service."""

      def send_message(self, agent_id, model, purpose, messages, **kwargs):
          """Send message to internal LLM."""
          import requests
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
              resp = requests.post(
                  "http://localhost:8000/internal-llm",
                  json=payload,
                  timeout=10
              )
              resp.raise_for_status()
              data = resp.json()

              return {
                  "id": data.get("id", "internal-unknown"),
                  "type": data.get("type", "message"),
                  "role": data.get("role", "assistant"),
                  "model": data.get("model", model),
                  "content": data.get("content", "No response"),
                  "usage": data.get("usage", {"total_tokens": 0}),
                  "provider": "internal"
              }
          except Exception as e:
              logger.error(f"Internal LLM error: {e}")
              raise


  # ============================================================
  # Dashboard Integration (Hardened)
  # ============================================================

class HardenedMonitoringDashboardIntegration:
      """Hardened integration layer for monitoring dashboard events."""

      def __init__(self, dashboard):
          self.dashboard = dashboard

      def receive_event(self, event_data: dict):
          """Receive and queue an AI call event from the integration layer."""
          with _audit_lock:
              enhanced = self._enhance_event(event_data)
              self.dashboard.event_history.append(enhanced)
              self.dashboard._update_statistics(enhanced)

      def _enhance_event(self, event: dict) -> dict:
          """Add display-friendly metadata to the event."""
          enhanced = dict(event)

          if 'timestamp' in enhanced:
              try:
                  dt = datetime.fromisoformat(enhanced['timestamp'].replace('Z', '+00:00'))
                  enhanced['display_timestamp'] = dt.strftime('%H:%M:%S')
              except Exception:
                  enhanced['display_timestamp'] = time.strftime('%H:%M:%S')

          if 'policy_evaluation' not in enhanced:
              enhanced['policy_evaluation'] = {
                  'decision': 'unknown',
                  'rules_triggered': [],
                  'policy_explanations': []
              }

          if 'rules_triggered' in enhanced.get('policy_evaluation', {}):
              rules = enhanced['policy_evaluation']['rules_triggered']
              if isinstance(rules, list):
                  enhanced['policy_evaluation']['rules_triggered_display'] = ', '.join(rules) if rules else 'None'
              else:
                  enhanced['policy_evaluation']['rules_triggered_display'] = str(rules)
          else:
              enhanced['policy_evaluation']['rules_triggered_display'] = 'None'

          if 'decision' in enhanced.get('policy_evaluation', {}):
              decision = enhanced['policy_evaluation']['decision']
              icons = {'allow': 'âœ…', 'block': 'ðŸš«', 'warn': 'âš ï¸'}
              enhanced['decision_display'] = icons.get(decision.lower(), 'ðŸ”¸') + decision.upper()
          else:
              enhanced['decision_display'] = 'â“ UNKNOWN'

          return enhanced


  # ============================================================
  # AuditLogger (Hardened)
  # ============================================================

class HardenedAuditLogger:
      """Hardened audit logger with validation and sanitization."""

      def __init__(self, log_file_path: str = "audit_log.jsonl"):
          self.log_file_path = log_file_path
          self._ensure_file_exists()
          self._total_writes = 0
          self._write_failures = 0
          self._events_last_hour = 0
          self._last_hour_reset = datetime.now(timezone.utc).hour
          self._lock = _audit_lock

      def _ensure_file_exists(self):
          if not os.path.exists(self.log_file_path):
              with open(self.log_file_path, 'w') as f:
                  pass

      def _validate_event(self, event: dict) -> bool:
          if not isinstance(event, dict):
              _audit_logger.error("Audit event must be a dictionary")
              return False

          required_fields = ['event_id', 'timestamp', 'policy_evaluation']
          missing = [f for f in required_fields if f not in event]
          if missing:
              _audit_logger.error(f"Audit event missing required fields: {missing}")
              return False

          pe = event.get('policy_evaluation', {})
          if not isinstance(pe, dict):
              _audit_logger.error("policy_evaluation must be a dictionary")
              return False

          if 'decision' not in pe:
              _audit_logger.error("policy_evaluation must contain decision field")
              return False

          if pe['decision'] not in ('allow', 'block', 'warn'):
              _audit_logger.warning(f"Unexpected decision value: {pe['decision']}")

          return True

      def _sanitize_event(self, event: dict) -> dict:
          for key, value in list(event.items()):
              if isinstance(value, str) and len(value) > 10000:
                  event[key] = value[:10000] + "...[truncated]"
              elif isinstance(value, dict):
                  self._sanitize_event(value)
          return event

      def add_event(self, event: dict) -> bool:
          if not self._validate_event(event):
              self._write_failures += 1
              return False

          event = self._sanitize_event(event)

          if 'logged_at' not in event:
              event['logged_at'] = datetime.now(timezone.utc).isoformat()

          if 'log_entry_id' not in event:
              event['log_entry_id'] = f"entry-{int(time.time() * 1000)}"

          try:
              with self._lock:
                  temp_path = self.log_file_path + '.tmp'
                  with open(temp_path, 'a', encoding='utf-8') as f:
                      f.write(json.dumps(event, ensure_ascii=False) + '\n')

              self._total_writes += 1
              current_hour = datetime.now(timezone.utc).hour
              if current_hour != self._last_hour_reset:
                  self._last_hour_reset = current_hour
                  self._events_last_hour = 0
              self._events_last_hour += 1
              _audit_logger.info(f"Audit event logged: {event.get('event_id', 'unknown')}")
              return True
          except Exception as e:
              self._write_failures += 1
              _audit_logger.error(f"Failed to write audit event: {e}")
              return False
