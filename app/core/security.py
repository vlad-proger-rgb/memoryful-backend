import datetime as dt
import hashlib
import hmac
from typing import Any
from uuid import uuid4

from fastapi import HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.security import OAuth2PasswordBearer
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from jose import jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import ALGORITHM, GOOGLE_ISSUERS
from app.core.config import redis
from app.core.settings import get_settings
from app.models import User, UserToken
from app.schemas import Token, VerifyCodeForm

settings = get_settings()


oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/auth/login",
)


def _token_config(token_type: str) -> tuple[str, int]:
    if token_type == "access":  # noqa: S105  # a token *kind*, not a secret
        return settings.access_secret_key, settings.access_token_expire_minutes
    if token_type == "refresh":  # noqa: S105  # a token *kind*, not a secret
        return settings.refresh_secret_key, settings.refresh_token_expire_minutes
    raise ValueError("Invalid token type. Choose 'access' or 'refresh'")


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def verify_refresh_token(token: str, hashed_token: str) -> bool:
    digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
    return hmac.compare_digest(digest, hashed_token)


def create_token(
    data: dict,
    token_type: str = "access",  # noqa: S107  # a token *kind*, not a secret
    expires_delta: dt.timedelta | None = None,
    jti: str | None = None,
) -> tuple[str, str]:
    secret_key, expire_minutes = _token_config(token_type)
    expiration_time = (
        dt.datetime.now(dt.UTC) + expires_delta
        if expires_delta
        else dt.datetime.now(dt.UTC) + dt.timedelta(minutes=expire_minutes)
    )

    jti = jti or str(uuid4())
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


async def verify_google_id_token(credential: str) -> dict[str, Any]:
    audiences = settings.google_client_ids
    if not audiences:
        raise HTTPException(503, "Google sign-in is not configured")

    def _verify() -> dict[str, Any]:
        verified: dict[str, Any] = id_token.verify_oauth2_token(
            credential, google_requests.Request(), audiences
        )
        return verified

    try:
        claims = await run_in_threadpool(_verify)
    except ValueError as e:
        print(f"UTILS verify_google_id_token rejected a credential: {e}")
        raise HTTPException(401, "Invalid Google credential") from e

    if claims.get("iss") not in GOOGLE_ISSUERS:
        raise HTTPException(401, "Invalid Google credential")

    if not claims.get("email") or not claims.get("email_verified"):
        raise HTTPException(403, "Google account has no verified email")

    return claims


async def create_and_store_tokens(
    db: AsyncSession,
    user: User,
    request: Request | None = None,
) -> Token:
    data = {"sub": str(user.id)}
    session_id = str(uuid4())
    access_token, _ = create_token(data=data, token_type="access", jti=session_id)  # noqa: S106  # a token *kind*, not a secret
    refresh_token, _ = create_token(data=data, token_type="refresh", jti=session_id)  # noqa: S106  # a token *kind*, not a secret

    token_db = UserToken(
        id=session_id,
        user_id=user.id,
        refresh_token_hash=hash_refresh_token(refresh_token),
        expires_at=dt.datetime.now(dt.UTC)
        + dt.timedelta(minutes=settings.refresh_token_expire_minutes),
    )

    if request:
        token_db.ip_address = request.client.host if request.client else None
        token_db.user_agent = request.headers.get("user-agent")

    db.add(token_db)
    await db.commit()

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",  # noqa: S106  # the OAuth2 scheme name, not a secret
    )
