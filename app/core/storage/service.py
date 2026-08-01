import asyncio
import logging
from typing import Any, Iterable
from uuid import UUID

from botocore.exceptions import ClientError

from app.core.config import s3_client, cache_redis
from app.core.settings import S3_BUCKET, S3_REGION
from app.core.storage.utils import (
    build_object_key,
    to_public_url,
    validate_content_type,
)
from app.schemas.storage import (
    PresignGetRequest,
    PresignPutRequest,
    PresignGetResponse,
    PresignPutResponse,
)

logger = logging.getLogger(__name__)

# Long-lived on purpose: the browser caches against the full URL including the
# signature, so a short expiry turns every re-signing into a cache miss and
# defeats the `immutable` header set below.
PRESIGNED_GET_EXPIRES_IN = 60 * 60 * 12
# Half the lifetime, so a URL served at the end of the cache window still has
# hours of validity left.
PRESIGNED_GET_CACHE_TTL = PRESIGNED_GET_EXPIRES_IN // 2


class StorageService:
    """Service layer for storage operations using S3/GCS compatible API"""

    def __init__(self, client=None):
        self.client = client or s3_client
        # Bucket existence rarely changes; avoid a `head_bucket` round trip
        # to S3/GCS on every single presign request.
        self._bucket_verified = False

    async def ensure_bucket_exists(self) -> None:
        """Ensure the S3 bucket exists, create if necessary"""
        if self._bucket_verified:
            return
        try:
            await asyncio.to_thread(self.client.head_bucket, Bucket=S3_BUCKET)
            self._bucket_verified = True
        except ClientError as e:
            code = str(e.response.get("Error", {}).get("Code", ""))
            if code in {"404", "NoSuchBucket", "NotFound"}:
                params: dict[str, Any] = {"Bucket": S3_BUCKET}
                # AWS requires LocationConstraint for most regions. us-east-1 must omit it.
                if S3_REGION and S3_REGION != "us-east-1":
                    params["CreateBucketConfiguration"] = {"LocationConstraint": S3_REGION}
                await asyncio.to_thread(self.client.create_bucket, **params)
                logger.info(f"Created bucket: {S3_BUCKET}")
                self._bucket_verified = True
                return
            logger.error(f"Failed to ensure bucket exists: {e}")
            raise

    async def generate_presigned_put(
        self, 
        user_id: UUID, 
        request: PresignPutRequest,
    ) -> PresignPutResponse:
        """Generate presigned URL for uploading a file"""
        await self.ensure_bucket_exists()

        validate_content_type(request.intent, request.content_type)
        object_key = build_object_key(user_id, request.model_dump())

        upload_url = self.client.generate_presigned_url(
            ClientMethod="put_object",
            Params={
                "Bucket": S3_BUCKET,
                "Key": object_key,
                "ContentType": request.content_type,
            },
            HttpMethod="PUT",
            ExpiresIn=60 * 5,  # 5 minutes
        )

        upload_url = to_public_url(upload_url)
        logger.info(f"Generated presigned PUT URL for user {user_id}: {object_key}")

        return PresignPutResponse(upload_url=upload_url, object_key=object_key)

    async def generate_presigned_get(
        self, 
        user_id: UUID, 
        request: PresignGetRequest,
    ) -> PresignGetResponse:
        """Generate presigned URL for downloading a file"""
        if not request.object_key.startswith(f"users/{user_id}/"):
            logger.warning(f"Access denied for user {user_id} to object: {request.object_key}")
            raise Exception("Access denied")

        cache_key = f"presign_get:{request.object_key}"
        cached_url = await cache_redis.get(cache_key)
        if cached_url is not None:
            return PresignGetResponse(download_url=cached_url.decode())

        await self.ensure_bucket_exists()

        download_url = self.client.generate_presigned_url(
            ClientMethod="get_object",
            Params={
                "Bucket": S3_BUCKET,
                "Key": request.object_key,
                # Safe because object keys embed a random asset id, so a key is
                # never overwritten with different content.
                "ResponseCacheControl": "private, max-age=2592000, immutable",
            },
            HttpMethod="GET",
            ExpiresIn=PRESIGNED_GET_EXPIRES_IN,
        )

        download_url = to_public_url(download_url)
        logger.info(f"Generated presigned GET URL for user {user_id}: {request.object_key}")

        await cache_redis.set(cache_key, download_url, ex=PRESIGNED_GET_CACHE_TTL)
        return PresignGetResponse(download_url=download_url)

    async def resolve_url(
        self,
        user_id: UUID,
        object_key: str,
    ) -> str:
        """An object key as a presigned URL the browser can fetch."""
        result = await self.generate_presigned_get(
            user_id,
            PresignGetRequest(object_key=object_key),
        )
        return result.download_url

    async def delete_objects(
        self,
        user_id: UUID,
        object_keys: Iterable[str],
    ) -> None:
        """Remove objects the user owns, best-effort.

        Call only after the write that orphaned them has committed — deleting
        first would destroy a still-referenced object if the commit then failed.

        Never raises: the caller's write already succeeded, and a failed delete
        only leaves an orphan behind.
        """
        for object_key in object_keys:
            if not object_key.startswith(f"users/{user_id}/"):
                logger.warning(f"Refusing to delete object outside user {user_id}: {object_key}")
                continue

            try:
                # boto3 is synchronous; off-thread so a slow delete can't stall
                # the event loop. Removing a large object can take tens of seconds.
                await asyncio.to_thread(
                    self.client.delete_object, Bucket=S3_BUCKET, Key=object_key
                )
            except ClientError:
                logger.exception(f"Failed to delete object: {object_key}")
                continue

            await cache_redis.delete(f"presign_get:{object_key}")
            logger.info(f"Deleted orphaned object for user {user_id}: {object_key}")
