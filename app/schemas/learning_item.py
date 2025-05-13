from uuid import UUID
from pydantic import ConfigDict
from fastapi_camelcase import CamelModel


class LearningItemBase(CamelModel):
    model_config = ConfigDict(from_attributes=True)
    title: str

class LearningItemCreate(LearningItemBase):
    description: str | None = None
    icon: str | None = None

class LearningItemInDB(LearningItemCreate):
    id: UUID
