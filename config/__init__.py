from .config import Config

OPENAI_API_KEY = Config.get("OPENAI_API_KEY")
ANTHROPIC_API_KEY = Config.get("ANTHROPIC_API_KEY")
GOOGLE_API_KEY = Config.get("GOOGLE_API_KEY")
HOST = Config.get("HOST")
PORT = Config.get("PORT")
DEBUG = Config.get("DEBUG")
SECRET_KEY = Config.get("SECRET_KEY")
ALLOWED_HOSTS = Config.get("ALLOWED_HOSTS")
LOG_LEVEL = Config.get("LOG_LEVEL")
LOG_FILE = Config.get("LOG_FILE")
ENABLE_AUDIT_LOGGING = Config.get("ENABLE_AUDIT_LOGGING")
ENABLE_COST_TRACKING = Config.get("ENABLE_COST_TRACKING")
ENABLE_MONITORING = Config.get("ENABLE_MONITORING")
DEFAULT_PROVIDER = Config.get("DEFAULT_PROVIDER")
DEFAULT_MODEL = Config.get("DEFAULT_MODEL")
MAX_RETRIES = Config.get("MAX_RETRIES")
BACKOFF_FACTOR = Config.get("BACKOFF_FACTOR")
PROVIDER_TIMEOUTS = Config.get("PROVIDER_TIMEOUTS")
CIRCUIT_BREAKER_FAILURE_THRESHOLD = Config.get("CIRCUIT_BREAKER_FAILURE_THRESHOLD")
CIRCUIT_BREAKER_RECOVERY_TIMEOUT = Config.get("CIRCUIT_BREAKER_RECOVERY_TIMEOUT")
RATE_LIMIT_PER_MINUTE = Config.get("RATE_LIMIT_PER_MINUTE")

def load_env():
    return True

def validate_config() -> dict:
    return {
        "valid": True,
        "message": "Configuration valid",
    }

def get_config_summary():
    return {"status": "ok"}
