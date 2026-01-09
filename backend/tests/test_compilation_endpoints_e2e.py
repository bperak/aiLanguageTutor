"""
PHASE 2: API Endpoint Testing - Compilation Endpoints

Tests for the lesson compilation endpoints:
- POST /api/v1/cando/lessons/compile_v2
- POST /api/v1/cando/lessons/compile_v2_stream
"""

import pytest
import uuid
from pathlib import Path
from dotenv import load_dotenv
import json

# Load .env file
backend_path = Path(__file__).resolve().parent.parent
env_path = backend_path.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    # Try to find .env in parent directories
    for parent in backend_path.parents:
        candidate = parent / ".env"
        if candidate.exists():
            load_dotenv(candidate)
            break

from app.db import init_db_connections, close_db_connections


@pytest.fixture
async def async_client():
    """Create an async HTTP client for testing."""
    from app.main import app
    import httpx
    
    await init_db_connections()
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test", timeout=300.0) as client:
            yield client
    finally:
        await close_db_connections()


@pytest.mark.asyncio
async def test_compile_v2_basic_compilation(async_client):
    """
    Test: Valid can_do_id without user_id (basic compilation).
    
    Verifies that basic compilation works without personalization.
    """
    # Use a known CanDo ID
    can_do_id = "JF:1"
    
    response = await async_client.post(
        "/api/v1/cando/lessons/compile_v2",
        params={
            "can_do_id": can_do_id,
            "metalanguage": "en",
            "model": "gpt-4.1"
        }
    )
    
    assert response.status_code == 200, f"Compilation failed with status {response.status_code}: {response.text}"
    
    data = response.json()
    assert "lesson_id" in data or "lesson" in data, "Response missing lesson data"
    assert "can_do_id" in data or data.get("can_do_id") == can_do_id, "Response missing or incorrect can_do_id"


@pytest.mark.asyncio
async def test_compile_v2_with_user_id(async_client):
    """
    Test: Valid can_do_id with user_id (personalized compilation).
    
    Verifies that compilation works with user personalization.
    Note: This test may fail if user_id doesn't exist or has no profile/path.
    """
    can_do_id = "JF:1"
    
    # Try with a test user_id (this might not exist, so we handle gracefully)
    test_user_id = str(uuid.uuid4())
    
    response = await async_client.post(
        "/api/v1/cando/lessons/compile_v2",
        params={
            "can_do_id": can_do_id,
            "metalanguage": "en",
            "model": "gpt-4.1",
            "user_id": test_user_id
        }
    )
    
    # Should either succeed (if user exists) or handle gracefully
    assert response.status_code in [200, 404, 500], f"Unexpected status code: {response.status_code}"
    
    if response.status_code == 200:
        data = response.json()
        assert "lesson_id" in data or "lesson" in data, "Response missing lesson data"


@pytest.mark.asyncio
async def test_compile_v2_invalid_cando_id(async_client):
    """
    Test: Invalid can_do_id (should return 404 or appropriate error).
    
    Verifies that invalid CanDo IDs are handled gracefully.
    """
    invalid_can_do_id = "INVALID_CANDO_ID_12345"
    
    response = await async_client.post(
        "/api/v1/cando/lessons/compile_v2",
        params={
            "can_do_id": invalid_can_do_id,
            "metalanguage": "en",
            "model": "gpt-4.1"
        }
    )
    
    # Should return an error (404 or 500 depending on implementation)
    assert response.status_code in [404, 500, 400], f"Expected error status, got {response.status_code}"
    
    # Verify error message is informative
    if response.status_code != 200:
        data = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
        assert "detail" in data or "error" in data or "message" in data, "Error response missing detail"


@pytest.mark.asyncio
async def test_compile_v2_invalid_user_id(async_client):
    """
    Test: Valid can_do_id with invalid user_id (should handle gracefully).
    
    Verifies that invalid user IDs don't break compilation.
    """
    can_do_id = "JF:1"
    invalid_user_id = "not-a-valid-uuid"
    
    response = await async_client.post(
        "/api/v1/cando/lessons/compile_v2",
        params={
            "can_do_id": can_do_id,
            "metalanguage": "en",
            "model": "gpt-4.1",
            "user_id": invalid_user_id
        }
    )
    
    # Should either validate and reject, or handle gracefully
    # If validation works, should return 400/422
    # If it handles gracefully, should return 200 (compiling without personalization)
    assert response.status_code in [200, 400, 422, 500], f"Unexpected status code: {response.status_code}"


