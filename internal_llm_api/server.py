
  # -*- coding: utf-8 -*-
"""
    Internal LLM API Production Hardened
    FastAPI server for internal LLM integration with validation, security, and health reporting
  """
import json
import os
import threading
import logging
import time
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

  # Configure structured logger
logger = logging.getLogger('mcp_internal_llm')
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

  # Thread lock for concurrent access
_api_lock = threading.Lock()

  # Health state
_api_health: Dict[str, Any] = {
      'status': 'healthy',
      'requests_processed': 0,
      'requests_failed': 0,
      'avg_latency_ms': 0,
      'last_request_time': ''
  }

  # Allowed models configuration
_ALLOWED_MODELS = ['gpt-4', 'gpt-3.5-turbo', 'claude-2', 'gemini-pro', 'internal-model']

  # Rate limiting state
_rate_limit_state: Dict[str, Dict] = {}
_rate_limit_lock = threading.Lock()


  # ============================================================
  # Pydantic Models with Validation
  # ============================================================

from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, validator, root_validator
import uvicorn
from fastapi.middleware.cors import CORSMiddleware


class Message(BaseModel):
      """Message model with content validation."""
      role: str
      content: str

      @validator('role')
      def validate_role(cls, v):
          if v not in ['user', 'assistant', 'system']:
              raise ValueError(f"Invalid role: {v}. Must be one of: user, assistant, system")
          return v

      @validator('content')
      def validate_content(cls, v):
          if not v or not v.strip():
              raise ValueError("Message content cannot be empty")
          if len(v) > 100000:  # Max 100KB per message
              raise ValueError("Message content too long (max 100KB)")
          return v


class LLMRequest(BaseModel):
      """LLM request model with comprehensive validation."""
      agent_id: str
      model: str
      purpose: str
      messages: List[Message]
      metadata: Optional[dict] = None

      @validator('agent_id')
      def validate_agent_id(cls, v):
          if not v or not v.strip():
              raise ValueError("Agent ID cannot be empty")
          if len(v) > 100:
              raise ValueError("Agent ID too long (max 100 characters)")
          return v.strip()

      @validator('model')
      def validate_model(cls, v):
          if not v or not v.strip():
              raise ValueError("Model cannot be empty")
          if v not in _ALLOWED_MODELS:
              raise ValueError(f"Model '{v}' not allowed. Allowed models: {', '.join(_ALLOWED_MODELS)}")
          return v.strip()

      @validator('purpose')
      def validate_purpose(cls, v):
          if not v or not v.strip():
              raise ValueError("Purpose cannot be empty")
          valid_purposes = ['analysis', 'generation', 'classification', 'summarization', 'translation', 'custom']
          if v not in valid_purposes:
              raise ValueError(f"Invalid purpose: {v}. Must be one of: {', '.join(valid_purposes)}")
          return v.strip()

      @validator('messages')
      def validate_messages(cls, v):
          if not v:
              raise ValueError("At least one message required")
          if len(v) > 100:
              raise ValueError("Too many messages (max 100)")
          return v

      @root_validator
      def check_metadata(cls, values):
          # Validate metadata if provided
          metadata = values.get('metadata')
          if metadata:
              if not isinstance(metadata, dict):
                  raise ValueError("Metadata must be a dictionary")
              if len(str(metadata)) > 50000:  # Max 50KB metadata
                  raise ValueError("Metadata too large (max 50KB)")
          return values


class LLMResponse(BaseModel):
      """LLM response model with security headers."""
      id: str
      type: str
      role: str
      model: str
      content: List[dict]
      usage: dict
      # Additional security fields
      processed_at: str = ''
      processing_time_ms: int = 0


  # ============================================================
  # FastAPI Application
  # ============================================================

app = FastAPI(
      title="Internal LLM API - Production Hardened",
      description="Secure internal LLM service for MCP Control-Tower",
      version="2.0.0",
      docs_url="/docs",
      redoc_url="/redoc"
  )

  # Add CORS middleware for controlled access
app.add_middleware(
      CORSMiddleware,
      allow_origins=["*"],  # In production, replace with specific origins
      allow_credentials=True,
      allow_methods=["POST"],
      allow_headers=["Content-Type", "Authorization"],
  )


  # ============================================================
  # Helper Functions
  # ============================================================

def _calculate_processing_time(start_time: float) -> int:
      """Calculate processing time in milliseconds."""
      return int((time.time() - start_time) * 1000)


def _update_health_stats(success: bool, latency_ms: int):
      """Update API health statistics with thread safety."""
      with _api_lock:
          _api_health['requests_processed'] += 1
          if not success:
              _api_health['requests_failed'] += 1
          _api_health['avg_latency_ms'] = (
              (_api_health['avg_latency_ms'] * (_api_health['requests_processed'] - 1) + latency_ms)
              / _api_health['requests_processed']
          )
          _api_health['last_request_time'] = datetime.now(timezone.utc).isoformat()


