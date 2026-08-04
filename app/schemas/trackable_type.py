from uuid import UUID

from fastapi_camelcase import CamelModel
from pydantic import ConfigDict


class TrackableTypeBase(CamelModel):
    name: str
    description: str | None = None
    value_type: str
    icon: "FAIcon | None" = None
    meta_schema: dict | None = None


class TrackableTypeCreate(TrackableTypeBase):
    pass


class TrackableTypeUpdate(CamelModel):
    name: str | None = None
    description: str | None = None
    value_type: str | None = None
    icon: "FAIcon | None" = None
    meta_schema: dict | None = None


class TrackableTypeInDB(TrackableTypeBase):
    model_config = ConfigDict(from_attributes=True)
    id: UUID


from app.schemas.font_awesome import FAIcon
