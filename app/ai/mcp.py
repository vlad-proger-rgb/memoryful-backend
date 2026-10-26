"""MCP tool loading for the in-app agent, forwarding the user's bearer per request.

Loaded fresh every time: `langchain-mcp-adapters` bakes the bearer into each tool, so a
shared cache would call the MCP server as the wrong user.
"""

import logging

from app.core.settings import get_settings

settings = get_settings()


logger = logging.getLogger(__name__)


async def load_mcp_tools(access_token: str) -> list:
    """Load the Memoryful MCP tools for a request, bound to the user's bearer."""
    from langchain_mcp_adapters.client import MultiServerMCPClient

    client = MultiServerMCPClient(
        {
            "memoryful": {
                "url": settings.mcp_server_url,
                "transport": "streamable_http",
                "headers": {"Authorization": f"Bearer {access_token}"},
            }
        }
    )
    return await client.get_tools()
