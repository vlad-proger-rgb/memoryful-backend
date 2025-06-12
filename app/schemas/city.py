from uuid import UUID
from pydantic import ConfigDict
from fastapi_camelcase import CamelModel


class CityBase(CamelModel):
    model_config = ConfigDict(from_attributes=True)
    name: str


class CityInDB(CityBase):
    id: UUID

class CityDetail(CityInDB):
    country: "CountryInDB"

from .country import CountryInDB
