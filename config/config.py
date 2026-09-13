#!/usr/bin/env python3

"""
Configuration module for MCP Control‑Tower.
Provides centralized access to environment variables and settings.
"""

import os

class Config:
    """Simple configuration loader."""

    @staticmethod
    def get(key: str, default=None):
        return os.getenv(key, default)
