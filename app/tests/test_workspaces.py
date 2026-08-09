"""Per-page workspace backgrounds.

The workspace is a sparse map: only customized pages have a row, and the client
supplies its own defaults for the rest. A PUT touches only the pages it names,
and `key=None` clears one.
"""

from collections.abc import AsyncIterator
from typing import Any
from uuid import UUID

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import CACHE_PREFIX
from app.core.config import cache_redis, redis
from app.enums import CacheNamespace, WorkspacePage
from app.models import WorkspaceBackground

from .conftest import MakeUser


@pytest_asyncio.fixture(autouse=True)
async def _drop_presign_cache() -> AsyncIterator[None]:
    async def keys() -> set[str]:
        return {k async for k in cache_redis.scan_iter(match=b"presign_get:*")}

    before = await keys()
    yield
    for key in await keys() - before:
        await cache_redis.delete(key)


def _background(user_id: UUID, name: str = "bg.jpg") -> str:
    return f"users/{user_id}/workspace/pages/dashboard/abc123_{name}"


def _put(**pages: dict[str, Any]) -> dict[str, Any]:
    return {"backgrounds": pages}


async def test_a_fresh_workspace_is_empty(
    client: AsyncClient, auth_headers: dict[str, str], user_id: UUID
) -> None:
    response = await client.get("/workspaces/me", headers=auth_headers)
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["userId"] == str(user_id)
    assert data["backgrounds"] == {}


async def test_setting_a_background_returns_it_resolved(
    client: AsyncClient, auth_headers: dict[str, str], user_id: UUID
) -> None:
    key = _background(user_id)
    response = await client.put(
        "/workspaces/me",
        headers=auth_headers,
        json=_put(dashboard={"key": key, "placeholder": "data:image/webp;base64,AA"}),
    )
    assert response.status_code == 200, response.text

    dashboard = response.json()["data"]["backgrounds"]["dashboard"]
    assert dashboard["key"] == key
    assert dashboard["placeholder"] == "data:image/webp;base64,AA"
    assert dashboard["url"].startswith("http")
    assert dashboard["isVideo"] is False


async def test_a_video_background_is_flagged(
    client: AsyncClient, auth_headers: dict[str, str], user_id: UUID
) -> None:
    response = await client.put(
        "/workspaces/me",
        headers=auth_headers,
        json=_put(dashboard={"key": _background(user_id, "clip.mp4")}),
    )
    assert response.status_code == 200, response.text
    assert response.json()["data"]["backgrounds"]["dashboard"]["isVideo"] is True


async def test_a_put_leaves_pages_it_does_not_name_alone(
    client: AsyncClient, auth_headers: dict[str, str], user_id: UUID
) -> None:
    await client.put(
        "/workspaces/me", headers=auth_headers, json=_put(dashboard={"key": _background(user_id)})
    )
    response = await client.put(
        "/workspaces/me",
        headers=auth_headers,
        json=_put(settings={"key": _background(user_id, "other.jpg")}),
    )
    assert response.status_code == 200, response.text

    backgrounds = response.json()["data"]["backgrounds"]
    assert set(backgrounds) == {"dashboard", "settings"}


async def test_a_null_key_clears_that_page(
    client: AsyncClient, db: AsyncSession, auth_headers: dict[str, str], user_id: UUID
) -> None:
    await client.put(
        "/workspaces/me", headers=auth_headers, json=_put(dashboard={"key": _background(user_id)})
    )

    cleared = await client.put(
        "/workspaces/me", headers=auth_headers, json=_put(dashboard={"key": None})
    )
    assert cleared.status_code == 200, cleared.text
    assert cleared.json()["data"]["backgrounds"] == {}

    row = await db.scalar(
        select(WorkspaceBackground).where(
            WorkspaceBackground.user_id == user_id,
            WorkspaceBackground.page == WorkspacePage.DASHBOARD.value,
        )
    )
    assert row is None, "clearing a page left its row behind"


async def test_replacing_a_background_updates_the_same_row(
    client: AsyncClient, db: AsyncSession, auth_headers: dict[str, str], user_id: UUID
) -> None:
    await client.put(
        "/workspaces/me", headers=auth_headers, json=_put(dashboard={"key": _background(user_id)})
    )
    replacement = _background(user_id, "second.jpg")
    await client.put(
        "/workspaces/me", headers=auth_headers, json=_put(dashboard={"key": replacement})
    )

    rows = (
        await db.scalars(select(WorkspaceBackground).where(WorkspaceBackground.user_id == user_id))
    ).all()
    assert len(rows) == 1, "replacing a background created a second row"
    assert rows[0].object_key == replacement


async def test_a_workspace_is_scoped_to_its_owner(
    client: AsyncClient, db: AsyncSession, make_user: MakeUser
) -> None:
    owner, owner_headers = await make_user()
    _, other_headers = await make_user()

    db.add(
        WorkspaceBackground(
            user_id=owner.id,
            page=WorkspacePage.DASHBOARD.value,
            object_key=_background(owner.id),
        )
    )
    await db.flush()

    theirs = await client.get("/workspaces/me", headers=other_headers)
    assert theirs.status_code == 200, theirs.text
    assert theirs.json()["data"]["backgrounds"] == {}

    mine = await client.get("/workspaces/me", headers=owner_headers)
    assert set(mine.json()["data"]["backgrounds"]) == {"dashboard"}


async def test_updating_clears_the_workspaces_cache(
    client: AsyncClient, auth_headers: dict[str, str], user_id: UUID
) -> None:
    key = f"{CACHE_PREFIX}:{CacheNamespace.workspaces}:{user_id}:testdigest"
    try:
        await redis.set(key, "cached", ex=60)
        await client.put(
            "/workspaces/me",
            headers=auth_headers,
            json=_put(dashboard={"key": _background(user_id)}),
        )
        assert not await redis.exists(key), "update left the workspaces cache stale"
    finally:
        await redis.delete(key)


async def test_an_unknown_page_is_rejected(
    client: AsyncClient, auth_headers: dict[str, str], user_id: UUID
) -> None:
    response = await client.put(
        "/workspaces/me",
        headers=auth_headers,
        json=_put(nonsense={"key": _background(user_id)}),
    )
    assert response.status_code == 422


async def test_workspace_needs_a_token(client: AsyncClient) -> None:
    assert (await client.get("/workspaces/me")).status_code == 401
    assert (await client.put("/workspaces/me", json=_put())).status_code == 401


@pytest.mark.xfail(reason="the row is committed before the response resolves it", strict=True)
async def test_a_rejected_background_is_not_persisted(
    client: AsyncClient, db: AsyncSession, auth_headers: dict[str, str], make_user: MakeUser
) -> None:
    # The key is stored verbatim, then _response resolves it and the presign guard
    # answers 403 — after the commit. The workspace then 403s on every later read.
    stranger, _ = await make_user()

    rejected = await client.put(
        "/workspaces/me",
        headers=auth_headers,
        json=_put(dashboard={"key": _background(stranger.id)}),
    )
    assert rejected.status_code in (400, 403)

    assert await db.scalar(select(WorkspaceBackground)) is None, "a rejected write was persisted"
    assert (await client.get("/workspaces/me", headers=auth_headers)).status_code == 200
