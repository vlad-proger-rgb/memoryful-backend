from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.ai.services import chat as chat_service
from app.schemas import Msg, ChatListItem, ChatDetail, ChatCreate, ChatUpdate

router = APIRouter(
    prefix="/chats",
    tags=["AI Chats"],
)


@router.get("/")
async def get_chats(
    db: Annotated[AsyncSession, Depends(get_db)],
    user_id: Annotated[UUID, Depends(get_current_user())],
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    query: str | None = Query(None, description="Substring to search for in chat title"),
) -> Msg[list[ChatListItem]]:
    items = await chat_service.list_chats(db, user_id, limit=limit, offset=offset, query=query)
    return Msg(code=200, msg="Chats retrieved", data=items)


@router.get("/{id}", response_model=Msg[ChatDetail])
async def get_chat(
    db: Annotated[AsyncSession, Depends(get_db)],
    user_id: Annotated[UUID, Depends(get_current_user())],
    id: UUID,
) -> Msg[ChatDetail]:
    detail = await chat_service.get_chat(db, id, user_id)
    return Msg(code=200, msg="Chat retrieved", data=detail)


@router.post("/", response_model=Msg[ChatDetail])
async def create_chat(
    db: Annotated[AsyncSession, Depends(get_db)],
    user_id: Annotated[UUID, Depends(get_current_user())],
    data: ChatCreate,
) -> Msg[ChatDetail]:
    chat = await chat_service.create_chat(db, user_id, data.model_id, title=data.title or "New chat")
    return Msg(code=200, msg="Chat created", data=ChatDetail.model_validate(chat))


@router.put("/{id}", response_model=Msg[None])
async def update_chat(
    db: Annotated[AsyncSession, Depends(get_db)],
    user_id: Annotated[UUID, Depends(get_current_user())],
    id: UUID,
    data: ChatUpdate,
) -> Msg[None]:
    if data.title is not None:
        await chat_service.rename_chat(db, id, user_id, data.title)
    return Msg(code=200, msg="Chat updated")


@router.delete("/{id}", response_model=Msg[None])
async def delete_chat(
    db: Annotated[AsyncSession, Depends(get_db)],
    user_id: Annotated[UUID, Depends(get_current_user())],
    id: UUID,
) -> Msg[None]:
    await chat_service.delete_chat(db, id, user_id)
    return Msg(code=200, msg="Chat deleted")
