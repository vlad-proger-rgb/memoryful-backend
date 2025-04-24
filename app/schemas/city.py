from uuid import UUID
from pydantic import ConfigDict
from fastapi_camelcase import CamelModel

class CityInDB(CamelModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    country_id: UUID
    name: str
