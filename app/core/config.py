import boto3
from botocore.config import Config
from redis.asyncio import Redis

from app.core.settings import get_settings

settings = get_settings()

redis = Redis(
    host=settings.redis_host,
    port=settings.redis_port,
    db=settings.redis_db,
    password=settings.redis_password,
    ssl=settings.redis_ssl,
    decode_responses=True,
)

# Dedicated client for FastAPICache: `redis` above decodes responses to `str`,
# but fastapi-cache2's JsonCoder calls `.decode()` on the raw bytes it gets
# back from Redis, so it needs a client with `decode_responses=False`.
cache_redis = Redis(
    host=settings.redis_host,
    port=settings.redis_port,
    db=settings.redis_db,
    password=settings.redis_password,
    ssl=settings.redis_ssl,
    decode_responses=False,
)

s3_client = boto3.client(
    "s3",
    endpoint_url=settings.s3_endpoint_url,
    aws_access_key_id=settings.s3_access_key_id,
    aws_secret_access_key=settings.s3_secret_access_key,
    region_name=settings.s3_region,
    config=Config(
        s3={"addressing_style": "path"},
        retries={"max_attempts": 3},
        max_pool_connections=50,
    ),
)
