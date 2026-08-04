import datetime as dt
from uuid import UUID

from fastapi_camelcase import CamelModel
from pydantic import ConfigDict, EmailStr

from app.schemas.city import CityInDB
from app.schemas.country import CountryInDB


class UserBase(CamelModel):
    country: CountryInDB | None = None
    city: CityInDB | None = None
    first_name: str | None = None
    last_name: str | None = None
    age: int | None = None
    bio: str | None = None
    photo: str | None = None


class UserInDB(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    is_enabled: bool
    created_at: dt.datetime
