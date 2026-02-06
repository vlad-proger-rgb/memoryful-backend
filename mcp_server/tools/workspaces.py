from fastmcp import Context
from ..utils.api_client import APIClient


async def get_workspaces(ctx: Context, access_token: str, limit: int = 10, offset: int = 0) -> list[dict[str, object]]:
    """Get workspaces from Memoryful API with pagination"""
    client = APIClient(ctx, access_token)
    return await client.get(f"/workspaces?limit={limit}&offset={offset}")


async def get_workspace_by_id(ctx: Context, access_token: str, workspace_id: str) -> dict[str, object]:
    """Get a specific workspace by ID"""
    client = APIClient(ctx, access_token)
    return await client.get(f"/workspaces/{workspace_id}")


async def get_workspace_days(ctx: Context, access_token: str, workspace_id: str, limit: int = 10, offset: int = 0) -> list[dict[str, object]]:
    """Get days for a specific workspace"""
    client = APIClient(ctx, access_token)
    return await client.get(f"/workspaces/{workspace_id}/days?limit={limit}&offset={offset}")


async def get_workspace_insights(ctx: Context, access_token: str, workspace_id: str, limit: int = 10) -> list[dict[str, object]]:
    """Get insights for a specific workspace"""
    client = APIClient(ctx, access_token)
    return await client.get(f"/workspaces/{workspace_id}/insights?limit={limit}")
