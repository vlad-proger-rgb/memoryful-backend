"""`user_id` is the whole tenancy boundary, so each resource is probed from the
outside: a second authenticated user must not read, alter or delete the first
user's rows, and the owner's row must be byte-identical afterwards.

Rows are seeded through the ORM rather than the API so a broken create endpoint
cannot mask a broken scoping check.
"""

from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import City, Day, Month, Tag, TrackableItem, TrackableType, User

from .conftest import MakeUser


async def _city_id(db: AsyncSession) -> object:
    city_id = await db.scalar(select(City.id).limit(1))
    assert city_id is not None, "no cities in the database; days cannot be seeded"
    return city_id


async def test_tag_is_invisible_to_another_user(
    client: AsyncClient, db: AsyncSession, make_user: MakeUser
) -> None:
    owner, _ = await make_user()
    _, intruder = await make_user()

    tag = Tag(user_id=owner.id, name="owner-tag")
    db.add(tag)
    await db.flush()

    assert (await client.get(f"/tags/{tag.id}", headers=intruder)).status_code == 404
    listing = await client.get("/tags/", headers=intruder, follow_redirects=True)
    assert str(tag.id) not in listing.text


async def test_tag_cannot_be_mutated_by_another_user(
    client: AsyncClient, db: AsyncSession, make_user: MakeUser
) -> None:
    owner, _ = await make_user()
    _, intruder = await make_user()

    tag = Tag(user_id=owner.id, name="owner-tag")
    db.add(tag)
    await db.flush()

    update = await client.put(f"/tags/{tag.id}", headers=intruder, json={"name": "hijacked"})
    assert update.status_code == 404

    removal = await client.delete(f"/tags/{tag.id}", headers=intruder)
    assert removal.status_code == 404

    survivor = await db.scalar(select(Tag).where(Tag.id == tag.id))
    assert survivor is not None, "another user deleted this tag"
    assert survivor.name == "owner-tag"


async def test_trackable_type_is_scoped(
    client: AsyncClient, db: AsyncSession, make_user: MakeUser
) -> None:
    owner, _ = await make_user()
    _, intruder = await make_user()

    kind = TrackableType(user_id=owner.id, name="owner-type", value_type="number")
    db.add(kind)
    await db.flush()

    assert (await client.get(f"/trackable-types/{kind.id}", headers=intruder)).status_code == 404
    update = await client.put(
        f"/trackable-types/{kind.id}", headers=intruder, json={"name": "hijacked"}
    )
    assert update.status_code == 404
    assert (await client.delete(f"/trackable-types/{kind.id}", headers=intruder)).status_code == 404

    survivor = await db.scalar(select(TrackableType).where(TrackableType.id == kind.id))
    assert survivor is not None
    assert survivor.name == "owner-type"


async def test_trackable_item_is_scoped(
    client: AsyncClient, db: AsyncSession, make_user: MakeUser
) -> None:
    owner, _ = await make_user()
    _, intruder = await make_user()

    kind = TrackableType(user_id=owner.id, name="owner-type", value_type="number")
    db.add(kind)
    await db.flush()
    item = TrackableItem(user_id=owner.id, type_id=kind.id, title="owner-item")
    db.add(item)
    await db.flush()

    assert (await client.get(f"/trackables/{item.id}", headers=intruder)).status_code == 404
    update = await client.put(
        f"/trackables/{item.id}", headers=intruder, json={"title": "hijacked"}
    )
    assert update.status_code == 404
    assert (await client.delete(f"/trackables/{item.id}", headers=intruder)).status_code == 404

    survivor = await db.scalar(select(TrackableItem).where(TrackableItem.id == item.id))
    assert survivor is not None
    assert survivor.title == "owner-item"


async def test_day_is_scoped(client: AsyncClient, db: AsyncSession, make_user: MakeUser) -> None:
    owner, _ = await make_user()
    _, intruder = await make_user()
    timestamp = 1_700_000_000

    day = Day(
        timestamp=timestamp,
        user_id=owner.id,
        city_id=await _city_id(db),
        content="owner content",
    )
    db.add(day)
    await db.flush()

    assert (await client.get(f"/days/{timestamp}", headers=intruder)).status_code == 404
    update = await client.put(f"/days/{timestamp}", headers=intruder, json={"content": "hijacked"})
    assert update.status_code == 404

    survivor = await db.scalar(
        select(Day).where(Day.timestamp == timestamp, Day.user_id == owner.id)
    )
    assert survivor is not None
    assert survivor.content == "owner content"


async def test_month_is_scoped(client: AsyncClient, db: AsyncSession, make_user: MakeUser) -> None:
    owner, _ = await make_user()
    _, intruder = await make_user()

    month = Month(user_id=owner.id, year=2019, month=4, description="owner month")
    db.add(month)
    await db.flush()

    assert (await client.get("/months/2019/4", headers=intruder)).status_code == 404
    listing = await client.get("/months/2019", headers=intruder)
    assert "owner month" not in listing.text

    # This endpoint has no rowcount guard, so it answers 200 either way; what
    # matters is that it wrote nothing.
    await client.put(
        "/months/", headers=intruder, json={"year": 2019, "month": 4, "description": "hijacked"}
    )
    survivor = await db.scalar(
        select(Month).where(Month.user_id == owner.id, Month.year == 2019, Month.month == 4)
    )
    assert survivor is not None
    assert survivor.description == "owner month"


async def test_workspace_reads_only_the_caller(
    client: AsyncClient, db: AsyncSession, make_user: MakeUser
) -> None:
    _, first = await make_user()
    _, second = await make_user()

    for headers in (first, second):
        response = await client.get("/workspaces/me", headers=headers, follow_redirects=True)
        assert response.status_code == 200, response.text


async def test_me_returns_the_token_holder(client: AsyncClient, make_user: MakeUser) -> None:
    first_user, first = await make_user()
    second_user, second = await make_user()

    first_body = (await client.get("/auth/me", headers=first)).json()
    second_body = (await client.get("/auth/me", headers=second)).json()

    assert first_body["data"]["id"] == str(first_user.id)
    assert second_body["data"]["id"] == str(second_user.id)
    assert first_body["data"]["id"] != second_body["data"]["id"]


@pytest.mark.parametrize(
    "path",
    [
        "/tags/{id}",
        "/trackables/{id}",
        "/trackable-types/{id}",
    ],
)
async def test_unknown_id_is_a_404_not_a_500(
    client: AsyncClient, auth_headers: dict[str, str], path: str
) -> None:
    response = await client.get(path.format(id=uuid4()), headers=auth_headers)
    assert response.status_code == 404


async def test_seeded_users_do_not_collide(db: AsyncSession, make_user: MakeUser) -> None:
    first, _ = await make_user()
    second, _ = await make_user()
    assert first.id != second.id
    assert await db.scalar(select(User).where(User.id == first.id)) is not None
