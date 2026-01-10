import datetime as dt
import logging
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import and_, delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from openai import OpenAIError

from langchain_core.messages import HumanMessage, SystemMessage

from app.core.database import AsyncSessionLocal
from app.models import Day, Insight, InsightType, Suggestion
from app.schemas.font_awesome import FAIcon
from app.ai.utils import (
    load_prompt,
    extract_json_array,
    sanitize_items,
    handle_openai_model_error,
    init_chat_model_with_provider,
    get_default_chat_model,
)


class _AIItem(BaseModel):
    description: str
    icon: FAIcon
    content: str


class _AIItemList(BaseModel):
    items: list[_AIItem]



async def _get_or_create_insight_type(db: AsyncSession, name: str, duration: dt.timedelta) -> InsightType:
    existing = await db.scalar(select(InsightType).where(InsightType.name == name))
    if existing:
        return existing

    insight_type = InsightType(name=name, duration=duration)
    db.add(insight_type)
    await db.commit()
    await db.refresh(insight_type)
    return insight_type


async def _replace_daily_insights(
    db: AsyncSession,
    *,
    user_id: UUID,
    model_id: UUID,
    date_begin: dt.date,
    items: list[dict],
) -> None:
    logging.info(f"Replacing daily insights for user {user_id} on {date_begin} with {len(items)} items")

    insight_type = await _get_or_create_insight_type(db, name="daily", duration=dt.timedelta(days=1))

    await db.execute(
        delete(Insight).where(
            and_(
                Insight.user_id == user_id,
                Insight.insight_type_id == insight_type.id,
                Insight.date_begin == date_begin,
            )
        )
    )

    insights_to_create = []
    for i, item in enumerate(items):
        logging.info(f"Creating insight {i+1}: description='{item.get('description', '')[:50]}...', icon={item.get('icon')}")
        insights_to_create.append(
            Insight(
                user_id=user_id,
                model_id=model_id,
                insight_type_id=insight_type.id,
                date_begin=date_begin,
                description=item.get("description", ""),
                icon=item.get("icon"),
                content=item.get("content", ""),
            )
        )

    db.add_all(insights_to_create)
    await db.commit()
    logging.info(f"Successfully saved {len(insights_to_create)} insights to database")


async def _replace_daily_suggestions(
    db: AsyncSession,
    *,
    user_id: UUID,
    model_id: UUID,
    date: dt.date,
    items: list[dict],
) -> None:
    logging.info(f"Replacing daily suggestions for user {user_id} on {date} with {len(items)} items")

    await db.execute(
        delete(Suggestion).where(
            and_(
                Suggestion.user_id == user_id,
                Suggestion.date == date,
            )
        )
    )

    suggestions_to_create = []
    for i, item in enumerate(items):
        logging.info(f"Creating suggestion {i+1}: description='{item.get('description', '')[:50]}...', icon={item.get('icon')}")
        suggestions_to_create.append(
            Suggestion(
                user_id=user_id,
                model_id=model_id,
                date=date,
                description=item.get("description", ""),
                icon=item.get("icon"),
                content=item.get("content", ""),
            )
        )

    db.add_all(suggestions_to_create)
    await db.commit()
    logging.info(f"Successfully saved {len(suggestions_to_create)} suggestions to database")


