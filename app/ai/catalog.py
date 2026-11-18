"""The chat models offered in the app, from `chat_models.yaml`.

`sync_chat_models()` runs on every startup, so editing the file and redeploying adds,
updates or retires a model.
"""

import logging
from pathlib import Path

import yaml
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.schemas import ChatModelCatalog, ChatModelSpec
from app.core.cache import clear_cache
from app.enums import CacheNamespace
from app.models import ChatModel

logger = logging.getLogger(__name__)

CATALOG_PATH = Path(__file__).with_name("chat_models.yaml")


def load_catalog(path: Path = CATALOG_PATH) -> ChatModelCatalog:
    return ChatModelCatalog.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))


async def sync_chat_models(db: AsyncSession, catalog: ChatModelCatalog | None = None) -> None:
    """Make `chat_models` match the catalog. Retired models are deactivated, not deleted,
    so chats and insights that reference them keep their foreign key.
    """
    specs = (catalog or load_catalog()).models
    rows = list(await db.scalars(select(ChatModel)))
    rows_by_slug = {row.slug: row for row in rows if row.slug is not None}

    added = False
    for position, spec in enumerate(specs):
        row = rows_by_slug.get(spec.slug)
        if row is None:
            row = ChatModel()
            db.add(row)
            added = True
        _copy_spec(spec, row)
        row.sort_order = position
        row.is_default = position == 0

    catalog_slugs = {spec.slug for spec in specs}
    for row in rows:
        if row.slug not in catalog_slugs and row.is_active:
            row.is_active = False
            row.is_default = False

    changed = added or any(db.is_modified(row) for row in rows)
    await db.commit()

    if changed:
        await clear_cache(CacheNamespace.chat_models)
        await clear_cache(CacheNamespace.ai_model_preferences)
        logger.info("Chat model catalog synced")


def _copy_spec(spec: ChatModelSpec, row: ChatModel) -> None:
    row.slug = spec.slug
    row.label = spec.label
    row.name = spec.provider_model
    row.provider = spec.provider.value
    row.gateway = spec.gateway.value
    row.no_sampling = spec.no_sampling
    row.is_active = True
