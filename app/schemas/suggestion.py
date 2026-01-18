import datetime as dt
from uuid import UUID

from pydantic import ConfigDict
from fastapi_camelcase import CamelModel

from app.schemas.font_awesome import FAIcon


class SuggestionInDB(CamelModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    user_id: UUID
    model_id: UUID
    timestamp: int
    description: str
    icon: FAIcon | None = None
    date: dt.date
    content: str
