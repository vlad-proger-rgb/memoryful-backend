"""Every user's tool calls share one HTTP client, so nothing about one user may stay on it:
the bearer is sent per request and cookies are never kept."""

from unittest.mock import patch

import pytest
import respx
from fastmcp import Context
from httpx import HTTPStatusError, Response

from ..tools.tags import get_tags
from .conftest import api_url

_OK = {"code": 200, "msg": "ok", "data": []}


def _as_user(token: str):  # type: ignore[no-untyped-def]
    return patch(
        "mcp_server.utils.api_client.get_http_headers",
        return_value={"authorization": f"Bearer {token}"},
    )


@pytest.mark.asyncio
@respx.mock
async def test_each_call_sends_only_its_own_bearer(ctx: Context) -> None:
    route = respx.get(api_url("/tags/")).mock(return_value=Response(200, json=_OK))

    with _as_user("token-a"):
        await get_tags(ctx)
    with _as_user("token-b"):
        await get_tags(ctx)

    assert [c.request.headers["authorization"] for c in route.calls] == [
        "Bearer token-a",
        "Bearer token-b",
    ]


@pytest.mark.asyncio
@respx.mock
async def test_a_cookie_from_one_response_is_never_sent_again(ctx: Context) -> None:
    route = respx.get(api_url("/tags/")).mock(
        side_effect=[
            Response(200, json=_OK, headers={"set-cookie": "refresh_token=user-a; Path=/"}),
            Response(200, json=_OK),
        ]
    )

    with _as_user("token-a"):
        await get_tags(ctx)
    with _as_user("token-b"):
        await get_tags(ctx)

    assert "cookie" not in route.calls[1].request.headers


@pytest.mark.asyncio
@respx.mock
async def test_a_redirect_fails_instead_of_being_followed(ctx: Context) -> None:
    respx.get(api_url("/tags/")).mock(
        return_value=Response(307, headers={"location": api_url("/elsewhere/")})
    )
    target = respx.get(api_url("/elsewhere/")).mock(return_value=Response(200, json=_OK))

    with pytest.raises(HTTPStatusError):
        await get_tags(ctx)

    assert not target.called
