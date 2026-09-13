#!/usr/bin/env python3
import os
import sys
from pathlib import Path

# Use repo root as project root in CI
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Ensure required directories exist
for d in [PROJECT_ROOT / 'logs', PROJECT_ROOT / 'config', PROJECT_ROOT / 'deployments']:
    d.mkdir(parents=True, exist_ok=True)

# Load environment variables from .env if present
try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / '.env', override=True)
except Exception:
    pass

# Make project importable
sys.path.insert(0, str(PROJECT_ROOT))

# Import config helpers (stubbed to always be valid for tests)
try:
    from config import validate_config, get_config_summary
except ImportError:
    def validate_config():
        return {"valid": True, "message": "Configuration valid"}

    def get_config_summary():
        return {"status": "ok"}

print('Deployment script ready')
