"""The Vertex token refresh is a blocking call to Google, so it must never run on the
event loop, where it would stall every other request on the worker."""

import asyncio
from typing import Any

import pytest

from app.ai import utils
from app.models import ChatModel
from app.tests.conftest import StubAPI

_COMPLETION = {
    "id": "chatcmpl-1",
    "object": "chat.completion",
    "created": 0,
    "model": "xai/grok-4.1-fast",
    "choices": [
        {
            "index": 0,
            "message": {"role": "assistant", "content": "hi"},
            "finish_reason": "stop",
        }
    ],
    "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
}


class _FakeCredentials:
    def __init__(self) -> None:
        self.valid = False
        self.token: str | None = None
        self.refreshed_on_loop: list[bool] = []

    def refresh(self, request: Any) -> None:
        try:
            asyncio.get_running_loop()
            self.refreshed_on_loop.append(True)
        except RuntimeError:
            self.refreshed_on_loop.append(False)
        self.token = "vertex-token"
        self.valid = True


@pytest.fixture
def credentials(monkeypatch: pytest.MonkeyPatch, stub_api: StubAPI) -> _FakeCredentials:
    fake = _FakeCredentials()
    monkeypatch.setattr("google.auth.default", lambda **_: (fake, "project"))
    monkeypatch.setattr(utils, "_gcp_credentials", None)
    monkeypatch.setattr(utils.settings, "llm_mode", "vertex")
    monkeypatch.setattr(utils.settings, "gcp_project_id", "project")
    monkeypatch.setattr(utils, "_vertex_openapi_base_url", lambda _location: stub_api.url)
    stub_api.body = _COMPLETION
    return fake


async def test_the_token_refreshes_off_the_event_loop_once_per_expiry(
    credentials: _FakeCredentials, stub_api: StubAPI
) -> None:
    model = utils.build_chat_model(ChatModel(name="xai/grok-4.1-fast", provider="xai"))

    await model.ainvoke("hello")
    await model.ainvoke("hello")

    assert credentials.refreshed_on_loop == [False]
    assert [h["authorization"] for h in stub_api.seen] == ["Bearer vertex-token"] * 2
