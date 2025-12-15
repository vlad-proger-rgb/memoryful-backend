from datetime import datetime, timezone
from typing import Annotated
from urllib.parse import urlparse, urlunparse
from uuid import UUID, uuid4

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from fastapi import APIRouter, Depends, HTTPException

from app.core.deps import get_current_user
from app.core.settings import (
    S3_ACCESS_KEY_ID,
    S3_BUCKET,
    S3_ENDPOINT_URL,
    S3_PUBLIC_BASE_URL,
    S3_REGION,
    S3_SECRET_ACCESS_KEY,
)
from app.enums import StorageUploadIntent
from app.schemas import (
    Msg,
    PresignGetRequest,
    PresignGetResponse,
    PresignPutRequest,
    PresignPutResponse,
)


router = APIRouter(
    prefix="/storage",
    tags=["Storage"],
)


def _s3_client():
    return boto3.client(
        "s3",
        endpoint_url=S3_ENDPOINT_URL,
        aws_access_key_id=S3_ACCESS_KEY_ID,
        aws_secret_access_key=S3_SECRET_ACCESS_KEY,
        region_name=S3_REGION,
        config=Config(s3={"addressing_style": "path"}),
    )


def _ensure_bucket_exists(s3) -> None:
    try:
        s3.head_bucket(Bucket=S3_BUCKET)
    except ClientError as e:
        code = str(e.response.get("Error", {}).get("Code", ""))
        if code in {"404", "NoSuchBucket", "NotFound"}:
            params: dict[str, object] = {"Bucket": S3_BUCKET}
            # AWS requires LocationConstraint for most regions. us-east-1 must omit it.
            if S3_REGION and S3_REGION != "us-east-1":
                params["CreateBucketConfiguration"] = {"LocationConstraint": S3_REGION}
            s3.create_bucket(**params)
            return
        raise


def _to_public_url(url: str) -> str:
    if not S3_PUBLIC_BASE_URL:
        return url

    public = urlparse(S3_PUBLIC_BASE_URL)
    if not public.scheme or not public.netloc:
        return url

    parsed = urlparse(url)
    return urlunparse(
        (
            public.scheme,
            public.netloc,
            parsed.path,
            parsed.params,
            parsed.query,
            parsed.fragment,
        )
    )


def _safe_filename(filename: str) -> str:
    return filename.replace("/", "_").replace("\\", "_")


def _day_parts(day_timestamp: int) -> tuple[str, str, str]:
    dt = datetime.fromtimestamp(day_timestamp, tz=timezone.utc)
    return (dt.strftime("%Y"), dt.strftime("%m"), dt.strftime("%d"))


def _build_object_key(user_id: UUID, body: PresignPutRequest) -> str:
    safe_name = _safe_filename(body.filename)
    asset_id = uuid4().hex

    if body.intent == StorageUploadIntent.AVATAR:
        return f"users/{user_id}/avatars/{asset_id}_{safe_name}"

    if body.intent in (StorageUploadIntent.DAY_MAIN, StorageUploadIntent.DAY_IMAGE):
        if body.day_timestamp is None:
            raise HTTPException(400, "dayTimestamp is required")
        yyyy, mm, dd = _day_parts(body.day_timestamp)
        kind = "main" if body.intent == StorageUploadIntent.DAY_MAIN else "images"
        return f"users/{user_id}/calendar/days/{yyyy}/{mm}/{dd}/{kind}/{asset_id}_{safe_name}"

    if body.intent == StorageUploadIntent.MONTH_IMAGE:
        if body.year is None or body.month is None:
            raise HTTPException(400, "year and month are required")
        yyyy = str(body.year)
        mm = str(body.month).zfill(2)
        return f"users/{user_id}/calendar/months/{yyyy}/{mm}/{asset_id}_{safe_name}"

    if body.intent == StorageUploadIntent.WORKSPACE_ASSET:
        if not body.workspace_page_key:
            raise HTTPException(400, "workspacePageKey is required")
        return f"users/{user_id}/workspace/pages/{body.workspace_page_key}/{asset_id}_{safe_name}"

    raise HTTPException(400, "Invalid upload intent")


def _validate_content_type(intent: StorageUploadIntent, content_type: str) -> None:
    if not content_type:
        raise HTTPException(400, "contentType is required")

    if intent == StorageUploadIntent.AVATAR:
        if not content_type.startswith("image/"):
            raise HTTPException(400, "Only image uploads are allowed for this intent")
        return

    if intent in (StorageUploadIntent.DAY_MAIN, StorageUploadIntent.DAY_IMAGE):
        if content_type.startswith("image/") or content_type.startswith("video/") or content_type.startswith("audio/"):
            return
        raise HTTPException(400, "Only image/video/audio uploads are allowed for days")

    if intent == StorageUploadIntent.MONTH_IMAGE:
        if content_type.startswith("image/") or content_type.startswith("video/"):
            return
        raise HTTPException(400, "Only image/video uploads are allowed for this intent")

    if intent == StorageUploadIntent.WORKSPACE_ASSET:
        if content_type.startswith("image/") or content_type.startswith("video/"):
            return
        raise HTTPException(400, "Only image/video uploads are allowed for workspace background")


@router.post("/presign-put", response_model=Msg[PresignPutResponse])
async def presign_put(
    body: PresignPutRequest,
    user_id: Annotated[UUID, Depends(get_current_user())],
) -> Msg[PresignPutResponse]:
    s3 = _s3_client()
    _ensure_bucket_exists(s3)

    _validate_content_type(body.intent, body.content_type)
    object_key = _build_object_key(user_id, body)

    upload_url = s3.generate_presigned_url(
        ClientMethod="put_object",
        Params={
            "Bucket": S3_BUCKET,
            "Key": object_key,
            "ContentType": body.content_type,
        },
        HttpMethod="PUT",
        ExpiresIn=60 * 5,
    )

    upload_url = _to_public_url(upload_url)

    return Msg(
        code=200,
        msg="Presigned URL generated",
        data=PresignPutResponse(upload_url=upload_url, object_key=object_key),
    )


@router.post("/presign-get", response_model=Msg[PresignGetResponse])
async def presign_get(
    body: PresignGetRequest,
    user_id: Annotated[UUID, Depends(get_current_user())],
) -> Msg[PresignGetResponse]:
    if not body.object_key.startswith(f"users/{user_id}/"):
        raise HTTPException(403, "Access denied")

    s3 = _s3_client()
    _ensure_bucket_exists(s3)
    download_url = s3.generate_presigned_url(
        ClientMethod="get_object",
        Params={
            "Bucket": S3_BUCKET,
            "Key": body.object_key,
        },
        HttpMethod="GET",
        ExpiresIn=60 * 5,
    )

    download_url = _to_public_url(download_url)

    return Msg(
        code=200,
        msg="Presigned URL generated",
        data=PresignGetResponse(download_url=download_url),
    )
