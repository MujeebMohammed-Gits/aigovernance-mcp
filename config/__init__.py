
#### FILE 3: config/__init__.py — Configuration Package Initializer


# -*- coding: utf-8 -*-
"""
Configuration Package Initializer
Exposes production configuration on import.
"""
from .config import (
# API Keys
OPENAI_API_KEY,
ANTHROPIC_API_KEY,
GOOGLE_API_KEY,
# Server config
HOST,
PORT,
DEBUG,
# Security
SECRET_KEY,
ALLOWED_HOSTS,
# Logging
LOG_LEVEL,
LOG_FILE,
# Features
ENABLE_AUDIT_LOGGING,
ENABLE_COST_TRACKING,
ENABLE_MONITORING,
# Models
DEFAULT_PROVIDER,
DEFAULT_MODEL,
MAX_RETRIES,
BACKOFF_FACTOR,
# Timeouts
PROVIDER_TIMEOUTS,
# Circuit breakers
CIRCUIT_BREAKER_FAILURE_THRESHOLD,
CIRCUIT_BREAKER_RECOVERY_TIMEOUT,
# Rate limiting
RATE_LIMIT_PER_MINUTE,
# Validation functions
validate_config,
get_config_summary,
)
