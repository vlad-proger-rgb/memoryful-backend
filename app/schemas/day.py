from uuid import UUID
from pydantic import ConfigDict, Field
from fastapi_camelcase import CamelModel


class DayBase(CamelModel):
    city_id: UUID
    description: str | None = None
    content: str
    steps: int = 0
    starred: bool = False
    main_image: str | None = None
    images: list[str] = Field(default_factory=list)
    learning_progresses: list["LearningProgress"] = Field(default_factory=list)

class DayCreate(DayBase):
    timestamp: int

class DayUpdate(DayBase):
    city_id: UUID | None = None
    content: str | None = None

class DayInDB(DayCreate):
    model_config = ConfigDict(from_attributes=True)

from .learning_progress import LearningProgress