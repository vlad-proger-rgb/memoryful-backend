from fastmcp import Context
from ..utils.api_client import APIClient


async def get_months(ctx: Context, access_token: str, limit: int = 10, offset: int = 0) -> list[dict[str, object]]:
    """Get months from Memoryful API with pagination"""
    client = APIClient(ctx, access_token)
    return await client.get(f"/months?limit={limit}&offset={offset}")


async def get_month_by_id(ctx: Context, access_token: str, month_id: str) -> dict[str, object]:
    """Get a specific month by ID"""
    client = APIClient(ctx, access_token)
    return await client.get(f"/months/{month_id}")


async def get_months_by_year(ctx: Context, access_token: str, year: int) -> list[dict[str, object]]:
    """Get all months for a specific year"""
    client = APIClient(ctx, access_token)
    return await client.get(f"/months?year={year}")


async def get_current_month(ctx: Context, access_token: str) -> dict[str, object]:
    """Get the current month"""
    client = APIClient(ctx, access_token)
    return await client.get("/months/current")
