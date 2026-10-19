"""Claude must authenticate by federation alone, never by a leftover ANTHROPIC_API_KEY."""

import json
import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

import pytest

from app.ai.integrations import anthropic as integration

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


@pytest.fixture
def anthropic_stub() -> Iterator[tuple[str, list[dict[str, str]]]]:
    """A loopback stand-in for the API; respx can't see the SDK's own HTTP stack."""
    seen: list[dict[str, str]] = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            self.rfile.read(int(self.headers["content-length"]))
            seen.append({k.lower(): v for k, v in self.headers.items()})
            body = json.dumps(_MESSAGE).encode()
            self.send_response(200)
            self.send_header("content-type", "application/json")
            self.send_header("content-length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args: Any) -> None:
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        yield f"http://127.0.0.1:{server.server_port}", seen
    finally:
        server.shutdown()
        server.server_close()


async def test_requests_carry_the_federated_bearer_only(
    fake_cache: _FakeCache, anthropic_stub: tuple[str, list[dict[str, str]]]
) -> None:
    base_url, seen = anthropic_stub
    model = integration.build_chat_anthropic("claude-haiku-4-5", temperature=0.4, base_url=base_url)

    model.invoke("hello")
    await model.ainvoke("hello")

    assert len(seen) == 2
    for headers in seen:
        assert headers["authorization"] == "Bearer federated-token"
        assert "x-api-key" not in headers


async def test_forced_refresh_invalidates_the_shared_cache(fake_cache: _FakeCache) -> None:
    token = integration._federated_token(force_refresh=True)

    assert token.token == "federated-token"
    assert fake_cache.invalidated == 1
