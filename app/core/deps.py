import logging
from collections.abc import Awaitable, Callable
from functools import lru_cache
from typing import Annotated
from uuid import UUID

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.interfaces import ORMOption

from app.core.config import redis
from app.core.database import get_db
from app.core.security import (
    InvalidTokenError,
    TokenClaims,
    oauth2_scheme,
    read_token,
    unauthorized,
)
from app.core.settings import get_settings
from app.core.storage.service import StorageService
from app.enums import RedisPrefix, TokenType
from app.models import User

settings = get_settings()


logger = logging.getLogger(__name__)


async def _access_claims(token: str) -> TokenClaims:
    try:
        claims = read_token(token, TokenType.access)
    except InvalidTokenError as e:
        logger.debug("Access token rejected: %s", e)
        raise unauthorized("Could not validate credentials") from e

    if await redis.exists(f"{RedisPrefix.revoked_session}{claims.session_id}"):
        raise unauthorized("Could not validate credentials")
    return claims


def get_current_user(
    load_user: bool = False, *load_options: ORMOption
) -> Callable[[AsyncSession, str], Awaitable[User | UUID]]:

    async def dependency(
        db: Annotated[AsyncSession, Depends(get_db)],
        token: Annotated[str, Depends(oauth2_scheme)],
    ) -> User | UUID:
        user_id = (await _access_claims(token)).user_id
        if not load_user:
            return user_id

        user = await db.get(User, user_id, options=load_options)
        if not user:
            raise unauthorized("Could not validate credentials")
        return user

    return dependency


async def get_session_id(token: Annotated[str, Depends(oauth2_scheme)]) -> UUID:
    return (await _access_claims(token)).session_id


@lru_cache
def get_storage_service() -> StorageService:
    return StorageService()


StorageServiceDep = Annotated[StorageService, Depends(get_storage_service)]
