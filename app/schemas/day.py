from uuid import UUID
import datetime as dt
from pydantic import ConfigDict, Field
from fastapi_camelcase import CamelModel


class DayBase(CamelModel):
    model_config = ConfigDict(from_attributes=True)
    timestamp: int


class DayListItem(DayBase):
    description: str | None = None
    steps: int = 0
    starred: bool = False
    main_image: str | None = None
    city: "CityBase"
    learning_progresses: list["LearningProgress"] = Field(default_factory=list)


class DayDetail(DayBase):
    content: str
    city_id: UUID
    description: str | None = None
    steps: int = 0
    starred: bool = False
    main_image: str | None = None
    created_at: dt.datetime
    updated_at: dt.datetime
    images: list[str] = Field(default_factory=list)
    learning_progresses: list["LearningProgress"] = Field(default_factory=list)


class DayCreate(CamelModel):
    city_id: UUID
    description: str | None = None
    content: str
    steps: int = 0
    main_image: str | None = None
    images: list[str] = Field(default_factory=list)
    learning_progresses: list["LearningProgressUpdate"] = Field(default_factory=list)


class DayUpdate(CamelModel):
    city_id: UUID | None = None
    description: str | None = None
    content: str | None = None
    steps: int | None = None
    starred: bool | None = None
    main_image: str | None = None
    images: list[str] | None = None
    learning_progresses: list["LearningProgressUpdate"] | None = None

from .learning_progress import LearningProgress, LearningProgressUpdate
from .city import CityBase
