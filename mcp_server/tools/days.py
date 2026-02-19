from typing import Literal, cast
from urllib.parse import urlencode

from fastmcp import Context

from ..utils.api_client import APIClient
from ..utils.validators import validate_non_empty_string, validate_non_negative_int


async def get_days(
    ctx: Context,
    limit: int = 10,
    offset: int = 0,
    sort_field: str | None = None,
    sort_order: str | None = None,
    view: Literal["list", "detail"] = "list",
    tag_names: str | None = None,
) -> list[dict[str, object]]:
    """Get days from Memoryful API with pagination"""
    validate_non_negative_int(limit, "limit")
    validate_non_negative_int(offset, "offset")
    validate_non_empty_string(sort_field, "sort_field")
    validate_non_empty_string(sort_order, "sort_order")
    validate_non_empty_string(tag_names, "tag_names")

    client = APIClient(ctx)
    params: dict[str, int | str] = {"limit": limit, "offset": offset, "view": view}
    if sort_field is not None:
        params["sortField"] = sort_field
    if sort_order is not None:
        params["sortOrder"] = sort_order
    if tag_names is not None:
        params["tagNames"] = tag_names
    return cast(list[dict[str, object]], await client.get(f"/days?{urlencode(params)}"))


async def get_day_by_timestamp(ctx: Context, timestamp: int) -> dict[str, object]:
    """Get a specific day by UNIX timestamp"""
    validate_non_negative_int(timestamp, "timestamp")

    client = APIClient(ctx)
    return cast(dict[str, object], await client.get(f"/days/{timestamp}"))


async def get_random_day(ctx: Context, timestampStart: int | None = None, timestampEnd: int | None = None) -> dict[str, object]:
    """Get a random day with optional date range"""
    if timestampStart is not None:
        validate_non_negative_int(timestampStart, "timestampStart")
    if timestampEnd is not None:
        validate_non_negative_int(timestampEnd, "timestampEnd")

    client = APIClient(ctx)
    params = {}
    if timestampStart is not None:
        params["timestampStart"] = timestampStart
    if timestampEnd is not None:
        params["timestampEnd"] = timestampEnd
    qs = f"?{urlencode(params)}" if params else ""
    return cast(dict[str, object], await client.get(f"/days/random{qs}"))
