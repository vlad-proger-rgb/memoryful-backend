from uuid import UUID
import datetime as dt
from pydantic import ConfigDict
from fastapi_camelcase import CamelModel


class ChatUpdate(CamelModel):
    title: str | None = None
    messages: list[dict[str, str]]

class ChatCreate(ChatUpdate):
    title: str
    model_id: UUID

class ChatInDB(ChatCreate):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    created_at: dt.datetime
