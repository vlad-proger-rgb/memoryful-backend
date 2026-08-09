"""Session listing and revocation.

A session is a `UserToken` row whose id *is* the token's `jti`, so revoking one
means both deleting the row and blacklisting that jti in Redis. Sessions are
created through `create_and_store_tokens`, the same call the login route uses —
the `make_user` fixture only mints a bare token and leaves no row behind.
"""

from collections.abc import AsyncIterator, Awaitable, Callable
from uuid import uuid4

import pytest_asyncio
from httpx import AsyncClient
from jose import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import ALGORITHM
from app.core.config import redis
from app.core.security import create_and_store_tokens
from app.core.settings import get_settings
from app.enums import RedisPrefix
from app.models import User, UserToken

from .conftest import MakeUser

settings = get_settings()

# A login yields one row whose id is the jti shared by both tokens.
StartSession = Callable[[User], Awaitable[tuple[str, dict[str, str]]]]


@pytest_asyncio.fixture
async def start_session(db: AsyncSession) -> AsyncIterator[StartSession]:
    created: list[str] = []

    async def _start(user: User) -> tuple[str, dict[str, str]]:
        tokens = await create_and_store_tokens(db, user)
        # Read the jti off the token rather than querying for the newest row:
        # created_at is Postgres now(), which is transaction time, so two sessions
        # started in one test are indistinguishable by it.
        jti = jwt.decode(tokens.access_token, settings.access_secret_key, algorithms=ALGORITHM)[
            "jti"
        ]
        created.append(jti)
        return jti, {"Authorization": f"Bearer {tokens.access_token}"}

    try:
        yield _start
    finally:
        # Blacklist entries outlive the DB rollback; they carry a 30 minute TTL.
        for jti in created:
            await redis.delete(f"{RedisPrefix.blacklisted_token}{jti}")


async def test_sessions_lists_only_the_callers_sessions(
    client: AsyncClient, make_user: MakeUser, start_session: StartSession
) -> None:
    mine, _ = await make_user()
    theirs, _ = await make_user()

    my_jti, my_headers = await start_session(mine)
    their_jti, _ = await start_session(theirs)

    response = await client.get("/auth/sessions", headers=my_headers)
    assert response.status_code == 200, response.text
    ids = {session["id"] for session in response.json()["data"]}
    assert my_jti in ids
    assert their_jti not in ids, "another user's session was listed"


async def test_the_calling_session_is_marked_current(
    client: AsyncClient, make_user: MakeUser, start_session: StartSession
) -> None:
    user, _ = await make_user()
    first_jti, first_headers = await start_session(user)
    second_jti, _ = await start_session(user)

    response = await client.get("/auth/sessions", headers=first_headers)
    current = {s["id"]: s["isCurrent"] for s in response.json()["data"]}
    assert current[first_jti] is True
    assert current[second_jti] is False


async def test_revoking_a_session_blacklists_and_deletes_it(
    client: AsyncClient, db: AsyncSession, make_user: MakeUser, start_session: StartSession
) -> None:
    user, _ = await make_user()
    doomed_jti, doomed_headers = await start_session(user)
    _, keeper_headers = await start_session(user)

    revoked = await client.delete(f"/auth/sessions/{doomed_jti}", headers=keeper_headers)
    assert revoked.status_code == 200, revoked.text

    assert await redis.exists(f"{RedisPrefix.blacklisted_token}{doomed_jti}")
    assert await db.scalar(select(UserToken).where(UserToken.id == doomed_jti)) is None

    # The revoked token must stop working, which is the point of the blacklist.
    assert (await client.get("/auth/me", headers=doomed_headers)).status_code == 401
    assert (await client.get("/auth/me", headers=keeper_headers)).status_code == 200


async def test_cannot_revoke_another_users_session(
    client: AsyncClient, db: AsyncSession, make_user: MakeUser, start_session: StartSession
) -> None:
    owner, _ = await make_user()
    _, intruder = await make_user()
    victim_jti, victim_headers = await start_session(owner)

    response = await client.delete(f"/auth/sessions/{victim_jti}", headers=intruder)
    assert response.status_code == 404

    assert await db.scalar(select(UserToken).where(UserToken.id == victim_jti)) is not None
    assert not await redis.exists(f"{RedisPrefix.blacklisted_token}{victim_jti}")
    assert (await client.get("/auth/me", headers=victim_headers)).status_code == 200


async def test_revoking_an_unknown_session_is_a_404(
    client: AsyncClient, make_user: MakeUser, start_session: StartSession
) -> None:
    user, _ = await make_user()
    _, headers = await start_session(user)
    response = await client.delete(f"/auth/sessions/{uuid4()}", headers=headers)
    assert response.status_code == 404


async def test_logout_all_revokes_every_session(
    client: AsyncClient, db: AsyncSession, make_user: MakeUser, start_session: StartSession
) -> None:
    user, _ = await make_user()
    first_jti, first_headers = await start_session(user)
    second_jti, second_headers = await start_session(user)

    response = await client.post("/auth/logout-all", headers=first_headers)
    assert response.status_code == 200, response.text

    remaining = (await db.scalars(select(UserToken).where(UserToken.user_id == user.id))).all()
    assert remaining == []

    for jti in (first_jti, second_jti):
        assert await redis.exists(f"{RedisPrefix.blacklisted_token}{jti}")
    for headers in (first_headers, second_headers):
        assert (await client.get("/auth/me", headers=headers)).status_code == 401


async def test_logout_all_leaves_other_users_alone(
    client: AsyncClient, db: AsyncSession, make_user: MakeUser, start_session: StartSession
) -> None:
    actor, _ = await make_user()
    bystander, _ = await make_user()
    _, actor_headers = await start_session(actor)
    bystander_jti, bystander_headers = await start_session(bystander)

    assert (await client.post("/auth/logout-all", headers=actor_headers)).status_code == 200

    assert await db.scalar(select(UserToken).where(UserToken.id == bystander_jti)) is not None
    assert (await client.get("/auth/me", headers=bystander_headers)).status_code == 200


async def test_logout_blacklists_the_calling_token(
    client: AsyncClient, make_user: MakeUser, start_session: StartSession
) -> None:
    user, _ = await make_user()
    jti, headers = await start_session(user)

    assert (await client.get("/auth/logout", headers=headers)).status_code == 200

    assert await redis.exists(f"{RedisPrefix.blacklisted_token}{jti}")
    assert (await client.get("/auth/me", headers=headers)).status_code == 401