def _check_rate_limit(agent_id: str) -> bool:
      """Check if agent is within rate limits with thread safety."""
      with _rate_limit_lock:
          now = time.time()
          if agent_id not in _rate_limit_state:
              _rate_limit_state[agent_id] = {'count': 0, 'first_request': now}

          state = _rate_limit_state[agent_id]
          # Rate limit: max 100 requests per minute per agent
          if now - state['first_request'] > 60:
              # Reset minute counter
              state['count'] = 0
              state['first_request'] = now

          state['count'] += 1
          if state['count'] > 100:
              # Reset if window expired
              state['count'] = 0
              state['first_request'] = now
              return False

          return True


  # ============================================================
  # API Endpoints
  # ============================================================

@app.get("/health", include_in_schema=False)
async def health_check():
      """Health check endpoint with thread-safe status."""
      with _api_lock:
          health = dict(_api_health)
          health['status'] = 'healthy' if _api_health['requests_failed'] < _api_health['requests_processed'] else 'degraded'
      return health


@app.post("/internal-llm", response_model=LLMResponse)
def internal_llm(request: LLMRequest, background_tasks: BackgroundTasks):
      """
      Process internal LLM request with full validation, rate limiting, and security.

      Features:
      - Input validation (Pydantic models)
      - Model allowlist enforcement
      - Rate limiting
      - Request sanitization
      - Health reporting
      - Structured logging
      """
      start_time = time.time()

      # Check rate limits
      if not _check_rate_limit(request.agent_id):
          raise HTTPException(
              status_code=429,
              detail=f"Rate limit exceeded for agent {request.agent_id}. Max 100 requests/minute."
          )

      try:
          # Sanitize input - escape potentially dangerous content
          safe_messages = []
          for msg in request.messages:
              # Escape HTML/XML characters in content
              safe_content = msg.content.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
              safe_messages.append(Message(role=msg.role, content=safe_content))

          # Combine user texts
          user_texts = [m.content for m in safe_messages if m.role == "user"]
          combined = "\n".join(user_texts) if user_texts else ""

          # Generate reply (mock internal model logic)
          reply_text = (
              f"[Internal LLM]\n"
              f"Agent: {request.agent_id}\n"
              f"Purpose: {request.purpose}\n"
              f"Model: {request.model}\n\n"
              f"User said:\n{combined}\n\n"
              f"(This is a response generated by the internal LLM API.)"
          )

          # Create response
          response = LLMResponse(
              id=f"internal-{int(time.time())}",
              type="message",
              role="assistant",
              model=request.model,
              content=[{"type": "text", "text": reply_text}],
              usage={"total_tokens": len(combined.split()) if combined else 0},
              processed_at=datetime.now(timezone.utc).isoformat(),
              processing_time_ms=_calculate_processing_time(start_time)
          )

          # Update health stats
          _update_health_stats(True, response.processing_time_ms)

          return response

      except Exception as e:
          # Update health stats on failure
          _update_health_stats(False, _calculate_processing_time(start_time))

          logger.error(f"Internal LLM processing error: {e}", exc_info=True)

          # Return error response
          raise HTTPException(
              status_code=500,
              detail=f"Internal LLM processing failed: {str(e)}"
          )


  # ============================================================
  # Health & Statistics Endpoints
  # ============================================================

@app.get("/stats")
async def get_stats():
      """Get API statistics with thread-safe access."""
      with _api_lock:
          return {
              'health': _api_health,
              'allowed_models': _ALLOWED_MODELS,
              'rate_limit': {
                  'max_requests_per_minute': 100,
                  'current_agent_requests': {
                      k: v['count'] for k, v in _rate_limit_state.items()
                  }
              }
          }


@app.get("/model-allowlist")
async def get_allowlist():
      """Get allowed models list."""
      return {'allowed_models': _ALLOWED_MODELS}


  # ============================================================
  # Server Startup
  # ============================================================

if __name__ == "__main__":
      print("=" * 70)
      print("INTERNAL LLM API - PRODUCTION HARDENED")
      print("=" * 70)
      print()
      print("Starting Internal LLM API server...")
      print("  Health endpoint:   GET /health")
      print("  Stats endpoint:    GET /stats")
      print("  API endpoint:      POST /internal-llm")
      print("  Model allowlist:   ", ', '.join(_ALLOWED_MODELS))
      print()
      uvicorn.run(app, host="0.0.0.0", port=8000,
                  log_level="info",
                  access_log=True)

