import datetime as dt
from uuid import UUID

from fastapi_camelcase import CamelModel
from pydantic import ConfigDict

from app.enums import InsightKind
from app.schemas.chat_model import ChatModelRef
from app.schemas.font_awesome import FAIcon


class InsightInDB(CamelModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    user_id: UUID
    chat_model: ChatModelRef
    timestamp: int
    kind: InsightKind
    description: str
    icon: FAIcon | None = None
    content: str
    created_at: dt.datetime
