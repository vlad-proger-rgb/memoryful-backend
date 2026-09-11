from typing import cast
from urllib.parse import urlencode

from fastmcp import Context

from ..utils.api_client import APIClient
from ..utils.validators import validate_non_negative_int


async def get_week_digests(
    ctx: Context,
    limit: int = 12,
    offset: int = 0,
) -> list[dict[str, object]]:
    """Get the user's weekly digests, newest first. Each one is a single AI pass over a
    finished week: its entries plus the observations and suggestions those days produced."""
    validate_non_negative_int(limit, "limit")
    validate_non_negative_int(offset, "offset")

    client = APIClient(ctx)
    params = urlencode({"limit": limit, "offset": offset})
    return cast(list[dict[str, object]], await client.get(f"/week-digests?{params}"))


async def get_week_digest(ctx: Context, week_start: str) -> dict[str, object]:
    """Get one weekly digest by the Monday it starts on, as an ISO date (YYYY-MM-DD)."""
    client = APIClient(ctx)
    return cast(dict[str, object], await client.get(f"/week-digests/{week_start}"))
