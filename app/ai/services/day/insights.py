import datetime as dt
import logging
from uuid import UUID

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.output_parsers import PydanticOutputParser
from openai import OpenAIError
from sqlalchemy import and_, delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.errors import handle_openai_model_error
from app.ai.schemas import AIItemList
from app.ai.utils import build_chat_model, get_default_chat_model, load_prompt
from app.core.cache import clear_cache
from app.core.database import AsyncSessionLocal
from app.enums import CacheNamespace, InsightKind
from app.models import Day, Insight

logger = logging.getLogger(__name__)

_PARSER = PydanticOutputParser(pydantic_object=AIItemList)


async def _replace_items(
    db: AsyncSession,
    *,
    user_id: UUID,
    model_id: UUID,
    timestamp: int,
    kind: InsightKind,
    items: list[dict],
) -> None:
    await db.execute(
        delete(Insight).where(
            and_(
                Insight.user_id == user_id,
                Insight.timestamp == timestamp,
                Insight.kind == kind,
            )
        )
    )

    db.add_all(
        [
            Insight(
                user_id=user_id,
                model_id=model_id,
                timestamp=timestamp,
                kind=kind,
                description=item.get("description", ""),
                icon=item.get("icon"),
                content=item.get("content", ""),
            )
            for item in items
        ]
    )
    await db.commit()
    logger.info("Stored %d %s items for user %s on day %s", len(items), kind, user_id, timestamp)


async def generate_day_insights(*, user_id: UUID, timestamp: int) -> None:
    async with AsyncSessionLocal() as db:
        day: Day | None = await db.get(Day, (timestamp, user_id))
        if not day:
            logger.warning("No day for user %s at %s", user_id, timestamp)
            return

        if day.ai_generated_at is not None and day.updated_at <= day.ai_generated_at:
            logger.info("Day %s for user %s is already current, skipping", timestamp, user_id)
            return

        model = await get_default_chat_model(db)
        llm = build_chat_model(model)

        system_base = load_prompt("system_base.md")
        insights_prompt = load_prompt("insights.md")
        suggestions_prompt = load_prompt("suggestions.md")

        date = dt.datetime.fromtimestamp(timestamp, tz=dt.UTC).date()

        existing = (
            (
                await db.execute(
                    select(Insight).where(
                        and_(Insight.user_id == user_id, Insight.timestamp == timestamp)
                    )
                )
            )
            .scalars()
            .all()
        )

        existing_section_lines: list[str] = []
        for kind, label in (
            (InsightKind.observation, "Existing insights (may be updated):"),
            (InsightKind.suggestion, "Existing suggestions (may be updated):"),
        ):
            of_kind = [item for item in existing if item.kind == kind]
            if of_kind:
                existing_section_lines.append(label)
                existing_section_lines.extend(f"- {item.description}" for item in of_kind)

        day_context = "\n".join(
            [
                f"Day date (UTC): {date.isoformat()}",
                f"Description: {day.description or ''}",
                f"Steps: {day.steps or 0}",
                "Content:",
                day.content,
                "\n".join(existing_section_lines),
            ]
        ).strip()

        async def _invoke_items(*, prompt: str, context: str) -> list[dict]:
            messages: list[BaseMessage] = [
                SystemMessage(content=system_base),
                SystemMessage(content=prompt),
                HumanMessage(content=context),
            ]
            try:
                parsed = AIItemList.model_validate(
                    await llm.with_structured_output(AIItemList).ainvoke(messages)
                )
            except Exception as e:
                logger.warning("Structured output failed (%s), parsing the raw reply", e)
                response = await llm.ainvoke(messages)
                parsed = _PARSER.parse(str(getattr(response, "content", response)))
            return [item.model_dump() for item in parsed.items]

        try:
            insight_items = await _invoke_items(prompt=insights_prompt, context=day_context)
        except OpenAIError as e:
            handle_openai_model_error(e)

        await _replace_items(
            db,
            user_id=user_id,
            model_id=model.id,
            timestamp=timestamp,
            kind=InsightKind.observation,
            items=insight_items,
        )

        suggestions_context = "\n".join(
            [
                day_context,
                "\nInsights just generated:",
                "\n".join(f"- {item.get('description', '')}" for item in insight_items),
            ]
        )

        try:
            suggestion_items = await _invoke_items(
                prompt=suggestions_prompt, context=suggestions_context
            )
        except OpenAIError as e:
            handle_openai_model_error(e)

        await _replace_items(
            db,
            user_id=user_id,
            model_id=model.id,
            timestamp=timestamp,
            kind=InsightKind.suggestion,
            items=suggestion_items,
        )

        day.ai_generated_at = dt.datetime.now(dt.UTC)
        await db.commit()

        for namespace in (
            CacheNamespace.insights,
            CacheNamespace.days_detail,
            CacheNamespace.days_list,
        ):
            await clear_cache(namespace, user_id)
