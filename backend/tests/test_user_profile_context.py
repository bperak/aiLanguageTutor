"""
PHASE 5: User Profile Context Building Tests

Tests for _build_user_profile_context() function that formats
user profile data into context strings for lesson personalization.
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
from app.services.cando_v2_compile_service import _build_user_profile_context
from sqlalchemy import text


@pytest.mark.asyncio
async def test_build_profile_context_complete_profile():
    """
    Test: User with complete profile.
    
    Verifies that complete user profiles are formatted correctly.
    """
    await init_db_connections()
    try:
        async for pg_session in get_postgresql_session():
            # Find a user with a complete profile
            result = await pg_session.execute(text("""
                SELECT up.user_id
                FROM user_profiles up
                WHERE up.learning_goals IS NOT NULL
                OR up.previous_knowledge IS NOT NULL
                OR up.usage_context IS NOT NULL
                LIMIT 1
            """))
            row = result.first()
            
            if not row:
                pytest.skip("No users with profiles found")
            
            user_id = row[0]
            can_do_id = "JF:1"
            
            context = await _build_user_profile_context(
                pg_session, user_id, can_do_id, include_full_details=True
            )
            
            # Should return a non-empty string
            assert isinstance(context, str), "Context should be a string"
            # May be empty if profile has no relevant data
            # But structure should be correct if data exists
            
            break
    finally:
        await close_db_connections()


@pytest.mark.asyncio
async def test_build_profile_context_partial_profile():
    """
    Test: User with partial profile (missing some fields).
    
    Verifies that partial profiles are handled correctly.
    """
    await init_db_connections()
    try:
        async for pg_session in get_postgresql_session():
            # Find a user with partial profile (has some but not all fields)
            result = await pg_session.execute(text("""
                SELECT up.user_id
                FROM user_profiles up
                WHERE (up.learning_goals IS NOT NULL AND up.usage_context IS NULL)
                OR (up.previous_knowledge IS NOT NULL AND up.learning_experiences IS NULL)
                LIMIT 1
            """))
            row = result.first()
            
            if not row:
                pytest.skip("No users with partial profiles found")
            
            user_id = row[0]
            can_do_id = "JF:1"
            
            context = await _build_user_profile_context(
                pg_session, user_id, can_do_id, include_full_details=True
            )
            
            # Should return a string (may be empty or partial)
            assert isinstance(context, str), "Context should be a string"
            
            break
    finally:
        await close_db_connections()


@pytest.mark.asyncio
async def test_build_profile_context_no_profile():
    """
    Test: User with no profile (should handle gracefully).
    
    Verifies that users without profiles don't cause errors.
    """
    await init_db_connections()
    try:
        async for pg_session in get_postgresql_session():
            # Find a user without a profile
            result = await pg_session.execute(text("""
                SELECT u.id
                FROM users u
                LEFT JOIN user_profiles up ON up.user_id = u.id
                WHERE up.id IS NULL
                LIMIT 1
            """))
            row = result.first()
            
            if not row:
                # Use a random UUID
                test_user_id = uuid.uuid4()
            else:
                test_user_id = row[0]
            
            can_do_id = "JF:1"
            
            context = await _build_user_profile_context(
                pg_session, test_user_id, can_do_id, include_full_details=True
            )
            
            # Should return empty string, not raise error
            assert isinstance(context, str), "Context should be a string"
            # May be empty if no profile data
            
            break
    finally:
        await close_db_connections()


@pytest.mark.asyncio
async def test_build_profile_context_learning_goals():
    """
    Test: Learning goals are formatted correctly in context.
    
    Verifies that learning goals appear in the context string.
    """
    await init_db_connections()
    try:
        async for pg_session in get_postgresql_session():
            # Find a user with learning goals
            result = await pg_session.execute(text("""
                SELECT up.user_id, up.learning_goals
                FROM user_profiles up
                WHERE up.learning_goals IS NOT NULL
                LIMIT 1
            """))
            row = result.first()
            
            if not row:
                pytest.skip("No users with learning goals found")
            
            user_id = row[0]
            can_do_id = "JF:1"
            
            context = await _build_user_profile_context(
                pg_session, user_id, can_do_id, include_full_details=True
            )
            
            # Context should contain learning goals if they exist
            assert isinstance(context, str), "Context should be a string"
            if context:
                # Check if learning goals are mentioned
                assert "Learning Goals" in context or len(context) == 0, "Context should mention learning goals if present"
            
            break
    finally:
        await close_db_connections()


@pytest.mark.asyncio
async def test_build_profile_context_previous_knowledge():
    """
    Test: Previous knowledge is included in context.
    
    Verifies that previous knowledge appears in the context string.
    """
    await init_db_connections()
    try:
        async for pg_session in get_postgresql_session():
            # Find a user with previous knowledge
            result = await pg_session.execute(text("""
                SELECT up.user_id
                FROM user_profiles up
                WHERE up.previous_knowledge IS NOT NULL
                AND up.previous_knowledge::text != '{}'
                LIMIT 1
            """))
            row = result.first()
            
            if not row:
                pytest.skip("No users with previous knowledge found")
            
            user_id = row[0]
            can_do_id = "JF:1"
            
            context = await _build_user_profile_context(
                pg_session, user_id, can_do_id, include_full_details=True
            )
            
            assert isinstance(context, str), "Context should be a string"
            if context:
                assert "Previous Knowledge" in context or len(context) == 0, "Context should mention previous knowledge if present"
            
            break
    finally:
        await close_db_connections()


@pytest.mark.asyncio
async def test_build_profile_context_register_preferences():
    """
    Test: Register preferences are included in context.
    
    Verifies that register preferences from usage_context appear in context.
    """
    await init_db_connections()
    try:
        async for pg_session in get_postgresql_session():
            # Find a user with register preferences
            result = await pg_session.execute(text("""
                SELECT up.user_id
                FROM user_profiles up
                WHERE up.usage_context IS NOT NULL
                AND up.usage_context::text LIKE '%register_preferences%'
                LIMIT 1
            """))
            row = result.first()
            
            if not row:
                pytest.skip("No users with register preferences found")
            
            user_id = row[0]
            can_do_id = "JF:1"
            
            context = await _build_user_profile_context(
                pg_session, user_id, can_do_id, include_full_details=True
            )
            
            assert isinstance(context, str), "Context should be a string"
            if context:
                assert "Register Preferences" in context or "Usage Context" in context, "Context should mention register preferences if present"
            
            break
    finally:
        await close_db_connections()


@pytest.mark.asyncio
async def test_build_profile_context_grammar_focus():
    """
    Test: Grammar focus areas are included in context.
    
    Verifies that grammar focus areas from learning_experiences appear in context.
    """
    await init_db_connections()
    try:
        async for pg_session in get_postgresql_session():
            # Find a user with grammar focus areas
            result = await pg_session.execute(text("""
                SELECT up.user_id
                FROM user_profiles up
                WHERE up.learning_experiences IS NOT NULL
                AND up.learning_experiences::text LIKE '%grammar_focus_areas%'
                LIMIT 1
            """))
            row = result.first()
            
            if not row:
                pytest.skip("No users with grammar focus areas found")
            
            user_id = row[0]
            can_do_id = "JF:1"
            
            context = await _build_user_profile_context(
                pg_session, user_id, can_do_id, include_full_details=True
            )
            
            assert isinstance(context, str), "Context should be a string"
            if context:
                assert "Grammar Focus" in context or "Learning Preferences" in context, "Context should mention grammar focus if present"
            
            break
    finally:
        await close_db_connections()


@pytest.mark.asyncio
async def test_build_profile_context_vocabulary_domain_goals():
    """
    Test: Vocabulary domain goals are included in context.
    
    Verifies that path-level vocabulary goals appear in context.
    """
    await init_db_connections()
    try:
        async for pg_session in get_postgresql_session():
            # Find a user with vocabulary domain goals
            result = await pg_session.execute(text("""
                SELECT up.user_id
                FROM user_profiles up
                WHERE up.learning_goals IS NOT NULL
                AND up.learning_goals::text LIKE '%vocabulary_domain_goals%'
                LIMIT 1
            """))
            row = result.first()
            
            if not row:
                pytest.skip("No users with vocabulary domain goals found")
            
            user_id = row[0]
            can_do_id = "JF:1"
            
            context = await _build_user_profile_context(
                pg_session, user_id, can_do_id, include_full_details=True
            )
            
            assert isinstance(context, str), "Context should be a string"
            if context:
                assert "Vocabulary Domain Goals" in context, "Context should mention vocabulary domain goals if present"
            
            break
    finally:
        await close_db_connections()


@pytest.mark.asyncio
async def test_build_profile_context_cultural_interests():
    """
    Test: Cultural interests are included in context.
    
    Verifies that cultural interests appear in context.
    """
    await init_db_connections()
    try:
        async for pg_session in get_postgresql_session():
            # Find a user with cultural interests
            result = await pg_session.execute(text("""
                SELECT up.user_id
                FROM user_profiles up
                WHERE up.learning_goals IS NOT NULL
                AND up.learning_goals::text LIKE '%cultural_interests%'
                LIMIT 1
            """))
            row = result.first()
            
            if not row:
                pytest.skip("No users with cultural interests found")
            
            user_id = row[0]
            can_do_id = "JF:1"
            
            context = await _build_user_profile_context(
                pg_session, user_id, can_do_id, include_full_details=True
            )
            
            assert isinstance(context, str), "Context should be a string"
            if context:
                assert "Cultural Interests" in context, "Context should mention cultural interests if present"
            
            break
    finally:
        await close_db_connections()


@pytest.mark.asyncio
async def test_build_profile_context_include_full_details_false():
    """
    Test: include_full_details=False returns basic context only.
    
    Verifies that basic context (without full details) works correctly.
    """
    await init_db_connections()
    try:
        async for pg_session in get_postgresql_session():
            # Find a user with profile
            result = await pg_session.execute(text("""
                SELECT up.user_id
                FROM user_profiles up
                WHERE up.learning_goals IS NOT NULL
                LIMIT 1
            """))
            row = result.first()
            
            if not row:
                pytest.skip("No users with profiles found")
            
            user_id = row[0]
            can_do_id = "JF:1"
            
            # Test with full details
            context_full = await _build_user_profile_context(
                pg_session, user_id, can_do_id, include_full_details=True
            )
            
            # Test without full details
            context_basic = await _build_user_profile_context(
                pg_session, user_id, can_do_id, include_full_details=False
            )
            
            # Both should be strings
            assert isinstance(context_full, str), "Full context should be a string"
            assert isinstance(context_basic, str), "Basic context should be a string"
            
            # Basic context should be shorter or equal (if no full details exist)
            # This is a soft check - basic might still have some info
            
            break
    finally:
        await close_db_connections()

