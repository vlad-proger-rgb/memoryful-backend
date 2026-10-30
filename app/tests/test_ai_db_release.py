"""The model calls run while the session holds no connection, so a slow provider never
pins one from the pool. A fake model records that at the moment it is called.
"""

from collections.abc import AsyncIterator
from typing import Any
from uuid import UUID

import pytest
from langchain_core.messages import AIMessage, AIMessageChunk
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.schemas import AIItem, AIItemList
from app.ai.services import completions
from app.ai.services.completions import ChatAgent
from app.ai.services.day import insights
from app.models import ChatModel, Day, Insight


class FakeLLM:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.holds_connection: list[bool] = []

    def _record(self) -> None:
        # Not in_transaction(): editing a loaded object autobegins one without a connection.
        transaction = self.db.sync_session.get_transaction()
        self.holds_connection.append(bool(transaction and transaction._connections))

    async def ainvoke(self, messages: Any) -> AIMessage:
        self._record()
        return AIMessage(content="A reply")

    async def astream(self, messages: Any) -> AsyncIterator[AIMessageChunk]:
        self._record()
        yield AIMessageChunk(content="A reply")

    def with_structured_output(self, schema: Any) -> "FakeStructured":
        return FakeStructured(self)


class FakeStructured:
    def __init__(self, llm: FakeLLM) -> None:
        self.llm = llm

    async def ainvoke(self, messages: Any) -> AIItemList:
        self.llm._record()
        return AIItemList(items=[AIItem(description="Walked a lot", content="Many steps.")])


async def test_completion_calls_the_model_without_a_connection(
    db: AsyncSession, user_id: UUID, chat_model_id: UUID, monkeypatch: pytest.MonkeyPatch
) -> None:
    llm = FakeLLM(db)
    monkeypatch.setattr(completions, "build_chat_model", lambda _model: llm)
    chat, message = await ChatAgent(db).run_completion(
        user_id, chat_id=None, model_id=chat_model_id, content="Hello"
    )

    assert llm.holds_connection == [False]
    assert message.content == "A reply"
    assert [m["role"] for m in chat.messages] == ["user", "assistant"]


async def test_streamed_completion_calls_the_model_without_a_connection(
    db: AsyncSession, user_id: UUID, chat_model_id: UUID, monkeypatch: pytest.MonkeyPatch
) -> None:
    llm = FakeLLM(db)
    monkeypatch.setattr(completions, "build_chat_model", lambda _model: llm)
    events = [
        event
        async for event in ChatAgent(db).stream_completion(
            user_id, chat_id=None, model_id=chat_model_id, content="Hello"
        )
    ]

    assert llm.holds_connection == [False]
    assert events[-1]["type"] == "done"
    assert events[-1]["content"] == "A reply"


async def test_day_insights_call_the_model_without_a_connection(
    db: AsyncSession,
    user_id: UUID,
    city_id: UUID,
    chat_model_id: UUID,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    timestamp = 1_788_000_000
    db.add(Day(timestamp=timestamp, user_id=user_id, city_id=city_id, content="A long walk."))
    await db.flush()

    async def chat_model_for(session: AsyncSession, **_: Any) -> ChatModel:
        model = await session.get(ChatModel, chat_model_id)
        assert model is not None
        return model

    llm = FakeLLM(db)
    monkeypatch.setattr(insights, "AsyncSessionLocal", lambda: db)
    monkeypatch.setattr(insights, "get_chat_model_for", chat_model_for)
    monkeypatch.setattr(insights, "build_chat_model", lambda _model: llm)
    await insights.generate_day_insights(user_id=user_id, timestamp=timestamp)

    assert llm.holds_connection == [False, False]
    stored = (await db.scalars(select(Insight).where(Insight.user_id == user_id))).all()
    assert len(stored) == 2
