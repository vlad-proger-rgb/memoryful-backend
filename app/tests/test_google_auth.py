"""Google sign-in: the checks wrapped around Google's verifier, and account linking.

Google's own verifier is stubbed at the library boundary rather than at our
`verify_google_id_token`, so everything we add on top of it — the issuer check,
`email_verified`, the audience guard — stays under test instead of being mocked away.
"""

from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.settings import get_settings
from app.models import User

settings = get_settings()


CLIENT_ID = "test-client-id.apps.googleusercontent.com"


@pytest.fixture
def email() -> str:
    return f"google-{uuid4().hex}@example.com"


@pytest.fixture
def claims(email: str) -> dict[str, object]:
    return {
        "iss": "https://accounts.google.com",
        "aud": CLIENT_ID,
        "sub": uuid4().hex,
        "email": email,
        "email_verified": True,
        "given_name": "Ada",
        "family_name": "Lovelace",
    }


@pytest.fixture(autouse=True)
def google_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "google_client_ids_raw", CLIENT_ID)


def stub_verifier(monkeypatch: pytest.MonkeyPatch, claims: dict[str, object]) -> None:
    monkeypatch.setattr(
        "app.core.security.id_token.verify_oauth2_token",
        lambda credential, request, audience: claims,
    )


async def test_creates_the_user(
    client: AsyncClient,
    db: AsyncSession,
    email: str,
    claims: dict[str, object],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stub_verifier(monkeypatch, claims)

    response = await client.post("/auth/google", json={"credential": "an.id.token"})
    assert response.status_code == 200, response.text

    body = response.json()["data"]
    assert body["isNewUser"] is True
    assert body["tokens"]["accessToken"]
    assert body["tokens"].get("refreshToken") is None, "the refresh token leaked into the body"
    assert response.cookies.get("refresh_token"), "no refresh cookie was set"

    created = await db.scalar(select(User).where(User.email == email))
    assert created is not None
    assert created.first_name == "Ada", "the name from the ID token was not prefilled"


async def test_links_to_an_existing_account(
    client: AsyncClient,
    db: AsyncSession,
    email: str,
    claims: dict[str, object],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    existing = User(email=email)
    db.add(existing)
    await db.flush()

    stub_verifier(monkeypatch, claims)
    response = await client.post("/auth/google", json={"credential": "an.id.token"})
    assert response.status_code == 200, response.text

    body = response.json()["data"]
    assert body["isNewUser"] is False
    assert body["userId"] == str(existing.id), "Google sign-in forked the account"

    rows = (await db.scalars(select(User).where(User.email == email))).all()
    assert len(rows) == 1


async def test_requires_a_verified_email(
    client: AsyncClient, claims: dict[str, object], monkeypatch: pytest.MonkeyPatch
) -> None:
    claims["email_verified"] = False
    stub_verifier(monkeypatch, claims)

    response = await client.post("/auth/google", json={"credential": "an.id.token"})
    assert response.status_code == 403, "an unverified Google email was accepted"


async def test_rejects_a_foreign_issuer(
    client: AsyncClient, claims: dict[str, object], monkeypatch: pytest.MonkeyPatch
) -> None:
    claims["iss"] = "https://accounts.example.com"
    stub_verifier(monkeypatch, claims)

    response = await client.post("/auth/google", json={"credential": "an.id.token"})
    assert response.status_code == 401


async def test_rejects_an_invalid_credential(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _reject(credential: str, request: object, audience: list[str]) -> dict[str, object]:
        raise ValueError("Token has wrong audience")

    monkeypatch.setattr("app.core.security.id_token.verify_oauth2_token", _reject)

    response = await client.post("/auth/google", json={"credential": "not.a.token"})
    assert response.status_code == 401


async def test_rejects_a_disabled_user(
    client: AsyncClient,
    db: AsyncSession,
    email: str,
    claims: dict[str, object],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db.add(User(email=email, is_enabled=False))
    await db.flush()

    stub_verifier(monkeypatch, claims)
    response = await client.post("/auth/google", json={"credential": "an.id.token"})
    assert response.status_code == 401, "a disabled user signed in through Google"


async def test_is_off_without_a_client_id(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "google_client_ids_raw", "")

    response = await client.post("/auth/google", json={"credential": "an.id.token"})
    assert response.status_code == 503
