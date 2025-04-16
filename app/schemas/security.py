from uuid import UUID
import datetime as dt
from pydantic import BaseModel

class Token(BaseModel):
    access_token: str
    refresh_token: str = None
    token_type: str

class AuthResponse(BaseModel):
    tokens: Token
    is_new_user: bool
    user_id: UUID

class Session(BaseModel):
    id: UUID
    ip_address: str | None = None
    user_agent: str | None = None
    created_at: dt.datetime
    expires_at: dt.datetime
