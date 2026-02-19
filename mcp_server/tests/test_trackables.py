import pytest
import respx
from httpx import Response

from fastmcp import Context

from .conftest import api_url
from ..tools.trackables import (
    get_trackables,
    get_trackable_by_id,
    get_trackable_types,
    get_trackable_type_by_id,
)

_FAKE_TR_ID = "00000000-0000-0000-0000-000000000001"
_FAKE_TT_ID = "00000000-0000-0000-0000-000000000010"


@pytest.mark.asyncio
@respx.mock
async def test_get_trackables_default(ctx: Context) -> None:
    mock_data = [{"id": _FAKE_TR_ID, "title": "Water intake", "typeId": _FAKE_TT_ID}]
    respx.get(api_url("/trackables")).mock(
        return_value=Response(200, json={"code": 200, "msg": "ok", "data": mock_data})
    )

    result = await get_trackables(ctx)

    assert len(result) == 1
    assert isinstance(result[0], dict)
    assert result[0]["title"] == "Water intake"


@pytest.mark.asyncio
@respx.mock
async def test_get_trackables_with_type_filter(ctx: Context) -> None:
    mock_data = [{"id": _FAKE_TR_ID, "title": "Steps", "typeId": _FAKE_TT_ID}]
    respx.get(api_url("/trackables")).mock(
        return_value=Response(200, json={"code": 200, "msg": "ok", "data": mock_data})
    )

    result = await get_trackables(ctx, type_id="type-abc")

    request = respx.calls.last.request
    assert "typeId=type-abc" in str(request.url)
    assert len(result) == 1


@pytest.mark.asyncio
@respx.mock
async def test_get_trackables_with_search(ctx: Context) -> None:
    respx.get(api_url("/trackables")).mock(
        return_value=Response(200, json={"code": 200, "msg": "ok", "data": []})
    )

    await get_trackables(ctx, search="water")

    request = respx.calls.last.request
    assert "search=water" in str(request.url)


@pytest.mark.asyncio
@respx.mock
async def test_get_trackable_by_id(ctx: Context) -> None:
    mock_data = {"id": _FAKE_TR_ID, "title": "Steps", "typeId": _FAKE_TT_ID}
    respx.get(api_url("/trackables/" + _FAKE_TR_ID)).mock(
        return_value=Response(200, json={"code": 200, "msg": "ok", "data": mock_data})
    )

    result = await get_trackable_by_id(ctx, _FAKE_TR_ID)

    assert isinstance(result, dict)
    assert result["title"] == "Steps"


@pytest.mark.asyncio
@respx.mock
async def test_get_trackable_types(ctx: Context) -> None:
    mock_data = [{"id": _FAKE_TT_ID, "name": "Health", "valueType": "number"}]
    respx.get(api_url("/trackable-types")).mock(
        return_value=Response(200, json={"code": 200, "msg": "ok", "data": mock_data})
    )

    result = await get_trackable_types(ctx)

    assert len(result) == 1
    assert isinstance(result[0], dict)
    assert result[0]["name"] == "Health"


@pytest.mark.asyncio
@respx.mock
async def test_get_trackable_type_by_id(ctx: Context) -> None:
    mock_data = {"id": _FAKE_TT_ID, "name": "Fitness", "valueType": "number"}
    respx.get(api_url("/trackable-types/" + _FAKE_TT_ID)).mock(
        return_value=Response(200, json={"code": 200, "msg": "ok", "data": mock_data})
    )

    result = await get_trackable_type_by_id(ctx, _FAKE_TT_ID)

    assert isinstance(result, dict)
    assert result["name"] == "Fitness"
