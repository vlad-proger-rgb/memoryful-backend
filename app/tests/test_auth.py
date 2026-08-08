"""Login, token issuance and the two Redis-backed gates: the login code and the
`jti` blacklist.

Redis is real here rather than faked, because the login code and the blacklist are
the behaviour under test. Every key is namespaced by a unique email or jti and
removed afterwards, so runs do not interfere.
"""

from collections.abc import AsyncIterator
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import ALGORITHM
from app.core.config import redis
from app.core.security import create_token
from app.core.settings import get_settings
from app.enums import RedisPrefix
from app.models import User

from .conftest import MakeUser

settings = get_settings()


@pytest.fixture
def email() -> str:
    return f"login-{uuid4().hex}@example.com"


@pytest_asyncio.fixture(autouse=True)
async def _no_broker(monkeypatch: pytest.MonkeyPatch) -> None:
    """`request_code` publishes to Pub/Sub; the email itself is not under test."""
    monkeypatch.setattr("app.routers.auth.send_email_task.delay", lambda **_: None)


@pytest_asyncio.fixture
async def login_code(email: str) -> AsyncIterator[str]:
    code = "424242"
    key = f"{RedisPrefix.login_code}{email}"
    await redis.setex(key, 300, code)
    try:
        yield code
    finally:
        await redis.delete(key)


async def test_request_code_stores_a_code(client: AsyncClient, email: str) -> None:
    response = await client.post("/auth/request-code", json={"email": email})
    assert response.status_code == 200

    key = f"{RedisPrefix.login_code}{email}"
    try:
        stored = await redis.get(key)
        assert stored is not None, "no login code was stored"
        assert len(stored) == 6 and stored.isdigit()
    finally:
        await redis.delete(key)


async def test_verify_code_rejects_an_unrequested_code(client: AsyncClient, email: str) -> None:
    response = await client.post("/auth/verify-code", json={"email": email, "code": "000000"})
    assert response.status_code == 400
    assert response.json()["detail"] == "Code not requested"


async def test_verify_code_rejects_a_wrong_code(
    client: AsyncClient, email: str, login_code: str
) -> None:
    response = await client.post("/auth/verify-code", json={"email": email, "code": "999999"})
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid code"


async def test_verify_code_accepts_the_right_code_and_creates_the_user(
    client: AsyncClient, db: AsyncSession, email: str, login_code: str
) -> None:
    response = await client.post("/auth/verify-code", json={"email": email, "code": login_code})
    assert response.status_code == 200, response.text
    body = response.json()["data"]
    assert body["isNewUser"] is True
    assert body["tokens"]["accessToken"]

    created = await db.scalar(select(User).where(User.email == email))
    assert created is not None


async def test_a_used_code_cannot_be_replayed(
    client: AsyncClient, email: str, login_code: str
) -> None:
    first = await client.post("/auth/verify-code", json={"email": email, "code": login_code})
    assert first.status_code == 200

    replay = await client.post("/auth/verify-code", json={"email": email, "code": login_code})
    assert replay.status_code == 400, "the login code survived being used"


async def test_trusted_email_skips_verification(
    client: AsyncClient, email: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The development-only bypass: no code is ever stored, any code is accepted.
    monkeypatch.setattr(settings, "trusted_emails_raw", email)
    assert settings.is_trusted_email(email)

    response = await client.post("/auth/verify-code", json={"email": email, "code": "not-the-code"})
    assert response.status_code == 200, response.text
    assert response.json()["data"]["tokens"]["accessToken"]


async def test_trusted_bypass_is_off_outside_development(
    email: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "trusted_emails_raw", email)
    monkeypatch.setattr(settings, "environment", "production")
    assert settings.trusted_emails == frozenset()
    assert not settings.is_trusted_email(email)


async def test_blacklisted_token_is_rejected(client: AsyncClient, make_user: MakeUser) -> None:
    user, headers = await make_user()
    token, jti = create_token(data={"sub": str(user.id)})
    headers = {"Authorization": f"Bearer {token}"}

    assert (await client.get("/auth/me", headers=headers)).status_code == 200

    key = f"{RedisPrefix.blacklisted_token}{jti}"
    await redis.setex(key, 60, "true")
    try:
        after = await client.get("/auth/me", headers=headers)
        assert after.status_code == 401, "a blacklisted jti still authenticated"
    finally:
        await redis.delete(key)


async def test_token_for_an_unknown_user_is_rejected(client: AsyncClient) -> None:
    token, _ = create_token(data={"sub": str(uuid4())})
    response = await client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 404


async def test_token_signed_with_the_wrong_key_is_rejected(
    client: AsyncClient, make_user: MakeUser
) -> None:
    user, _ = await make_user()
    # The refresh key must not be accepted where the access key is expected.
    from jose import jwt

    forged = jwt.encode(
        {"sub": str(user.id), "jti": str(uuid4()), "exp": 9_999_999_999},
        settings.refresh_secret_key,
        ALGORITHM,
    )
    response = await client.get("/auth/me", headers={"Authorization": f"Bearer {forged}"})
    assert response.status_code == 401


async def test_garbage_token_is_rejected(client: AsyncClient) -> None:
    response = await client.get("/auth/me", headers={"Authorization": "Bearer not.a.jwt"})
    assert response.status_code == 401


async def test_refresh_rejects_a_missing_token(client: AsyncClient) -> None:
    response = await client.get("/auth/refresh")
    assert response.status_code == 401


async def test_refresh_rejects_an_access_token(client: AsyncClient, make_user: MakeUser) -> None:
    user, _ = await make_user()
    access, _ = create_token(data={"sub": str(user.id)})
    response = await client.get("/auth/refresh", headers={"Authorization": f"Bearer {access}"})
    assert response.status_code == 401, "an access token was accepted as a refresh token"
