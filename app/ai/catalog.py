"""Canonical catalog of chat models exposed in the in-app selector.

`sync_chat_models()` runs on every startup, so editing this list and redeploying adds,
updates or retires a model. `name` is the exact id passed to the provider SDK.
"""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import clear_cache
from app.enums import CacheNamespace
from app.enums.provider import Provider
from app.models import ChatModel

logger = logging.getLogger(__name__)

CHAT_MODEL_CATALOG: list[dict[str, object]] = [
    # Gemini takes the bare id; the "google/..." form is only for the OpenAI-compat endpoint.
    {
        "label": "Gemini 2.5 Flash Lite",
        "name": "gemini-2.5-flash-lite",
        "provider": Provider.google.value,
        "supports_tools": True,
        "is_default": True,
        "sort_order": 10,
    },
    {
        "label": "Gemini 3.1 Flash Lite",
        "name": "gemini-3.1-flash-lite",
        "provider": Provider.google.value,
        "supports_tools": True,
        "sort_order": 20,
    },
    # Bare aliases only: no date suffix, and the "@version" form is Vertex-only.
    {
        "label": "Claude Haiku 4.5",
        "name": "claude-haiku-4-5",
        "provider": Provider.anthropic.value,
        "supports_tools": True,
        "sort_order": 30,
    },
    # Keep the "xai/" publisher prefix: the OpenAI-compatible endpoint expects it.
    {
        "label": "Grok 4.1 Fast",
        "name": "xai/grok-4.1-fast-non-reasoning",
        "provider": Provider.xai.value,
        "supports_tools": True,
        "sort_order": 40,
    },
    {
        # Thinking tokens bill at the output rate, so this costs more than its listed price.
        "label": "Grok 4.1 Fast (Reasoning)",
        "name": "xai/grok-4.1-fast-reasoning",
        "provider": Provider.xai.value,
        "supports_tools": True,
        "sort_order": 50,
    },
    {
        "label": "GPT-5.4 Nano",
        "name": "gpt-5.4-nano",
        "provider": Provider.openai.value,
        "supports_tools": True,
        "sort_order": 60,
    },
    {
        "label": "GPT-5.4 Mini",
        "name": "gpt-5.4-mini",
        "provider": Provider.openai.value,
        "supports_tools": True,
        "sort_order": 70,
    },
    {
        "label": "GPT-4o Mini",
        "name": "gpt-4o-mini",
        "provider": Provider.openai.value,
        "supports_tools": True,
        "sort_order": 80,
    },
]

_SYNCED_FIELDS = ("label", "provider", "region", "supports_tools", "is_default", "sort_order")
_OPTIONAL_DEFAULTS: dict[str, object] = {"is_default": False, "region": None}


async def sync_chat_models(db: AsyncSession) -> None:
    """Reconcile `chat_models` with the catalog. Retired models are deactivated, not deleted,
    so chats and insights that reference them keep their foreign key.
    """
    pending = {str(spec["name"]): spec for spec in CHAT_MODEL_CATALOG}
    rows = list((await db.scalars(select(ChatModel))).all())

    retired = 0
    for row in rows:
        spec = pending.pop(row.name, None)
        if spec is None:
            if row.is_active:
                row.is_active = False
                retired += 1
            row.is_default = False
            continue
        for field in _SYNCED_FIELDS:
            setattr(row, field, spec.get(field, _OPTIONAL_DEFAULTS.get(field)))
        row.is_active = True

    added = [ChatModel(**spec) for spec in pending.values()]
    db.add_all(added)
    await db.commit()

    if added or retired:
        await clear_cache(CacheNamespace.chat_models)
        await clear_cache(CacheNamespace.ai_model_preferences)
        logger.info("Chat model catalog synced: %d added, %d retired", len(added), retired)
