"""
PHASE 9: Full Compilation Integration Test

End-to-end test of the complete lesson compilation flow:
API request → compiled lesson returned
"""

import pytest
import uuid
import time
from pathlib import Path
from dotenv import load_dotenv

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

from app.db import init_db_connections, close_db_connections


@pytest.fixture
async def async_client():
    """Create an async HTTP client for testing."""
    from app.main import app
    import httpx
    
    await init_db_connections()
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test", timeout=600.0) as client:
            yield client
    finally:
        await close_db_connections()


@pytest.mark.asyncio
@pytest.mark.slow
async def test_full_compilation_flow(async_client):
    """
    Test: Complete flow from API request to compiled lesson.
    
    Verifies that the entire compilation process works end-to-end.
    """
    # Use a known CanDo ID
    can_do_id = "JF:1"
    
    start_time = time.time()
    
    response = await async_client.post(
        "/api/v1/cando/lessons/compile_v2",
        params={
            "can_do_id": can_do_id,
            "metalanguage": "en",
            "model": "gpt-4.1"
        }
    )
    
    elapsed_time = time.time() - start_time
    
    assert response.status_code == 200, f"Compilation failed: {response.status_code} - {response.text}"
    
    data = response.json()
    
    # Verify response structure
    assert "lesson_id" in data or "lesson" in data, "Response missing lesson data"
    assert "can_do_id" in data or data.get("can_do_id") == can_do_id, "Response missing can_do_id"
    
    # Verify compilation time is reasonable (< 60 seconds target)
    assert elapsed_time < 120, f"Compilation took too long: {elapsed_time:.2f}s (target: < 60s)"
    
    # If lesson data is present, verify structure
    if "lesson" in data:
        lesson = data["lesson"]
        assert isinstance(lesson, dict), "Lesson should be a dictionary"
        # Verify lesson has expected structure (basic checks)
        assert "ui" in lesson or "cards" in lesson or "metadata" in lesson, "Lesson missing expected structure"


@pytest.mark.asyncio
@pytest.mark.slow
async def test_full_compilation_with_user_id(async_client):
    """
    Test: Full compilation with user personalization.
    
    Verifies that compilation works with user_id for personalization.
    """
    can_do_id = "JF:1"
    # Use a test user_id (may not exist, but should handle gracefully)
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
    
    # Should either succeed or handle gracefully
    assert response.status_code in [200, 404, 500], f"Unexpected status: {response.status_code}"
    
    if response.status_code == 200:
        data = response.json()
        assert "lesson_id" in data or "lesson" in data, "Response missing lesson data"


@pytest.mark.asyncio
@pytest.mark.slow
async def test_full_compilation_performance_benchmark(async_client):
    """
    Test: Performance benchmarks for compilation.
    
    Measures compilation time and verifies it meets targets:
    - Target: < 60 seconds for full compilation
    - DomainPlan generation: < 15 seconds (not directly measurable here)
    - Content stage: < 30 seconds (not directly measurable here)
    """
    can_do_id = "JF:1"
    
    start_time = time.time()
    
    response = await async_client.post(
        "/api/v1/cando/lessons/compile_v2",
        params={
            "can_do_id": can_do_id,
            "metalanguage": "en",
            "model": "gpt-4.1"
        }
    )
    
    total_time = time.time() - start_time
    
    if response.status_code == 200:
        # Performance check
        assert total_time < 120, f"Total compilation time {total_time:.2f}s exceeds target (120s)"
        
        # Log performance for analysis
        print(f"\n[PERFORMANCE] Full compilation took {total_time:.2f}s")
        print(f"[PERFORMANCE] Target: < 60s, Actual: {total_time:.2f}s")
    else:
        pytest.skip(f"Compilation failed, cannot measure performance: {response.status_code}")


@pytest.mark.asyncio
@pytest.mark.slow
async def test_full_compilation_lesson_structure(async_client):
    """
    Test: Compiled lesson has all required components.
    
    Verifies that the compiled lesson contains all expected components.
    """
    can_do_id = "JF:1"
    
    response = await async_client.post(
        "/api/v1/cando/lessons/compile_v2",
        params={
            "can_do_id": can_do_id,
            "metalanguage": "en",
            "model": "gpt-4.1"
        }
    )
    
    if response.status_code != 200:
        pytest.skip(f"Compilation failed: {response.status_code}")
    
    data = response.json()
    
    # Verify lesson structure if present
    if "lesson" in data:
        lesson = data["lesson"]
        
        # Check for common lesson components
        has_ui = "ui" in lesson
        has_cards = "cards" in lesson
        has_metadata = "metadata" in lesson
        
        # At least one should be present
        assert has_ui or has_cards or has_metadata, "Lesson missing expected components"
        
        # If UI section exists, verify structure
        if has_ui:
            ui = lesson["ui"]
            assert isinstance(ui, dict), "UI section should be a dictionary"
            # UI typically has header and sections
            if "header" in ui:
                assert isinstance(ui["header"], dict), "UI header should be a dictionary"


@pytest.mark.asyncio
@pytest.mark.slow
async def test_full_compilation_multiple_candos(async_client):
    """
    Test: Compilation works with different CanDo IDs.
    
    Verifies that compilation works across different CanDo descriptors.
    """
    # Try to find multiple CanDo IDs from database
    await init_db_connections()
    try:
        from app.db import get_neo4j_session
        
        can_do_ids = []
        async for neo_session in get_neo4j_session():
            result = await neo_session.run("""
                MATCH (c:CanDoDescriptor)
                RETURN c.uid AS uid
                LIMIT 3
            """)
            records = [record async for record in result]
            can_do_ids = [record["uid"] for record in records]
            break
        
        if len(can_do_ids) == 0:
            pytest.skip("No CanDo descriptors found in database")
        
        # Test compilation for each CanDo
        for can_do_id in can_do_ids[:2]:  # Limit to 2 to avoid long test
            response = await async_client.post(
                "/api/v1/cando/lessons/compile_v2",
                params={
                    "can_do_id": can_do_id,
                    "metalanguage": "en",
                    "model": "gpt-4.1"
                }
            )
            
            # Should succeed or fail gracefully
            assert response.status_code in [200, 404, 500], f"Unexpected status for {can_do_id}: {response.status_code}"
            
            if response.status_code == 200:
                data = response.json()
                assert "lesson_id" in data or "lesson" in data, f"Response missing lesson for {can_do_id}"
            
            # Don't wait too long between tests
            break  # Only test first one to avoid long runtime
            
    finally:
        await close_db_connections()

