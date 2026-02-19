from typing import cast

from fastmcp import Context

from ..utils.api_client import APIClient
from ..utils.validators import validate_non_negative_int, validate_month_number


async def get_months_by_year(ctx: Context, year: int) -> list[dict[str, object]]:
    """Get all months for a specific year"""
    validate_non_negative_int(year, "year")

    client = APIClient(ctx)
    return cast(list[dict[str, object]], await client.get(f"/months/{year}"))


async def get_month_by_year_and_month_number(ctx: Context, year: int, month_number: int) -> dict[str, object]:
    """Get a specific month by ID"""
    validate_non_negative_int(year, "year")
    validate_month_number(month_number)

    client = APIClient(ctx)
    return cast(dict[str, object], await client.get(f"/months/{year}/{month_number}"))
