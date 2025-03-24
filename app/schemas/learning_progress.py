from uuid import UUID
from pydantic import BaseModel, Field

class LearningProgress(BaseModel):
    learning_item_id: UUID
    time_involved: int = Field(gt=0, le=60*24, description="Time in minutes")
