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
    SuggestionInDB,
)
from app.core.database import get_db
from app.models import Suggestion
from app.core.deps import get_current_user


router = APIRouter(
    prefix="/suggestions",
    tags=["Suggestions"],
)


@router.get("/", response_model=Msg[list[schemas.SuggestionInDB]])
async def get_suggestions(
    db: Annotated[AsyncSession, Depends(get_db)],
    user_id: Annotated[UUID, Depends(get_current_user())],
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> Msg[list[SuggestionInDB]]:
    stmt = (
        select(Suggestion)
        .where(Suggestion.user_id == user_id)
        .order_by(Suggestion.date.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await db.execute(stmt)
    suggestions = result.scalars().all()
    return Msg(code=200, msg="Suggestions retrieved", data=[SuggestionInDB.model_validate(s) for s in suggestions])
