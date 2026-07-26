"""Canonical catalog of chat models exposed in the in-app selector.

This is the single source of truth for which models the product offers.
`sync_chat_models()` runs on every startup (dev and prod), so editing this list
and redeploying is all it takes to add, update, or retire a model.

Cheap-first ordering on purpose — these are the low-cost models to lead with
before AI usage is metered/billed (Stripe).

IMPORTANT: `name` is the *exact* id passed to the provider SDK. Vertex model ids
and their regional availability change over time — verify against the GCP console
(Vertex AI > Model Garden) for VERTEX_LOCATION before relying on them in prod.
"""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import clear_cache
from app.enums.provider import Provider
from app.models import ChatModel

logger = logging.getLogger(__name__)

# Each entry maps directly to ChatModel(**entry). `provider` drives routing in
# app/ai/utils.build_chat_model.
CHAT_MODEL_CATALOG: list[dict[str, object]] = [
    # --- Google Gemini via Vertex (ChatGoogleGenerativeAI, bare model id) ---
    # NOTE: use the bare id, NOT the "google/..." form — that prefix is only for
    # NOTE: the OpenAI-compatible endpoint used by partner models below.
    {
        # ~$0.10/$0.40 per 1M tokens — cheapest option, hence the default.
        # Scheduled for retirement around Oct 2026; swap `is_default` to the
        # 3.1 row below when that lands (a DB change, not a code change).
        "label": "Gemini 2.5 Flash Lite",
        "name": "gemini-2.5-flash-lite",
        "provider": Provider.google.value,
        "supports_tools": True,
        "is_default": True,
        "sort_order": 10,
    },
    {
        # ~$0.25/$1.50 per 1M tokens — successor to 2.5 Flash Lite.
        "label": "Gemini 3.1 Flash Lite",
        "name": "gemini-3.1-flash-lite",
        "provider": Provider.google.value,
        "supports_tools": True,
        "sort_order": 20,
    },
    # --- Anthropic Claude, direct API (requires ANTHROPIC_API_KEY) ---
    # Not via Vertex Model Garden: that route needs a per-model quota grant
    # Google declined for this project. Use the bare aliases — never append a
    # date suffix, and the "@version" form is Vertex-only.
    {
        # ~$1.00/$5.00 per 1M tokens — ~10x Gemini but the cheapest Claude, and
        # plenty for this app. 200K context. Flagship Sonnet/Opus deliberately
        # left out — overkill and expensive for the current goals.
        "label": "Claude Haiku 4.5",
        "name": "claude-haiku-4-5",
        "provider": Provider.anthropic.value,
        "supports_tools": True,
        "sort_order": 30,
    },
    # --- xAI Grok via Vertex OpenAI-compatible endpoint ---
    # These MUST keep the "xai/" publisher prefix; it's part of the model string
    # the OpenAI-compatible endpoint expects. Tool-calling works via
    # _VertexMaaSChatOpenAI (utils.py), which pads the empty tool-call turns the
    # Vertex shim would otherwise reject.
    {
        # Cheaper/lower latency — the better fit for interactive chat.
        "label": "Grok 4.1 Fast",
        "name": "xai/grok-4.1-fast-non-reasoning",
        "provider": Provider.xai.value,
        "supports_tools": True,
        "sort_order": 40,
    },
    {
        # Chain-of-thought; thinking tokens bill at the output rate, so this costs
        # more than its sticker price. Suited to insights/suggestions generation.
        "label": "Grok 4.1 Fast (Reasoning)",
        "name": "xai/grok-4.1-fast-reasoning",
        "provider": Provider.xai.value,
        "supports_tools": True,
        "sort_order": 50,
    },
    # --- OpenAI direct API (requires OPENAI_API_KEY; not on Vertex) ---
    {
        # ~$0.20/$1.25 per 1M tokens — OpenAI's cheapest current chat model.
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
        # Older but cheap and well-understood; useful comparison baseline.
        "label": "GPT-4o Mini",
        "name": "gpt-4o-mini",
        "provider": Provider.openai.value,
        "supports_tools": True,
        "sort_order": 80,
    },
]

_SYNCED_FIELDS = ("label", "provider", "region", "supports_tools", "is_default", "sort_order")
# Fields a catalog entry may omit; reset to these defaults when absent.
_OPTIONAL_DEFAULTS: dict[str, object] = {"is_default": False, "region": None}


async def sync_chat_models(db: AsyncSession) -> None:
    """Reconcile the `chat_models` table with CHAT_MODEL_CATALOG.

    Insert new models, refresh metadata on existing ones, and deactivate any row
    that's no longer in the catalog. Retired models are deactivated rather than
    deleted so existing chats/insights that reference them keep their foreign key.
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
            # Never leave a retired row holding the default flag.
            row.is_default = False
            continue
        for field in _SYNCED_FIELDS:
            setattr(row, field, spec.get(field, _OPTIONAL_DEFAULTS.get(field)))
        row.is_active = True

    added = [ChatModel(**spec) for spec in pending.values()]  # type: ignore[arg-type]
    db.add_all(added)
    await db.commit()

    if added or retired:
        # The selector endpoint is cached; drop it so the new list shows immediately.
        await clear_cache("chat_models")
        logger.info("Chat model catalog synced: %d added, %d retired", len(added), retired)
