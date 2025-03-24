from uuid import UUID
from pydantic import BaseModel, ConfigDict

class ChatModelInDB(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    label: str
    name: str
