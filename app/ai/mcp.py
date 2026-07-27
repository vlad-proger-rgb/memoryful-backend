"""MCP tool loading for the in-app agent.

Loads the Memoryful MCP tools for a request, forwarding the user's bearer so the
MCP server executes each call as that user (per-user isolation).

Note: this is a fresh load per request. We do NOT cache the tool objects, because
`langchain-mcp-adapters` bakes the bearer into each tool at load time — a shared
cache would call the MCP server as the wrong user. The proper optimization (cache
the static tool *schemas* once and inject the bearer per request) needs a small
custom tool wrapper; left as a deliberate follow-up.
"""

import logging

from app.core.settings import MCP_SERVER_URL

logger = logging.getLogger(__name__)


async def load_mcp_tools(access_token: str) -> list:
    """Load the Memoryful MCP tools for a request, bound to the user's bearer."""
    from langchain_mcp_adapters.client import MultiServerMCPClient

    client = MultiServerMCPClient(
        {
            "memoryful": {
                "url": MCP_SERVER_URL,
                "transport": "streamable_http",
                "headers": {"Authorization": f"Bearer {access_token}"},
            }
        }
    )
    return await client.get_tools()
