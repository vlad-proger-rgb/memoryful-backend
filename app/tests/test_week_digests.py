"""Week-window arithmetic and the digest read endpoints.

The LLM call is not exercised here; everything below it is deterministic.
"""

import datetime as dt
from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.services.week.window import last_finished_week, week_of
from app.core.dates import day_timestamp
from app.models import ChatModel, WeekDigest

from .conftest import MakeUser

MONDAY = dt.date(2026, 8, 24)
SUNDAY = dt.date(2026, 8, 30)


def test_week_of_snaps_to_monday() -> None:
    for offset in range(7):
        week = week_of(MONDAY + dt.timedelta(days=offset))
        assert week.start == MONDAY
        assert week.end == SUNDAY


def test_week_dates_cover_seven_days() -> None:
    assert week_of(MONDAY).dates == [MONDAY + dt.timedelta(days=i) for i in range(7)]


def test_day_timestamp_is_midnight_utc() -> None:
    ts = day_timestamp(MONDAY)
    assert ts % 86_400 == 0
    assert dt.datetime.fromtimestamp(ts, tz=dt.UTC).date() == MONDAY


def test_week_bounds_are_inclusive_timestamps() -> None:
    week = week_of(MONDAY)
    assert week.end_ts - week.start_ts == 6 * 86_400


@pytest.mark.parametrize("weekday", range(7))
def test_last_finished_week_never_includes_today(weekday: int) -> None:
    today = MONDAY + dt.timedelta(days=weekday)
    week = last_finished_week(today)
    assert week.end < today
    assert week.start == MONDAY - dt.timedelta(days=7)


async def _make_digest(db: AsyncSession, user_id: UUID, week_start: dt.date) -> WeekDigest:
    model_id = await db.scalar(select(ChatModel.id).limit(1))
    assert model_id is not None, "no chat models in the database"

    digest = WeekDigest(
        user_id=user_id,
        model_id=model_id,
        week_start=week_start,
        title="A quiet week",
        summary="Not much happened.",
        sections=[{"description": "Rest", "icon": None, "content": "You rested."}],
        source_day_count=2,
    )
    db.add(digest)
    await db.flush()
    return digest


async def test_list_returns_digests_newest_first(
    client: AsyncClient, db: AsyncSession, auth_headers: dict[str, str], user_id: UUID
) -> None:
    await _make_digest(db, user_id, MONDAY - dt.timedelta(days=7))
    await _make_digest(db, user_id, MONDAY)

    response = await client.get("/week-digests/", headers=auth_headers)
    assert response.status_code == 200, response.text

    weeks = [d["weekStart"] for d in response.json()["data"]]
    assert weeks == [MONDAY.isoformat(), (MONDAY - dt.timedelta(days=7)).isoformat()]


async def test_a_digest_is_readable_by_its_week_start(
    client: AsyncClient, db: AsyncSession, auth_headers: dict[str, str], user_id: UUID
) -> None:
    await _make_digest(db, user_id, MONDAY)

    response = await client.get(f"/week-digests/{MONDAY.isoformat()}", headers=auth_headers)
    assert response.status_code == 200, response.text

    data = response.json()["data"]
    assert data["title"] == "A quiet week"
    assert data["sourceDayCount"] == 2
    assert data["sections"][0]["description"] == "Rest"
    assert data["chatModel"]["label"]


async def test_a_week_without_a_digest_is_a_404(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    response = await client.get("/week-digests/2019-01-07", headers=auth_headers)
    assert response.status_code == 404


async def test_a_digest_is_invisible_to_another_user(
    client: AsyncClient, db: AsyncSession, make_user: MakeUser, user_id: UUID
) -> None:
    await _make_digest(db, user_id, MONDAY)
    _, other_headers = await make_user()

    listed = await client.get("/week-digests/", headers=other_headers)
    assert listed.json()["data"] == []

    fetched = await client.get(f"/week-digests/{MONDAY.isoformat()}", headers=other_headers)
    assert fetched.status_code == 404


async def test_the_endpoints_need_a_token(client: AsyncClient) -> None:
    assert (await client.get("/week-digests/")).status_code == 401
    assert (await client.get(f"/week-digests/{MONDAY.isoformat()}")).status_code == 401
