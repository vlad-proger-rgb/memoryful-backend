from typing import Any

import pytest
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import catalog as catalog_module
from app.ai.catalog import load_catalog, sync_chat_models
from app.ai.schemas import ChatModelCatalog
from app.enums import CacheNamespace, Gateway
from app.models import ChatModel


def _spec(slug: str, **fields: Any) -> dict[str, Any]:
    return {
        "slug": slug,
        "label": slug.title(),
        "provider": "openai",
        "gateway": "openai",
        "provider_model": f"{slug}-model",
        "source": f"openai/{slug}",
        **fields,
    }


def _catalog(*specs: dict[str, Any]) -> ChatModelCatalog:
    return ChatModelCatalog.model_validate({"models": list(specs)})


async def _row(db: AsyncSession, slug: str) -> ChatModel:
    row = await db.scalar(select(ChatModel).where(ChatModel.slug == slug))
    assert row is not None
    return row


@pytest.fixture
def cleared(monkeypatch: pytest.MonkeyPatch) -> list[CacheNamespace]:
    calls: list[CacheNamespace] = []

    async def record(namespace: CacheNamespace) -> None:
        calls.append(namespace)

    monkeypatch.setattr(catalog_module, "clear_cache", record)
    return calls


def test_the_committed_catalog_is_valid() -> None:
    models = load_catalog().models

    assert {m.gateway for m in models} <= set(Gateway)


@pytest.mark.parametrize(
    "specs",
    [
        pytest.param([], id="empty"),
        pytest.param([_spec("a"), _spec("a")], id="duplicate slug"),
        pytest.param([_spec("a", gateway="bedrock")], id="unknown gateway"),
        pytest.param([_spec("a", provider="acme")], id="unknown provider"),
        pytest.param([_spec("a", is_default=True)], id="unknown field"),
    ],
)
def test_an_invalid_catalog_is_rejected(specs: list[dict[str, Any]]) -> None:
    with pytest.raises(ValidationError):
        _catalog(*specs)


async def test_the_first_model_is_the_default_and_order_follows_the_list(
    db: AsyncSession, cleared: list[CacheNamespace]
) -> None:
    await sync_chat_models(db, _catalog(_spec("first"), _spec("second")))
    first, second = await _row(db, "first"), await _row(db, "second")
    assert (first.is_default, second.is_default) == (True, False)
    assert first.sort_order < second.sort_order

    await sync_chat_models(db, _catalog(_spec("second"), _spec("first")))
    assert (first.is_default, second.is_default) == (False, True)
    assert second.sort_order < first.sort_order


async def test_any_changed_field_clears_the_caches(
    db: AsyncSession, cleared: list[CacheNamespace]
) -> None:
    await sync_chat_models(db, _catalog(_spec("keep")))
    cleared.clear()

    await sync_chat_models(db, _catalog(_spec("keep")))
    assert cleared == []

    await sync_chat_models(db, _catalog(_spec("keep", no_sampling=True)))
    assert set(cleared) == {CacheNamespace.chat_models, CacheNamespace.ai_model_preferences}


async def test_a_model_dropped_from_the_catalog_is_retired(
    db: AsyncSession, cleared: list[CacheNamespace]
) -> None:
    await sync_chat_models(db, _catalog(_spec("old"), _spec("new")))
    old = await _row(db, "old")

    await sync_chat_models(db, _catalog(_spec("new")))

    assert (old.is_active, old.is_default) == (False, False)
