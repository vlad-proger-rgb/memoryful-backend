import logging
from typing import Any

import httpx
from fastmcp import Context
from ..settings import MEMORYFUL_API_BASE_URL

logger = logging.getLogger(__name__)


class APIClient:
    """HTTP client for making requests to the Memoryful API using a user-provided access token"""

    def __init__(self, ctx: Context, access_token: str):
        self.ctx = ctx
        self.base_url = MEMORYFUL_API_BASE_URL
        self.access_token = access_token

        if not self.base_url:
            raise ValueError("MEMORYFUL_API_BASE_URL environment variable is required")

        if not self.access_token:
            raise ValueError("access_token is required")

    @property
    def headers(self) -> dict:
        """Get headers with current access token"""
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.access_token}",
        }

    async def _make_request(self, method: str, endpoint: str, **kwargs) -> Any:
        """Make an authenticated request to the API"""
        url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        await self.ctx.info(f"{method=} {endpoint=} {kwargs=}")
        logger.info("%s %s", method, url)

        async with httpx.AsyncClient() as client:
            response = await client.request(method, url, headers=self.headers, **kwargs)
            logger.debug("Response: %s %s", response.status_code, method)
            response.raise_for_status()
            return response.json()

    async def get(self, endpoint: str) -> Any:
        """Make a GET request to the API"""
        try:
            return await self._make_request("GET", endpoint)
        except httpx.HTTPStatusError as e:
            logger.error("HTTP error on GET %s: %s - %s", endpoint, e.response.status_code, e.response.text)
            await self.ctx.error(f"HTTP error {e.response.status_code}: {e.response.text}")
            raise
        except Exception as e:
            logger.error("Request failed on GET %s: %s", endpoint, e, exc_info=True)
            await self.ctx.error(f"Request failed: {str(e)}")
            raise
