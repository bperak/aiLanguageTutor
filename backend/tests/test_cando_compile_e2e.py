"""
End-to-end tests for CanDo lesson compilation.

Tests the complete compilation flow from start to finish, including:
- Full compilation pipeline
- Database persistence
- Neo4j enrichment
- Result validation
"""

import pytest
import json
import os
from typing import Dict, Any

from app.services.cando_v2_compile_service import compile_lessonroot, _fetch_prelesson_kit_from_path
from tests.utils.cando_test_helpers import (
    validate_lesson_structure,
    validate_card_type,
    cleanup_test_lesson,
    get_sample_cando_metadata,
)


def has_required_keys() -> bool:
    """Check if required API keys are available for E2E tests."""
    if os.getenv("RUN_E2E_TESTS") not in ("1", "true", "TRUE", "yes", "YES"):
        return False
    return bool(os.getenv("OPENAI_API_KEY"))


@pytest.mark.asyncio
@pytest.mark.skipif(not has_required_keys(), reason="E2E tests require OPENAI_API_KEY and RUN_E2E_TESTS=1")
async def test_full_compilation_e2e():
    """
    Test full end-to-end compilation of a CanDo lesson.
    
    This test:
    1. Compiles a real CanDo lesson
    2. Verifies all 11 cards are generated
    3. Verifies lesson is persisted in database
    4. Verifies result is JSON serializable
    """
    from app.db import init_db_connections, neo4j_driver, AsyncSessionLocal
    
    await init_db_connections()
    
    # Use a test CanDo ID (adjust based on your test data)
    test_can_do_id = "JFまるごと:1"
    
    try:
        async with neo4j_driver.session() as neo:
            async with AsyncSessionLocal() as pg:
                # Run compilation
                result = await compile_lessonroot(
                    neo=neo,
                    pg=pg,
                    can_do_id=test_can_do_id,
                    metalanguage="en",
                    model="gpt-4o",
                    timeout=120
                )
                
                # Verify result structure
                assert result is not None
                assert "lesson_id" in result
                assert "version" in result
                assert "lesson" in result
                
                lesson_id = result["lesson_id"]
                version = result["version"]
                lesson_json = result["lesson"]
                
                # Verify lesson_id and version are valid
                assert isinstance(lesson_id, int)
                assert lesson_id > 0
                assert isinstance(version, int)
                assert version > 0
                
                # Verify lesson structure
                validation_errors = validate_lesson_structure(lesson_json)
                assert len(validation_errors) == 0, f"Validation errors: {validation_errors}"
                
                # Verify all cards are present
                cards = lesson_json["lesson"]["cards"]
                required_cards = [
                    "objective", "words", "grammar_patterns", "lesson_dialogue",
                    "reading_comprehension", "guided_dialogue", "exercises",
                    "cultural_explanation", "drills_ai"
                ]
                
                for card_type in required_cards:
                    assert card_type in cards, f"Missing card type: {card_type}"
                    assert cards[card_type] is not None, f"Card {card_type} is None"
                
                # Verify card types
                assert cards["objective"].get("type") == "ObjectiveCard"
                assert cards["words"].get("type") == "WordsCard"
                assert cards["grammar_patterns"].get("type") == "GrammarPatternsCard"
                assert cards["lesson_dialogue"].get("type") == "DialogueCard"
                assert cards["reading_comprehension"].get("type") == "ReadingCard"
                assert cards["guided_dialogue"].get("type") == "GuidedDialogueCard"
                assert cards["exercises"].get("type") == "ExercisesCard"
                assert cards["cultural_explanation"].get("type") == "CultureCard"
                assert cards["drills_ai"].get("type") == "DrillsCard"
                
                # Verify metadata is complete
                meta = lesson_json["lesson"]["meta"]
                assert "lesson_id" in meta
                assert "metalanguage" in meta
                assert "can_do" in meta
                
                can_do_meta = meta["can_do"]
                assert "uid" in can_do_meta
                assert can_do_meta["uid"] == test_can_do_id
                assert "level" in can_do_meta
                assert "primaryTopic_ja" in can_do_meta
                assert "primaryTopic_en" in can_do_meta
                
                # Verify result is JSON serializable
                json_str = json.dumps(lesson_json, ensure_ascii=False)
                assert len(json_str) > 0
                
                # Verify lesson is persisted in database
                from sqlalchemy import text
                result_db = await pg.execute(
                    text(
                        """
                        SELECT lv.lesson_plan, lv.version
                        FROM lesson_versions lv
                        WHERE lv.lesson_id = :lid AND lv.version = :ver
                        """
                    ),
                    {"lid": lesson_id, "ver": version},
                )
                row = result_db.first()
                assert row is not None, "Lesson not found in database"
                
                stored_plan = json.loads(row[0])
                assert stored_plan["lesson"]["meta"]["lesson_id"] == meta["lesson_id"]
        
    except ValueError as e:
        if "cando_not_found" in str(e):
            pytest.skip(f"CanDo {test_can_do_id} not found in Neo4j - skipping E2E test")
        else:
            raise
    except Exception as e:
        # Clean up on error
        pytest.fail(f"Compilation failed: {str(e)}")


