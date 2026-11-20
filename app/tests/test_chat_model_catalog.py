from decimal import Decimal
from typing import Any

import pytest
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import catalog as catalog_module
from app.ai.catalog import load_catalog, sync_chat_models
from app.ai.schemas import ChatModelCatalog
from app.enums import CacheNamespace
from app.models import ChatModel


def _spec(slug: str, **fields: Any) -> dict[str, Any]:
    return {
        "slug": slug,
        "label": slug.title(),
        "provider": "openai",
        "gateway": "openai",
        "provider_model": f"{slug}-model",
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


def test_the_committed_catalog_is_valid_and_priced() -> None:
    for spec in load_catalog().models:
        assert spec.input_price is not None and spec.output_price is not None, spec.slug


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


async def test_prices_and_limits_are_written(
    db: AsyncSession, cleared: list[CacheNamespace]
) -> None:
    await sync_chat_models(
        db, _catalog(_spec("a", input_price=0.1, output_price=0.4, context_limit=1000))
    )
    row = await _row(db, "a")

    assert (row.input_price, row.output_price) == (Decimal("0.1"), Decimal("0.4"))
    assert (row.cached_input_price, row.context_limit) == (None, 1000)


async def test_any_changed_field_clears_the_caches(
    db: AsyncSession, cleared: list[CacheNamespace]
) -> None:
    await sync_chat_models(db, _catalog(_spec("keep", input_price=0.1)))
    cleared.clear()

    await sync_chat_models(db, _catalog(_spec("keep", input_price=0.1)))
    assert cleared == []

    await sync_chat_models(db, _catalog(_spec("keep", input_price=0.2)))
    assert set(cleared) == {CacheNamespace.chat_models, CacheNamespace.ai_model_preferences}


async def test_a_model_dropped_from_the_catalog_is_retired(
    db: AsyncSession, cleared: list[CacheNamespace]
) -> None:
    await sync_chat_models(db, _catalog(_spec("old"), _spec("new")))
    old = await _row(db, "old")

    await sync_chat_models(db, _catalog(_spec("new")))

    assert (old.is_active, old.is_default) == (False, False)
