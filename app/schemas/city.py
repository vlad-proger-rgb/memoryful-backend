from uuid import UUID
from pydantic import ConfigDict
from fastapi_camelcase import CamelModel


class CityBase(CamelModel):
    model_config = ConfigDict(from_attributes=True)
    name: str


class CityInDB(CityBase):
    id: UUID
    country_id: UUID
