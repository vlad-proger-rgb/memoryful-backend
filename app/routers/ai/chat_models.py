from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import CACHE_TTL_STATIC
from app.core.cache import cached
from app.core.database import get_db
from app.enums import CacheNamespace
from app.models import ChatModel
from app.schemas import (
    ChatModelInDB as C,
    Msg,
)

router = APIRouter(
    prefix="/chat-models",
    tags=["AI Chat Models"],
)


@router.get("/", response_model=Msg[list[C]])
@cached(expire=CACHE_TTL_STATIC, namespace=CacheNamespace.chat_models)
async def get_chat_models(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Msg[list[C]]:
    # Retired models stay in the table (chats/insights reference them) but are
    # hidden from the selector.
    stmt = (
        select(ChatModel)
        .where(ChatModel.is_active == True)
        .order_by(ChatModel.sort_order.asc())
    )  # fmt: skip
    result = await db.execute(stmt)
    chat_models = result.scalars().all()

    return Msg(
        code=200, msg="Chat Models retrieved", data=[C.model_validate(m) for m in chat_models]
    )


@router.get("/{id}", response_model=Msg[C])
@cached(expire=CACHE_TTL_STATIC, namespace=CacheNamespace.chat_models)
async def get_chat_model(
    db: Annotated[AsyncSession, Depends(get_db)],
    id: UUID,
) -> Msg[C]:
    stmt = select(ChatModel).where(ChatModel.id == id)
    chat_model = await db.scalar(stmt)
    if not chat_model:
        raise HTTPException(404, "Chat Model not found")

    return Msg(code=200, msg="Chat Model retrieved", data=C.model_validate(chat_model))
