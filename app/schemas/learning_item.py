from uuid import UUID
from pydantic import ConfigDict
from fastapi_camelcase import CamelModel


class LearningItemBase(CamelModel):
    title: str
    description: str
    icon: str | None = None

class LearningItemInDB(LearningItemBase):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
