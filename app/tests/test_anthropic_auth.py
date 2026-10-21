"""Claude must authenticate by federation alone, never by a leftover ANTHROPIC_API_KEY."""

import pytest

from app.ai.integrations import anthropic as integration
from app.tests.conftest import StubAPI

_MESSAGE = {
    "id": "msg_1",
    "type": "message",
    "role": "assistant",
    "model": "claude-haiku-4-5",
    "content": [{"type": "text", "text": "hi"}],
    "stop_reason": "end_turn",
    "stop_sequence": None,
    "usage": {"input_tokens": 1, "output_tokens": 1},
}


class _FakeCache:
    def __init__(self) -> None:
        self.invalidated = 0

    def get_token(self) -> str:
        return "federated-token"

    def invalidate(self) -> None:
        self.invalidated += 1


@pytest.fixture
def fake_cache(monkeypatch: pytest.MonkeyPatch) -> _FakeCache:
    cache = _FakeCache()
    monkeypatch.setattr(integration, "_federated_cache", lambda: cache)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-stale")
    return cache


async def test_requests_carry_the_federated_bearer_only(
    fake_cache: _FakeCache, stub_api: StubAPI
) -> None:
    stub_api.body = _MESSAGE
    model = integration.build_chat_anthropic(
        "claude-haiku-4-5", temperature=0.4, base_url=stub_api.url
    )

    model.invoke("hello")
    await model.ainvoke("hello")

    assert len(stub_api.seen) == 2
    for headers in stub_api.seen:
        assert headers["authorization"] == "Bearer federated-token"
        assert "x-api-key" not in headers


async def test_forced_refresh_invalidates_the_shared_cache(fake_cache: _FakeCache) -> None:
    token = integration._federated_token(force_refresh=True)

    assert token.token == "federated-token"
    assert fake_cache.invalidated == 1
