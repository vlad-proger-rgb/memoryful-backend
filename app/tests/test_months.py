"""Month CRUD.

A month is keyed by (user_id, year, month) rather than an id, so create and update
address the row through the body instead of the path.
"""

from typing import Any
from uuid import UUID

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import CACHE_PREFIX
from app.core.config import redis
from app.enums import CacheNamespace
from app.models import Month

from .conftest import MakeUser

YEAR = 2019
MONTH = 4
# top_day_timestamp is floored to the start of its day by a validator on MonthBase.
MIDNIGHT = 1_699_920_000


def _payload(**overrides: Any) -> dict[str, Any]:
    body: dict[str, Any] = {"year": YEAR, "month": MONTH, "description": "a month"}
    body.update(overrides)
    return body


async def test_create_then_read_a_month(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    created = await client.post("/months/", headers=auth_headers, json=_payload())
    assert created.status_code == 200, created.text

    fetched = await client.get(f"/months/{YEAR}/{MONTH}", headers=auth_headers)
    assert fetched.status_code == 200, fetched.text
    data = fetched.json()["data"]
    assert data["year"] == YEAR
    assert data["month"] == MONTH
    assert data["description"] == "a month"


async def test_unknown_month_is_a_404(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    assert (await client.get(f"/months/{YEAR}/12", headers=auth_headers)).status_code == 404


async def test_month_number_is_validated(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    response = await client.post("/months/", headers=auth_headers, json=_payload(month=13))
    assert response.status_code == 422


async def test_listing_a_year_returns_only_the_callers_months(
    client: AsyncClient, db: AsyncSession, make_user: MakeUser
) -> None:
    _, mine = await make_user()
    other, theirs = await make_user()

    await client.post("/months/", headers=mine, json=_payload(description="mine"))
    db.add(Month(user_id=other.id, year=YEAR, month=MONTH, description="theirs"))
    await db.flush()

    listing = await client.get(f"/months/{YEAR}", headers=theirs)
    assert listing.status_code == 200, listing.text
    descriptions = [m["description"] for m in listing.json()["data"]]
    assert descriptions == ["theirs"]


async def test_update_changes_only_what_was_sent(
    client: AsyncClient, db: AsyncSession, auth_headers: dict[str, str], user_id: UUID
) -> None:
    await client.post("/months/", headers=auth_headers, json=_payload(topDayTimestamp=MIDNIGHT))

    updated = await client.put(
        "/months/", headers=auth_headers, json=_payload(description="rewritten")
    )
    assert updated.status_code == 200, updated.text

    month = await db.scalar(
        select(Month).where(Month.user_id == user_id, Month.year == YEAR, Month.month == MONTH)
    )
    assert month is not None
    assert month.description == "rewritten"
    assert month.top_day_timestamp == MIDNIGHT, "an unsent field was overwritten"


async def test_updating_a_month_that_does_not_exist_writes_nothing(
    client: AsyncClient, db: AsyncSession, auth_headers: dict[str, str], user_id: UUID
) -> None:
    # No rowcount guard on this route, so it answers 200 either way; what matters
    # is that it does not conjure a row.
    response = await client.put("/months/", headers=auth_headers, json=_payload(month=11))
    assert response.status_code == 200

    assert (
        await db.scalar(
            select(Month).where(Month.user_id == user_id, Month.year == YEAR, Month.month == 11)
        )
        is None
    )


async def test_writes_clear_the_months_cache(
    client: AsyncClient, auth_headers: dict[str, str], user_id: UUID
) -> None:
    key = f"{CACHE_PREFIX}:{CacheNamespace.months}:{user_id}:testdigest"
    try:
        await redis.set(key, "cached", ex=60)
        await client.post("/months/", headers=auth_headers, json=_payload())
        assert not await redis.exists(key), "create_month left the months cache stale"

        await redis.set(key, "cached", ex=60)
        await client.put("/months/", headers=auth_headers, json=_payload(description="x"))
        assert not await redis.exists(key), "update_month left the months cache stale"
    finally:
        await redis.delete(key)


async def test_top_day_timestamp_is_floored_to_its_day(
    client: AsyncClient, db: AsyncSession, auth_headers: dict[str, str], user_id: UUID
) -> None:
    noon = MIDNIGHT + 12 * 60 * 60
    created = await client.post(
        "/months/", headers=auth_headers, json=_payload(topDayTimestamp=noon)
    )
    assert created.status_code == 200, created.text

    stored = await db.scalar(
        select(Month.top_day_timestamp).where(
            Month.user_id == user_id, Month.year == YEAR, Month.month == MONTH
        )
    )
    assert stored == MIDNIGHT, "a mid-day timestamp was not normalized to the day"


async def test_creating_the_same_month_twice_is_a_conflict(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    # create_month has no duplicate guard of its own; (user_id, year, month) is the
    # primary key, and the IntegrityError handler turns the violation into a 409.
    first = await client.post("/months/", headers=auth_headers, json=_payload())
    assert first.status_code == 200

    second = await client.post("/months/", headers=auth_headers, json=_payload())
    assert second.status_code == 409
    assert second.json()["detail"] == "Record already exists"
