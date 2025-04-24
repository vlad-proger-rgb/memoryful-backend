from uuid import UUID
from pydantic import ConfigDict
from fastapi_camelcase import CamelModel


class CountryInDB(CamelModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    code: str