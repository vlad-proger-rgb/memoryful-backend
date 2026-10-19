"""Federated AI providers get identity tokens for the shared GCP service account."""

from typing import Any

import pytest

from app.ai.integrations import google_identity
from app.core.settings import get_settings


@pytest.fixture
def minted(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    import google.auth
    from google.auth import impersonated_credentials

    calls: list[dict[str, Any]] = []

    class _FakeIdTokenCredentials:
        valid = False

        def __init__(self, target: Any, **kwargs: Any) -> None:
            calls.append({"target_principal": target, **kwargs})
            self.token = f"token-for-{kwargs['target_audience']}"

        def refresh(self, request: Any) -> None:
            self.valid = True

    monkeypatch.setattr(google_identity, "_credentials_by_audience", {})
    monkeypatch.setattr(google.auth, "default", lambda scopes: (object(), None))
    monkeypatch.setattr(
        impersonated_credentials, "Credentials", lambda **kwargs: kwargs["target_principal"]
    )
    monkeypatch.setattr(impersonated_credentials, "IDTokenCredentials", _FakeIdTokenCredentials)
    return calls


async def test_token_impersonates_the_ai_account_with_email(minted: list[dict[str, Any]]) -> None:
    assert (
        google_identity.google_identity_token("https://a.example") == "token-for-https://a.example"
    )
    assert minted == [
        {
            "target_principal": get_settings().gcp_ai_service_account,
            "target_audience": "https://a.example",
            "include_email": True,
        }
    ]


async def test_each_audience_gets_its_own_reused_credentials(
    minted: list[dict[str, Any]],
) -> None:
    google_identity.google_identity_token("https://a.example")
    google_identity.google_identity_token("https://a.example")
    google_identity.google_identity_token("https://b.example")

    assert [call["target_audience"] for call in minted] == [
        "https://a.example",
        "https://b.example",
    ]
