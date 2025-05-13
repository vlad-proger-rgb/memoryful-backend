from typing import Annotated, Literal
from uuid import UUID

from fastapi import (
    APIRouter,
    HTTPException,
    Depends,
    Query,
)
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, load_only

from app.core.database import get_db
from app.models import Chat, ChatModel
from app.core.deps import get_current_user
from app.schemas import (
    Msg,
    ChatListItem,
    ChatDetail,
    ChatCreate,
    ChatUpdate,
)


router = APIRouter(
    prefix="/chats",
    tags=["Chats"],
)


@router.get("/")
async def get_chats(
    db: Annotated[AsyncSession, Depends(get_db)],
    user_id: Annotated[UUID, Depends(get_current_user())],
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    query: str | None = Query(None, description="Substring to search for in chat title"),
    view: Literal["list", "detail"] = Query("list", description="View type to return"),
) -> Msg[list[ChatListItem | ChatDetail]]:
    stmt = (
        select(Chat)
        .where(Chat.user_id == user_id, Chat.is_deleted == False)
        .order_by(Chat.created_at.desc())
        .limit(limit)
        .offset(offset)
    )

    if query:
        stmt = stmt.where(Chat.title.ilike(f"%{query}%"))

    if view == "list":
        stmt = stmt.options(
            load_only(Chat.id, Chat.title, Chat.created_at)
        )
    else:
        stmt = stmt.options(selectinload(Chat.chat_model))

    result = await db.execute(stmt)
    chats = list(result.scalars().unique())

    response_model = ChatDetail if view == "detail" else ChatListItem
    return Msg(
        code=200,
        msg="Chats retrieved",
        data=[response_model.model_validate(chat) for chat in chats]
    )


@router.get("/{id}", response_model=Msg[ChatDetail])
async def get_chat(
    db: Annotated[AsyncSession, Depends(get_db)],
    user_id: Annotated[UUID, Depends(get_current_user())],
    id: UUID,
) -> Msg[ChatDetail]:
    stmt = (
        select(Chat)
        .options(selectinload(Chat.chat_model))
        .where(Chat.id == id, Chat.user_id == user_id, Chat.is_deleted == False)
    )
    result = await db.execute(stmt)
    chat = result.scalar_one_or_none()

    if not chat:
        raise HTTPException(404, "Chat not found")

    return Msg(code=200, msg="Chat retrieved", data=ChatDetail.model_validate(chat))


@router.post("/", response_model=Msg[UUID])
async def create_chat(
    db: Annotated[AsyncSession, Depends(get_db)],
    user_id: Annotated[UUID, Depends(get_current_user())],
    data: ChatCreate,
) -> Msg[UUID]:
    stmt = select(ChatModel).where(ChatModel.id == data.model_id)
    chat_model = await db.scalar(stmt)
    if not chat_model:
        raise HTTPException(404, "Chat Model not found")

    chat = Chat(**data.model_dump(), user_id=user_id)
    db.add(chat)
    await db.commit()
    await db.refresh(chat)

    return Msg(code=200, msg="Chat created", data=chat.id)


@router.put("/{id}", response_model=Msg[None])
async def update_chat(
    db: Annotated[AsyncSession, Depends(get_db)],
    user_id: Annotated[UUID, Depends(get_current_user())],
    id: UUID,
    data: ChatUpdate,
) -> Msg[None]:
    stmt = (
        update(Chat)
        .where(Chat.id == id, Chat.user_id == user_id)
        .values(**data.model_dump(exclude_unset=True))
    )
    await db.execute(stmt)
    await db.commit()

    return Msg(code=200, msg="Chat updated")


@router.delete("/{id}", response_model=Msg[None])
async def delete_chat(
    db: Annotated[AsyncSession, Depends(get_db)],
    user_id: Annotated[UUID, Depends(get_current_user())],
    id: UUID,
) -> Msg[None]:
    stmt = (
        update(Chat)
        .where(Chat.id == id, Chat.user_id == user_id)
        .values(is_deleted=True)
    )
    await db.execute(stmt)
    await db.commit()

    return Msg(code=200, msg="Chat deleted")

