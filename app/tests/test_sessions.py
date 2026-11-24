"""Sessions: listing, revocation, logout and refresh-token rotation.

A session is one `UserToken` row whose id is the `sid` claim of every token it
issues. Refresh rotates the row's token in place, so the id survives; revoking a
session deletes the row and blacklists its id in Redis, which stops its access
tokens too. Sessions are created through `create_and_store_tokens`, the same call
the login route uses — the `make_user` fixture only mints a bare access token.
"""

import datetime as dt
import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from httpx import AsyncClient, Response
from jose import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import ALGORITHM, REFRESH_REUSE_GRACE_SECONDS
from app.core.config import redis
from app.core.security import hash_refresh_token
from app.core.sessions import create_and_store_tokens
from app.core.settings import get_settings
from app.enums import RedisPrefix
from app.models import User, UserToken

from .conftest import MakeUser

settings = get_settings()


@dataclass
class StartedSession:
    id: UUID
    headers: dict[str, str]
    refresh_token: str


StartSession = Callable[[User], Awaitable[StartedSession]]


def _session_id(access_token: str) -> UUID:
    claims = jwt.decode(access_token, settings.access_secret_key, algorithms=ALGORITHM)
    return UUID(claims["sid"])


def _revoked_key(session_id: UUID) -> str:
    return f"{RedisPrefix.revoked_session}{session_id}"


@pytest_asyncio.fixture
async def start_session(db: AsyncSession) -> AsyncIterator[StartSession]:
    created: list[UUID] = []

    async def _start(user: User) -> StartedSession:
        tokens = await create_and_store_tokens(db, user)
        assert tokens.refresh_token
        session_id = _session_id(tokens.access_token)
        created.append(session_id)
        return StartedSession(
            id=session_id,
            headers={"Authorization": f"Bearer {tokens.access_token}"},
            refresh_token=tokens.refresh_token,
        )

    try:
        yield _start
    finally:
        # Blacklist entries outlive the DB rollback.
        for session_id in created:
            await redis.delete(_revoked_key(session_id))


async def _refresh(client: AsyncClient, refresh_token: str) -> Response:
    # The jar would otherwise send the cookie from an earlier refresh, which wins.
    client.cookies.clear()
    return await client.get("/auth/refresh", headers={"Authorization": f"Bearer {refresh_token}"})


async def test_sessions_lists_only_the_callers_sessions(
    client: AsyncClient, make_user: MakeUser, start_session: StartSession
) -> None:
    mine, _ = await make_user()
    theirs, _ = await make_user()

    my_session = await start_session(mine)
    their_session = await start_session(theirs)

    response = await client.get("/auth/sessions", headers=my_session.headers)
    assert response.status_code == 200, response.text
    ids = {session["id"] for session in response.json()["data"]}
    assert str(my_session.id) in ids
    assert str(their_session.id) not in ids, "another user's session was listed"


async def test_the_calling_session_is_marked_current(
    client: AsyncClient, make_user: MakeUser, start_session: StartSession
) -> None:
    user, _ = await make_user()
    first = await start_session(user)
    second = await start_session(user)

    response = await client.get("/auth/sessions", headers=first.headers)
    current = {s["id"]: s["isCurrent"] for s in response.json()["data"]}
    assert current[str(first.id)] is True
    assert current[str(second.id)] is False


async def test_revoking_a_session_blacklists_and_deletes_it(
    client: AsyncClient, db: AsyncSession, make_user: MakeUser, start_session: StartSession
) -> None:
    user, _ = await make_user()
    doomed = await start_session(user)
    keeper = await start_session(user)

    revoked = await client.delete(f"/auth/sessions/{doomed.id}", headers=keeper.headers)
    assert revoked.status_code == 200, revoked.text

    assert await redis.exists(_revoked_key(doomed.id))
    assert await db.scalar(select(UserToken).where(UserToken.id == doomed.id)) is None

    assert (await client.get("/auth/me", headers=doomed.headers)).status_code == 401
    assert (await client.get("/auth/me", headers=keeper.headers)).status_code == 200


async def test_cannot_revoke_another_users_session(
    client: AsyncClient, db: AsyncSession, make_user: MakeUser, start_session: StartSession
) -> None:
    owner, _ = await make_user()
    _, intruder = await make_user()
    victim = await start_session(owner)

    response = await client.delete(f"/auth/sessions/{victim.id}", headers=intruder)
    assert response.status_code == 404

    assert await db.scalar(select(UserToken).where(UserToken.id == victim.id)) is not None
    assert not await redis.exists(_revoked_key(victim.id))
    assert (await client.get("/auth/me", headers=victim.headers)).status_code == 200


async def test_revoking_an_unknown_session_is_a_404(
    client: AsyncClient, make_user: MakeUser, start_session: StartSession
) -> None:
    user, _ = await make_user()
    session = await start_session(user)
    response = await client.delete(f"/auth/sessions/{uuid4()}", headers=session.headers)
    assert response.status_code == 404


async def test_logout_all_revokes_every_session(
    client: AsyncClient, db: AsyncSession, make_user: MakeUser, start_session: StartSession
) -> None:
    user, _ = await make_user()
    first = await start_session(user)
    second = await start_session(user)

    response = await client.post("/auth/logout-all", headers=first.headers)
    assert response.status_code == 200, response.text

    remaining = (await db.scalars(select(UserToken).where(UserToken.user_id == user.id))).all()
    assert remaining == []

    for session in (first, second):
        assert await redis.exists(_revoked_key(session.id))
        assert (await client.get("/auth/me", headers=session.headers)).status_code == 401


