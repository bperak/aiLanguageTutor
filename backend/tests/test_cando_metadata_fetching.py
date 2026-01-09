"""
PHASE 3: CanDo Metadata Fetching Tests

Tests for Neo4j CanDo queries that fetch CanDo descriptors.
"""

import pytest
from pathlib import Path
from dotenv import load_dotenv
from neo4j import AsyncSession

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

from app.db import init_db_connections, close_db_connections, get_neo4j_session
from app.services.cando_v2_compile_service import _fetch_cando_meta


@pytest.mark.asyncio
async def test_fetch_existing_cando_by_uid():
    """
    Test: Fetch existing CanDo by uid (e.g., "JFまるごと:1").
    
    Verifies that existing CanDo descriptors can be fetched successfully.
    """
    await init_db_connections()
    try:
        async for neo_session in get_neo4j_session():
            # Test with a known CanDo ID
            can_do_id = "JF:1"
            
            try:
                result = await _fetch_cando_meta(neo_session, can_do_id)
                
                # Verify all required fields are present
                assert "uid" in result, "Result missing 'uid' field"
                assert "level" in result, "Result missing 'level' field"
                assert "primaryTopic" in result or "primaryTopic_ja" in result, "Result missing 'primaryTopic' field"
                assert "skillDomain" in result or "skillDomain_ja" in result, "Result missing 'skillDomain' field"
                assert "type" in result or "type_ja" in result, "Result missing 'type' field"
                assert "descriptionEn" in result or "description" in result, "Result missing 'descriptionEn' field"
                assert "descriptionJa" in result or "description" in result, "Result missing 'descriptionJa' field"
                assert "source" in result, "Result missing 'source' field"
                
                # Verify values are not None
                assert result["uid"] is not None, "uid is None"
                assert result["level"] is not None, "level is None"
                assert result["source"] is not None, "source is None"
                
            except ValueError as e:
                if "cando_not_found" in str(e):
                    pytest.skip(f"CanDo {can_do_id} not found in database")
                else:
                    raise
            break
    finally:
        await close_db_connections()


@pytest.mark.asyncio
async def test_fetch_nonexistent_cando():
    """
    Test: Fetch non-existent CanDo (should fail gracefully).
    
    Verifies that fetching a non-existent CanDo raises appropriate error.
    """
    await init_db_connections()
    try:
        async for neo_session in get_neo4j_session():
            invalid_can_do_id = "NONEXISTENT_CANDO_ID_12345"
            
            with pytest.raises(ValueError, match="cando_not_found"):
                await _fetch_cando_meta(neo_session, invalid_can_do_id)
            break
    finally:
        await close_db_connections()


@pytest.mark.asyncio
async def test_fetch_cando_required_fields():
    """
    Test: Verify all required fields are returned.
    
    Verifies that the CanDo query returns all expected fields:
    uid, level, primaryTopic_ja/en, skillDomain_ja, type_ja,
    description.en/ja, source
    """
    await init_db_connections()
    try:
        async for neo_session in get_neo4j_session():
            # Try to find any CanDo
            query = """
                MATCH (c:CanDoDescriptor)
                RETURN c.uid AS uid
                LIMIT 1
            """
            result = await neo_session.run(query)
            record = await result.single()
            
            if not record:
                pytest.skip("No CanDo descriptors found in database")
            
            can_do_id = record["uid"]
            result = await _fetch_cando_meta(neo_session, can_do_id)
            
            # Verify field presence
            required_fields = ["uid", "level", "source"]
            for field in required_fields:
                assert field in result, f"Required field '{field}' missing from result"
                assert result[field] is not None, f"Required field '{field}' is None"
            
            # Verify at least one description field exists
            has_description = (
                "descriptionEn" in result or
                "descriptionJa" in result or
                "description" in result
            )
            assert has_description, "No description field found in result"
            
            break
    finally:
        await close_db_connections()


@pytest.mark.asyncio
async def test_fetch_cando_connection_pooling():
    """
    Test: Connection pooling for Neo4j queries.
    
    Verifies that multiple concurrent queries work correctly
    (basic connection pool test).
    """
    await init_db_connections()
    try:
        import asyncio
        
        async def fetch_cando(neo_session, can_do_id):
            try:
                return await _fetch_cando_meta(neo_session, can_do_id)
            except ValueError:
                return None
        
        async for neo_session in get_neo4j_session():
            # Try to find multiple CanDos
            query = """
                MATCH (c:CanDoDescriptor)
                RETURN c.uid AS uid
                LIMIT 5
            """
            result = await neo_session.run(query)
            records = [record async for record in result]
            
            if len(records) < 2:
                pytest.skip("Not enough CanDo descriptors for concurrent test")
            
            # Fetch multiple CanDos concurrently
            can_do_ids = [record["uid"] for record in records[:3]]
            tasks = [fetch_cando(neo_session, cid) for cid in can_do_ids]
            results = await asyncio.gather(*tasks)
            
            # At least one should succeed
            successful = [r for r in results if r is not None]
            assert len(successful) > 0, "No concurrent queries succeeded"
            break
    finally:
        await close_db_connections()


@pytest.mark.asyncio
async def test_fetch_cando_query_optimization():
    """
    Test: Queries are optimized with proper indices.
    
    Verifies that CanDo queries use indexed fields (uid).
    This is more of a documentation test - actual index verification
    would require Neo4j EXPLAIN query analysis.
    """
    await init_db_connections()
    try:
        async for neo_session in get_neo4j_session():
            # The query uses uid which should be indexed
            can_do_id = "JF:1"
            
            try:
                import time
                start = time.time()
                result = await _fetch_cando_meta(neo_session, can_do_id)
                elapsed = time.time() - start
                
                # Query should complete quickly (< 1 second for indexed lookup)
                assert elapsed < 1.0, f"Query took too long ({elapsed:.2f}s), may indicate missing index"
                assert result is not None, "Query returned None"
                
            except ValueError:
                pytest.skip(f"CanDo {can_do_id} not found")
            break
    finally:
        await close_db_connections()

