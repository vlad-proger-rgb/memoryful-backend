import os
from collections.abc import Generator
from typing import cast
from unittest.mock import AsyncMock, patch

import pytest
from fastmcp import Context

# Set env before any mcp_server imports
os.environ.setdefault("MEMORYFUL_API_BASE_URL", "http://testserver")

_TEST_TOKEN = "test-access-token"


class MockContext:
    """Lightweight stub for fastmcp.Context used in tool tests."""

    def __init__(self) -> None:
        self.info = AsyncMock()
        self.error = AsyncMock()
        self.warning = AsyncMock()
        self.debug = AsyncMock()
        self.report_progress = AsyncMock()


@pytest.fixture
def ctx() -> Context:
    return cast(Context, MockContext())


@pytest.fixture(autouse=True)
def _mock_mcp_headers() -> Generator[None]:
    """Auto-mock get_http_headers so APIClient picks up the Authorization header."""
    with patch(
        "mcp_server.utils.api_client.get_http_headers",
        return_value={"authorization": f"Bearer {_TEST_TOKEN}"},
    ):
        yield


def api_url(path: str) -> str:
    """Build a full URL for the test API server."""
    base = os.environ["MEMORYFUL_API_BASE_URL"].rstrip("/")
    return f"{base}/{path.lstrip('/')}"
