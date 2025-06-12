from uuid import UUID
from pydantic import ConfigDict
from fastapi_camelcase import CamelModel

class TrackableTypeInDB(CamelModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    description: str | None = None
    value_type: str
    icon: str | None = None
    meta: dict | None = None
