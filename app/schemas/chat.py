import datetime as dt
from typing import Literal
from uuid import UUID

from fastapi_camelcase import CamelModel
from pydantic import ConfigDict


class ToolCallSchema(CamelModel):
    """A tool the assistant ran while producing a message."""

    name: str
    args: dict = {}  # noqa: RUF012  # Pydantic copies mutable defaults per instance


class MessageSchema(CamelModel):
    role: Literal["system", "user", "assistant"]
    content: str
    # Both optional: messages stored before these existed simply don't have them
    # (the column is JSON, so there's nothing to migrate).
    tools: list[ToolCallSchema] = []  # noqa: RUF012
    created_at: dt.datetime | None = None


class ChatUpdate(CamelModel):
    title: str | None = None
    messages: list[MessageSchema] | None = None


class ChatCreate(CamelModel):
    title: str
    model_id: UUID
    messages: list[MessageSchema]


class ChatBase(CamelModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    title: str


class ChatListItem(ChatBase):
    created_at: dt.datetime


class ChatDetail(ChatBase):
    user_id: UUID
    model_id: UUID
    messages: list[MessageSchema]
    created_at: dt.datetime
    updated_at: dt.datetime
    chat_model: "ChatModelInDB"


class CompletionCreate(CamelModel):
    chat_id: UUID | None = None
    model_id: UUID | None = None
    content: str


class CompletionResponse(CamelModel):
    chat_id: UUID
    title: str
    message: MessageSchema


from .chat_model import ChatModelInDB
