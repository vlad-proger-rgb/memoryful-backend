from typing import cast
from urllib.parse import urlencode

from fastmcp import Context

from ..utils.api_client import APIClient
from ..utils.validators import validate_non_empty_string


async def get_trackables(ctx: Context, type_id: str | None = None, search: str | None = None) -> list[dict[str, object]]:
    """Get trackable items from Memoryful API, optionally filtered by type or search query"""
    validate_non_empty_string(type_id, "type_id")
    validate_non_empty_string(search, "search")

    client = APIClient(ctx)
    params: dict[str, str] = {}
    if type_id is not None:
        params["typeId"] = type_id
    if search is not None:
        params["search"] = search
    qs = f"?{urlencode(params)}" if params else ""
    return cast(list[dict[str, object]], await client.get(f"/trackables{qs}"))


async def get_trackable_by_id(ctx: Context, trackable_id: str) -> dict[str, object]:
    """Get a specific trackable item by ID"""
    validate_non_empty_string(trackable_id, "trackable_id")

    client = APIClient(ctx)
    return cast(dict[str, object], await client.get(f"/trackables/{trackable_id}"))


async def get_trackable_types(ctx: Context) -> list[dict[str, object]]:
    """Get trackable types from Memoryful API"""
    client = APIClient(ctx)
    return cast(list[dict[str, object]], await client.get("/trackable-types"))


async def get_trackable_type_by_id(ctx: Context, type_id: str) -> dict[str, object]:
    """Get a specific trackable type by ID"""
    validate_non_empty_string(type_id, "type_id")

    client = APIClient(ctx)
    return cast(dict[str, object], await client.get(f"/trackable-types/{type_id}"))
