import pytest
import respx
from httpx import Response

from fastmcp import Context

from .conftest import api_url
from ..tools.tags import get_tags, get_tag_by_id

_FAKE_TAG_ID = "00000000-0000-0000-0000-000000000001"
_FAKE_TAG_ID_2 = "00000000-0000-0000-0000-000000000002"


@pytest.mark.asyncio
@respx.mock
async def test_get_tags(ctx: Context) -> None:
    mock_data = [
        {"id": _FAKE_TAG_ID, "name": "travel"},
        {"id": _FAKE_TAG_ID_2, "name": "food"},
    ]
    respx.get(api_url("/tags/")).mock(
        return_value=Response(200, json={"code": 200, "msg": "ok", "data": mock_data})
    )

    result = await get_tags(ctx)

    assert len(result) == 2
    assert all(isinstance(t, dict) for t in result)
    assert result[0]["name"] == "travel"


@pytest.mark.asyncio
@respx.mock
async def test_get_tags_empty(ctx: Context) -> None:
    respx.get(api_url("/tags/")).mock(
        return_value=Response(200, json={"code": 200, "msg": "ok", "data": []})
    )

    result = await get_tags(ctx)

    assert result == []


@pytest.mark.asyncio
@respx.mock
async def test_get_tag_by_id(ctx: Context) -> None:
    mock_data = {"id": _FAKE_TAG_ID, "name": "fitness"}
    respx.get(api_url("/tags/" + _FAKE_TAG_ID)).mock(
        return_value=Response(200, json={"code": 200, "msg": "ok", "data": mock_data})
    )

    result = await get_tag_by_id(ctx, _FAKE_TAG_ID)

    assert isinstance(result, dict)
    assert result["name"] == "fitness"


@pytest.mark.asyncio
@respx.mock
async def test_get_tag_by_id_not_found(ctx: Context) -> None:
    respx.get(api_url("/tags/nonexistent")).mock(
        return_value=Response(404, json={"code": 404, "msg": "Not found", "data": None})
    )

    with pytest.raises(Exception):
        await get_tag_by_id(ctx, "nonexistent")
