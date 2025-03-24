from uuid import UUID
from pydantic import BaseModel, ConfigDict


class LearningItemBase(BaseModel):
    title: str
    description: str
    icon: str | None = None

class LearningItemInDB(LearningItemBase):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
