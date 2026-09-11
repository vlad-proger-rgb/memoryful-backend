from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    Query,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app import schemas
from app.constants import CACHE_TTL_AI_CONTENT
from app.core.cache import cached
from app.core.database import get_db
from app.core.deps import get_current_user
from app.enums import CacheNamespace, InsightKind
from app.models import Insight
from app.schemas import (
    InsightInDB,
    Msg,
)

router = APIRouter(
    prefix="/insights",
    tags=["Insights"],
)


@router.get("/", response_model=Msg[list[schemas.InsightInDB]])
@cached(expire=CACHE_TTL_AI_CONTENT, namespace=CacheNamespace.insights)
async def get_insights(
    db: Annotated[AsyncSession, Depends(get_db)],
    user_id: Annotated[UUID, Depends(get_current_user())],
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    timestamp: int | None = Query(None, description="Filter insights by day timestamp"),
    kind: InsightKind | None = Query(None, description="Filter by observation or suggestion"),
) -> Msg[list[InsightInDB]]:
    stmt = (
        select(Insight).where(Insight.user_id == user_id).options(selectinload(Insight.chat_model))
    )
    if timestamp is not None:
        stmt = stmt.where(Insight.timestamp == timestamp)
    if kind is not None:
        stmt = stmt.where(Insight.kind == kind)
    stmt = stmt.order_by(Insight.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(stmt)
    insights = result.scalars().all()
    return Msg(
        code=200, msg="Insights retrieved", data=[InsightInDB.model_validate(i) for i in insights]
    )
