from uuid import UUID
from pydantic import Field, ConfigDict
from fastapi_camelcase import CamelModel


class DayTrackableProgress(CamelModel):
    model_config = ConfigDict(from_attributes=True)
    value: float = Field(..., description="The value of the progress (e.g., minutes, steps, pages)")
    description: str | None
    trackable_item: "TrackableDetail"

class DayTrackableProgressUpdate(CamelModel):
    model_config = ConfigDict(from_attributes=True)
    value: float = Field(..., description="The value of the progress (e.g., minutes, steps, pages)")
    description: str | None = None
    trackable_item_id: UUID = Field(..., description="ID of the trackable item")

class TrackableTypeWithProgress(CamelModel):
    type: "TrackableTypeInDB" = Field(..., description="The trackable type information")
    progresses: list["DayTrackableProgress"] = Field(default_factory=list, description="List of progresses for this type")


from .trackable import TrackableDetail
from .trackable_type import TrackableTypeInDB
