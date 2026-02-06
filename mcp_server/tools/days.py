from typing import Literal
from urllib.parse import urlencode

from fastmcp import Context
from ..utils.api_client import APIClient


async def get_days(
    ctx: Context,
    access_token: str,
    limit: int = 10,
    offset: int = 0,
    sort_field: str | None = None,
    sort_order: str | None = None,
    view: Literal["list", "detail"] = "list",
    tag_names: str | None = None,
) -> list[dict[str, object]]:
    """Get days from Memoryful API with pagination"""
    client = APIClient(ctx, access_token)
    params: dict[str, int | str] = {"limit": limit, "offset": offset, "view": view}
    if sort_field is not None:
        params["sortField"] = sort_field
    if sort_order is not None:
        params["sortOrder"] = sort_order
    if tag_names is not None:
        params["tagNames"] = tag_names
    return await client.get(f"/days?{urlencode(params)}")


async def get_day_by_timestamp(ctx: Context, access_token: str, timestamp: int) -> dict[str, object]:
    """Get a specific day by UNIX timestamp"""
    client = APIClient(ctx, access_token)
    return await client.get(f"/days/{timestamp}")


async def get_random_day(ctx: Context, access_token: str, timestampStart: int | None = None, timestampEnd: int | None = None) -> dict[str, object]:
    """Get a random day with optional date range"""
    client = APIClient(ctx, access_token)
    params = {}
    if timestampStart is not None:
        params["timestampStart"] = timestampStart
    if timestampEnd is not None:
        params["timestampEnd"] = timestampEnd
    qs = f"?{urlencode(params)}" if params else ""
    return await client.get(f"/days/random{qs}")

