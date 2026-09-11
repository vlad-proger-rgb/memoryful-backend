import datetime as dt
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app import schemas
from app.ai.services.week import last_finished_week, week_of
from app.constants import CACHE_TTL_AI_CONTENT
from app.core.cache import cached
from app.core.database import get_db
from app.core.deps import get_current_user
from app.enums import CacheNamespace
from app.models import WeekDigest
from app.schemas import Msg, WeekDigestInDB
from app.tasks.ai_tasks import generate_week_digest

router = APIRouter(
    prefix="/week-digests",
    tags=["Week digests"],
)


@router.get("/", response_model=Msg[list[schemas.WeekDigestInDB]])
@cached(expire=CACHE_TTL_AI_CONTENT, namespace=CacheNamespace.week_digests)
async def get_week_digests(
    db: Annotated[AsyncSession, Depends(get_db)],
    user_id: Annotated[UUID, Depends(get_current_user())],
    limit: int = Query(12, ge=1, le=52),
    offset: int = Query(0, ge=0),
) -> Msg[list[WeekDigestInDB]]:
    """The weeks that have a digest, newest first."""
    stmt = (
        select(WeekDigest)
        .where(WeekDigest.user_id == user_id)
        .options(selectinload(WeekDigest.chat_model))
        .order_by(WeekDigest.week_start.desc())
        .limit(limit)
        .offset(offset)
    )

    digests = (await db.execute(stmt)).scalars().all()

    return Msg(
        code=200,
        msg="Week digests retrieved",
        data=[WeekDigestInDB.model_validate(d) for d in digests],
    )


@router.post("/generate", response_model=Msg[None])
async def request_week_digest(
    user_id: Annotated[UUID, Depends(get_current_user())],
    week_start: dt.date | None = Query(
        None,
        alias="weekStart",
        description="Any date in the target week. Defaults to the last finished week.",
    ),
) -> Msg[None]:
    """Queue a digest by hand, overwriting that week's and skipping the readiness wait."""
    week = week_of(week_start) if week_start else last_finished_week()
    generate_week_digest.delay(str(user_id), week.start.isoformat(), True)
    return Msg(code=202, msg=f"Digest queued for the week of {week.start.isoformat()}")


@router.get("/{week_start}", response_model=Msg[schemas.WeekDigestInDB])
@cached(expire=CACHE_TTL_AI_CONTENT, namespace=CacheNamespace.week_digests)
async def get_week_digest(
    db: Annotated[AsyncSession, Depends(get_db)],
    user_id: Annotated[UUID, Depends(get_current_user())],
    week_start: dt.date,
) -> Msg[WeekDigestInDB]:
    digest = await db.scalar(
        select(WeekDigest)
        .where(and_(WeekDigest.user_id == user_id, WeekDigest.week_start == week_start))
        .options(selectinload(WeekDigest.chat_model))
    )

    if not digest:
        raise HTTPException(404, "Week digest not found")

    return Msg(code=200, msg="Week digest retrieved", data=WeekDigestInDB.model_validate(digest))
