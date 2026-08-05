import datetime as dt
import logging
from collections.abc import AsyncIterator
from uuid import UUID

from fastapi import HTTPException
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.context import ChatContextBuilder
from app.ai.mcp import load_mcp_tools
from app.ai.services.chats import ChatStore
from app.ai.utils import build_chat_model
from app.models import Chat
from app.schemas import MessageSchema, ToolCallSchema

logger = logging.getLogger(__name__)

TITLE_MAX_LEN = 60


def _derive_title(content: str) -> str:
    stripped = " ".join(content.strip().split())
    if len(stripped) <= TITLE_MAX_LEN:
        return stripped or "New chat"
    return stripped[:TITLE_MAX_LEN].rstrip() + "..."


def _extract_text(content: object) -> str:
    """Flatten a model reply to plain text. LangChain 1.x (esp. Gemini) can return
    content blocks, not a string; str() on that leaks a repr, so pull text blocks out."""
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


def _dump(message: MessageSchema) -> dict:
    """JSON-mode dump for the `chats.messages` JSON column: `created_at` has to go
    in as an ISO string, not a datetime."""
    return message.model_dump(mode="json")


def _tool_args(raw: object) -> dict:
    """Shrink tool input to something small and JSON-safe for the UI."""
    if not isinstance(raw, dict):
        return {}
    args: dict = {}
    for key, value in raw.items():
        if value is None or isinstance(value, (str, int, float, bool)):
            args[key] = value
        else:
            args[key] = str(value)
    return args


def _to_lc_history(messages: list[dict[str, str]]) -> list:
    """Flat {role, content} history -> LangChain messages. No system message: the
    plain path prepends it, the agent path passes system_prompt to create_agent."""
    lc_messages: list = []
    for m in messages:
        if m["role"] == "user":
            lc_messages.append(HumanMessage(content=m["content"]))
        elif m["role"] == "assistant":
            lc_messages.append(AIMessage(content=m["content"]))
        elif m["role"] == "system":
            lc_messages.append(SystemMessage(content=m["content"]))
    return lc_messages


