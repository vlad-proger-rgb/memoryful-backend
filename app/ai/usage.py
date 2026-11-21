import logging
from decimal import Decimal
from typing import Any
from uuid import UUID

from langchain_core.callbacks import AsyncCallbackHandler
from langchain_core.messages import AIMessage
from langchain_core.messages.ai import UsageMetadata
from langchain_core.outputs import ChatGeneration, LLMResult

from app.constants import TOKENS_PER_PRICE_UNIT
from app.core.database import AsyncSessionLocal
from app.enums import AiUsagePurpose
from app.models import AiUsageEvent, ChatModel

logger = logging.getLogger(__name__)


class UsageRecorder(AsyncCallbackHandler):
    """Writes one ai_usage_events row per provider call, in a session of its own, so a
    row survives the caller's transaction rolling back or its stream being dropped."""

    def __init__(self, model: ChatModel, *, user_id: UUID, purpose: AiUsagePurpose) -> None:
        self.user_id = user_id
        self.purpose = purpose
        self.model_id = model.id
        self.input_price = model.input_price or Decimal(0)
        self.cached_input_price = model.cached_input_price or self.input_price
        self.output_price = model.output_price or Decimal(0)

    async def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        usage = _usage_of(response)
        if usage is None:
            logger.warning("Model %s finished without reporting token usage", self.model_id)
            return
        await self._record(usage)

    async def on_llm_error(self, error: BaseException, **kwargs: Any) -> None:
        response = kwargs.get("response")
        usage = _usage_of(response) if isinstance(response, LLMResult) else None
        if usage is not None:
            await self._record(usage)

    async def _record(self, usage: UsageMetadata) -> None:
        cached = usage.get("input_token_details", {}).get("cache_read") or 0
        event = AiUsageEvent(
            user_id=self.user_id,
            chat_model_id=self.model_id,
            purpose=self.purpose,
            input_tokens=usage["input_tokens"],
            cached_input_tokens=cached,
            output_tokens=usage["output_tokens"],
            cost_usd=self.cost(usage["input_tokens"], cached, usage["output_tokens"]),
        )
        async with AsyncSessionLocal() as db:
            db.add(event)
            await db.commit()

    def cost(self, input_tokens: int, cached_input_tokens: int, output_tokens: int) -> Decimal:
        # LangChain's input_tokens includes cache reads; the details only break it down.
        uncached = input_tokens - cached_input_tokens
        total = (
            uncached * self.input_price
            + cached_input_tokens * self.cached_input_price
            + output_tokens * self.output_price
        )
        return total / TOKENS_PER_PRICE_UNIT


def _usage_of(response: LLMResult) -> UsageMetadata | None:
    for generations in response.generations:
        for generation in generations:
            if not isinstance(generation, ChatGeneration):
                continue
            message = generation.message
            if isinstance(message, AIMessage) and message.usage_metadata:
                return message.usage_metadata
    return None
