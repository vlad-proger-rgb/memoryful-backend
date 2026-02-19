import logging
import os
from typing import Any

import httpx
from fastmcp import Context
from fastmcp.server.dependencies import get_http_headers
from ..settings import MEMORYFUL_API_BASE_URL
from ..schemas import Msg

logger = logging.getLogger(__name__)


class APIClient:
    """HTTP client for making requests to the Memoryful API.

    Reads the Authorization header from the incoming MCP HTTP request
    so individual tool functions don't need an access_token parameter.
    """

    def __init__(self, ctx: Context):
        self.ctx = ctx
        self.base_url = MEMORYFUL_API_BASE_URL

        if not self.base_url:
            raise ValueError("MEMORYFUL_API_BASE_URL environment variable is required")

    @property
    def headers(self) -> dict[str, str]:
        """Get headers, forwarding the Authorization header from the MCP request.

        Falls back to the MEMORYFUL_ACCESS_TOKEN env var for stdio transports
        (e.g. Claude Desktop) where HTTP headers are not available.
        """
        auth = ""
        try:
            mcp_headers = get_http_headers()
            auth = mcp_headers.get("authorization", "")
        except Exception as e:
            logger.debug("Failed to get MCP headers: %s", e)
            pass

        if not auth:
            token = os.environ.get("MEMORYFUL_ACCESS_TOKEN", "")
            if token:
                auth = f"Bearer {token}"

        if not auth:
            raise ValueError(
                "No Authorization found. Either set the Authorization header "
                "in your MCP client, or set the MEMORYFUL_ACCESS_TOKEN env var."
            )
        return {
            "Content-Type": "application/json",
            "Authorization": auth,
        }

    async def _make_request(self, method: str, endpoint: str, **kwargs: Any) -> Any:
        """Make an authenticated request to the API"""
        if not endpoint:
            raise ValueError("endpoint cannot be empty")

        endpoint = endpoint.lstrip('/')
        if not endpoint:
            raise ValueError("endpoint cannot be empty after normalization")

        url = f"{self.base_url.rstrip('/')}/{endpoint}"
        await self.ctx.info(f"{method=} {endpoint=}")
        logger.info("%s %s", method, url)

        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.request(method, url, headers=self.headers, **kwargs)
            logger.debug("Response: %s %s", response.status_code, method)
            response.raise_for_status()

            try:
                raw = response.json()
            except Exception as e:
                logger.error("Failed to parse JSON response from %s: %s", url, e)
                raise ValueError(f"Invalid JSON response from API: {str(e)}")

            msg: Msg[object] = Msg.model_validate(raw)
            if msg.data is None:
                logger.debug("API returned null data for %s %s - this may be valid for empty datasets", method, endpoint)
            return msg.data

    async def get(self, endpoint: str) -> Any:
        """Make a GET request to the API"""
        try:
            return await self._make_request("GET", endpoint)
        except httpx.HTTPStatusError as e:
            url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
            logger.error("HTTP error on GET %s: %s - %s", url, e.response.status_code, e.response.text)
            await self.ctx.error(f"HTTP error {e.response.status_code} on {url}: {e.response.text}")
            raise
        except Exception as e:
            url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
            logger.error("Request failed on GET %s: %s", url, e, exc_info=True)
            await self.ctx.error(f"Request failed on {url}: {str(e)}")
            raise
