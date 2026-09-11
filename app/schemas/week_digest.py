import datetime as dt
from uuid import UUID

from fastapi_camelcase import CamelModel
from pydantic import ConfigDict

from app.schemas.chat_model import ChatModelRef
from app.schemas.font_awesome import FAIcon


class WeekDigestSection(CamelModel):
    description: str
    icon: FAIcon | None = None
    content: str


class WeekDigestInDB(CamelModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    user_id: UUID
    chat_model: ChatModelRef
    week_start: dt.date
    title: str
    summary: str
    sections: list[WeekDigestSection]
    source_day_count: int
    created_at: dt.datetime
    updated_at: dt.datetime
