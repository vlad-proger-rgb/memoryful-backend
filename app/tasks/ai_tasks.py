import asyncio
import datetime as dt
from collections.abc import Coroutine
from typing import Any
from uuid import UUID

from sqlalchemy import and_, select

from app.ai.services.day import generate_day_insights
from app.core.celery_app import celery
from app.core.database import AsyncSessionLocal
from app.core.dates import day_timestamp
from app.models import Day

_celery_async_loop: asyncio.AbstractEventLoop | None = None


def _run_async(coro: "Coroutine[Any, Any, Any]") -> Any:
    global _celery_async_loop

    if _celery_async_loop is None or _celery_async_loop.is_closed():
        _celery_async_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(_celery_async_loop)

    return _celery_async_loop.run_until_complete(coro)


@celery.task(queue="ai_queue")
def generate_day_ai(user_id: str, timestamp: int) -> None:
    _run_async(generate_day_insights(user_id=UUID(user_id), timestamp=timestamp))


async def _enqueue_fallback_for_yesterday() -> None:
    target_date = dt.datetime.now(dt.UTC).date() - dt.timedelta(days=1)
    target_ts = day_timestamp(target_date)

    async with AsyncSessionLocal() as db:
        stmt = (
            select(Day)
            .where(
                and_(
                    Day.timestamp == target_ts,
                    (Day.ai_generated_at.is_(None) | (Day.updated_at > Day.ai_generated_at)),
                )
            )
            .order_by(Day.user_id.asc())
        )  # fmt: skip
        days = (await db.execute(stmt)).scalars().all()

    for day in days:
        generate_day_ai.delay(str(day.user_id), day.timestamp)


@celery.task(queue="ai_queue")
def generate_yesterday_ai_fallback() -> None:
    _run_async(_enqueue_fallback_for_yesterday())
