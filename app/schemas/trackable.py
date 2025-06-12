from uuid import UUID

from pydantic import ConfigDict
from fastapi_camelcase import CamelModel


class TrackableBase(CamelModel):
    model_config = ConfigDict(from_attributes=True)
    title: str
    description: str | None = None
    icon: str | None = None

class TrackableInDB(TrackableBase):
    id: UUID

class TrackableDetail(TrackableInDB):
    meta: dict | None = None

class TrackableCreate(TrackableBase):
    type_id: UUID
    meta: dict | None = None

class TrackableUpdate(CamelModel):
    title: str | None = None
    description: str | None = None
    icon: str | None = None
    meta: dict | None = None
