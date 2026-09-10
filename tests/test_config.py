"""Configuration tests for MCP Control-Tower."""
import os
import sys
sys.path.insert(0, '.')

def test_env_file_exists():
    """Test that .env file exists."""
    assert os.path.exists('.env'), '.env file should exist'

def test_required_keys_present():
    """Test that required API keys are configured."""
    from config import load_env, validate_config
    load_env()
    config = validate_config()
    assert config['valid'], f'Configuration invalid: {config["message"]}'

def test_config_summary():
    """Test that config summary can be retrieved."""
    from config import get_config_summary
    summary = get_config_summary()
    assert summary is not None, 'Config summary should not be None'
