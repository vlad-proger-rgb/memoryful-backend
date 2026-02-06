from fastmcp import Context
from ..utils.api_client import APIClient


async def get_suggestions(ctx: Context, access_token: str, limit: int = 10, offset: int = 0) -> list[dict[str, object]]:
    """Get suggestions from Memoryful API with pagination"""
    client = APIClient(ctx, access_token)
    return await client.get(f"/suggestions?limit={limit}&offset={offset}")


async def get_suggestion_by_id(ctx: Context, access_token: str, suggestion_id: str) -> dict[str, object]:
    """Get a specific suggestion by ID"""
    client = APIClient(ctx, access_token)
    return await client.get(f"/suggestions/{suggestion_id}")


async def get_suggestions_by_type(ctx: Context, access_token: str, suggestion_type: str, limit: int = 10) -> list[dict[str, object]]:
    """Get suggestions filtered by type"""
    client = APIClient(ctx, access_token)
    return await client.get(f"/suggestions?type={suggestion_type}&limit={limit}")
