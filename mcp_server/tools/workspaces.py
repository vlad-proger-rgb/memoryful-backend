from typing import cast

from fastmcp import Context

from ..utils.api_client import APIClient


async def get_my_workspace(ctx: Context) -> dict[str, object]:
    """Get the current user's workspace settings (backgrounds, etc.)"""
    client = APIClient(ctx)
    return cast(dict[str, object], await client.get("/workspaces/me"))
