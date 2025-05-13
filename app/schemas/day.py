from uuid import UUID
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
    learning_items: list["LearningItemBase"] = Field(default_factory=list)


class DayDetail(DayBase):
    content: str
    city_id: UUID
    description: str | None = None
    steps: int = 0
    starred: bool = False
    main_image: str | None = None
    images: list[str] = Field(default_factory=list)
    learning_progresses: list["LearningProgress"] = Field(default_factory=list)


class DayCreate(CamelModel):
    timestamp: int
    city_id: UUID
    description: str | None = None
    content: str
    steps: int = 0
    main_image: str | None = None
    images: list[str] = Field(default_factory=list)
    learning_progresses: list["LearningProgress"] = Field(default_factory=list)


class DayUpdate(CamelModel):
    city_id: UUID | None = None
    content: str | None = None
    description: str | None = None
    steps: int | None = None
    starred: bool | None = None
    main_image: str | None = None
    images: list[str] | None = None
    learning_progresses: list["LearningProgress"] | None = None

from .learning_progress import LearningProgress
from .learning_item import LearningItemBase
from .city import CityBase
