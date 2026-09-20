# -*- coding: utf-8 -*-
"""
Internal LLM API - Production Hardened
FastAPI server for internal LLM integration with validation, security, and health reporting
"""

import json
import os
import threading
import logging
import time
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator, model_validator
import uvicorn

# ============================================================
# Logging
# ============================================================

logger = logging.getLogger("mcp_internal_llm")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
logger.addHandler(handler)

# ============================================================
# Global State
# ============================================================

_api_lock = threading.Lock()

_api_health: Dict[str, Any] = {
    "status": "healthy",
    "requests_processed": 0,
    "requests_failed": 0,
    "avg_latency_ms": 0,
    "last_request_time": ""
}

_ALLOWED_MODELS = ["gpt-4", "gpt-3.5-turbo", "claude-2", "gemini-pro", "internal-model"]

_rate_limit_state: Dict[str, Dict] = {}
_rate_limit_lock = threading.Lock()

# ============================================================
# Pydantic Models (Pydantic v2)
# ============================================================

class Message(BaseModel):
    role: str
    content: str

    @field_validator("role")
    def validate_role(cls, v):
        allowed = ["user", "assistant", "system"]
        if v not in allowed:
            raise ValueError(f"Invalid role: {v}. Must be one of: {allowed}")
        return v

    @field_validator("content")
    def validate_content(cls, v):
        if not v.strip():
            raise ValueError("Message content cannot be empty")
        if len(v) > 100000:
            raise ValueError("Message content too long (max 100KB)")
        return v


class LLMRequest(BaseModel):
    agent_id: str
    model: str
    purpose: str
    messages: List[Message]
    metadata: Optional[dict] = None

    @field_validator("agent_id")
    def validate_agent_id(cls, v):
        if not v.strip():
            raise ValueError("Agent ID cannot be empty")
        if len(v) > 100:
            raise ValueError("Agent ID too long (max 100 chars)")
        return v.strip()

    @field_validator("model")
    def validate_model(cls, v):
        if v not in _ALLOWED_MODELS:
            raise ValueError(f"Model '{v}' not allowed. Allowed: {', '.join(_ALLOWED_MODELS)}")
        return v.strip()

    @field_validator("purpose")
    def validate_purpose(cls, v):
        valid = ["analysis", "generation", "classification", "summarization", "translation", "custom"]
        if v not in valid:
            raise ValueError(f"Invalid purpose: {v}. Must be one of: {valid}")
        return v.strip()

    @field_validator("messages")
    def validate_messages(cls, v):
        if not v:
            raise ValueError("At least one message required")
        if len(v) > 100:
            raise ValueError("Too many messages (max 100)")
        return v

    @model_validator(mode="after")
    def validate_metadata(self):
        metadata = self.metadata
        if metadata:
            if not isinstance(metadata, dict):
                raise ValueError("Metadata must be a dictionary")
            if len(str(metadata)) > 50000:
                raise ValueError("Metadata too large (max 50KB)")
        return self


class LLMResponse(BaseModel):
    id: str
    type: str
    role: str
    model: str
    content: List[dict]
    usage: dict
    processed_at: str = ""
    processing_time_ms: int = 0

# ============================================================
# FastAPI App
# ============================================================

app = FastAPI(
    title="Internal LLM API - Production Hardened",
    description="Secure internal LLM service for MCP Control-Tower",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["POST"],
    allow_headers=["Content-Type", "Authorization"],
)

# ============================================================
# Helper Functions
# ============================================================

def _calculate_processing_time(start_time: float) -> int:
    return int((time.time() - start_time) * 1000)

def _update_health_stats(success: bool, latency_ms: int):
    with _api_lock:
        _api_health["requests_processed"] += 1
        if not success:
            _api_health["requests_failed"] += 1

        count = _api_health["requests_processed"]
        prev_avg = _api_health["avg_latency_ms"]

        _api_health["avg_latency_ms"] = (prev_avg * (count - 1) + latency_ms) / count
        _api_health["last_request_time"] = datetime.now(timezone.utc).isoformat()

def _check_rate_limit(agent_id: str) -> bool:
    with _rate_limit_lock:
        now = time.time()
        if agent_id not in _rate_limit_state:
            _rate_limit_state[agent_id] = {"count": 0, "first_request": now}

        state = _rate_limit_state[agent_id]

        if now - state["first_request"] > 60:
            state["count"] = 0
            state["first_request"] = now

        state["count"] += 1

        return state["count"] <= 100

# ============================================================
# API Endpoints
# ============================================================

@app.get("/health")
async def health_check():
    with _api_lock:
        health = dict(_api_health)
        health["status"] = (
            "healthy"
            if _api_health["requests_failed"] < _api_health["requests_processed"]
            else "degraded"
        )
    return health

@app.post("/internal-llm", response_model=LLMResponse)
def internal_llm(request: LLMRequest, background_tasks: BackgroundTasks):
    start_time = time.time()

    if not _check_rate_limit(request.agent_id):
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded for agent {request.agent_id}. Max 100 requests/minute."
        )

    try:
        safe_messages = []
        for msg in request.messages:
            safe_content = (
                msg.content.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
            )
            safe_messages.append(Message(role=msg.role, content=safe_content))

        user_texts = [m.content for m in safe_messages if m.role == "user"]
        combined = "\n".join(user_texts) if user_texts else ""

        reply_text = (
            f"[Internal LLM]\n"
            f"Agent: {request.agent_id}\n"
            f"Purpose: {request.purpose}\n"
            f"Model: {request.model}\n\n"
            f"User said:\n{combined}\n\n"
            f"(This is a response generated by the internal LLM API.)"
        )

        response = LLMResponse(
            id=f"internal-{int(time.time())}",
            type="message",
            role="assistant",
            model=request.model,
            content=[{"type": "text", "text": reply_text}],
            usage={"total_tokens": len(combined.split())},
            processed_at=datetime.now(timezone.utc).isoformat(),
            processing_time_ms=_calculate_processing_time(start_time)
        )

        _update_health_stats(True, response.processing_time_ms)
        return response

    except Exception as e:
        _update_health_stats(False, _calculate_processing_time(start_time))
        logger.error(f"Internal LLM processing error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal LLM processing failed: {str(e)}")

# ============================================================
# Server Startup
# ============================================================

if __name__ == "__main__":
    uvicorn.run(
        "internal_llm_api.server:app",
        host="0.0.0.0",
        port=8000,
        log_level="info",
        access_log=True,
        reload=False
    )
