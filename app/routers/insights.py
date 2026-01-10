from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    Query,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import schemas
from app.schemas import (
    Msg,
    InsightInDB,
)
from app.core.database import get_db
from app.models import Insight
from app.core.deps import get_current_user


router = APIRouter(
    prefix="/insights",
    tags=["Insights"],
)


@router.get("/", response_model=Msg[list[schemas.InsightInDB]])
async def get_insights(
    db: Annotated[AsyncSession, Depends(get_db)],
    user_id: Annotated[UUID, Depends(get_current_user())],
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> Msg[list[InsightInDB]]:
    stmt = (
        select(Insight)
        .where(Insight.user_id == user_id)
        .order_by(Insight.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await db.execute(stmt)
    insights = result.scalars().all()
    return Msg(code=200, msg="Insights retrieved", data=[InsightInDB.model_validate(i) for i in insights])
