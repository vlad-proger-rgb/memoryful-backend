import datetime as dt
import hashlib
import hmac
import logging
from typing import Any, NamedTuple
from uuid import UUID, uuid4

from fastapi import HTTPException
from fastapi.concurrency import run_in_threadpool
from fastapi.security import OAuth2PasswordBearer
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from jose import JWTError, jwt

from app.constants import ALGORITHM, GOOGLE_ISSUERS
from app.core.config import redis
from app.core.settings import get_settings
from app.enums import TokenType
from app.schemas import VerifyCodeForm

settings = get_settings()
logger = logging.getLogger(__name__)


oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/auth/login",
)

# RFC 7235: every 401 carries a challenge naming the scheme it expects.
BEARER_CHALLENGE = {"WWW-Authenticate": "Bearer"}


class InvalidTokenError(Exception):
    pass


class TokenSigning(NamedTuple):
    secret_key: str
    lifetime: dt.timedelta


class TokenClaims(NamedTuple):
    user_id: UUID
    session_id: UUID


def unauthorized(detail: str) -> HTTPException:
    return HTTPException(401, detail, BEARER_CHALLENGE)


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def verify_refresh_token(token: str, hashed_token: str) -> bool:
    return hmac.compare_digest(hash_refresh_token(token), hashed_token)


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
        logger.warning("Rejected a Google ID token: %s", type(e).__name__)
        raise unauthorized("Invalid Google credential") from e

    if claims.get("iss") not in GOOGLE_ISSUERS:
        raise unauthorized("Invalid Google credential")

    if not claims.get("email") or not claims.get("email_verified"):
        raise HTTPException(403, "Google account has no verified email")

    return claims


def create_token(
    *, user_id: UUID, session_id: UUID, token_type: TokenType = TokenType.access
) -> str:
    signing = _signing_for(token_type)
    payload = {
        "sub": str(user_id),
        "sid": str(session_id),
        "jti": str(uuid4()),
        "exp": dt.datetime.now(dt.UTC) + signing.lifetime,
    }
    return jwt.encode(payload, signing.secret_key, ALGORITHM)


def read_token(token: str, token_type: TokenType) -> TokenClaims:
    """Verifies the signature, algorithm and expiry; raises `InvalidTokenError` otherwise."""
    try:
        payload = jwt.decode(
            token,
            _signing_for(token_type).secret_key,
            algorithms=[ALGORITHM],
            options={"require_exp": True},
        )
        return TokenClaims(user_id=UUID(payload["sub"]), session_id=UUID(payload["sid"]))
    except (JWTError, KeyError, TypeError, ValueError) as e:
        raise InvalidTokenError(type(e).__name__) from e


def _signing_for(token_type: TokenType) -> TokenSigning:
    match token_type:
        case TokenType.access:
            return TokenSigning(
                settings.access_secret_key,
                dt.timedelta(minutes=settings.access_token_expire_minutes),
            )
        case TokenType.refresh:
            return TokenSigning(
                settings.refresh_secret_key,
                dt.timedelta(minutes=settings.refresh_token_expire_minutes),
            )