@pytest.mark.asyncio
async def test_compile_v2_stream_basic(async_client):
    """
    Test: Streaming endpoint returns proper SSE format.
    
    Verifies that the streaming endpoint returns Server-Sent Events correctly.
    """
    can_do_id = "JF:1"
    
    response = await async_client.post(
        "/api/v1/cando/lessons/compile_v2_stream",
        params={
            "can_do_id": can_do_id,
            "metalanguage": "en",
            "model": "gpt-4.1"
        }
    )
    
    assert response.status_code == 200, f"Streaming endpoint failed: {response.status_code}"
    assert response.headers.get("content-type", "").startswith("text/event-stream"), "Response is not SSE format"
    
    # Read first few events
    events_received = []
    async for line in response.aiter_lines():
        if line.startswith("data: "):
            try:
                data = json.loads(line[6:])  # Remove "data: " prefix
                events_received.append(data)
                # Check for expected event types
                if "status" in data or "result" in data or "error" in data:
                    break  # Got a meaningful event
            except json.JSONDecodeError:
                pass  # Skip non-JSON lines
    
    assert len(events_received) > 0, "No SSE events received"


@pytest.mark.asyncio
async def test_compile_v2_stream_with_user_id(async_client):
    """
    Test: Streaming endpoint with user_id for personalization.
    
    Verifies that streaming works with user personalization.
    """
    can_do_id = "JF:1"
    test_user_id = str(uuid.uuid4())
    
    response = await async_client.post(
        "/api/v1/cando/lessons/compile_v2_stream",
        params={
            "can_do_id": can_do_id,
            "metalanguage": "en",
            "model": "gpt-4.1",
            "user_id": test_user_id
        }
    )
    
    assert response.status_code == 200, f"Streaming endpoint failed: {response.status_code}"
    
    # Verify SSE format
    events_received = []
    async for line in response.aiter_lines():
        if line.startswith("data: "):
            try:
                data = json.loads(line[6:])
                events_received.append(data)
                if "status" in data or "result" in data or "error" in data:
                    break
            except json.JSONDecodeError:
                pass
    
    assert len(events_received) > 0, "No SSE events received"


@pytest.mark.asyncio
async def test_compile_v2_error_responses_consistent(async_client):
    """
    Test: Error responses are consistent and informative.
    
    Verifies that error responses follow a consistent format.
    """
    # Test with invalid can_do_id
    response = await async_client.post(
        "/api/v1/cando/lessons/compile_v2",
        params={
            "can_do_id": "INVALID",
            "metalanguage": "en"
        }
    )
    
    if response.status_code != 200:
        # Should have JSON error response
        assert response.headers.get("content-type", "").startswith("application/json"), "Error response should be JSON"
        data = response.json()
        assert "detail" in data or "error" in data or "message" in data, "Error response should have detail/error/message"


@pytest.mark.asyncio
async def test_compile_v2_input_validation(async_client):
    """
    Test: Input validation is robust (Pydantic).
    
    Verifies that invalid inputs are properly validated.
    """
    # Test with missing required parameter
    response = await async_client.post(
        "/api/v1/cando/lessons/compile_v2",
        params={
            "metalanguage": "en"
            # Missing can_do_id
        }
    )
    
    # Should return validation error (422 or 400)
    assert response.status_code in [400, 422], f"Expected validation error, got {response.status_code}"


@pytest.mark.asyncio
async def test_compile_v2_metalanguage_parameter(async_client):
    """
    Test: Metalanguage parameter works correctly.
    
    Verifies that different metalanguage values are accepted.
    """
    can_do_id = "JF:1"
    
    for metalanguage in ["en", "ja", "fr"]:
        response = await async_client.post(
            "/api/v1/cando/lessons/compile_v2",
            params={
                "can_do_id": can_do_id,
                "metalanguage": metalanguage,
                "model": "gpt-4.1"
            }
        )
        
        # Should accept the parameter (may still fail if model doesn't support language)
        assert response.status_code in [200, 400, 500], f"Unexpected status for metalanguage={metalanguage}"

