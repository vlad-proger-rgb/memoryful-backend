from fastmcp import Context
from ..utils.api_client import APIClient


async def get_tags(ctx: Context, access_token: str) -> list[dict[str, object]]:
    """Get tags from Memoryful API"""
    client = APIClient(ctx, access_token)
    return await client.get(f"/tags/")


async def get_tag_by_id(ctx: Context, access_token: str, tag_id: str) -> dict[str, object]:
    """Get a specific tag by ID"""
    client = APIClient(ctx, access_token)
    return await client.get(f"/tags/{tag_id}")