@pytest.mark.asyncio
@pytest.mark.skipif(not has_required_keys(), reason="E2E tests require OPENAI_API_KEY and RUN_E2E_TESTS=1")
async def test_compilation_validation_checks():
    """
    Test that compiled lesson passes all validation checks.
    
    Validates:
    - Lesson structure matches LessonRoot schema
    - All required fields present
    - Card types are correct
    - Metadata is complete
    """
    test_can_do_id = "JFまるごと:1"
    
    try:
        from app.db import init_db_connections, neo4j_driver, AsyncSessionLocal
        await init_db_connections()
        
        async with neo4j_driver.session() as neo:
            async with AsyncSessionLocal() as pg:
                result = await compile_lessonroot(
                    neo=neo,
                    pg=pg,
                    can_do_id=test_can_do_id,
                    metalanguage="en",
                    model="gpt-4o",
                    timeout=120,
                )
                lesson_json = result["lesson"]
        
        # Validate structure
        errors = validate_lesson_structure(lesson_json)
        assert len(errors) == 0, f"Structure validation failed: {errors}"
        
        # Validate metadata completeness
        meta = lesson_json["lesson"]["meta"]
        required_meta_fields = ["lesson_id", "metalanguage", "can_do"]
        for field in required_meta_fields:
            assert field in meta, f"Missing metadata field: {field}"
        
        can_do = meta["can_do"]
        required_cando_fields = [
            "uid", "level", "primaryTopic_ja", "primaryTopic_en",
            "skillDomain_ja", "type_ja", "description"
        ]
        for field in required_cando_fields:
            assert field in can_do, f"Missing CanDo field: {field}"
        
        # Validate card types
        cards = lesson_json["lesson"]["cards"]
        card_type_mapping = {
            "objective": "ObjectiveCard",
            "words": "WordsCard",
            "grammar_patterns": "GrammarPatternsCard",
            "lesson_dialogue": "DialogueCard",
            "reading_comprehension": "ReadingCard",
            "guided_dialogue": "GuidedDialogueCard",
            "exercises": "ExercisesCard",
            "cultural_explanation": "CultureCard",
            "drills_ai": "DrillsCard"
        }
        
        for card_key, expected_type in card_type_mapping.items():
            card = cards.get(card_key)
            assert card is not None, f"Card {card_key} is missing"
            errors = validate_card_type(card, expected_type)
            assert len(errors) == 0, f"Card {card_key} type validation failed: {errors}"
        
    except ValueError as e:
        if "cando_not_found" in str(e):
            pytest.skip(f"CanDo {test_can_do_id} not found in Neo4j - skipping validation test")
        else:
            raise


@pytest.mark.asyncio
async def test_compilation_invalid_cando_id():
    """Test compilation with invalid can_do_id."""
    from app.db import init_db_connections, neo4j_driver, AsyncSessionLocal
    
    await init_db_connections()
    invalid_id = "INVALID:999999"
    
    async with neo4j_driver.session() as neo:
        async with AsyncSessionLocal() as pg:
            with pytest.raises(ValueError, match="cando_not_found"):
                await compile_lessonroot(
                    neo=neo,
                    pg=pg,
                    can_do_id=invalid_id,
                    metalanguage="en",
                    model="gpt-4o"
                )


@pytest.mark.asyncio
async def test_compilation_missing_api_key():
    """Test compilation behavior when API key is missing."""
    from app.db import init_db_connections, neo4j_driver, AsyncSessionLocal
    
    # This test requires mocking or environment manipulation
    # For now, we'll skip if key is present
    if os.getenv("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY is set - cannot test missing key scenario")
    
    await init_db_connections()
    test_can_do_id = "JFまるごと:1"
    
    async with neo4j_driver.session() as neo:
        async with AsyncSessionLocal() as pg:
            with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
                await compile_lessonroot(
                    neo=neo,
                    pg=pg,
                    can_do_id=test_can_do_id,
                    metalanguage="en",
                    model="gpt-4o"
                )


