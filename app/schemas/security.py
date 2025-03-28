import datetime as dt
from pydantic import BaseModel

class Token(BaseModel):
    access_token: str
    refresh_token: str | None = None
    token_type: str

class Session(BaseModel):
    id: str
    ip_address: str | None = None
    user_agent: str | None = None
    created_at: dt.datetime
    expires_at: dt.datetime
