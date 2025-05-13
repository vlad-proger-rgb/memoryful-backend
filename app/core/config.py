from pathlib import Path
from fastapi_mail import ConnectionConfig
from redis.asyncio import Redis

from app.core.settings import (
    MAIL_USERNAME,
    MAIL_PASSWORD,
    MAIL_FROM,
    MAIL_PORT, 
    MAIL_SERVER,
    MAIL_FROM_NAME,
    REDIS_HOST,
    REDIS_PORT,
    REDIS_DB,
)


conf = ConnectionConfig(
    MAIL_USERNAME=MAIL_USERNAME or "",
    MAIL_PASSWORD=MAIL_PASSWORD or "",
    MAIL_FROM=MAIL_FROM or "",
    MAIL_PORT=int(MAIL_PORT) if MAIL_PORT else 587,
    MAIL_SERVER=MAIL_SERVER or "localhost",
    MAIL_FROM_NAME=MAIL_FROM_NAME or "",
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    TEMPLATE_FOLDER=Path("app/templates/email"),
)

redis = Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    db=REDIS_DB,
    decode_responses=True,
)
