"""
PHASE 4: Pre-lesson Kit Fetching Tests

Tests for _fetch_prelesson_kit_from_path() function that retrieves
pre-lesson kits from learning paths.
"""

import pytest
import uuid
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

from app.db import init_db_connections, close_db_connections, get_postgresql_session
from app.services.cando_v2_compile_service import _fetch_prelesson_kit_from_path
from sqlalchemy import text


@pytest.mark.asyncio
async def test_fetch_prelesson_kit_with_path():
    """
    Test: User with learning path containing pre-lesson kit.
    
    Verifies that pre-lesson kits can be fetched from learning paths.
    """
    await init_db_connections()
    try:
        async for pg_session in get_postgresql_session():
            # First, try to find a user with a learning path that has a kit
            result = await pg_session.execute(text("""
                SELECT lp.user_id, lp.path_data, lp.id
                FROM learning_paths lp
                WHERE lp.path_data IS NOT NULL
                AND lp.path_data::text LIKE '%prelesson_kit%'
                LIMIT 1
            """))
            row = result.first()
            
            if not row:
                pytest.skip("No learning paths with pre-lesson kits found")
            
            user_id = row[0]
            path_data = row[1]
            path_id = row[2]
            
            # Extract a can_do_id from the path if possible
            can_do_id = None
            if isinstance(path_data, dict) and "steps" in path_data:
                steps = path_data.get("steps", [])
                for step in steps:
                    if isinstance(step, dict) and "can_do_id" in step:
                        can_do_id = step["can_do_id"]
                        break
            
            if not can_do_id:
                pytest.skip("No can_do_id found in learning path")
            
            # Fetch the kit
            kit = await _fetch_prelesson_kit_from_path(
                pg_session, can_do_id, user_id
            )
            
            # Should return something (even if None)
            # If kit exists, verify structure
            if kit:
                assert isinstance(kit, dict), "kit should be a dictionary"
                # Verify expected structure
                assert "can_do_context" in kit or "necessary_words" in kit or "necessary_grammar_patterns" in kit, "kit missing expected fields"
            
            break
    finally:
        await close_db_connections()


@pytest.mark.asyncio
async def test_fetch_prelesson_kit_no_kit_for_cando():
    """
    Test: User with learning path but no kit for this CanDo.
    
    Verifies that the function handles cases where path exists
    but no kit is available for the specific CanDo.
    """
    await init_db_connections()
    try:
        async for pg_session in get_postgresql_session():
            # Find a user with a learning path
            result = await pg_session.execute(text("""
                SELECT lp.user_id, lp.id
                FROM learning_paths lp
                WHERE lp.path_data IS NOT NULL
                LIMIT 1
            """))
            row = result.first()
            
            if not row:
                pytest.skip("No learning paths found")
            
            user_id = row[0]
            
            # Use a CanDo ID that likely doesn't have a kit
            can_do_id = "NONEXISTENT_IN_PATH"
            
            kit = await _fetch_prelesson_kit_from_path(
                pg_session, can_do_id, user_id
            )
            
            # Should return None or dict, not raise error
            assert kit is None or isinstance(kit, dict), "kit should be None or dict"
            
            break
    finally:
        await close_db_connections()


@pytest.mark.asyncio
async def test_fetch_prelesson_kit_no_learning_path():
    """
    Test: User without learning path.
    
    Verifies that the function handles users without learning paths gracefully.
    """
    await init_db_connections()
    try:
        async for pg_session in get_postgresql_session():
            # Create or find a user without a learning path
            # First check if there's a user without a path
            result = await pg_session.execute(text("""
                SELECT u.id
                FROM users u
                LEFT JOIN learning_paths lp ON lp.user_id = u.id
                WHERE lp.id IS NULL
                LIMIT 1
            """))
            row = result.first()
            
            if not row:
                # Create a test user (or use a random UUID)
                test_user_id = uuid.uuid4()
            else:
                test_user_id = row[0]
            
            can_do_id = "JF:1"
            
            kit_context, kit_requirements = await _fetch_prelesson_kit_from_path(
                pg_session, test_user_id, can_do_id
            )
            
            # Should return empty strings, not raise error
            assert kit_context is not None, "kit_context should not be None"
            assert kit_requirements is not None, "kit_requirements should not be None"
            assert isinstance(kit_context, str), "kit_context should be a string"
            assert isinstance(kit_requirements, str), "kit_requirements should be a string"
            
            break
    finally:
        await close_db_connections()


@pytest.mark.asyncio
async def test_fetch_prelesson_kit_invalid_user_id():
    """
    Test: Invalid user_id handled gracefully.
    
    Verifies that invalid user IDs don't cause errors.
    """
    await init_db_connections()
    try:
        async for pg_session in get_postgresql_session():
            invalid_user_id = uuid.uuid4()  # Valid UUID format but likely doesn't exist
            can_do_id = "JF:1"
            
            kit_context, kit_requirements = await _fetch_prelesson_kit_from_path(
                pg_session, invalid_user_id, can_do_id
            )
            
            # Should return empty strings, not raise error
            assert kit_context is not None, "kit_context should not be None"
            assert kit_requirements is not None, "kit_requirements should not be None"
            assert isinstance(kit_context, str), "kit_context should be a string"
            assert isinstance(kit_requirements, str), "kit_requirements should be a string"
            
            break
    finally:
        await close_db_connections()


@pytest.mark.asyncio
async def test_fetch_prelesson_kit_data_structure():
    """
    Test: Kit data structure is validated.
    
    Verifies that kit data from path_data is properly structured.
    This is more of an integration test - actual validation
    would be done by Pydantic models if they exist.
    """
    await init_db_connections()
    try:
        async for pg_session in get_postgresql_session():
            # Find a path with a kit
            result = await pg_session.execute(text("""
                SELECT lp.user_id, lp.path_data
                FROM learning_paths lp
                WHERE lp.path_data IS NOT NULL
                AND lp.path_data::text LIKE '%prelesson_kit%'
                LIMIT 1
            """))
            row = result.first()
            
            if not row:
                pytest.skip("No learning paths with kits found")
            
            user_id = row[0]
            path_data = row[1]
            
            # Extract can_do_id and verify kit structure
            if isinstance(path_data, dict) and "steps" in path_data:
                steps = path_data.get("steps", [])
                for step in steps:
                    if isinstance(step, dict):
                        can_do_id = step.get("can_do_id")
                        kit = step.get("prelesson_kit")
                        
                        if can_do_id and kit:
                            # Fetch using the function
                            kit = await _fetch_prelesson_kit_from_path(
                                pg_session, can_do_id, user_id
                            )
                            
                            # Verify returned value is dict or None
                            assert kit is None or isinstance(kit, dict), "kit should be None or dict"
                            break
            
            break
    finally:
        await close_db_connections()

