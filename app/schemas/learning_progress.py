from uuid import UUID
from pydantic import Field
from fastapi_camelcase import CamelModel


class LearningProgress(CamelModel):
    learning_item_id: UUID
    time_involved: int = Field(gt=0, le=60*24, description="Time in minutes")
