"""MCP tool loading for the in-app agent, forwarding the user's bearer per request.

The tool schemas are fetched once per process. The bearer lives only in each request's
connection config, so the LangChain tools are rebuilt per user and never shared.
"""

import asyncio
import logging
from typing import TYPE_CHECKING

from app.core.settings import get_settings

if TYPE_CHECKING:
    from langchain_core.tools import BaseTool
    from langchain_mcp_adapters.sessions import StreamableHttpConnection
    from mcp.types import Tool

settings = get_settings()


logger = logging.getLogger(__name__)

_SERVER_NAME = "memoryful"

_tool_schemas: list["Tool"] | None = None
_tool_schemas_lock = asyncio.Lock()


def _connection(access_token: str) -> "StreamableHttpConnection":
    return {
        "url": settings.mcp_server_url,
        "transport": "streamable_http",
        "headers": {"Authorization": f"Bearer {access_token}"},
    }


async def _fetch_tool_schemas(access_token: str) -> list["Tool"]:
    from langchain_mcp_adapters.sessions import create_session
    from mcp.types import PaginatedRequestParams

    tools: list[Tool] = []
    cursor: str | None = None
    async with create_session(_connection(access_token)) as session:
        await session.initialize()
        while True:
            page = await session.list_tools(params=PaginatedRequestParams(cursor=cursor))
            tools.extend(page.tools)
            cursor = page.nextCursor
            if not cursor:
                return tools


async def _get_tool_schemas(access_token: str) -> list["Tool"]:
    global _tool_schemas
    if _tool_schemas is None:
        async with _tool_schemas_lock:
            if _tool_schemas is None:
                _tool_schemas = await _fetch_tool_schemas(access_token)
    return _tool_schemas


async def load_mcp_tools(access_token: str) -> list["BaseTool"]:
    """Load the Memoryful MCP tools for a request, bound to the user's bearer."""
    from langchain_mcp_adapters.tools import convert_mcp_tool_to_langchain_tool

    connection = _connection(access_token)
    return [
        convert_mcp_tool_to_langchain_tool(
            None, schema, connection=connection, server_name=_SERVER_NAME
        )
        for schema in await _get_tool_schemas(access_token)
    ]
