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
    city: "CityInDB"
    trackable_progresses: list["DayTrackableProgress"] = Field(default_factory=list)


class DayDetail(DayBase):
    content: str
    city: "CityDetail"
    description: str | None = None
    steps: int = 0
    starred: bool = False
    main_image: str | None = None
    created_at: dt.datetime
    updated_at: dt.datetime
    completed_at: dt.datetime | None = None
    ai_generated_at: dt.datetime | None = None
    images: list[str] | None = Field(default_factory=list)
    trackable_progresses: list["TrackableTypeWithProgress"] = Field(default_factory=list, description="List of trackable types with their associated progresses")
    tags: list["TagInDB"] | None = Field(default_factory=list)
    insights: list["InsightInDB"] | None = Field(default_factory=list, description="List of insights for this day")
    suggestions: list["SuggestionInDB"] | None = Field(default_factory=list, description="List of suggestions for this day")


class DayCreate(CamelModel):
    city_id: UUID
    description: str | None = None
    content: str
    steps: int = 0
    main_image: str | None = None
    images: list[str] | None = Field(default_factory=list)
    trackable_progresses: list["DayTrackableProgressUpdate"] = Field(default_factory=list)
    tags: list[UUID] = Field(default_factory=list)


class DayUpdate(CamelModel):
    city_id: UUID | None = None
    description: str | None = None
    content: str | None = None
    steps: int | None = None
    starred: bool | None = None
    main_image: str | None = None
    images: list[str] | None = None
    trackable_progresses: list["DayTrackableProgressUpdate"] | None = None
    tags: list[UUID] | None = None


class DayFilters(CamelModel):
    """Advanced filters for days querying."""
    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True,
    )
    steps: dict[str, int] | None = Field(
        None,
        description="Filter by steps. Operators: gt, lt, gte, lte, eq, ne. Example: {'gt': 5000}",
    )
    description: dict[str, str] | None = Field(
        None,
        description="Filter by description. Operators: like, eq, ne. Example: {'like': 'park'}",
    )
    starred: bool | None = Field(
        None, description="Filter by starred status"
    )
    city_id: UUID | None = Field(
        None, description="Filter by city ID", alias="cityId"
    )
    country_id: str | None = Field(
        None, description="Filter by country ID", alias="countryId"
    )
    created_after: int | None = Field(
        None, description="Filter by creation timestamp (after)", alias="createdAfter"
    )
    created_before: int | None = Field(
        None, description="Filter by creation timestamp (before)", alias="createdBefore"
    )


from .city import CityInDB, CityDetail
from .tag import TagInDB
from .day_trackable_progress import DayTrackableProgress, DayTrackableProgressUpdate, TrackableTypeWithProgress
from .insight import InsightInDB
from .suggestion import SuggestionInDB
