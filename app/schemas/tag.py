from uuid import UUID
from pydantic import ConfigDict
from fastapi_camelcase import CamelModel

from app.schemas.font_awesome import FAIcon


class TagBase(CamelModel):
    name: str
    icon: FAIcon | None = None
    color: str | None = None

class TagInDB(TagBase):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
