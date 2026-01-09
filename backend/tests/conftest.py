"""
Pytest fixtures for backend tests.

This test suite includes both unit tests and API contract/integration tests.
The contract tests use `pytest.mark.anyio` and expect an `async_client` fixture
that can call the FastAPI app in-process.
"""

from __future__ import annotations

import pytest
import pytest_asyncio
import httpx

from app.main import app
from app.db import init_db_connections, close_db_connections


@pytest.fixture
def anyio_backend() -> str:
    """
    Restrict pytest-anyio to asyncio backend only.

    Reason: the test environment doesn't include trio, and contract tests should
    be backend-agnostic.
    """
    return "asyncio"


@pytest_asyncio.fixture(scope="function")
async def async_client():
    """
    Create an AsyncClient bound to the FastAPI ASGI app.

    Returns:
        httpx.AsyncClient: client that can make in-process requests.
    """
    # Ensure DB connections are initialized for in-process API tests.
    await init_db_connections()
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            yield client
    finally:
        await close_db_connections()


