"""Checks on the harness itself, so a broken fixture fails here and not everywhere."""

from uuid import UUID

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.settings import REQUIRED_SECRETS, Settings, get_settings
from app.enums import CacheNamespace
from app.models import User


async def test_root_is_reachable(client: AsyncClient) -> None:
    response = await client.get("/")
    assert response.status_code == 200
    assert response.json()["code"] == 200


async def test_caching_is_off(client: AsyncClient) -> None:
    # A cached response from one test would otherwise leak into the next.
    assert get_settings().cache_enabled is False


async def test_secret_manager_source_is_wired_in() -> None:
    # Spelled with a "z" this hook is never called and Secret Manager drops out
    # silently, which local runs cannot otherwise detect.
    from app.core.settings import SecretManagerSource

    sources = Settings.settings_customise_sources(Settings, *[object()] * 4)  # type: ignore[arg-type]
    assert any(isinstance(source, SecretManagerSource) for source in sources)


async def test_every_required_secret_is_a_field() -> None:
    assert set(Settings.model_fields) >= REQUIRED_SECRETS


async def test_required_secrets_have_no_default() -> None:
    for name in REQUIRED_SECRETS:
        field = Settings.model_fields[name]
        assert field.is_required(), f"{name} has a default and can boot blank"


async def test_cache_namespace_values_match_member_names() -> None:
    # clear_cache scans by the value; a mismatch would clear the wrong namespace.
    for member in CacheNamespace:
        assert member.value == member.name


async def test_authenticated_request_resolves_the_right_user(
    client: AsyncClient, auth_headers: dict[str, str], user_id: UUID
) -> None:
    response = await client.get("/auth/me", headers=auth_headers, follow_redirects=True)
    assert response.status_code == 200, response.text
    assert response.json()["data"]["id"] == str(user_id)


async def test_request_without_a_token_is_rejected(client: AsyncClient) -> None:
    response = await client.get("/auth/me", follow_redirects=True)
    assert response.status_code == 401


async def test_writes_are_rolled_back_between_tests(db: AsyncSession) -> None:
    db.add(User(email="leak-check@example.com"))
    await db.commit()
    found = await db.scalar(select(User).where(User.email == "leak-check@example.com"))
    assert found is not None


async def test_previous_test_left_nothing_behind(db: AsyncSession) -> None:
    found = await db.scalar(select(User).where(User.email == "leak-check@example.com"))
    assert found is None, "rollback did not undo the previous test's commit"
