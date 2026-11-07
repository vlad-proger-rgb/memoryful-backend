"""MCP tool schemas are shared across users; the bearer on each tool call never is."""

import asyncio
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager
from typing import Any

import pytest
from langchain_mcp_adapters import tools as adapter_tools
from mcp.types import CallToolResult, TextContent, Tool

from app.ai import mcp


class _FakeSession:
    async def initialize(self) -> None:
        return None

    async def call_tool(self, name: str, arguments: dict[str, Any], **_: Any) -> CallToolResult:
        return CallToolResult(content=[TextContent(type="text", text="ok")], isError=False)


@pytest.fixture
def fetches(monkeypatch: pytest.MonkeyPatch) -> Iterator[list[str]]:
    calls: list[str] = []

    async def fake_fetch(access_token: str) -> list[Tool]:
        calls.append(access_token)
        await asyncio.sleep(0)
        return [Tool(name="get_tags", inputSchema={"type": "object", "properties": {}})]

    monkeypatch.setattr(mcp, "_fetch_tool_schemas", fake_fetch)
    monkeypatch.setattr(mcp, "_tool_schemas", None)
    yield calls


@pytest.mark.asyncio
async def test_schemas_are_fetched_once_for_concurrent_users(fetches: list[str]) -> None:
    await asyncio.gather(mcp.load_mcp_tools("token-a"), mcp.load_mcp_tools("token-b"))
    await mcp.load_mcp_tools("token-c")

    assert len(fetches) == 1


@pytest.mark.asyncio
async def test_each_user_tool_calls_with_its_own_bearer(
    fetches: list[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    sent: list[str] = []

    @asynccontextmanager
    async def fake_create_session(
        connection: dict[str, Any], **_: Any
    ) -> AsyncIterator[_FakeSession]:
        sent.append(connection["headers"]["Authorization"])
        yield _FakeSession()

    monkeypatch.setattr(adapter_tools, "create_session", fake_create_session)

    tools_a = await mcp.load_mcp_tools("token-a")
    tools_b = await mcp.load_mcp_tools("token-b")
    await tools_b[0].ainvoke({})
    await tools_a[0].ainvoke({})

    assert sent == ["Bearer token-b", "Bearer token-a"]
