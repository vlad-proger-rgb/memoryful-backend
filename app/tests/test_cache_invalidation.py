"""The cross-namespace invalidation rule, which lives only as prose in CLAUDE.md:
a write must clear every namespace whose payload *embeds* the changed object, not
just its own. A day payload embeds its tags and trackables, so touching either has
to clear `days_list` and `days_detail`.

`CACHE_ENABLED` is false in tests, so `@cached` never writes. `clear_cache` is not
gated by it, so the keys are seeded directly and the mutation is asked which ones
it removes. Missing one is invisible in production until the TTL expires.
"""

from collections.abc import Iterable
from uuid import UUID

import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import CACHE_PREFIX
from app.core.config import redis
from app.enums import CacheNamespace
from app.models import Tag, TrackableItem, TrackableType

from .conftest import MakeUser

WATCHED = [
    CacheNamespace.tags,
    CacheNamespace.trackables,
    CacheNamespace.trackable_types,
    CacheNamespace.days_list,
    CacheNamespace.days_detail,
]


def _key(namespace: CacheNamespace, user_id: UUID) -> str:
    return f"{CACHE_PREFIX}:{namespace}:{user_id}:testdigest"


async def _seed(user_id: UUID, namespaces: Iterable[CacheNamespace]) -> None:
    for namespace in namespaces:
        await redis.set(_key(namespace, user_id), "cached", ex=60)


async def _surviving(user_id: UUID) -> set[CacheNamespace]:
    return {ns for ns in WATCHED if await redis.exists(_key(ns, user_id))}


@pytest_asyncio.fixture(autouse=True)
async def _clean_watched_keys(make_user: MakeUser):  # type: ignore[no-untyped-def]
    yield
    async for key in redis.scan_iter(match=f"{CACHE_PREFIX}:*:testdigest"):
        await redis.delete(key)


async def test_deleting_a_tag_clears_the_day_namespaces(
    client: AsyncClient, db: AsyncSession, make_user: MakeUser
) -> None:
    user, headers = await make_user()
    tag = Tag(user_id=user.id, name="cached-tag")
    db.add(tag)
    await db.flush()
    await _seed(user.id, WATCHED)

    response = await client.delete(f"/tags/{tag.id}", headers=headers)
    assert response.status_code == 200, response.text

    assert await _surviving(user.id) == {
        CacheNamespace.trackables,
        CacheNamespace.trackable_types,
    }


async def test_updating_a_tag_clears_the_day_namespaces(
    client: AsyncClient, db: AsyncSession, make_user: MakeUser
) -> None:
    user, headers = await make_user()
    tag = Tag(user_id=user.id, name="cached-tag")
    db.add(tag)
    await db.flush()
    await _seed(user.id, WATCHED)

    response = await client.put(f"/tags/{tag.id}", headers=headers, json={"name": "renamed"})
    assert response.status_code == 200, response.text

    surviving = await _surviving(user.id)
    assert CacheNamespace.days_list not in surviving, "renamed tag left days_list stale"
    assert CacheNamespace.days_detail not in surviving, "renamed tag left days_detail stale"
    assert CacheNamespace.tags not in surviving


async def test_updating_a_trackable_item_clears_the_day_namespaces(
    client: AsyncClient, db: AsyncSession, make_user: MakeUser
) -> None:
    user, headers = await make_user()
    kind = TrackableType(user_id=user.id, name="kind", value_type="number")
    db.add(kind)
    await db.flush()
    item = TrackableItem(user_id=user.id, type_id=kind.id, title="item")
    db.add(item)
    await db.flush()
    await _seed(user.id, WATCHED)

    response = await client.put(
        f"/trackables/{item.id}", headers=headers, json={"title": "renamed"}
    )
    assert response.status_code == 200, response.text

    surviving = await _surviving(user.id)
    assert CacheNamespace.days_list not in surviving
    assert CacheNamespace.days_detail not in surviving
    assert CacheNamespace.trackables not in surviving


async def test_invalidation_does_not_cross_users(
    client: AsyncClient, db: AsyncSession, make_user: MakeUser
) -> None:
    # clear_cache takes the acting user_id; omitting it would wipe the namespace
    # for everyone, which is a cache-stampede bug rather than a correctness one.
    actor, headers = await make_user()
    bystander, _ = await make_user()

    tag = Tag(user_id=actor.id, name="cached-tag")
    db.add(tag)
    await db.flush()
    await _seed(actor.id, WATCHED)
    await _seed(bystander.id, WATCHED)

    response = await client.delete(f"/tags/{tag.id}", headers=headers)
    assert response.status_code == 200

    assert await _surviving(bystander.id) == set(WATCHED), (
        "one user's write cleared another user's cache"
    )


async def test_a_failed_mutation_leaves_the_cache_alone(
    client: AsyncClient, db: AsyncSession, make_user: MakeUser
) -> None:
    owner, _ = await make_user()
    intruder, intruder_headers = await make_user()

    tag = Tag(user_id=owner.id, name="cached-tag")
    db.add(tag)
    await db.flush()
    await _seed(intruder.id, WATCHED)

    response = await client.delete(f"/tags/{tag.id}", headers=intruder_headers)
    assert response.status_code == 404

    assert await _surviving(intruder.id) == set(WATCHED), (
        "a rejected write still dropped the caller's cache"
    )
