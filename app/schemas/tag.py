from uuid import UUID
from pydantic import BaseModel, ConfigDict

class TagBase(BaseModel):
    name: str
    icon: str | None = None
    color: str | None = None

class TagInDB(TagBase):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    user_id: UUID
