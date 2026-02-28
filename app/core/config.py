from pathlib import Path
from fastapi_mail import ConnectionConfig
from redis.asyncio import Redis
import boto3
from botocore.config import Config

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
    S3_ACCESS_KEY_ID,
    S3_ENDPOINT_URL,
    S3_REGION,
    S3_SECRET_ACCESS_KEY,
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

s3_client = boto3.client(
    "s3",
    endpoint_url=S3_ENDPOINT_URL,
    aws_access_key_id=S3_ACCESS_KEY_ID,
    aws_secret_access_key=S3_SECRET_ACCESS_KEY,
    region_name=S3_REGION,
    config=Config(
        s3={"addressing_style": "path"},
        retries={'max_attempts': 3},
        max_pool_connections=50,
    )
)
