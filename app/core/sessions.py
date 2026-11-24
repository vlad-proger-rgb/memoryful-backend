"""Signed-in sessions: one `UserToken` row each, whose id is the `sid` of every token it issues."""

import datetime as dt
from uuid import UUID, uuid4

from fastapi import Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import REFRESH_REUSE_GRACE_SECONDS
from app.core.config import redis
from app.core.security import create_token, hash_refresh_token, verify_refresh_token
from app.core.settings import get_settings
from app.enums import RedisPrefix, TokenType
from app.models import User, UserToken
from app.schemas import Token

settings = get_settings()


async def issue_session(
    db: AsyncSession, user: User, request: Request, response: Response
) -> Token:
    return set_refresh_cookie(response, await create_and_store_tokens(db, user, request))


async def create_and_store_tokens(
    db: AsyncSession,
    user: User,
    request: Request | None = None,
) -> Token:
    session = UserToken(id=uuid4(), user_id=user.id)
    refresh_token = _issue_refresh_token(session, request)
    db.add(session)
    await db.commit()
    return _bearer(session, refresh_token)


async def rotate_session_tokens(
    db: AsyncSession, session: UserToken, request: Request | None = None
) -> Token:
    session.previous_refresh_token_hash = session.refresh_token_hash
    session.rotated_at = dt.datetime.now(dt.UTC)
    refresh_token = _issue_refresh_token(session, request)
    await db.commit()
    return _bearer(session, refresh_token)


def access_token_only(session: UserToken) -> Token:
    return _bearer(session, refresh_token=None)


def within_reuse_grace(session: UserToken, refresh_token: str) -> bool:
    previous = session.previous_refresh_token_hash
    if not previous or not session.rotated_at:
        return False
    grace = dt.timedelta(seconds=REFRESH_REUSE_GRACE_SECONDS)
    in_window = dt.datetime.now(dt.UTC) - session.rotated_at <= grace
    return in_window and verify_refresh_token(refresh_token, previous)


async def blacklist_session(session_id: UUID) -> None:
    """Its access tokens stay valid until they expire unless the session id is blacklisted."""
    await redis.setex(
        f"{RedisPrefix.revoked_session}{session_id}",
        settings.access_token_expire_minutes * 60,
        "true",
    )


def set_refresh_cookie(response: Response, tokens: Token) -> Token:
    if tokens.refresh_token:
        response.set_cookie(
            key="refresh_token",
            value=tokens.refresh_token,
            httponly=True,
            secure=not settings.is_development,
            samesite="lax",
            max_age=settings.refresh_token_expire_minutes * 60,
            path="/",
        )

    tokens.refresh_token = None
    return tokens


def _issue_refresh_token(session: UserToken, request: Request | None) -> str:
    refresh_token = create_token(
        user_id=session.user_id, session_id=session.id, token_type=TokenType.refresh
    )
    session.refresh_token_hash = hash_refresh_token(refresh_token)
    session.expires_at = dt.datetime.now(dt.UTC) + dt.timedelta(
        minutes=settings.refresh_token_expire_minutes
    )
    if request:
        session.ip_address = request.client.host if request.client else None
        session.user_agent = request.headers.get("user-agent")
    return refresh_token


def _bearer(session: UserToken, refresh_token: str | None) -> Token:
    return Token(
        access_token=create_token(user_id=session.user_id, session_id=session.id),
        refresh_token=refresh_token,
        token_type="bearer",  # noqa: S106  # the OAuth2 scheme name, not a secret
    )