async def test_logout_all_leaves_other_users_alone(
    client: AsyncClient, db: AsyncSession, make_user: MakeUser, start_session: StartSession
) -> None:
    actor, _ = await make_user()
    bystander, _ = await make_user()
    actor_session = await start_session(actor)
    bystander_session = await start_session(bystander)

    response = await client.post("/auth/logout-all", headers=actor_session.headers)
    assert response.status_code == 200

    row = await db.scalar(select(UserToken).where(UserToken.id == bystander_session.id))
    assert row is not None
    assert (await client.get("/auth/me", headers=bystander_session.headers)).status_code == 200


async def test_logout_ends_only_the_calling_session(
    client: AsyncClient, db: AsyncSession, make_user: MakeUser, start_session: StartSession
) -> None:
    # Both sessions share a user agent and IP here, which the old logout matched on.
    user, _ = await make_user()
    leaving = await start_session(user)
    staying = await start_session(user)

    assert (await client.get("/auth/logout", headers=leaving.headers)).status_code == 200

    assert await redis.exists(_revoked_key(leaving.id))
    assert await db.scalar(select(UserToken).where(UserToken.id == leaving.id)) is None
    assert (await client.get("/auth/me", headers=leaving.headers)).status_code == 401

    assert await db.scalar(select(UserToken).where(UserToken.id == staying.id)) is not None
    assert (await client.get("/auth/me", headers=staying.headers)).status_code == 200


async def test_refresh_keeps_the_session_id_and_rotates_the_token(
    client: AsyncClient, db: AsyncSession, make_user: MakeUser, start_session: StartSession
) -> None:
    user, _ = await make_user()
    session = await start_session(user)

    response = await _refresh(client, session.refresh_token)
    assert response.status_code == 200, response.text
    assert _session_id(response.json()["data"]["accessToken"]) == session.id

    new_refresh_token = response.cookies.get("refresh_token")
    assert new_refresh_token and new_refresh_token != session.refresh_token

    row = await db.scalar(select(UserToken).where(UserToken.user_id == user.id))
    assert row is not None and row.id == session.id
    assert row.refresh_token_hash == hash_refresh_token(new_refresh_token)
    assert row.previous_refresh_token_hash == hash_refresh_token(session.refresh_token)


async def test_a_racing_refresh_gets_an_access_token_without_rotating(
    client: AsyncClient, db: AsyncSession, make_user: MakeUser, start_session: StartSession
) -> None:
    user, _ = await make_user()
    session = await start_session(user)
    first = await _refresh(client, session.refresh_token)
    rotated_to = first.cookies.get("refresh_token")
    assert rotated_to

    # A second tab sent the same token before the first response landed.
    second = await _refresh(client, session.refresh_token)
    assert second.status_code == 200, second.text
    assert _session_id(second.json()["data"]["accessToken"]) == session.id
    assert "refresh_token" not in second.cookies, "the racing request rotated the token again"

    row = await db.scalar(select(UserToken).where(UserToken.id == session.id))
    assert row is not None
    assert row.refresh_token_hash == hash_refresh_token(rotated_to)


async def test_a_reused_refresh_token_revokes_the_session(
    client: AsyncClient,
    db: AsyncSession,
    make_user: MakeUser,
    start_session: StartSession,
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.DEBUG)
    user, _ = await make_user()
    session = await start_session(user)
    rotated = await _refresh(client, session.refresh_token)
    new_headers = {"Authorization": f"Bearer {rotated.json()['data']['accessToken']}"}

    row = await db.scalar(select(UserToken).where(UserToken.id == session.id))
    assert row is not None and row.rotated_at is not None
    row.rotated_at -= dt.timedelta(seconds=REFRESH_REUSE_GRACE_SECONDS + 1)
    await db.flush()

    replayed = await _refresh(client, session.refresh_token)
    assert replayed.status_code == 401

    assert await db.scalar(select(UserToken).where(UserToken.id == session.id)) is None
    assert await redis.exists(_revoked_key(session.id))
    assert (await client.get("/auth/me", headers=new_headers)).status_code == 401, (
        "the session's live access token survived the reuse"
    )
    assert session.refresh_token not in caplog.text


async def test_a_token_older_than_the_previous_one_is_reuse_even_in_the_window(
    client: AsyncClient, db: AsyncSession, make_user: MakeUser, start_session: StartSession
) -> None:
    user, _ = await make_user()
    session = await start_session(user)
    first = await _refresh(client, session.refresh_token)
    second_token = first.cookies.get("refresh_token")
    assert second_token
    assert (await _refresh(client, second_token)).status_code == 200

    replayed = await _refresh(client, session.refresh_token)
    assert replayed.status_code == 401
    assert await db.scalar(select(UserToken).where(UserToken.id == session.id)) is None


async def test_a_refresh_token_without_a_session_id_is_rejected(
    client: AsyncClient, make_user: MakeUser
) -> None:
    user, _ = await make_user()
    # The shape refresh tokens had before sessions carried a stable id.
    legacy = jwt.encode(
        {"sub": str(user.id), "jti": str(uuid4()), "exp": 9_999_999_999},
        settings.refresh_secret_key,
        ALGORITHM,
    )
    assert (await _refresh(client, legacy)).status_code == 401
