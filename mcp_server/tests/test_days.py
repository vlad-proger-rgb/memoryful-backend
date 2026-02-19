import pytest
import respx
from httpx import Response

from fastmcp import Context

from .conftest import api_url
from ..tools.days import get_days, get_day_by_timestamp, get_random_day

_FAKE_CITY_ID = "00000000-0000-0000-0000-000000000010"
_FAKE_COUNTRY_ID = "00000000-0000-0000-0000-000000000020"
_FAKE_CITY = {"id": _FAKE_CITY_ID, "name": "Kyiv"}
_FAKE_CITY_DETAIL = {
    "id": _FAKE_CITY_ID,
    "name": "Kyiv",
    "country": {"id": _FAKE_COUNTRY_ID, "name": "Ukraine", "code": "UA"},
}


def _day_list_item(ts: int = 1700000000, **overrides: object) -> dict:
    return {"timestamp": ts, "city": _FAKE_CITY, **overrides}


def _day_detail(ts: int = 1700000000, **overrides: object) -> dict:
    return {
        "timestamp": ts,
        "content": "Day content",
        "city": _FAKE_CITY_DETAIL,
        "createdAt": "2025-01-01T00:00:00",
        "updatedAt": "2025-01-01T00:00:00",
        **overrides,
    }


@pytest.mark.asyncio
@respx.mock
async def test_get_days_default_params(ctx: Context) -> None:
    mock_data = [_day_list_item(description="A day")]
    respx.get(api_url("/days")).mock(
        return_value=Response(200, json={"code": 200, "msg": "ok", "data": mock_data})
    )

    result = await get_days(ctx)

    assert len(result) == 1
    assert isinstance(result[0], dict)
    assert result[0]["timestamp"] == 1700000000
    assert result[0]["description"] == "A day"
    request = respx.calls.last.request
    assert "limit=10" in str(request.url)
    assert "offset=0" in str(request.url)
    assert "view=list" in str(request.url)


@pytest.mark.asyncio
@respx.mock
async def test_get_days_with_pagination(ctx: Context) -> None:
    mock_data = [_day_detail()]
    respx.get(api_url("/days")).mock(
        return_value=Response(200, json={"code": 200, "msg": "ok", "data": mock_data})
    )

    result = await get_days(ctx, limit=5, offset=10, view="detail")

    assert isinstance(result[0], dict)
    request = respx.calls.last.request
    assert "limit=5" in str(request.url)
    assert "offset=10" in str(request.url)
    assert "view=detail" in str(request.url)


@pytest.mark.asyncio
@respx.mock
async def test_get_days_with_sort_and_tags(ctx: Context) -> None:
    respx.get(api_url("/days")).mock(
        return_value=Response(200, json={"code": 200, "msg": "ok", "data": []})
    )

    await get_days(ctx, sort_field="timestamp", sort_order="desc", tag_names="travel,food")

    request = respx.calls.last.request
    url_str = str(request.url)
    assert "sortField=timestamp" in url_str
    assert "sortOrder=desc" in url_str
    assert "tagNames=travel" in url_str


@pytest.mark.asyncio
@respx.mock
async def test_get_day_by_timestamp(ctx: Context) -> None:
    mock_data = _day_detail(steps=5000)
    respx.get(api_url("/days/1700000000")).mock(
        return_value=Response(200, json={"code": 200, "msg": "ok", "data": mock_data})
    )

    result = await get_day_by_timestamp(ctx, 1700000000)

    assert isinstance(result, dict)
    assert result["steps"] == 5000


@pytest.mark.asyncio
@respx.mock
async def test_get_day_by_timestamp_not_found(ctx: Context) -> None:
    respx.get(api_url("/days/9999999999")).mock(
        return_value=Response(404, json={"code": 404, "msg": "Not found", "data": None})
    )

    with pytest.raises(Exception):
        await get_day_by_timestamp(ctx, 9999999999)


@pytest.mark.asyncio
@respx.mock
async def test_get_random_day(ctx: Context) -> None:
    mock_data = _day_detail(description="Random day")
    respx.get(api_url("/days/random")).mock(
        return_value=Response(200, json={"code": 200, "msg": "ok", "data": mock_data})
    )

    result = await get_random_day(ctx)

    assert isinstance(result, dict)
    assert result["description"] == "Random day"


@pytest.mark.asyncio
@respx.mock
async def test_get_random_day_with_range(ctx: Context) -> None:
    mock_data = _day_detail()
    respx.get(api_url("/days/random")).mock(
        return_value=Response(200, json={"code": 200, "msg": "ok", "data": mock_data})
    )

    result = await get_random_day(ctx, timestampStart=1690000000, timestampEnd=1700000000)

    assert isinstance(result, dict)
    request = respx.calls.last.request
    url_str = str(request.url)
    assert "timestampStart=1690000000" in url_str
    assert "timestampEnd=1700000000" in url_str
