import logging
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.models import Chat
from app.schemas import MessageSchema
from app.ai.utils import build_chat_model
from app.ai.context import ChatContextBuilder
from app.ai.mcp import load_mcp_tools
from app.ai.services.chats import ChatStore

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

        user_message = MessageSchema(role="user", content=content)
        chat.messages = [*chat.messages, user_message.model_dump()]

        reply_text = await self._generate_reply(chat, access_token)
        assistant_message = MessageSchema(role="assistant", content=reply_text)

        chat.messages = [*chat.messages, assistant_message.model_dump()]
        chat = await self.store.persist(chat, user_id, invalidate_list=is_new_chat)

        return chat, assistant_message

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
