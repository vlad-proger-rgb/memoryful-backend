from typing import cast

from fastmcp import Context

from ..utils.api_client import APIClient
from ..utils.validators import validate_non_empty_string


async def get_tags(ctx: Context) -> list[dict[str, object]]:
    """Get tags from Memoryful API"""
    client = APIClient(ctx)
    return cast(list[dict[str, object]], await client.get("/tags/"))


async def get_tag_by_id(ctx: Context, tag_id: str) -> dict[str, object]:
    """Get a specific tag by ID"""
    validate_non_empty_string(tag_id, "tag_id")

    client = APIClient(ctx)
    return cast(dict[str, object], await client.get(f"/tags/{tag_id}"))
