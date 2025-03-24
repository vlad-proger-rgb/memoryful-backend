from uuid import UUID
from pydantic import BaseModel, ConfigDict

class CityInDB(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    country_id: UUID
    name: str
