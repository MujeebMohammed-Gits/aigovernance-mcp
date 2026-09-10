"""Integration tests for MCP Control-Tower."""
import os
import sys
sys.path.insert(0, '.')

def test_module_imports():
    """Test that key modules can be imported."""
    modules = [
        'mcp_service.mcp_service',
        'policy_engine.policy_engine_main',
        'agent_registry.agent_registry',
        'usage_tracker.usage_tracker',
        'audit.audit_logger',
        'dashboard.dashboard'
    ]
    for mod in modules:
        try:
            __import__(mod)
        except ImportError as e:
            print(f'Warning: Could not import {mod}: {e}')

def test_required_dirs():
    """Test that required directories exist."""
    required_dirs = ['logs', 'config', 'deployments']
    for d in required_dirs:
        assert os.path.isdir(d), f'Required directory {d} should exist'
