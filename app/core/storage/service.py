import logging
from typing import Any
from uuid import UUID

from botocore.exceptions import ClientError

from app.core.config import s3_client
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


class StorageService:
    """Service layer for storage operations using S3/GCS compatible API"""

    def __init__(self, client=None):
        self.client = client or s3_client

    async def ensure_bucket_exists(self) -> None:
        """Ensure the S3 bucket exists, create if necessary"""
        try:
            self.client.head_bucket(Bucket=S3_BUCKET)
        except ClientError as e:
            code = str(e.response.get("Error", {}).get("Code", ""))
            if code in {"404", "NoSuchBucket", "NotFound"}:
                params: dict[str, Any] = {"Bucket": S3_BUCKET}
                # AWS requires LocationConstraint for most regions. us-east-1 must omit it.
                if S3_REGION and S3_REGION != "us-east-1":
                    params["CreateBucketConfiguration"] = {"LocationConstraint": S3_REGION}
                self.client.create_bucket(**params)
                logger.info(f"Created bucket: {S3_BUCKET}")
                return
            logger.error(f"Failed to ensure bucket exists: {e}")
            raise

    async def generate_presigned_put(
        self, 
        user_id: UUID, 
        request: PresignPutRequest
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
        request: PresignGetRequest
    ) -> PresignGetResponse:
        """Generate presigned URL for downloading a file"""
        # Security check: ensure user can only access their own files or defaults
        if not (
            request.object_key.startswith(f"users/{user_id}/")
            or request.object_key.startswith("users/defaults/")
        ):
            logger.warning(f"Access denied for user {user_id} to object: {request.object_key}")
            raise Exception("Access denied")

        await self.ensure_bucket_exists()

        download_url = self.client.generate_presigned_url(
            ClientMethod="get_object",
            Params={
                "Bucket": S3_BUCKET,
                "Key": request.object_key,
            },
            HttpMethod="GET",
            ExpiresIn=60 * 5,  # 5 minutes
        )

        download_url = to_public_url(download_url)
        logger.info(f"Generated presigned GET URL for user {user_id}: {request.object_key}")

        return PresignGetResponse(download_url=download_url)
