from uuid import UUID
import datetime as dt

from pydantic import BaseModel, ConfigDict, EmailStr


class UserBase(BaseModel):
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
