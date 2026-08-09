"""Day CRUD through the API, including the paths that touch tags and starring."""

from typing import Any
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import City, Day, Tag

from .conftest import MakeUser

TIMESTAMP = 1_700_000_000


@pytest_asyncio.fixture
async def city_id(db: AsyncSession) -> UUID:
    found = await db.scalar(select(City.id).limit(1))
    assert found is not None, "no cities in the database; days cannot be created"
    return found


def _payload(city_id: UUID, **overrides: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "cityId": str(city_id),
        "content": "a day",
        "description": "short",
        "steps": 1234,
    }
    body.update(overrides)
    return body


async def test_create_then_read_a_day(
    client: AsyncClient, auth_headers: dict[str, str], city_id: UUID
) -> None:
    created = await client.post(f"/days/{TIMESTAMP}", headers=auth_headers, json=_payload(city_id))
    assert created.status_code == 200, created.text

    fetched = await client.get(f"/days/{TIMESTAMP}", headers=auth_headers)
    assert fetched.status_code == 200, fetched.text
    data = fetched.json()["data"]
    assert data["timestamp"] == TIMESTAMP
    assert data["content"] == "a day"
    assert data["steps"] == 1234


async def test_creating_the_same_day_twice_is_refused(
    client: AsyncClient, auth_headers: dict[str, str], city_id: UUID
) -> None:
    first = await client.post(f"/days/{TIMESTAMP}", headers=auth_headers, json=_payload(city_id))
    assert first.status_code == 200

    second = await client.post(f"/days/{TIMESTAMP}", headers=auth_headers, json=_payload(city_id))
    assert second.status_code == 404
    assert second.json()["detail"] == "Day already exists"


async def test_create_rejects_an_unknown_city(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    response = await client.post(f"/days/{TIMESTAMP}", headers=auth_headers, json=_payload(uuid4()))
    assert response.status_code == 404
    assert response.json()["detail"] == "City not found"


async def test_unknown_day_is_a_404(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    assert (await client.get("/days/1234567", headers=auth_headers)).status_code == 404


async def test_update_changes_only_what_was_sent(
    client: AsyncClient,
    db: AsyncSession,
    auth_headers: dict[str, str],
    user_id: UUID,
    city_id: UUID,
) -> None:
    await client.post(f"/days/{TIMESTAMP}", headers=auth_headers, json=_payload(city_id))

    updated = await client.put(
        f"/days/{TIMESTAMP}", headers=auth_headers, json={"description": "rewritten"}
    )
    assert updated.status_code == 200, updated.text

    day = await db.scalar(select(Day).where(Day.timestamp == TIMESTAMP, Day.user_id == user_id))
    assert day is not None
    assert day.description == "rewritten"
    assert day.content == "a day", "an unsent field was overwritten"
    assert day.steps == 1234


async def test_toggle_starred_flips_and_flips_back(
    client: AsyncClient,
    db: AsyncSession,
    auth_headers: dict[str, str],
    user_id: UUID,
    city_id: UUID,
) -> None:
    await client.post(f"/days/{TIMESTAMP}", headers=auth_headers, json=_payload(city_id))

    async def starred() -> bool:
        day = await db.scalar(select(Day).where(Day.timestamp == TIMESTAMP, Day.user_id == user_id))
        assert day is not None
        await db.refresh(day)
        return day.starred

    assert await starred() is False
    assert (
        await client.patch(f"/days/{TIMESTAMP}/toggle-starred", headers=auth_headers)
    ).status_code == 200
    assert await starred() is True
    assert (
        await client.patch(f"/days/{TIMESTAMP}/toggle-starred", headers=auth_headers)
    ).status_code == 200
    assert await starred() is False


@pytest.mark.xfail(reason="create_day ignores DayCreate.tags", strict=True)
async def test_a_day_carries_its_tags(
    client: AsyncClient,
    db: AsyncSession,
    auth_headers: dict[str, str],
    user_id: UUID,
    city_id: UUID,
) -> None:
    tag = Tag(user_id=user_id, name="tagged")
    db.add(tag)
    await db.flush()

    created = await client.post(
        f"/days/{TIMESTAMP}",
        headers=auth_headers,
        json=_payload(city_id, tags=[str(tag.id)]),
    )
    assert created.status_code == 200, created.text

    fetched = await client.get(f"/days/{TIMESTAMP}", headers=auth_headers)
    names = [t["name"] for t in fetched.json()["data"]["tags"]]
    assert names == ["tagged"]


async def test_listing_returns_only_the_callers_days(
    client: AsyncClient, db: AsyncSession, make_user: MakeUser, city_id: UUID
) -> None:
    _, mine = await make_user()
    other, theirs = await make_user()

    await client.post(f"/days/{TIMESTAMP}", headers=mine, json=_payload(city_id))
    db.add(Day(timestamp=TIMESTAMP, user_id=other.id, city_id=city_id, content="theirs", steps=0))
    await db.flush()

    listing = await client.get("/days/", headers=theirs)
    assert listing.status_code == 200, listing.text
    contents = [d.get("description") for d in listing.json()["data"]]
    assert "short" not in contents, "another user's day appeared in the listing"


@pytest.mark.xfail(reason="DayListItem.steps is int, but Day.steps is nullable", strict=True)
async def test_null_steps_does_not_break_the_listing(
    client: AsyncClient, auth_headers: dict[str, str], city_id: UUID
) -> None:
    # Reachable from the API: PUT accepts an explicit null, and every later listing
    # then fails to serialize — the whole list, not just this day.
    await client.post(f"/days/{TIMESTAMP}", headers=auth_headers, json=_payload(city_id))
    await client.put(f"/days/{TIMESTAMP}", headers=auth_headers, json={"steps": None})

    listing = await client.get("/days/", headers=auth_headers)
    assert listing.status_code == 200
