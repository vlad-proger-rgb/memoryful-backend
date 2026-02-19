import pytest
import respx
from httpx import Response

from fastmcp import Context

from .conftest import api_url
from ..tools.insights import get_insights

_FAKE_ID = "00000000-0000-0000-0000-000000000001"
_FAKE_USER_ID = "00000000-0000-0000-0000-000000000002"
_FAKE_MODEL_ID = "00000000-0000-0000-0000-000000000003"
_FAKE_TYPE_ID = "00000000-0000-0000-0000-000000000004"


def _insight(ts: int = 1700000000, **overrides: object) -> dict:
    return {
        "id": _FAKE_ID,
        "userId": _FAKE_USER_ID,
        "modelId": _FAKE_MODEL_ID,
        "insightTypeId": _FAKE_TYPE_ID,
        "timestamp": ts,
        "dateBegin": "2025-01-01",
        "description": "Test insight",
        "content": "Feeling good",
        "createdAt": "2025-01-01T00:00:00",
        **overrides,
    }


@pytest.mark.asyncio
@respx.mock
async def test_get_insights_default(ctx: Context) -> None:
    mock_data = [_insight()]
    respx.get(api_url("/insights")).mock(
        return_value=Response(200, json={"code": 200, "msg": "ok", "data": mock_data})
    )

    result = await get_insights(ctx)

    assert len(result) == 1
    assert isinstance(result[0], dict)
    assert result[0]["content"] == "Feeling good"
    request = respx.calls.last.request
    assert "limit=10" in str(request.url)
    assert "offset=0" in str(request.url)


@pytest.mark.asyncio
@respx.mock
async def test_get_insights_with_pagination(ctx: Context) -> None:
    respx.get(api_url("/insights")).mock(
        return_value=Response(200, json={"code": 200, "msg": "ok", "data": []})
    )

    await get_insights(ctx, limit=5, offset=20)

    request = respx.calls.last.request
    assert "limit=5" in str(request.url)
    assert "offset=20" in str(request.url)


@pytest.mark.asyncio
@respx.mock
async def test_get_insights_by_timestamp(ctx: Context) -> None:
    mock_data = [_insight(ts=1700000000)]
    respx.get(api_url("/insights")).mock(
        return_value=Response(200, json={"code": 200, "msg": "ok", "data": mock_data})
    )

    result = await get_insights(ctx, timestamp=1700000000)

    assert len(result) == 1
    assert result[0]["timestamp"] == 1700000000
    request = respx.calls.last.request
    assert "timestamp=1700000000" in str(request.url)


@pytest.mark.asyncio
@respx.mock
async def test_get_insights_empty(ctx: Context) -> None:
    respx.get(api_url("/insights")).mock(
        return_value=Response(200, json={"code": 200, "msg": "ok", "data": []})
    )

    result = await get_insights(ctx)

    assert result == []
