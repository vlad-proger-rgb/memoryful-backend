import pytest
import respx
from httpx import Response

from fastmcp import Context

from .conftest import api_url
from ..tools.suggestions import get_suggestions

_FAKE_ID = "00000000-0000-0000-0000-000000000001"
_FAKE_USER_ID = "00000000-0000-0000-0000-000000000002"
_FAKE_MODEL_ID = "00000000-0000-0000-0000-000000000003"


def _suggestion(ts: int = 1700000000, **overrides: object) -> dict:
    return {
        "id": _FAKE_ID,
        "userId": _FAKE_USER_ID,
        "modelId": _FAKE_MODEL_ID,
        "timestamp": ts,
        "description": "Test suggestion",
        "date": "2025-01-01",
        "content": "Go for a walk",
        **overrides,
    }


@pytest.mark.asyncio
@respx.mock
async def test_get_suggestions_default(ctx: Context) -> None:
    mock_data = [_suggestion()]
    respx.get(api_url("/suggestions")).mock(
        return_value=Response(200, json={"code": 200, "msg": "ok", "data": mock_data})
    )

    result = await get_suggestions(ctx)

    assert len(result) == 1
    assert isinstance(result[0], dict)
    assert result[0]["content"] == "Go for a walk"
    request = respx.calls.last.request
    assert "limit=10" in str(request.url)
    assert "offset=0" in str(request.url)


@pytest.mark.asyncio
@respx.mock
async def test_get_suggestions_with_pagination(ctx: Context) -> None:
    respx.get(api_url("/suggestions")).mock(
        return_value=Response(200, json={"code": 200, "msg": "ok", "data": []})
    )

    await get_suggestions(ctx, limit=3, offset=6)

    request = respx.calls.last.request
    assert "limit=3" in str(request.url)
    assert "offset=6" in str(request.url)


@pytest.mark.asyncio
@respx.mock
async def test_get_suggestions_by_timestamp(ctx: Context) -> None:
    mock_data = [_suggestion(ts=1700000000)]
    respx.get(api_url("/suggestions")).mock(
        return_value=Response(200, json={"code": 200, "msg": "ok", "data": mock_data})
    )

    result = await get_suggestions(ctx, timestamp=1700000000)

    assert len(result) == 1
    assert result[0]["timestamp"] == 1700000000
    request = respx.calls.last.request
    assert "timestamp=1700000000" in str(request.url)


@pytest.mark.asyncio
@respx.mock
async def test_get_suggestions_empty(ctx: Context) -> None:
    respx.get(api_url("/suggestions")).mock(
        return_value=Response(200, json={"code": 200, "msg": "ok", "data": []})
    )

    result = await get_suggestions(ctx)

    assert result == []
