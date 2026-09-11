from uuid import UUID

from fastapi_camelcase import CamelModel
from pydantic import ConfigDict

from app.enums.provider import Provider


class ChatModelRef(CamelModel):
    """Just enough of a model to name it in the UI."""

    model_config = ConfigDict(from_attributes=True)
    id: UUID
    label: str
    provider: Provider


class ChatModelInDB(CamelModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    label: str
    name: str
    provider: Provider
    supports_tools: bool