class ChatAgent:
    """Runs a single chat turn: model routing + optional MCP tool loop, persisting
    via ChatStore. One instance per request."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.store = ChatStore(db)
        self.context = ChatContextBuilder(db)

    async def run_completion(
        self,
        user_id: UUID,
        *,
        chat_id: UUID | None,
        model_id: UUID | None,
        content: str,
        access_token: str | None = None,
    ) -> tuple[Chat, MessageSchema]:
        is_new_chat = chat_id is None

        if is_new_chat:
            if not model_id:
                raise HTTPException(400, "model_id is required to start a new chat")
            chat = await self.store.create(user_id, model_id, title=_derive_title(content))
        else:
            chat = await self.store.load(chat_id, user_id)

        user_message = MessageSchema(
            role="user", content=content, created_at=dt.datetime.now(dt.UTC)
        )
        chat.messages = [*chat.messages, _dump(user_message)]

        reply_text = await self._generate_reply(chat, access_token)
        assistant_message = MessageSchema(
            role="assistant", content=reply_text, created_at=dt.datetime.now(dt.UTC)
        )

        chat.messages = [*chat.messages, _dump(assistant_message)]
        chat = await self.store.persist(chat, user_id, invalidate_list=is_new_chat)

        return chat, assistant_message

    async def stream_completion(
        self,
        user_id: UUID,
        *,
        chat_id: UUID | None,
        model_id: UUID | None,
        content: str,
        access_token: str | None = None,
    ) -> AsyncIterator[dict]:
        """Same turn as `run_completion`, but yielded as events: a `start`, then
        `token` / `toolCall` / `toolResult` as they happen, then `done` once the
        reply is persisted. Only the final text is stored (tool steps are transient).
        """
        is_new_chat = chat_id is None

        if is_new_chat:
            if not model_id:
                raise HTTPException(400, "model_id is required to start a new chat")
            chat = await self.store.create(user_id, model_id, title=_derive_title(content))
        else:
            chat = await self.store.load(chat_id, user_id)

        user_message = MessageSchema(
            role="user", content=content, created_at=dt.datetime.now(dt.UTC)
        )
        chat.messages = [*chat.messages, _dump(user_message)]

        yield {
            "type": "start",
            "chatId": str(chat.id),
            "title": chat.title,
            "createdAt": user_message.created_at.isoformat(),
        }

        # Text is collected per model turn: a turn that ends in a tool call is a
        # preamble ("let me check..."), so segments are joined with a blank line to
        # read the same on reload as it did while streaming.
        segments: list[str] = []
        current: list[str] = []
        tools: list[ToolCallSchema] = []
        async for event in self._stream_reply(chat, access_token):
            if event["type"] == "token":
                current.append(event["text"])
            elif event["type"] == "toolCall":
                tools.append(ToolCallSchema(name=event["name"], args=event.get("args") or {}))
                if current:
                    segments.append("".join(current))
                    current = []
            yield event

        if current:
            segments.append("".join(current))
        reply_text = "\n\n".join(s.strip() for s in segments if s.strip())

        assistant_message = MessageSchema(
            role="assistant",
            content=reply_text,
            tools=tools,
            created_at=dt.datetime.now(dt.UTC),
        )
        chat.messages = [*chat.messages, _dump(assistant_message)]
        chat = await self.store.persist(chat, user_id, invalidate_list=is_new_chat)

        yield {
            "type": "done",
            "chatId": str(chat.id),
            "title": chat.title,
            "content": reply_text,
            "createdAt": assistant_message.created_at.isoformat(),
        }

    async def _stream_reply(self, chat: Chat, access_token: str | None) -> AsyncIterator[dict]:
        """Stream the reply, preferring the tool loop. If the agent fails before
        emitting anything we fall back to a plain stream; if it fails mid-stream we
        surface an error instead, so the user never sees duplicated text."""
        system_prompt = await self.context.system_prompt(chat.user_id)
        llm = build_chat_model(chat.chat_model)
        history = _to_lc_history(chat.messages)

        if chat.chat_model.supports_tools and access_token:
            emitted = False
            try:
                async for event in self._stream_agent(llm, system_prompt, history, access_token):
                    emitted = True
                    yield event
            except Exception:
                logger.exception("MCP agent stream failed (emitted=%s)", emitted)
                if emitted:
                    yield {
                        "type": "error",
                        "message": "The assistant stopped early. Please try again.",
                    }
                    return
            else:
                return

        async for event in self._stream_plain(llm, system_prompt, history):
            yield event

    async def _stream_agent(
        self, llm, system_prompt: str, history: list, access_token: str
    ) -> AsyncIterator[dict]:
        from langchain.agents import create_agent

        tools = await load_mcp_tools(access_token)
        agent = create_agent(llm, tools, system_prompt=system_prompt)

        async for event in agent.astream_events({"messages": history}):
            kind = event.get("event")
            if kind == "on_chat_model_stream":
                chunk = event.get("data", {}).get("chunk")
                text = _extract_text(getattr(chunk, "content", "")) if chunk is not None else ""
                if text:
                    yield {"type": "token", "text": text}
            elif kind == "on_tool_start":
                yield {
                    "type": "toolCall",
                    "name": event.get("name", ""),
                    "args": _tool_args(event.get("data", {}).get("input")),
                }
            elif kind == "on_tool_end":
                yield {"type": "toolResult", "name": event.get("name", "")}

    async def _stream_plain(self, llm, system_prompt: str, history: list) -> AsyncIterator[dict]:
        async for chunk in llm.astream([SystemMessage(content=system_prompt), *history]):
            text = _extract_text(chunk.content)
            if text:
                yield {"type": "token", "text": text}

    async def _generate_reply(self, chat: Chat, access_token: str | None) -> str:
        """Reply to the chat's current history. Tool-capable models with a bearer run
        the MCP loop; everything else (and any MCP failure) falls back to plain completion."""
        system_prompt = await self.context.system_prompt(chat.user_id)
        llm = build_chat_model(chat.chat_model)
        history = _to_lc_history(chat.messages)

        if chat.chat_model.supports_tools and access_token:
            try:
                return await self._run_agent(llm, system_prompt, history, access_token)
            except Exception:
                logger.exception("MCP agent loop failed; falling back to plain completion")

        response = await llm.ainvoke([SystemMessage(content=system_prompt), *history])
        return _extract_text(response.content)

    async def _run_agent(self, llm, system_prompt: str, history: list, access_token: str) -> str:
        """Run the MCP tool loop over the (cached) tools for this bearer, which the
        MCP server executes as that user (per-user isolation)."""
        from langchain.agents import create_agent

        tools = await load_mcp_tools(access_token)
        agent = create_agent(llm, tools, system_prompt=system_prompt)
        result = await agent.ainvoke({"messages": history})

        # Persist only the final assistant text: the last AIMessage with non-empty
        # content (trailing tool-call AIMessages are empty).
        for message in reversed(result.get("messages", [])):
            if isinstance(message, AIMessage):
                text = _extract_text(message.content)
                if text:
                    return text
        return ""
