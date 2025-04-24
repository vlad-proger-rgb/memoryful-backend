from uuid import UUID
from pydantic import ConfigDict
from fastapi_camelcase import CamelModel

class ChatModelInDB(CamelModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    label: str
    name: str
