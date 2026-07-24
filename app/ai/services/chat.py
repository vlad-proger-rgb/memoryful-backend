import datetime as dt
import json
import logging
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.core.config import redis
from app.core.settings import RP_CHAT, RP_CHAT_LIST, CACHE_TTL_CHAT_HOT, CACHE_TTL_USER_DATA
from app.models import Chat, ChatModel
from app.schemas import ChatDetail, ChatListItem, MessageSchema
from app.ai.utils import load_prompt, build_chat_model

logger = logging.getLogger(__name__)

TITLE_MAX_LEN = 60


def _chat_key(chat_id: UUID) -> str:
    return f"{RP_CHAT}{chat_id}"


def _chat_list_key(user_id: UUID) -> str:
    return f"{RP_CHAT_LIST}{user_id}"


async def _cache_chat(chat: Chat) -> None:
    """Write-through: refresh the hot cache for a chat. DB stays the source of truth."""
    detail = ChatDetail.model_validate(chat)
    await redis.set(_chat_key(chat.id), detail.model_dump_json(), ex=CACHE_TTL_CHAT_HOT)


async def _invalidate_chat_list(user_id: UUID) -> None:
    await redis.delete(_chat_list_key(user_id))


async def _load_chat_from_db(db: AsyncSession, chat_id: UUID, user_id: UUID) -> Chat:
    stmt = (
        select(Chat)
        .options(selectinload(Chat.chat_model))
        .where(Chat.id == chat_id, Chat.user_id == user_id, Chat.is_deleted == False)
    )
    chat = await db.scalar(stmt)
    if not chat:
        raise HTTPException(404, "Chat not found")
    return chat


async def get_chat(db: AsyncSession, chat_id: UUID, user_id: UUID) -> ChatDetail:
    """Read-through: try the hot cache first, fall back to DB on miss."""
    cached = await redis.get(_chat_key(chat_id))
    if cached:
        detail = ChatDetail.model_validate_json(cached)
        if detail.user_id == user_id:
            return detail

    chat = await _load_chat_from_db(db, chat_id, user_id)
    await _cache_chat(chat)
    return ChatDetail.model_validate(chat)


async def list_chats(
    db: AsyncSession,
    user_id: UUID,
    *,
    limit: int = 20,
    offset: int = 0,
    query: str | None = None,
) -> list[ChatListItem]:
    # Only cache the default (unfiltered, first-page) view; anything else hits the DB directly.
    use_cache = not query and offset == 0
    if use_cache:
        cached = await redis.get(_chat_list_key(user_id))
        if cached:
            items = [ChatListItem.model_validate(item) for item in json.loads(cached)]
            return items[:limit]

    stmt = (
        select(Chat)
        .where(Chat.user_id == user_id, Chat.is_deleted == False)
        .order_by(Chat.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    if query:
        stmt = stmt.where(Chat.title.ilike(f"%{query}%"))

    result = await db.execute(stmt)
    chats = result.scalars().all()
    items = [ChatListItem.model_validate(chat) for chat in chats]

    if use_cache:
        payload = json.dumps([item.model_dump(mode="json") for item in items])
        await redis.set(_chat_list_key(user_id), payload, ex=CACHE_TTL_USER_DATA)

    return items


async def create_chat(db: AsyncSession, user_id: UUID, model_id: UUID, title: str = "New chat") -> Chat:
    chat_model = await db.get(ChatModel, model_id)
    if not chat_model:
        raise HTTPException(404, "Chat Model not found")

    chat = Chat(user_id=user_id, model_id=model_id, title=title, messages=[])
    db.add(chat)
    await db.commit()
    await db.refresh(chat)
    chat.chat_model = chat_model

    await _cache_chat(chat)
    await _invalidate_chat_list(user_id)
    return chat


async def rename_chat(db: AsyncSession, chat_id: UUID, user_id: UUID, title: str) -> None:
    stmt = update(Chat).where(Chat.id == chat_id, Chat.user_id == user_id).values(title=title)
    await db.execute(stmt)
    await db.commit()

    chat = await _load_chat_from_db(db, chat_id, user_id)
    await _cache_chat(chat)
    await _invalidate_chat_list(user_id)


async def delete_chat(db: AsyncSession, chat_id: UUID, user_id: UUID) -> None:
    stmt = update(Chat).where(Chat.id == chat_id, Chat.user_id == user_id).values(is_deleted=True)
    await db.execute(stmt)
    await db.commit()

    await redis.delete(_chat_key(chat_id))
    await _invalidate_chat_list(user_id)


def _derive_title(content: str) -> str:
    stripped = " ".join(content.strip().split())
    if len(stripped) <= TITLE_MAX_LEN:
        return stripped or "New chat"
    return stripped[:TITLE_MAX_LEN].rstrip() + "..."


def _extract_text(content: object) -> str:
    """Flatten a model reply to plain text.

    LangChain 1.x models (Gemini especially) return a list of content blocks
    rather than a string, and each block may carry provider metadata such as
    thought signatures. str() on that leaks a Python repr into the chat, so
    pull out the text blocks explicitly.
    """
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and block.get("type") == "text":
                text = block.get("text")
                if isinstance(text, str):
                    parts.append(text)
        return "".join(parts)

    return str(content)


def _to_langchain_messages(system_prompt: str, messages: list[dict[str, str]]) -> list:
    lc_messages: list = [SystemMessage(content=system_prompt)]
    for m in messages:
        if m["role"] == "user":
            lc_messages.append(HumanMessage(content=m["content"]))
        elif m["role"] == "assistant":
            lc_messages.append(AIMessage(content=m["content"]))
        elif m["role"] == "system":
            lc_messages.append(SystemMessage(content=m["content"]))
    return lc_messages


async def run_completion(
    db: AsyncSession,
    user_id: UUID,
    *,
    chat_id: UUID | None,
    model_id: UUID | None,
    content: str,
) -> tuple[Chat, MessageSchema]:
    is_new_chat = chat_id is None

    if is_new_chat:
        if not model_id:
            raise HTTPException(400, "model_id is required to start a new chat")
        chat = await create_chat(db, user_id, model_id, title=_derive_title(content))
    else:
        chat = await _load_chat_from_db(db, chat_id, user_id)

    user_message = MessageSchema(role="user", content=content)
    chat.messages = [*chat.messages, user_message.model_dump()]

    system_prompt = load_prompt("chat_system.md")
    llm = build_chat_model(chat.chat_model)
    lc_messages = _to_langchain_messages(system_prompt, chat.messages)

    response = await llm.ainvoke(lc_messages)
    reply_text = _extract_text(response.content)
    assistant_message = MessageSchema(role="assistant", content=reply_text)

    chat.messages = [*chat.messages, assistant_message.model_dump()]
    chat.updated_at = dt.datetime.now(dt.UTC)
    await db.commit()

    chat = await _load_chat_from_db(db, chat.id, user_id)
    await _cache_chat(chat)
    if is_new_chat:
        await _invalidate_chat_list(user_id)

    return chat, assistant_message
