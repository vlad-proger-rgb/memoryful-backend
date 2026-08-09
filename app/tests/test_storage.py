"""Presigned upload and download URLs.

The security boundary here is the object key: every key is namespaced
`users/{user_id}/`, and `generate_presigned_get` refuses any key outside the
caller's own prefix. That check is the only thing standing between a user and
someone else's photos, since a presigned URL needs no further authentication.

Key construction and content-type rules are exercised directly as well as through
the API — they are pure functions and each intent has its own required fields.
"""

from collections.abc import AsyncIterator
from typing import Any
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from fastapi import HTTPException
from httpx import AsyncClient

from app.core.config import cache_redis
from app.core.storage.utils import build_object_key, is_video_key, validate_content_type
from app.enums import StorageUploadIntent, WorkspacePage

from .conftest import MakeUser


@pytest_asyncio.fixture(autouse=True)
async def _drop_presign_cache() -> AsyncIterator[None]:
    """A served presign is cached for six hours; tests must not leave those behind."""

    async def keys() -> set[str]:
        return {k async for k in cache_redis.scan_iter(match=b"presign_get:*")}

    before = await keys()
    yield
    for key in await keys() - before:
        await cache_redis.delete(key)


def _put(intent: StorageUploadIntent, **extra: object) -> dict[str, object]:
    body: dict[str, object] = {
        "intent": intent.value,
        "filename": "photo.jpg",
        "contentType": "image/jpeg",
    }
    body.update(extra)
    return body


async def test_presign_put_returns_a_key_under_the_callers_prefix(
    client: AsyncClient, auth_headers: dict[str, str], user_id: UUID
) -> None:
    response = await client.post(
        "/storage/presign-put", headers=auth_headers, json=_put(StorageUploadIntent.AVATAR)
    )
    assert response.status_code == 200, response.text

    data = response.json()["data"]
    assert data["objectKey"].startswith(f"users/{user_id}/avatars/")
    assert data["objectKey"].endswith("_photo.jpg")
    assert data["uploadUrl"].startswith("http")


