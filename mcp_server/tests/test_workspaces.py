import pytest
import respx
from httpx import Response

from fastmcp import Context

from .conftest import api_url
from ..tools.workspaces import get_my_workspace

_FAKE_USER_ID = "00000000-0000-0000-0000-000000000001"


@pytest.mark.asyncio
@respx.mock
async def test_get_my_workspace(ctx: Context) -> None:
    mock_data = {
        "userId": _FAKE_USER_ID,
        "dashboardBackground": "img1.jpg",
        "dayBackground": "img2.jpg",
        "searchBackground": None,
        "settingsBackground": None,
    }
    respx.get(api_url("/workspaces/me")).mock(
        return_value=Response(200, json={"code": 200, "msg": "ok", "data": mock_data})
    )

    result = await get_my_workspace(ctx)

    assert isinstance(result, dict)
    assert result["dashboardBackground"] == "img1.jpg"
    assert result["dayBackground"] == "img2.jpg"
