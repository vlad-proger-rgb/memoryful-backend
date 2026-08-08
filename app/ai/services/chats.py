import datetime as dt
import json
import logging
from typing import Any, cast
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import CursorResult, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.constants import CACHE_TTL_CHAT_HOT, CACHE_TTL_USER_DATA
from app.core.config import redis
from app.enums import RedisPrefix
from app.models import Chat, ChatModel
from app.schemas import ChatDetail, ChatListItem

logger = logging.getLogger(__name__)


def _chat_key(chat_id: UUID) -> str:
    return f"{RedisPrefix.chat}{chat_id}"


def _chat_list_key(user_id: UUID) -> str:
    return f"{RedisPrefix.chat_list}{user_id}"


class ChatStore:
    """Persistence + write-through Redis cache for chats. One instance per request
    (holds the session); DB is the source of truth."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def _cache(self, chat: Chat) -> None:
        detail = ChatDetail.model_validate(chat)
        await redis.set(_chat_key(chat.id), detail.model_dump_json(), ex=CACHE_TTL_CHAT_HOT)

    async def _invalidate_list(self, user_id: UUID) -> None:
        await redis.delete(_chat_list_key(user_id))

    async def load(self, chat_id: UUID, user_id: UUID) -> Chat:
        """Load the ORM `Chat` (with `chat_model`) or 404 — for mutations/agent
        that need the live object, not the cached `ChatDetail`."""
        stmt = (
            select(Chat)
            .options(selectinload(Chat.chat_model))
            .where(Chat.id == chat_id, Chat.user_id == user_id, Chat.is_deleted == False)
        )  # fmt: skip
        chat = await self.db.scalar(stmt)
        if not chat:
            raise HTTPException(404, "Chat not found")
        return chat

    async def get(self, chat_id: UUID, user_id: UUID) -> ChatDetail:
        """Read-through: try the hot cache first, fall back to DB on miss."""
        cached = await redis.get(_chat_key(chat_id))
        if cached:
            detail = ChatDetail.model_validate_json(cached)
            if detail.user_id == user_id:
                return detail

        chat = await self.load(chat_id, user_id)
        await self._cache(chat)
        return ChatDetail.model_validate(chat)

    async def list(
        self,
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
        )  # fmt: skip
        if query:
            stmt = stmt.where(Chat.title.ilike(f"%{query}%"))

        result = await self.db.execute(stmt)
        chats = result.scalars().all()
        items = [ChatListItem.model_validate(chat) for chat in chats]

        if use_cache:
            payload = json.dumps([item.model_dump(mode="json") for item in items])
            await redis.set(_chat_list_key(user_id), payload, ex=CACHE_TTL_USER_DATA)

        return items

    async def create(self, user_id: UUID, model_id: UUID, title: str = "New chat") -> Chat:
        chat_model = await self.db.get(ChatModel, model_id)
        if not chat_model:
            raise HTTPException(404, "Chat Model not found")

        chat = Chat(user_id=user_id, model_id=model_id, title=title, messages=[])
        self.db.add(chat)
        await self.db.commit()
        await self.db.refresh(chat)
        chat.chat_model = chat_model

        await self._cache(chat)
        await self._invalidate_list(user_id)
        return chat

    async def rename(self, chat_id: UUID, user_id: UUID, title: str) -> None:
        # is_deleted filter + rowcount check: never rename a deleted/missing chat.
        stmt = (
            update(Chat)
            .where(Chat.id == chat_id, Chat.user_id == user_id, Chat.is_deleted == False)
            .values(title=title)
        )  # fmt: skip
        result = cast("CursorResult[Any]", await self.db.execute(stmt))
        if result.rowcount == 0:
            raise HTTPException(404, "Chat not found")
        await self.db.commit()

        chat = await self.load(chat_id, user_id)
        await self._cache(chat)
        await self._invalidate_list(user_id)

    async def delete(self, chat_id: UUID, user_id: UUID) -> None:
        stmt = (
            update(Chat).where(Chat.id == chat_id, Chat.user_id == user_id).values(is_deleted=True)
        )
        await self.db.execute(stmt)
        await self.db.commit()

        await redis.delete(_chat_key(chat_id))
        await self._invalidate_list(user_id)

    async def persist(self, chat: Chat, user_id: UUID, *, invalidate_list: bool = False) -> Chat:
        """Commit pending changes (e.g. appended messages), refresh cache from a
        clean reload, return it."""
        chat.updated_at = dt.datetime.now(dt.UTC)
        await self.db.commit()

        fresh = await self.load(chat.id, user_id)
        await self._cache(fresh)
        if invalidate_list:
            await self._invalidate_list(user_id)
        return fresh
