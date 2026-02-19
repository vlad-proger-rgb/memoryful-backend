import pytest
import respx
from httpx import Response

from fastmcp import Context

from .conftest import api_url
from ..tools.months import get_months_by_year, get_month_by_year_and_month_number

_FAKE_USER_ID = "00000000-0000-0000-0000-000000000001"


@pytest.mark.asyncio
@respx.mock
async def test_get_months_by_year(ctx: Context) -> None:
    mock_data = [
        {"userId": _FAKE_USER_ID, "year": 2025, "month": 1, "description": "January"},
        {"userId": _FAKE_USER_ID, "year": 2025, "month": 2, "description": "February"},
    ]
    respx.get(api_url("/months/2025")).mock(
        return_value=Response(200, json={"code": 200, "msg": "ok", "data": mock_data})
    )

    result = await get_months_by_year(ctx, 2025)

    assert len(result) == 2
    assert all(isinstance(m, dict) for m in result)
    assert result[0]["month"] == 1


@pytest.mark.asyncio
@respx.mock
async def test_get_months_by_year_empty(ctx: Context) -> None:
    respx.get(api_url("/months/2020")).mock(
        return_value=Response(200, json={"code": 200, "msg": "ok", "data": []})
    )

    result = await get_months_by_year(ctx, 2020)

    assert result == []


@pytest.mark.asyncio
@respx.mock
async def test_get_month_by_year_and_month_number(ctx: Context) -> None:
    mock_data = {
        "userId": _FAKE_USER_ID,
        "year": 2025,
        "month": 3,
        "description": "March",
        "backgroundImage": None,
    }
    respx.get(api_url("/months/2025/3")).mock(
        return_value=Response(200, json={"code": 200, "msg": "ok", "data": mock_data})
    )

    result = await get_month_by_year_and_month_number(ctx, 2025, 3)

    assert isinstance(result, dict)
    assert result["month"] == 3
    assert result["description"] == "March"


@pytest.mark.asyncio
@respx.mock
async def test_get_month_by_year_and_month_number_not_found(ctx: Context) -> None:
    respx.get(api_url("/months/2025/13")).mock(
        return_value=Response(404, json={"code": 404, "msg": "Not found", "data": None})
    )

    with pytest.raises(Exception):
        await get_month_by_year_and_month_number(ctx, 2025, 13)
