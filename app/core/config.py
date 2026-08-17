from typing import TYPE_CHECKING

import boto3
from botocore.config import Config
from redis.asyncio import Redis

from app.core.settings import get_settings

if TYPE_CHECKING:
    from mypy_boto3_s3.client import S3Client

settings = get_settings()

redis = Redis(
    host=settings.redis_host,
    port=settings.redis_port,
    db=settings.redis_db,
    password=settings.redis_password,
    ssl=settings.redis_ssl,
    decode_responses=True,
)

# FastAPICache needs raw bytes, not decoded strings
cache_redis = Redis(
    host=settings.redis_host,
    port=settings.redis_port,
    db=settings.redis_db,
    password=settings.redis_password,
    ssl=settings.redis_ssl,
    decode_responses=False,
)


def _build_s3_client(endpoint_url: str) -> "S3Client":
    return boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=settings.s3_access_key_id,
        aws_secret_access_key=settings.s3_secret_access_key,
        region_name=settings.s3_region,
        config=Config(
            # Pinned to SigV4: MinIO otherwise falls back to SigV2, which doesn't sign host/headers
            signature_version="s3v4",
            s3={"addressing_style": "path"},
            retries={"max_attempts": 3},
            max_pool_connections=50,
        ),
    )


s3_client = _build_s3_client(settings.s3_endpoint_url)

# SigV4 signs Host header, so presigned URLs are host-specific
s3_presign_client = (
    s3_client
    if settings.s3_public_base_url in ("", settings.s3_endpoint_url)
    else _build_s3_client(settings.s3_public_base_url)
)
