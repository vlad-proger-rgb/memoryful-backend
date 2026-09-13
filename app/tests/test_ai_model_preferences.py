"""Per-purpose model selection: endpoints and resolver."""

from uuid import UUID, uuid4

import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.utils import get_chat_model_for, get_default_chat_model
from app.enums import AnalysisPurpose
from app.models import AiModelPreference, ChatModel

from .conftest import MakeUser

URL = "/ai/model-preferences/me"


@pytest_asyncio.fixture
async def other_model_id(db: AsyncSession, chat_model_id: UUID) -> UUID:
    found = await db.scalar(
        select(ChatModel.id)
        .where(
            ChatModel.id != chat_model_id,
            ChatModel.is_active == True,
            ChatModel.is_default == False,
        )
        .limit(1)
    )  # fmt: skip
    if found is not None:
        return found

    model = ChatModel(label="Second Model", name="second-model", provider="other")
    db.add(model)
    await db.flush()
    return model.id


async def test_defaults_cover_every_purpose(
    client: AsyncClient, auth_headers: dict[str, str], chat_model_id: UUID
) -> None:
    res = await client.get(URL, headers=auth_headers)
    assert res.status_code == 200

    purposes = res.json()["data"]
    assert set(purposes) == {p.value for p in AnalysisPurpose}
    for entry in purposes.values():
        assert entry["isDefault"] is True
        assert entry["model"]["id"]


async def test_pick_is_stored_per_purpose(
    client: AsyncClient, auth_headers: dict[str, str], other_model_id: UUID
) -> None:
    res = await client.put(
        f"{URL}/week", headers=auth_headers, json={"modelId": str(other_model_id)}
    )
    assert res.status_code == 200

    purposes = res.json()["data"]
    assert purposes["week"]["isDefault"] is False
    assert purposes["week"]["model"]["id"] == str(other_model_id)
    assert purposes["day"]["isDefault"] is True

    res = await client.get(URL, headers=auth_headers)
    assert res.json()["data"]["week"]["model"]["id"] == str(other_model_id)


async def test_null_restores_the_default(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db: AsyncSession,
    user_id: UUID,
    other_model_id: UUID,
) -> None:
    await client.put(f"{URL}/day", headers=auth_headers, json={"modelId": str(other_model_id)})
    res = await client.put(f"{URL}/day", headers=auth_headers, json={"modelId": None})
    assert res.status_code == 200
    assert res.json()["data"]["day"]["isDefault"] is True

    remaining = await db.scalars(
        select(AiModelPreference).where(
            AiModelPreference.user_id == user_id, AiModelPreference.purpose == "day"
        )
    )
    assert list(remaining) == []


async def test_unknown_model_is_rejected(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    res = await client.put(f"{URL}/day", headers=auth_headers, json={"modelId": str(uuid4())})
    assert res.status_code == 404


async def test_unknown_purpose_is_rejected(
    client: AsyncClient, auth_headers: dict[str, str], other_model_id: UUID
) -> None:
    res = await client.put(
        f"{URL}/decade", headers=auth_headers, json={"modelId": str(other_model_id)}
    )
    assert res.status_code == 422


async def test_one_users_pick_does_not_reach_another(
    client: AsyncClient, make_user: MakeUser, other_model_id: UUID
) -> None:
    _, mine = await make_user()
    _, theirs = await make_user()

    await client.put(f"{URL}/week", headers=mine, json={"modelId": str(other_model_id)})

    res = await client.get(URL, headers=theirs)
    assert res.json()["data"]["week"]["isDefault"] is True


async def test_resolver_falls_back_to_the_default(
    db: AsyncSession, user_id: UUID, chat_model_id: UUID
) -> None:
    fallback = await get_default_chat_model(db)
    picked = await get_chat_model_for(db, user_id=user_id, purpose=AnalysisPurpose.day)
    assert picked.id == fallback.id


async def test_resolver_honors_the_pick(
    db: AsyncSession, user_id: UUID, other_model_id: UUID
) -> None:
    db.add(
        AiModelPreference(
            user_id=user_id, purpose=AnalysisPurpose.week.value, model_id=other_model_id
        )
    )
    await db.flush()

    picked = await get_chat_model_for(db, user_id=user_id, purpose=AnalysisPurpose.week)
    assert picked.id == other_model_id

    day = await get_chat_model_for(db, user_id=user_id, purpose=AnalysisPurpose.day)
    assert day.id == (await get_default_chat_model(db)).id


async def test_retired_pick_falls_back(
    db: AsyncSession, user_id: UUID, other_model_id: UUID
) -> None:
    retired = ChatModel(label="Retired", name="retired-model", provider="other", is_active=False)
    db.add(retired)
    await db.flush()
    db.add(
        AiModelPreference(user_id=user_id, purpose=AnalysisPurpose.day.value, model_id=retired.id)
    )
    await db.flush()

    picked = await get_chat_model_for(db, user_id=user_id, purpose=AnalysisPurpose.day)
    assert picked.id != retired.id
