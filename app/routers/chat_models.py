from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    HTTPException,
    Depends,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas import (
    Msg,
    ChatModelInDB as C,
)
from app.core.database import get_db
from app.models import ChatModel


router = APIRouter(
    prefix="/chat-models",
    tags=["Chat Models"],
)


@router.get("/", response_model=Msg[list[C]])
async def get_chat_models(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Msg[list[C]]:
    stmt = select(ChatModel)
    result = await db.execute(stmt)
    chat_models = result.scalars().all()

    return Msg(code=200, msg="Chat Models retrieved", data=[C.model_validate(m) for m in chat_models])


@router.get("/{id}", response_model=Msg[C])
async def get_chat_model(
    db: Annotated[AsyncSession, Depends(get_db)],
    id: UUID,
) -> Msg[C]:
    stmt = select(ChatModel).where(ChatModel.id == id)
    chat_model = await db.scalar(stmt)
    if not chat_model:
        raise HTTPException(404, "Chat Model not found")

    return Msg(code=200, msg="Chat Model retrieved", data=C.model_validate(chat_model))
