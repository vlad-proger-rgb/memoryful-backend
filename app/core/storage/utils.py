from typing import Any
from datetime import datetime, timezone
from urllib.parse import urlparse, urlunparse
from uuid import UUID, uuid4

from fastapi import HTTPException

from app.core.settings import S3_PUBLIC_BASE_URL
from app.enums import StorageUploadIntent


def safe_filename(filename: str) -> str:
    """Make filename safe for storage by replacing path separators"""
    return filename.replace("/", "_").replace("\\", "_")


def day_parts(day_timestamp: int) -> tuple[str, str, str]:
    """Extract year, month, day from timestamp"""
    dt = datetime.fromtimestamp(day_timestamp, tz=timezone.utc)
    return (dt.strftime("%Y"), dt.strftime("%m"), dt.strftime("%d"))


def build_object_key(user_id: UUID, body: dict[str, Any]) -> str:
    """Build S3 object key based on upload intent and parameters"""
    safe_name = safe_filename(body["filename"])
    asset_id = uuid4().hex

    if body["intent"] == StorageUploadIntent.AVATAR:
        return f"users/{user_id}/avatars/{asset_id}_{safe_name}"

    if body["intent"] in (StorageUploadIntent.DAY_MAIN, StorageUploadIntent.DAY_IMAGE):
        if body.get("day_timestamp") is None:
            raise HTTPException(400, "dayTimestamp is required")
        yyyy, mm, dd = day_parts(body["day_timestamp"])
        kind = "main" if body["intent"] == StorageUploadIntent.DAY_MAIN else "images"
        return f"users/{user_id}/calendar/days/{yyyy}/{mm}/{dd}/{kind}/{asset_id}_{safe_name}"

    if body["intent"] == StorageUploadIntent.MONTH_IMAGE:
        if body.get("year") is None or body.get("month") is None:
            raise HTTPException(400, "year and month are required")
        yyyy = str(body["year"])
        mm = str(body["month"]).zfill(2)
        return f"users/{user_id}/calendar/months/{yyyy}/{mm}/{asset_id}_{safe_name}"

    if body["intent"] == StorageUploadIntent.WORKSPACE_ASSET:
        if not body.get("workspace_page_key"):
            raise HTTPException(400, "workspacePageKey is required")
        return f"users/{user_id}/workspace/pages/{body['workspace_page_key']}/{asset_id}_{safe_name}"

    raise HTTPException(400, "Invalid upload intent")


def validate_content_type(intent: StorageUploadIntent, content_type: str) -> None:
    """Validate content type based on upload intent"""
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


def to_public_url(url: str) -> str:
    """Convert internal S3 URL to public URL if configured"""
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