async def test_presign_put_rejects_a_wrong_content_type(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    response = await client.post(
        "/storage/presign-put",
        headers=auth_headers,
        json=_put(StorageUploadIntent.AVATAR, contentType="application/pdf"),
    )
    assert response.status_code == 400


async def test_presign_put_requires_the_fields_its_intent_needs(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    # A day upload without a dayTimestamp has nowhere to go.
    response = await client.post(
        "/storage/presign-put", headers=auth_headers, json=_put(StorageUploadIntent.DAY_IMAGE)
    )
    assert response.status_code == 400
    assert "dayTimestamp" in response.json()["detail"]


async def test_presign_get_refuses_another_users_object(
    client: AsyncClient, auth_headers: dict[str, str], make_user: MakeUser
) -> None:
    stranger, _ = await make_user()
    victim_key = f"users/{stranger.id}/avatars/deadbeef_photo.jpg"

    response = await client.post(
        "/storage/presign-get", headers=auth_headers, json={"objectKey": victim_key}
    )
    assert response.status_code == 403, "a presigned URL was issued for another user's object"


async def test_presign_get_refuses_a_traversal_attempt(
    client: AsyncClient, auth_headers: dict[str, str], user_id: UUID
) -> None:
    # The check is a prefix match, so anything not starting with the caller's
    # own prefix must be refused however it is dressed up.
    for key in (
        "../../etc/passwd",
        f"../{uuid4()}/avatars/x.jpg",
        "users/../secrets.txt",
        f"x/users/{user_id}/avatars/x.jpg",
    ):
        response = await client.post(
            "/storage/presign-get", headers=auth_headers, json={"objectKey": key}
        )
        assert response.status_code == 403, f"{key!r} was accepted"


async def test_presign_get_issues_a_url_for_your_own_object(
    client: AsyncClient, auth_headers: dict[str, str], user_id: UUID
) -> None:
    own_key = f"users/{user_id}/avatars/deadbeef_photo.jpg"
    response = await client.post(
        "/storage/presign-get", headers=auth_headers, json={"objectKey": own_key}
    )
    assert response.status_code == 200, response.text
    assert response.json()["data"]["downloadUrl"].startswith("http")


async def test_presign_endpoints_need_a_token(client: AsyncClient) -> None:
    assert (
        await client.post("/storage/presign-put", json=_put(StorageUploadIntent.AVATAR))
    ).status_code == 401
    assert (
        await client.post("/storage/presign-get", json={"objectKey": "users/x/y.jpg"})
    ).status_code == 401


# --- key construction and content types, exercised directly ---


def test_every_intent_builds_a_key_inside_the_user_prefix() -> None:
    user_id = uuid4()
    cases: list[tuple[dict[str, Any], str]] = [
        ({"intent": StorageUploadIntent.AVATAR}, f"users/{user_id}/avatars/"),
        (
            {"intent": StorageUploadIntent.DAY_MAIN, "day_timestamp": 1_700_000_000},
            f"users/{user_id}/calendar/days/",
        ),
        (
            {"intent": StorageUploadIntent.DAY_IMAGE, "day_timestamp": 1_700_000_000},
            f"users/{user_id}/calendar/days/",
        ),
        (
            {"intent": StorageUploadIntent.MONTH_IMAGE, "year": 2019, "month": 4},
            f"users/{user_id}/calendar/months/2019/04/",
        ),
        (
            {
                "intent": StorageUploadIntent.WORKSPACE_ASSET,
                "workspace_page_key": WorkspacePage.DASHBOARD,
            },
            f"users/{user_id}/workspace/pages/dashboard/",
        ),
    ]
    for extra, prefix in cases:
        key = build_object_key(user_id, {"filename": "photo.jpg", **extra})
        assert key.startswith(prefix), f"{extra['intent']} -> {key}"


def test_a_filename_cannot_escape_its_directory() -> None:
    # Separators are replaced, so a crafted filename stays one path segment.
    key = build_object_key(
        uuid4(), {"filename": "../../evil.jpg", "intent": StorageUploadIntent.AVATAR}
    )
    assert "/avatars/" in key
    assert key.count("/") == 3, f"filename introduced a path segment: {key}"


@pytest.mark.parametrize(
    ("intent", "content_type", "allowed"),
    [
        (StorageUploadIntent.AVATAR, "image/png", True),
        (StorageUploadIntent.AVATAR, "video/mp4", False),
        (StorageUploadIntent.DAY_IMAGE, "video/mp4", True),
        (StorageUploadIntent.DAY_IMAGE, "audio/mpeg", True),
        (StorageUploadIntent.DAY_IMAGE, "application/pdf", False),
        (StorageUploadIntent.MONTH_IMAGE, "video/webm", True),
        (StorageUploadIntent.MONTH_IMAGE, "audio/mpeg", False),
        (StorageUploadIntent.WORKSPACE_ASSET, "image/webp", True),
        (StorageUploadIntent.WORKSPACE_ASSET, "text/html", False),
    ],
)
def test_content_type_rules_per_intent(
    intent: StorageUploadIntent, content_type: str, allowed: bool
) -> None:
    if allowed:
        validate_content_type(intent, content_type)
        return
    with pytest.raises(HTTPException) as raised:
        validate_content_type(intent, content_type)
    assert raised.value.status_code == 400


def test_an_empty_content_type_is_refused() -> None:
    with pytest.raises(HTTPException):
        validate_content_type(StorageUploadIntent.AVATAR, "")


def test_video_keys_are_recognized_case_insensitively() -> None:
    assert is_video_key("users/x/clip.MP4")
    assert is_video_key("users/x/clip.webm")
    assert not is_video_key("users/x/photo.jpg")
