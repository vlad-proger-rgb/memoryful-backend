import datetime as dt
from uuid import uuid4

from fastapi import HTTPException, Request
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from jose import jwt

from app.core.config import redis
from app.models import User, UserToken
from app.schemas import VerifyCodeForm, Token
from app.core.settings import (
    ALGORITHM,
    ACCESS_SECRET_KEY,
    REFRESH_SECRET_KEY,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    REFRESH_TOKEN_EXPIRE_MINUTES,
    RP_LOGIN_CODE,
)


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl = "/auth/login",
)

TOKEN_SETTINGS = {
    "access": (ACCESS_SECRET_KEY, ACCESS_TOKEN_EXPIRE_MINUTES),
    "refresh": (REFRESH_SECRET_KEY, REFRESH_TOKEN_EXPIRE_MINUTES),
}

def hash_refresh_token(token: str) -> str:
    return pwd_context.hash(token)

def verify_refresh_token(token: str, hashed_token: str) -> bool:
    return pwd_context.verify(token, hashed_token)


def create_token(
    data: dict,
    token_type: str = "access",
    expires_delta: dt.timedelta | None = None,
) -> tuple[str, str]:
    if token_type not in TOKEN_SETTINGS:
        raise ValueError("Invalid token type. Choose 'access' or 'refresh'")

    secret_key, expire_minutes = TOKEN_SETTINGS[token_type]
    expiration_time = (
        dt.datetime.now(dt.UTC) + expires_delta
        if expires_delta
        else dt.datetime.now(dt.UTC) + dt.timedelta(minutes=expire_minutes)
    )

    jti = str(uuid4())
    to_encode = {
        **data,
        "jti": jti,
        "exp": expiration_time,
    }

    return jwt.encode(to_encode, secret_key, ALGORITHM), jti


async def verify_code_form(
    key: str,
    code_form: VerifyCodeForm,
) -> None:
    code = await redis.get(key)

    if not code:
        raise HTTPException(400, "Code not requested")

    if await redis.ttl(key) < 0:
        raise HTTPException(400, "Code expired")

    if code != code_form.code:
        raise HTTPException(400, "Invalid code")

    await redis.delete(key)


async def create_and_store_tokens(
    db: AsyncSession, 
    user: User, 
    request: Request | None = None,
) -> Token:
    data = {"sub": str(user.id)}
    access_token, _ = create_token(data=data, token_type="access")
    refresh_token, jti = create_token(data=data, token_type="refresh")

    token_db = UserToken(
        id=jti,
        user_id=user.id,
        refresh_token_hash=hash_refresh_token(refresh_token),
        expires_at=dt.datetime.now(dt.UTC) + dt.timedelta(minutes=REFRESH_TOKEN_EXPIRE_MINUTES),
    )

    if request:
        token_db.ip_address = request.client.host if request.client else None
        token_db.user_agent = request.headers.get("user-agent")

    db.add(token_db)
    await db.commit()

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
    )

