from fastmcp import Context
from ..utils.api_client import APIClient


async def get_insights(ctx: Context, access_token: str, limit: int = 10, offset: int = 0) -> list[dict[str, object]]:
    """Get insights from Memoryful API with pagination"""
    client = APIClient(ctx, access_token)
    return await client.get(f"/insights?limit={limit}&offset={offset}")


async def get_insight_by_id(ctx: Context, access_token: str, insight_id: str) -> dict[str, object]:
    """Get a specific insight by ID"""
    client = APIClient(ctx, access_token)
    return await client.get(f"/insights/{insight_id}")


async def get_insights_by_type(ctx: Context, access_token: str, insight_type: str, limit: int = 10) -> list[dict[str, object]]:
    """Get insights filtered by type"""
    client = APIClient(ctx, access_token)
    return await client.get(f"/insights?type={insight_type}&limit={limit}")


async def get_insights_for_day(ctx: Context, access_token: str, day_id: str) -> list[dict[str, object]]:
    """Get insights for a specific day"""
    client = APIClient(ctx, access_token)
    return await client.get(f"/days/{day_id}/insights")
