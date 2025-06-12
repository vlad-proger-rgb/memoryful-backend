from uuid import UUID
import datetime as dt

from pydantic import ConfigDict, EmailStr
from fastapi_camelcase import CamelModel

from app.schemas.country import CountryInDB
from app.schemas.city import CityInDB

class UserBase(CamelModel):
    country: CountryInDB | None = None
    city: CityInDB | None = None
    first_name: str | None = None
    last_name: str | None = None
    age: int | None = None
    bio: str | None = None
    job_title: str | None = None
    photo: str | None = None

class UserInDB(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    is_enabled: bool
    created_at: dt.datetime
