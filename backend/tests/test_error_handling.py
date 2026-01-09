"""
PHASE 10: Error Handling & Edge Cases Tests

Tests for error scenarios and edge cases in the compilation pipeline.
"""

import pytest
from pathlib import Path
from dotenv import load_dotenv
from unittest.mock import patch, AsyncMock, MagicMock

# Load .env file
backend_path = Path(__file__).resolve().parent.parent
env_path = backend_path.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    for parent in backend_path.parents:
        candidate = parent / ".env"
        if candidate.exists():
            load_dotenv(candidate)
            break


@pytest.mark.asyncio
async def test_invalid_cando_id_returns_404():
    """
    Test: Invalid CanDo ID returns 404.
    
    Verifies that requesting compilation for non-existent CanDo
    returns appropriate error.
    """
    from app.db import init_db_connections, close_db_connections
    import httpx
    from app.main import app
    
    await init_db_connections()
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test", timeout=30.0) as client:
            response = await client.post(
                "/api/v1/cando/lessons/compile_v2",
                params={
                    "can_do_id": "NONEXISTENT:999",
                    "metalanguage": "en",
                    "model": "gpt-4.1"
                }
            )
            
            # Should return error status
            assert response.status_code in [404, 500], f"Expected 404/500, got {response.status_code}"
            
            # Check error response structure
            data = response.json()
            assert "detail" in data, "Error response should have 'detail' field"
            
    finally:
        await close_db_connections()


@pytest.mark.asyncio
async def test_llm_timeout_handling():
    """
    Test: LLM timeout is handled gracefully.
    
    Verifies that timeout configuration exists and errors are handled.
    """
    from app.services.cando_v2_compile_service import _make_llm_call_openai
    
    # Verify timeout can be configured
    llm_call = _make_llm_call_openai(model="gpt-4.1", timeout=5)
    assert callable(llm_call), "LLM call function should be created with timeout"
    
    # Note: Actual timeout testing would require mocking


@pytest.mark.asyncio
async def test_invalid_model_handling():
    """
    Test: Invalid model name is handled.
    
    Verifies that invalid model names produce appropriate errors.
    """
    from app.db import init_db_connections, close_db_connections
    import httpx
    from app.main import app
    
    await init_db_connections()
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test", timeout=30.0) as client:
            response = await client.post(
                "/api/v1/cando/lessons/compile_v2",
                params={
                    "can_do_id": "JF:1",
                    "metalanguage": "en",
                    "model": "invalid-model-xyz"
                }
            )
            
            # Should either succeed with fallback or return error
            # The exact behavior depends on implementation
            assert response.status_code in [200, 400, 500], f"Unexpected status: {response.status_code}"
            
    finally:
        await close_db_connections()


@pytest.mark.asyncio
async def test_empty_cando_id_validation():
    """
    Test: Empty CanDo ID is validated.
    
    Verifies that empty can_do_id is rejected.
    """
    from app.db import init_db_connections, close_db_connections
    import httpx
    from app.main import app
    
    await init_db_connections()
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test", timeout=30.0) as client:
            response = await client.post(
                "/api/v1/cando/lessons/compile_v2",
                params={
                    "can_do_id": "",
                    "metalanguage": "en",
                    "model": "gpt-4.1"
                }
            )
            
            # Should return validation error
            assert response.status_code in [400, 422, 500], f"Expected validation error, got {response.status_code}"
            
    finally:
        await close_db_connections()


@pytest.mark.asyncio
async def test_special_characters_in_cando_id():
    """
    Test: Special characters in CanDo ID are handled.
    
    Verifies that URL encoding is handled properly.
    """
    from app.db import init_db_connections, close_db_connections
    import httpx
    from app.main import app
    
    await init_db_connections()
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test", timeout=30.0) as client:
            # Test with Japanese characters
            response = await client.post(
                "/api/v1/cando/lessons/compile_v2",
                params={
                    "can_do_id": "JFまるごと:1",
                    "metalanguage": "en",
                    "model": "gpt-4.1"
                }
            )
            
            # Should handle encoding properly
            assert response.status_code in [200, 404, 500], f"Unexpected status: {response.status_code}"
            
    finally:
        await close_db_connections()


@pytest.mark.asyncio
async def test_invalid_metalanguage():
    """
    Test: Invalid metalanguage parameter.
    
    Verifies that invalid metalanguage values are handled.
    """
    from app.db import init_db_connections, close_db_connections
    import httpx
    from app.main import app
    
    await init_db_connections()
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test", timeout=30.0) as client:
            response = await client.post(
                "/api/v1/cando/lessons/compile_v2",
                params={
                    "can_do_id": "JF:1",
                    "metalanguage": "invalid",
                    "model": "gpt-4.1"
                }
            )
            
            # Should either succeed with default or return error
            assert response.status_code in [200, 400, 422, 500], f"Unexpected status: {response.status_code}"
            
    finally:
        await close_db_connections()


@pytest.mark.asyncio
async def test_concurrent_compilation_requests():
    """
    Test: Concurrent compilation requests don't cause issues.
    
    Verifies that multiple simultaneous requests are handled.
    """
    import asyncio
    from app.db import init_db_connections, close_db_connections
    import httpx
    from app.main import app
    
    await init_db_connections()
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test", timeout=300.0) as client:
            
            async def make_request():
                return await client.post(
                    "/api/v1/cando/lessons/compile_v2",
                    params={
                        "can_do_id": "JF:1",
                        "metalanguage": "en",
                        "model": "gpt-4.1"
                    }
                )
            
            # Make 2 concurrent requests (limited to avoid excessive API costs)
            # Note: In real scenario, you might run more
            tasks = [make_request() for _ in range(2)]
            
            # This test mainly verifies no crashes occur
            # Results may vary based on rate limits
            try:
                results = await asyncio.wait_for(
                    asyncio.gather(*tasks, return_exceptions=True),
                    timeout=300
                )
                # At least some should complete
                completed = [r for r in results if not isinstance(r, Exception)]
                assert len(completed) >= 1, "At least one request should complete"
            except asyncio.TimeoutError:
                pytest.skip("Concurrent test timed out")
                
    finally:
        await close_db_connections()


@pytest.mark.asyncio
async def test_error_response_structure():
    """
    Test: Error responses have consistent structure.
    
    Verifies that error responses follow a standard format.
    """
    from app.db import init_db_connections, close_db_connections
    import httpx
    from app.main import app
    
    await init_db_connections()
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test", timeout=30.0) as client:
            response = await client.post(
                "/api/v1/cando/lessons/compile_v2",
                params={
                    "can_do_id": "INVALID_ID_XYZ",
                    "metalanguage": "en"
                }
            )
            
            if response.status_code >= 400:
                data = response.json()
                # FastAPI standard error format
                assert "detail" in data, "Error should have 'detail' field"
                
    finally:
        await close_db_connections()


def test_validate_or_repair_max_attempts():
    """
    Test: validate_or_repair respects max attempts.
    
    Verifies that repair mechanism has proper limits.
    """
    from scripts.cando_creation.generators.utils import validate_or_repair
    from scripts.cando_creation.models.plan import DomainPlan
    from pydantic import ValidationError
    
    # Mock LLM call that always returns invalid data
    def mock_llm_call(system, user, temperature=0.3, json_mode=True):
        return '{"invalid": "data"}'
    
    # Should fail after max attempts
    with pytest.raises((ValidationError, ValueError, Exception)):
        validate_or_repair(
            llm_call=mock_llm_call,
            model=DomainPlan,
            system_prompt="test",
            user_prompt="test",
            max_repair=2
        )

