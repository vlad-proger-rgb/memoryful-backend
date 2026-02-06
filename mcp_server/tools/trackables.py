from fastmcp import Context
from ..utils.api_client import APIClient


async def get_trackables(ctx: Context, access_token: str, limit: int = 10, offset: int = 0) -> list[dict[str, object]]:
    """Get trackable items from Memoryful API with pagination"""
    client = APIClient(ctx, access_token)
    return await client.get(f"/trackables?limit={limit}&offset={offset}")


async def get_trackable_by_id(ctx: Context, access_token: str, trackable_id: str) -> dict[str, object]:
    """Get a specific trackable item by ID"""
    client = APIClient(ctx, access_token)
    return await client.get(f"/trackables/{trackable_id}")


async def get_trackable_types(ctx: Context, access_token: str, limit: int = 10, offset: int = 0) -> list[dict[str, object]]:
    """Get trackable types from Memoryful API with pagination"""
    client = APIClient(ctx, access_token)
    return await client.get(f"/trackable-types?limit={limit}&offset={offset}")


async def get_trackable_type_by_id(ctx: Context, access_token: str, type_id: str) -> dict[str, object]:
    """Get a specific trackable type by ID"""
    client = APIClient(ctx, access_token)
    return await client.get(f"/trackable-types/{type_id}")


async def get_trackables_for_day(ctx: Context, access_token: str, day_id: str) -> list[dict[str, object]]:
    """Get trackable items for a specific day"""
    client = APIClient(ctx, access_token)
    return await client.get(f"/days/{day_id}/trackables")


async def get_trackable_progress(ctx: Context, access_token: str, trackable_id: str, limit: int = 10) -> list[dict[str, object]]:
    """Get progress history for a specific trackable"""
    client = APIClient(ctx, access_token)
    return await client.get(f"/trackables/{trackable_id}/progress?limit={limit}")
