"""Shared fixtures for the app suite.

Runs against the local Postgres, not a separate test database: every test gets a
connection with an open transaction that is rolled back at the end, so nothing it
writes survives. Routers call `db.commit()` themselves, which would normally end
that transaction, so the session runs inside a SAVEPOINT that is reopened after
each commit.
"""

import os
from collections.abc import AsyncIterator, Awaitable, Callable
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession

# Redis-backed response caching would serve one test's payload to another.
os.environ["CACHE_ENABLED"] = "false"

from app.core.database import engine, get_db
from app.core.security import create_token
from app.main import app
from app.models import City, User


@pytest_asyncio.fixture
async def connection() -> AsyncIterator[AsyncConnection]:
    conn = await engine.connect()
    await conn.begin()
    try:
        yield conn
    finally:
        # Discards everything the test wrote, committed or not.
        await conn.rollback()
        await conn.close()


@pytest_asyncio.fixture
async def db(connection: AsyncConnection) -> AsyncIterator[AsyncSession]:
    session = AsyncSession(
        bind=connection, expire_on_commit=False, join_transaction_mode="create_savepoint"
    )
    try:
        yield session
    finally:
        await session.close()


@pytest_asyncio.fixture
async def client(db: AsyncSession) -> AsyncIterator[AsyncClient]:
    async def override_get_db() -> AsyncIterator[AsyncSession]:
        yield db

    app.dependency_overrides[get_db] = override_get_db
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as async_client:
            yield async_client
    finally:
        app.dependency_overrides.clear()


AuthedUser = tuple[User, dict[str, str]]
MakeUser = Callable[[], Awaitable[AuthedUser]]


@pytest_asyncio.fixture
async def make_user(db: AsyncSession) -> MakeUser:
    """Create a user and return it with headers carrying a genuine access token.

    The token is signed by the app's own `create_token`, so requests go through the
    real `get_current_user` rather than a dependency override — which could not be
    keyed anyway, since every route holds its own `get_current_user()` closure.
    """

    async def _make() -> AuthedUser:
        user = User(email=f"test-{uuid4().hex}@example.com")
        db.add(user)
        await db.flush()
        token, _ = create_token(data={"sub": str(user.id)})
        return user, {"Authorization": f"Bearer {token}"}

    return _make


@pytest_asyncio.fixture
async def user(make_user: MakeUser) -> AuthedUser:
    return await make_user()


@pytest.fixture
def auth_headers(user: AuthedUser) -> dict[str, str]:
    return user[1]


@pytest.fixture
def user_id(user: AuthedUser) -> UUID:
    return user[0].id


@pytest_asyncio.fixture
async def city_id(db: AsyncSession) -> UUID:
    """Days need a city; the restore and the dev seed both provide some."""
    found = await db.scalar(select(City.id).limit(1))
    assert found is not None, "no cities in the database; days cannot be created"
    return found
