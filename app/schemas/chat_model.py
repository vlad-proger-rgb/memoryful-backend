from uuid import UUID
from pydantic import ConfigDict
from fastapi_camelcase import CamelModel

from app.enums.provider import Provider


class ChatModelInDB(CamelModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    label: str
    name: str
    provider: Provider
    supports_tools: bool
