import os
from dotenv import load_dotenv

from app.core.utils import get_secret

load_dotenv()


# GCP Configuration
GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID")
USE_SECRET_MANAGER = os.getenv("USE_SECRET_MANAGER", "false").lower() == "true"

# Environment
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
SEED_DB_ON_EMPTY = os.getenv("SEED_DB_ON_EMPTY", "false").lower() == "true"

# Postgres
POSTGRES_USER = get_secret("POSTGRES_USER") or os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = get_secret("POSTGRES_PASSWORD") or os.getenv("POSTGRES_PASSWORD")
POSTGRES_HOST = get_secret("POSTGRES_HOST") or os.getenv("POSTGRES_HOST")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", 5432)
POSTGRES_DB = os.getenv("POSTGRES_DB", "memoryful")
POSTGRES_SSLMODE = os.getenv("POSTGRES_SSLMODE", "require")

MAIN_DATABASE_URL = (
    f"postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}"
    f"@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
)

# Token
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
REFRESH_TOKEN_EXPIRE_MINUTES = int(os.getenv("REFRESH_TOKEN_EXPIRE_MINUTES", str(60 * 24 * 7)))
ACCESS_SECRET_KEY = str(os.getenv("ACCESS_SECRET_KEY"))
REFRESH_SECRET_KEY = str(os.getenv("REFRESH_SECRET_KEY"))
ALGORITHM = "HS256"

# Verification code
VERIFICATION_CODE_EXPIRE_MINUTES = 5
VERIFICATION_CODE_LENGTH = 6

# RabbitMQ
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", 5672))
RABBITMQ_USER = os.getenv("RABBITMQ_DEFAULT_USER", "guest")
RABBITMQ_PASS = os.getenv("RABBITMQ_DEFAULT_PASS", "guest")
RABBITMQ_URL = f"amqp://{RABBITMQ_USER}:{RABBITMQ_PASS}@{RABBITMQ_HOST}:{RABBITMQ_PORT}/"

# Redis
REDIS_HOST = get_secret("REDIS_HOST") or os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_PASSWORD = get_secret("REDIS_PASSWORD") or os.getenv("REDIS_PASSWORD")
REDIS_DB = int(os.getenv("REDIS_DB", 0))
REDIS_SSL = os.getenv("REDIS_SSL", "false").lower() == "true"

# Construct Redis URL
redis_protocol = "rediss" if REDIS_SSL else "redis"
redis_auth = f"default:{REDIS_PASSWORD}@" if REDIS_PASSWORD else ""
REDIS_URL = f"{redis_protocol}://{redis_auth}{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"
if REDIS_SSL:
    REDIS_URL += "?ssl_cert_reqs=CERT_REQUIRED"

# Celery
CELERY_BROKER_URL = RABBITMQ_URL
CELERY_RESULT_BACKEND = REDIS_URL

# Mail
MAIL_USERNAME = os.getenv("MAIL_USERNAME")
MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
MAIL_FROM = os.getenv("MAIL_FROM")
MAIL_PORT = os.getenv("MAIL_PORT")
MAIL_SERVER = os.getenv("MAIL_SERVER")
MAIL_FROM_NAME = os.getenv("MAIL_FROM_NAME")

# Auth
TRUSTED_EMAILS = {
    e.strip().lower()
    for e in os.getenv("TRUSTED_EMAILS", "").split(",")
    if e.strip()
}

# CORS
_allowed_origins_raw = os.getenv('ALLOWED_ORIGINS', '')
ALLOWED_ORIGINS = [o.strip() for o in _allowed_origins_raw.split(',') if o.strip()]
if not ALLOWED_ORIGINS and ENVIRONMENT == "development":
    ALLOWED_ORIGINS = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

_allow_credentials_raw = os.getenv('ALLOW_CREDENTIALS')
if _allow_credentials_raw is None:
    ALLOW_CREDENTIALS = ENVIRONMENT == "development"
else:
    ALLOW_CREDENTIALS = _allow_credentials_raw.lower() == 'true'
ALLOWED_METHODS = os.getenv('ALLOWED_METHODS', '*').split(',')
ALLOWED_HEADERS = os.getenv('ALLOWED_HEADERS', '*').split(',')

# S3 / MinIO (now GCS-compatible) - Environment-based configuration
if ENVIRONMENT == "development":
    S3_ENDPOINT_URL = os.getenv("S3_ENDPOINT_URL", "http://localhost:9000")
    S3_ACCESS_KEY_ID = os.getenv("S3_ACCESS_KEY_ID", "minioadmin")
    S3_SECRET_ACCESS_KEY = os.getenv("S3_SECRET_ACCESS_KEY", "minioadmin")
    S3_REGION = os.getenv("S3_REGION", "us-east-1")
    S3_BUCKET = os.getenv("S3_BUCKET", "memoryful")
    S3_PUBLIC_BASE_URL = os.getenv("S3_PUBLIC_BASE_URL", "http://localhost:9000")
else:
    # Production with GCS - ensure endpoint is always set
    S3_ENDPOINT_URL = os.getenv("S3_ENDPOINT_URL", "https://storage.googleapis.com")
    S3_ACCESS_KEY_ID = get_secret("S3_ACCESS_KEY_ID") or os.getenv("S3_ACCESS_KEY_ID", "")
    S3_SECRET_ACCESS_KEY = get_secret("S3_SECRET_ACCESS_KEY") or os.getenv("S3_SECRET_ACCESS_KEY", "")
    S3_REGION = os.getenv("S3_REGION", "europe-central2")
    S3_BUCKET = os.getenv("S3_BUCKET", "memoryful")
    S3_PUBLIC_BASE_URL = os.getenv("S3_PUBLIC_BASE_URL", "https://storage.googleapis.com")

# S3 / MinIO defaults
DEFAULT_DASHBOARD_BACKGROUND = "users/defaults/workspace/dashboard_bg.jpg"
DEFAULT_DAY_BACKGROUND = "users/defaults/workspace/day_bg.jpg"
DEFAULT_SEARCH_BACKGROUND = "users/defaults/workspace/search_bg.mp4"
DEFAULT_SETTINGS_BACKGROUND = "users/defaults/workspace/settings_bg.jpg"

# Redis prefixes
# RP short for Redis Prefix
RP_LOGIN_CODE = "login_code:"
RP_BLACKLISTED_TOKEN = "blacklist:"
RP_AI_CONTEXT = "ai_context:"

# LLM Configuration
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai").strip().lower()
OPENAI_TEMPERATURE = float(os.getenv("OPENAI_TEMPERATURE", "0.4"))
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20240620")
LOCAL_LLM_BASE_URL = os.getenv("LOCAL_LLM_BASE_URL", "http://ollama:11434/v1")
LOCAL_LLM_MODEL = os.getenv("LOCAL_LLM_MODEL", "llama3.1")
LOCAL_LLM_API_KEY = os.getenv("LOCAL_LLM_API_KEY", "local")
