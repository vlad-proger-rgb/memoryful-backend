from uuid import UUID
from pydantic import BaseModel, ConfigDict


class CountryInDB(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    code: str