from redis.asyncio import Redis
import boto3
from botocore.config import Config

from app.core.settings import (
    REDIS_HOST,
    REDIS_PORT,
    REDIS_DB,
    REDIS_PASSWORD,
    REDIS_SSL,
    S3_ACCESS_KEY_ID,
    S3_ENDPOINT_URL,
    S3_REGION,
    S3_SECRET_ACCESS_KEY,
)

redis = Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    db=REDIS_DB,
    password=REDIS_PASSWORD,
    ssl=REDIS_SSL,
    decode_responses=True,
)

# Dedicated client for FastAPICache: `redis` above decodes responses to `str`,
# but fastapi-cache2's JsonCoder calls `.decode()` on the raw bytes it gets
# back from Redis, so it needs a client with `decode_responses=False`.
cache_redis = Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    db=REDIS_DB,
    password=REDIS_PASSWORD,
    ssl=REDIS_SSL,
    decode_responses=False,
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
