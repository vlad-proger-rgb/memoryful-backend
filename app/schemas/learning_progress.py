from uuid import UUID
from pydantic import Field, ConfigDict
from fastapi_camelcase import CamelModel


class LearningProgress(CamelModel):
    model_config = ConfigDict(from_attributes=True)
    time_involved: int = Field(gt=0, le=60*24, description="Time in minutes")
    learning_item: "LearningItemInDB"

class LearningProgressUpdate(CamelModel):
    model_config = ConfigDict(from_attributes=True)
    time_involved: int = Field(gt=0, le=60*24, description="Time in minutes")
    learning_item_id: UUID


from .learning_item import LearningItemInDB
