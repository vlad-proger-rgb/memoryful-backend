from typing import cast
from urllib.parse import urlencode

from fastmcp import Context

from ..utils.api_client import APIClient
from ..utils.validators import validate_non_negative_int


async def get_insights(
    ctx: Context,
    limit: int = 10,
    offset: int = 0,
    timestamp: int | None = None,
) -> list[dict[str, object]]:
    """Get insights from Memoryful API with pagination, optionally filtered by day timestamp"""
    validate_non_negative_int(limit, "limit")
    validate_non_negative_int(offset, "offset")
    if timestamp is not None:
        validate_non_negative_int(timestamp, "timestamp")

    client = APIClient(ctx)
    params: dict[str, int | str] = {"limit": limit, "offset": offset}
    if timestamp is not None:
        params["timestamp"] = timestamp
    return cast(list[dict[str, object]], await client.get(f"/insights?{urlencode(params)}"))