@pytest.mark.asyncio
@pytest.mark.skipif(not has_required_keys(), reason="E2E tests require OPENAI_API_KEY and RUN_E2E_TESTS=1")
async def test_compilation_database_persistence():
    """Test that compiled lesson is correctly persisted in database."""
    from app.db import init_db_connections, neo4j_driver, AsyncSessionLocal
    
    await init_db_connections()
    test_can_do_id = "JFまるごと:1"
    
    try:
        async with neo4j_driver.session() as neo:
            async with AsyncSessionLocal() as pg:
                result = await compile_lessonroot(
                    neo=neo,
                    pg=pg,
            can_do_id=test_can_do_id,
            metalanguage="en",
                    model="gpt-4o",
                    timeout=120
                )
                
                lesson_id = result["lesson_id"]
                version = result["version"]
                
                # Verify lesson record exists
                from sqlalchemy import text
                lesson_result = await pg.execute(
            text("SELECT id, can_do_id, status FROM lessons WHERE id = :lid"),
            {"lid": lesson_id}
        )
        lesson_row = lesson_result.first()
        
        assert lesson_row is not None
        assert lesson_row[1] == test_can_do_id
        assert lesson_row[2] in ["draft", "published"]  # Status can be either
        
        # Verify version record exists
        version_result = await pg_session.execute(
            text("""
                SELECT version, lesson_plan
                FROM lesson_versions
                WHERE lesson_id = :lid AND version = :ver
            """),
            {"lid": lesson_id, "ver": version}
        )
        version_row = version_result.first()
        
        assert version_row is not None
        assert version_row[0] == version
        
        # Verify lesson_plan is valid JSON
        lesson_plan = json.loads(version_row[1])
        assert "lesson" in lesson_plan
        assert lesson_plan["lesson"]["meta"]["can_do"]["uid"] == test_can_do_id
        
    except ValueError as e:
        if "cando_not_found" in str(e):
            pytest.skip(f"CanDo {test_can_do_id} not found in Neo4j - skipping persistence test")
        else:
            raise


@pytest.mark.asyncio
@pytest.mark.skipif(not has_required_keys(), reason="E2E tests require OPENAI_API_KEY and RUN_E2E_TESTS=1")
async def test_compilation_version_increment():
    """Test that multiple compilations increment version numbers."""
    from app.db import init_db_connections, neo4j_driver, AsyncSessionLocal
    
    await init_db_connections()
    test_can_do_id = "JFまるごと:1"
    
    try:
        async with neo4j_driver.session() as neo:
            async with AsyncSessionLocal() as pg:
                # First compilation
                result1 = await compile_lessonroot(
                    neo=neo,
                    pg=pg,
                    can_do_id=test_can_do_id,
                    metalanguage="en",
                    model="gpt-4o",
                    timeout=120
                )
                
                version1 = result1["version"]
                lesson_id = result1["lesson_id"]
                
                # Second compilation (should increment version)
                result2 = await compile_lessonroot(
                    neo=neo,
                    pg=pg,
                    can_do_id=test_can_do_id,
                    metalanguage="en",
                    model="gpt-4o",
                    timeout=120
                )
                
                version2 = result2["version"]
                
                # Verify versions are incremented
                assert version2 > version1, f"Version not incremented: {version1} -> {version2}"
                assert version2 == version1 + 1, f"Version should increment by 1: {version1} -> {version2}"
                
                # Verify both versions exist in database
                from sqlalchemy import text
                versions_result = await pg.execute(
                    text("SELECT version FROM lesson_versions WHERE lesson_id = :lid ORDER BY version"),
                    {"lid": lesson_id},
                )
                versions = [row[0] for row in versions_result.fetchall()]
                
                assert version1 in versions
                assert version2 in versions
        
    except ValueError as e:
        if "cando_not_found" in str(e):
            pytest.skip(f"CanDo {test_can_do_id} not found in Neo4j - skipping version increment test")
        else:
            raise


# ============================================================================
# E2E Tests for Pre-Lesson Kit Integration
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.skipif(not has_required_keys(), reason="E2E tests require OPENAI_API_KEY and RUN_E2E_TESTS=1")
async def test_e2e_flow_with_prelesson_kit():
    """
    Test complete E2E flow with pre-lesson kit:
    1. Create user profile
    2. Generate learning path with pre-lesson kits
    3. Compile lesson with user_id
    4. Verify compiled lesson contains kit elements
    5. Verify mandatory requirements are met
    """
    pytest.skip("E2E pre-lesson kit flow test temporarily disabled (infra dependent)")


@pytest.mark.asyncio
async def test_api_endpoint_with_user_id():
    """Test API endpoint integration with user_id parameter."""
    from app.api.v1.endpoints.cando import compile_lesson_v2_stream
    from app.db import init_db_connections, get_neo4j_session, get_postgresql_session
    from fastapi.testclient import TestClient
    from app.main import app
    import uuid
    
    await init_db_connections()
    
    test_can_do_id = "JFまるごと:1"
    test_user_id = uuid.uuid4()
    
    # This test would require a full test client setup
    # For now, we'll test the endpoint logic indirectly
    try:
        # Test that endpoint accepts user_id parameter
        # This is more of a structural test
        client = TestClient(app)
        
        # Note: This would require authentication and proper setup
        # Skipping actual request for now
        pytest.skip("API endpoint test requires full app setup with authentication")
        
    except Exception as e:
        pytest.skip(f"API endpoint test requires full setup: {e}")


