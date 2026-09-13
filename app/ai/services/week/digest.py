import logging
from uuid import UUID

from langchain_core.exceptions import OutputParserException
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.output_parsers import PydanticOutputParser
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.ai.schemas import WeekDigestDraft, bounded_week_digest_draft
from app.ai.utils import build_chat_model, get_chat_model_for, load_prompt
from app.core.cache import clear_cache
from app.core.database import AsyncSessionLocal
from app.enums import AnalysisPurpose, CacheNamespace, InsightKind
from app.models import Day, Insight, WeekDigest

from .context import ItemsByDay, build_week_context
from .window import Week

logger = logging.getLogger(__name__)

_PARSER = PydanticOutputParser(pydantic_object=WeekDigestDraft)


def _section_budget(day_count: int) -> int:
    """A thin week has no threads to find, and the model pads unless handed a number."""
    if day_count <= 2:
        return 1
    return 2 if day_count <= 5 else 4


class WeekNotReady(Exception):
    """A day in the week has no current AI items of its own."""


async def _load_week(
    db: AsyncSession, *, user_id: UUID, week: Week
) -> tuple[list[Day], ItemsByDay, ItemsByDay]:
    in_week = and_(Day.timestamp >= week.start_ts, Day.timestamp <= week.end_ts)

    days = list(
        (
            await db.scalars(
                select(Day)
                .where(and_(Day.user_id == user_id, in_week))
                .options(selectinload(Day.city), selectinload(Day.tags))
                .order_by(Day.timestamp.asc())
            )
        ).all()
    )
    if not days:
        return [], {}, {}

    timestamps = [day.timestamp for day in days]

    insights: ItemsByDay = {}
    suggestions: ItemsByDay = {}
    for item in await db.scalars(
        select(Insight)
        .where(and_(Insight.user_id == user_id, Insight.timestamp.in_(timestamps)))
        .order_by(Insight.created_at.asc())
    ):
        bucket = suggestions if item.kind is InsightKind.suggestion else insights
        bucket.setdefault(item.timestamp, []).append(item)

    return days, insights, suggestions


def _days_pending_ai(days: list[Day]) -> list[Day]:
    return [
        day for day in days if day.ai_generated_at is None or day.updated_at > day.ai_generated_at
    ]


async def _store(
    db: AsyncSession,
    *,
    user_id: UUID,
    model_id: UUID,
    week: Week,
    digest: WeekDigestDraft,
    day_count: int,
) -> None:
    existing = await db.scalar(
        select(WeekDigest).where(
            and_(WeekDigest.user_id == user_id, WeekDigest.week_start == week.start)
        )
    )
    values = {
        "model_id": model_id,
        "title": digest.title,
        "summary": digest.summary,
        "sections": [section.model_dump(mode="json") for section in digest.sections],
        "source_day_count": day_count,
    }

    if existing is None:
        db.add(WeekDigest(user_id=user_id, week_start=week.start, **values))
    else:
        for field, value in values.items():
            setattr(existing, field, value)

    await db.commit()


async def generate_week_digest_for_user(
    *, user_id: UUID, week: Week, allow_incomplete: bool = False
) -> bool:
    """Digest one finished week. Returns False if the user wrote nothing that week.

    Raises `WeekNotReady` unless `allow_incomplete`, when days still lack their own AI.
    """
    async with AsyncSessionLocal() as db:
        days, insights, suggestions = await _load_week(db, user_id=user_id, week=week)
        if not days:
            logger.info("No days for user %s in week of %s, skipping", user_id, week.start)
            return False

        pending = _days_pending_ai(days)
        if pending and not allow_incomplete:
            raise WeekNotReady(
                f"{len(pending)} of {len(days)} days in the week of {week.start} "
                "have no current AI content"
            )

        model = await get_chat_model_for(db, user_id=user_id, purpose=AnalysisPurpose.week)
        llm = build_chat_model(model)
        budget = _section_budget(len(days))
        context = build_week_context(
            week=week,
            days=days,
            insights=insights,
            suggestions=suggestions,
            max_sections=budget,
        )
        messages: list[BaseMessage] = [
            SystemMessage(content=load_prompt("system_base.md")),
            SystemMessage(content=load_prompt("week_digest.md")),
            HumanMessage(content=context),
        ]

        try:
            digest = WeekDigestDraft.model_validate(
                await llm.with_structured_output(bounded_week_digest_draft(budget)).ainvoke(
                    messages
                )
            )
        except Exception as e:
            logger.warning("Structured digest failed (%s), parsing the raw reply", e)
            response = await llm.ainvoke(messages)
            raw = str(getattr(response, "content", response))
            try:
                # Unbounded on purpose: a reply that overshoots is still worth keeping.
                digest = _PARSER.parse(raw)
            except OutputParserException:
                logger.exception("Could not parse a digest from a %d-character reply", len(raw))
                raise

        if len(digest.sections) > budget:
            logger.warning(
                "Model wrote %d sections for a %d-day week that asked for %d",
                len(digest.sections),
                len(days),
                budget,
            )

        await _store(
            db,
            user_id=user_id,
            model_id=model.id,
            week=week,
            digest=digest,
            day_count=len(days),
        )

        await clear_cache(CacheNamespace.week_digests, user_id)
        logger.info(
            "Digested week of %s for user %s from %d days (complete=%s)",
            week.start,
            user_id,
            len(days),
            not pending,
        )
        return True
