# -*- coding: utf-8 -*-
"""
Production Configuration for MCP Control‑Tower
Environment Configuration, Secrets Management, Rate Limiting,
Circuit Breakers, Logging, and Deployment Defaults.
"""

import os
import sys
import time
from pathlib import Path
from typing import Optional, Dict, Any

# Base paths
PROJECT_ROOT = Path(__file__).parent.parent
ENV_FILE = PROJECT_ROOT / ".env"
CONFIG_DIR = PROJECT_ROOT / "config"
LOG_DIR = PROJECT_ROOT / "logs"

# Ensure directories exist
CONFIG_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)

# Load environment variables from .env file
def load_env():
    """Load environment variables from .env file."""
    try:
        from dotenv import load_dotenv
        load_dotenv(ENV_FILE, override=True)
    except Exception as e:
        print(f"[ERROR] Failed to load .env file: {e}", file=sys.stderr)

# Load environment variables
load_env()

# API Keys
OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY: Optional[str] = os.getenv("ANTHROPIC_API_KEY")
GOOGLE_API_KEY: Optional[str] = os.getenv("GOOGLE_API_KEY")

# Server Configuration
HOST: str = os.getenv("HOST", "0.0.0.0")
PORT: int = int(os.getenv("PORT", "8000"))
DEBUG: bool = os.getenv("DEBUG", "False").lower() in ("true", "1", "yes")

# Security
SECRET_KEY: str = os.getenv("SECRET_KEY", "change-me-in-production")
ALLOWED_HOSTS: list = [
    host.strip() for host in os.getenv("ALLOWED_HOSTS", "").split(",") if host.strip()
]

# Logging
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE: str = str(LOG_DIR / "mcp_control_tower.log")

# Feature Flags
ENABLE_AUDIT_LOGGING: bool = os.getenv("ENABLE_AUDIT_LOGGING", "True").lower() in ("true", "1", "yes")
ENABLE_COST_TRACKING: bool = os.getenv("ENABLE_COST_TRACKING", "True").lower() in ("true", "1", "yes")
ENABLE_MONITORING: bool = os.getenv("ENABLE_MONITORING", "True").lower() in ("true", "1", "yes")

# Model Configuration
DEFAULT_PROVIDER: str = os.getenv("DEFAULT_PROVIDER", "openai")
DEFAULT_MODEL: str = os.getenv("DEFAULT_MODEL", "gpt-4")
MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "3"))
BACKOFF_FACTOR: float = float(os.getenv("BACKOFF_FACTOR", "2.0"))

# Timeout Configurations
PROVIDER_TIMEOUTS: Dict[str, int] = {
    "openai": int(os.getenv("OPENAI_TIMEOUT", "60")),
    "anthropic": int(os.getenv("ANTHROPIC_TIMEOUT", "90")),
    "google": int(os.getenv("GOOGLE_TIMEOUT", "60")),
    "internal": int(os.getenv("INTERNAL_TIMEOUT", "30")),
}

# Circuit Breaker Configurations
CIRCUIT_BREAKER_FAILURE_THRESHOLD: int = int(os.getenv("CIRCUIT_FAILURE_THRESHOLD", "5"))
CIRCUIT_BREAKER_RECOVERY_TIMEOUT: int = int(os.getenv("CIRCUIT_RECOVERY_TIMEOUT", "60"))

# Rate Limiting
RATE_LIMIT_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "100"))

# Internal state for rate limiting
_last_rate_reset = time.time()
_request_count = 0

def check_rate_limit() -> bool:
    """
    Check if the current request exceeds the rate limit.
    Returns True if allowed, False if rate limit exceeded.
    """
    global _last_rate_reset, _request_count

    now = time.time()
    elapsed = now - _last_rate_reset

    # Reset every minute
    if elapsed >= 60:
        _last_rate_reset = now
        _request_count = 0

    if _request_count >= RATE_LIMIT_PER_MINUTE:
        return False

    _request_count += 1
    return True


# Circuit Breaker State
_circuit_breaker_state: Dict[str, Dict[str, Any]] = {
    "openai": {"failures": 0, "open": False, "opened_at": None},
    "anthropic": {"failures": 0, "open": False, "opened_at": None},
    "google": {"failures": 0, "open": False, "opened_at": None},
    "internal": {"failures": 0, "open": False, "opened_at": None},
}

def record_failure(provider: str):
    """Record a failure for a provider and open circuit if threshold exceeded."""
    state = _circuit_breaker_state.get(provider)
    if not state:
        return

    state["failures"] += 1

    if state["failures"] >= CIRCUIT_BREAKER_FAILURE_THRESHOLD:
        state["open"] = True
        state["opened_at"] = time.time()

def circuit_allows(provider: str) -> bool:
    """Check if circuit breaker allows calls to this provider."""
    state = _circuit_breaker_state.get(provider)
    if not state:
        return True

    if not state["open"]:
        return True

    # Check recovery timeout
    if time.time() - state["opened_at"] >= CIRCUIT_BREAKER_RECOVERY_TIMEOUT:
        # Reset circuit
        state["open"] = False
        state["failures"] = 0
        state["opened_at"] = None
        return True

    return False


def get_health_report() -> Dict[str, Any]:
    """Return a health report for deployment readiness."""
    return {
        "host": HOST,
        "port": PORT,
        "debug": DEBUG,
        "allowed_hosts": ALLOWED_HOSTS,
        "log_level": LOG_LEVEL,
        "rate_limit_per_minute": RATE_LIMIT_PER_MINUTE,
        "provider_timeouts": PROVIDER_TIMEOUTS,
        "circuit_breaker": _circuit_breaker_state,
        "features": {
            "audit_logging": ENABLE_AUDIT_LOGGING,
            "cost_tracking": ENABLE_COST_TRACKING,
            "monitoring": ENABLE_MONITORING,
        },
    }
