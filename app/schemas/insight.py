import datetime as dt
from uuid import UUID

from pydantic import ConfigDict
from fastapi_camelcase import CamelModel

from app.schemas.font_awesome import FAIcon


class InsightInDB(CamelModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    user_id: UUID
    model_id: UUID
    insight_type_id: UUID
    date_begin: dt.date
    description: str
    icon: FAIcon | None = None
    content: str
    created_at: dt.datetime