async def generate_daily_insights_and_suggestions_for_day(*, user_id: UUID, timestamp: int) -> None:
    logging.info(f"Starting AI generation for user {user_id}, timestamp {timestamp}")
    async with AsyncSessionLocal() as db:
        day: Day | None = await db.get(Day, (timestamp, user_id))
        if not day:
            logging.warning(f"No day found for user {user_id}, timestamp {timestamp}")
            return

        if day.ai_generated_at is not None and day.updated_at <= day.ai_generated_at:
            logging.info(f"AI already generated for day {timestamp}, skipping")
            return

        logging.info(f"Loading default chat model for user {user_id}")
        model = await get_default_chat_model(db)

        system_base = load_prompt("system_base.md")
        insights_prompt = load_prompt("insights.md")
        suggestions_prompt = load_prompt("suggestions.md")

        llm = init_chat_model_with_provider(db_model_name=model.name)
        logging.info(f"Initialized LLM: {model.name} (provider: {llm.__class__.__name__})")

        date = dt.datetime.fromtimestamp(timestamp, tz=dt.UTC).date()

        existing_insights = (
            await db.execute(
                select(Insight).where(and_(Insight.user_id == user_id, Insight.date_begin == date))
            )
        ).scalars().all()

        existing_suggestions = (
            await db.execute(
                select(Suggestion).where(and_(Suggestion.user_id == user_id, Suggestion.date == date))
            )
        ).scalars().all()

        existing_section_lines: list[str] = []
        if existing_insights:
            existing_section_lines.append("Existing insights (may be updated):")
            existing_section_lines.extend([f"- {i.description}" for i in existing_insights])
        if existing_suggestions:
            existing_section_lines.append("Existing suggestions (may be updated):")
            existing_section_lines.extend([f"- {s.description}" for s in existing_suggestions])

        existing_section = "\n".join(existing_section_lines)

        day_context = "\n".join(
            [
                f"Day date (UTC): {date.isoformat()}",
                f"Description: {day.description or ''}",
                f"Steps: {day.steps or 0}",
                "Content:",
                day.content,
                existing_section,
            ]
        ).strip()

        def _invoke_items(*, prompt: str, context: str) -> list[dict]:
            structured_llm = llm.with_structured_output(_AIItemList)
            try:
                logging.info(f"Attempting structured output generation for {len(context)} characters of context")
                parsed = structured_llm.invoke(
                    [
                        SystemMessage(content=system_base),
                        SystemMessage(content=prompt),
                        HumanMessage(content=context),
                    ]
                )
                result = [i.model_dump() for i in parsed.items]  # type: ignore
                logging.info(f"Structured output succeeded, generated {len(result)} items")
                for i, item in enumerate(result):
                    logging.info(f"Item {i+1}: description='{item.get('description', '')[:50]}...', icon={item.get('icon')}")
                return result
            except Exception as e:
                logging.warning(f"Structured output failed: {e}. Falling back to text parsing")
                resp = llm.invoke(
                    [
                        SystemMessage(content=system_base),
                        SystemMessage(content=prompt),
                        HumanMessage(content=context),
                    ]
                )

                # Log the raw response from Ollama
                raw_content = getattr(resp, "content", str(resp))
                logging.info(f"Raw LLM response:\n{raw_content}")

                try:
                    result = extract_json_array(raw_content)
                    logging.info(f"Text parsing succeeded, extracted {len(result)} items")
                    for i, item in enumerate(result):
                        logging.info(f"Item {i+1}: description='{item.get('description', '')[:50]}...', icon={item.get('icon')}")
                    return result
                except Exception as parse_error:
                    logging.error(f"Text parsing also failed: {parse_error}")
                    logging.error(f"Failed to parse JSON from: {raw_content}")
                    raise

        try:
            insight_items = _invoke_items(prompt=insights_prompt, context=day_context)
        except OpenAIError as e:
            handle_openai_model_error(e)

        await _replace_daily_insights(
            db,
            user_id=user_id,
            model_id=model.id,
            date_begin=date,
            items=sanitize_items(insight_items),
        )

        suggestions_context = "\n".join(
            [
                day_context,
                "\nInsights just generated:",
                "\n".join([f"- {i.get('description', '')}" for i in insight_items]),
            ]
        )

        try:
            suggestion_items = _invoke_items(prompt=suggestions_prompt, context=suggestions_context)
        except OpenAIError as e:
            handle_openai_model_error(e)

        await _replace_daily_suggestions(
            db,
            user_id=user_id,
            model_id=model.id,
            date=date,
            items=sanitize_items(suggestion_items),
        )

        day.ai_generated_at = dt.datetime.now(dt.UTC)
        await db.commit()
        logging.info(f"AI generation completed successfully for user {user_id}, timestamp {timestamp}")
