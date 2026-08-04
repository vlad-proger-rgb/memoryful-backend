from uuid import UUID

from fastapi_camelcase import CamelModel
from pydantic import ConfigDict


class CountryInDB(CamelModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    code: str
