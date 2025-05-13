from uuid import UUID
import datetime as dt
from fastapi_camelcase import CamelModel

class Token(CamelModel):
    access_token: str
    refresh_token: str | None = None
    token_type: str

class AuthResponse(CamelModel):
    tokens: Token
    is_new_user: bool
    user_id: UUID

class Session(CamelModel):
    id: UUID
    ip_address: str | None = None
    user_agent: str | None = None
    created_at: dt.datetime
    expires_at: dt.datetime
