from typing import Annotated, Callable, Awaitable
from uuid import UUID

from fastapi import HTTPException, Depends
from sqlalchemy.orm import Load
from sqlalchemy.ext.asyncio import AsyncSession
from jose import jwt, JWTError
from pydantic import ValidationError

from app.core.database import get_db
from app.core.security import oauth2_scheme
from app.core.config import redis
from app.core.settings import ALGORITHM, ACCESS_SECRET_KEY, RP_BLACKLISTED_TOKEN
from app.models import User


def get_current_user(load_user: bool = False, *load_options: type[Load]) -> Callable[[AsyncSession, str], Awaitable[User | UUID]]:
    print(f"UTILS get_current_user {load_user=} {load_options=}")
    async def dependency(
        db: Annotated[AsyncSession, Depends(get_db)],
        token: Annotated[str, Depends(oauth2_scheme)],
    ) -> User | UUID:
        print(f"UTILS get_current_user dependency {token=}")

        credentials_exception = HTTPException(401, "Could not validate credentials",
                                                {"WWW-Authenticate": "Bearer"})

        user_id: UUID | None = None
        try:
            payload = jwt.decode(token, ACCESS_SECRET_KEY, algorithms=ALGORITHM)
            if (jti := payload.get("jti")) and await redis.get(f"{RP_BLACKLISTED_TOKEN}{jti}"):
                print(f"UTILS get_current_user {jti=} is blacklisted")
                raise credentials_exception

            if not (sub := payload.get("sub")):
                print(f"UTILS get_current_user {sub=}")
                raise credentials_exception

            if isinstance(sub, str):
                user_id = UUID(sub)

        except (JWTError, ValidationError) as e:
            print(f"UTILS get_current_user Token validation failed: {e}")
            raise credentials_exception

        if not load_user and user_id:
            return user_id

        options: tuple[Load, ...] = tuple(opt(User) for opt in load_options)
        user = await db.get(User, user_id, options=options)
        if not user:
            raise credentials_exception

        return user

    return dependency

