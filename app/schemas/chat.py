from uuid import UUID
import datetime as dt
from typing import Literal
from pydantic import ConfigDict
from fastapi_camelcase import CamelModel


class MessageSchema(CamelModel):
    role: Literal["system", "user", "assistant"]
    content: str


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


from .chat_model import ChatModelInDB
