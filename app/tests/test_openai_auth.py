"""OpenAI must authenticate by federation alone, never by a leftover OPENAI_API_KEY."""

import pytest

from app.ai.integrations import openai as integration
from app.core.settings import get_settings
from app.tests.conftest import StubAPI

_COMPLETION = {
    "id": "chatcmpl-1",
    "object": "chat.completion",
    "created": 0,
    "model": "gpt-5.4-nano",
    "choices": [
        {
            "index": 0,
            "message": {"role": "assistant", "content": "hi"},
            "finish_reason": "stop",
        }
    ],
    "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
}


class _FakeAuth:
    def __init__(self) -> None:
        self.calls = 0

    def get_token(self) -> str:
        self.calls += 1
        return "federated-token"


@pytest.fixture
def fake_auth(monkeypatch: pytest.MonkeyPatch) -> _FakeAuth:
    auth = _FakeAuth()
    monkeypatch.setattr(integration, "_federated_auth", lambda: auth)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-proj-stale")
    return auth


async def test_requests_carry_the_federated_bearer_only(
    fake_auth: _FakeAuth, stub_api: StubAPI
) -> None:
    stub_api.body = _COMPLETION
    model = integration.build_chat_openai("gpt-5.4-nano", temperature=0.4, base_url=stub_api.url)

    model.invoke("hello")
    await model.ainvoke("hello")

    assert len(stub_api.seen) == 2
    assert fake_auth.calls >= 2
    for headers in stub_api.seen:
        assert headers["authorization"] == "Bearer federated-token"


async def test_exchange_uses_the_configured_ids_and_openai_audience(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(integration, "_shared_auth", None)
    monkeypatch.setattr(
        integration, "google_identity_token", lambda audience: f"jwt-for-{audience}"
    )

    identity = integration._federated_auth().workload_identity

    assert identity["identity_provider_id"] == get_settings().openai_identity_provider_id
    assert identity["service_account_id"] == get_settings().openai_service_account_id
    assert identity["provider"]["get_token"]() == "jwt-for-https://api.openai.com/v1"
