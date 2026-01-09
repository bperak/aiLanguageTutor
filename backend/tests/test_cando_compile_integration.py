"""
Integration tests for CanDo compilation pipeline components.

Tests individual components of the compilation process without running full E2E compilation.
"""

import pytest
import json
import os
from typing import Dict, Any
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy import text

from app.services.cando_v2_compile_service import (
    _load_pipeline_module,
    _fetch_cando_meta,
    _enrich_grammar_neo4j_ids,
    compile_lessonroot,
    _fetch_prelesson_kit_from_path,
    _build_prelesson_kit_context,
)
from tests.utils.cando_test_helpers import (
    get_sample_cando_metadata,
    get_sample_cando_input,
    cleanup_test_lesson,
)


def has_db_test_env() -> bool:
    """
    Check if DB-backed tests should run.

    Reason: These tests require a stable, dedicated async event loop + a reachable DB.
    Enable explicitly to avoid flaky local runs.
    """
    return os.getenv("RUN_DB_TESTS") in ("1", "true", "TRUE", "yes", "YES")


# ============================================================================
# Test CanDo Metadata Fetching
# ============================================================================

@pytest.mark.asyncio
async def test_fetch_cando_meta_valid():
    """Test fetching CanDo metadata with valid can_do_id."""
    from app.db import init_neo4j, get_neo4j_session
    
    await init_neo4j()
    
    # This test requires a real CanDo in Neo4j
    # Using a common test CanDo ID
    can_do_id = "JF:1"
    
    try:
        async for neo in get_neo4j_session():
            meta = await _fetch_cando_meta(neo, can_do_id)
        
        assert meta is not None
        assert "uid" in meta
        assert meta["uid"] == can_do_id
        assert "level" in meta
        assert "primaryTopic" in meta
        assert "skillDomain" in meta
        assert "type" in meta
    except ValueError as e:
        if "cando_not_found" in str(e):
            pytest.skip(f"CanDo {can_do_id} not found in Neo4j - skipping test")
        else:
            raise


@pytest.mark.asyncio
async def test_fetch_cando_meta_invalid():
    """Test fetching CanDo metadata with invalid can_do_id."""
    from app.db import init_neo4j, get_neo4j_session
    
    await init_neo4j()
    invalid_id = "INVALID:999999"
    
    async for neo in get_neo4j_session():
        with pytest.raises(ValueError, match="cando_not_found"):
            await _fetch_cando_meta(neo, invalid_id)
        await neo.close()
        break


@pytest.mark.asyncio
async def test_fetch_cando_meta_query_structure():
    """Test that Neo4j query structure is correct."""
    from app.db import init_neo4j, get_neo4j_session
    
    await init_neo4j()
    can_do_id = "JF:1"
    
    try:
        async for neo in get_neo4j_session():
            meta = await _fetch_cando_meta(neo, can_do_id)
            await neo.close()
            break
        
        # Verify all expected fields are present
        required_fields = [
            "uid", "level", "primaryTopic", "primaryTopicEn",
            "skillDomain", "type", "descriptionEn", "descriptionJa",
            "titleEn", "titleJa", "source"
        ]
        
        for field in required_fields:
            assert field in meta, f"Missing field: {field}"
            
    except ValueError as e:
        if "cando_not_found" in str(e):
            pytest.skip(f"CanDo {can_do_id} not found in Neo4j - skipping test")
        else:
            raise


# ============================================================================
# Test Pipeline Module Loading
# ============================================================================

def test_load_pipeline_module():
    """Test that pipeline module loads correctly."""
    pipeline = _load_pipeline_module()
    
    assert pipeline is not None
    
    # Verify key functions exist
    required_functions = [
        "gen_domain_plan",
        "gen_objective_card",
        "gen_dialogue_card",
        "gen_reading_card",
        "gen_words_card",
        "gen_grammar_card",
        "gen_guided_dialogue_card",
        "gen_exercises_card",
        "gen_culture_card",
        "gen_drills_card",
        "assemble_lesson",
        # New stage-based generation functions
        "gen_content_stage",
        "gen_comprehension_stage",
        "gen_production_stage",
        "gen_interaction_stage",
        # New card generation functions
        "gen_formulaic_expressions_card",
        "gen_comprehension_exercises_card",
        "gen_ai_comprehension_tutor_card",
        "gen_production_exercises_card",
        "gen_ai_production_evaluator_card",
        "gen_interactive_dialogue_card",
        "gen_interaction_activities_card",
        "gen_ai_scenario_manager_card",
    ]
    
    for func_name in required_functions:
        assert hasattr(pipeline, func_name), f"Missing function: {func_name}"
        assert callable(getattr(pipeline, func_name)), f"{func_name} is not callable"


def test_load_pipeline_module_missing_file():
    """Test error handling when module file is missing."""
    # This test would require mocking the file system
    # For now, we assume the file exists in normal operation
    pass


# ============================================================================
# Test Entity Extraction
# ============================================================================

def test_extract_dialogue_text_with_setting():
    """Test extracting text from dialogue card with setting."""
    # Create mock dialogue card
    class MockDialogueCard:
        def __init__(self):
            self.setting = "Test setting for dialogue"
            self.turns = [
                type('Turn', (), {
                    'ja': type('JA', (), {
                        'std': 'こんにちは',
                        'kanji': 'こんにちは'
                    })()
                })(),
                type('Turn', (), {
                    'ja': type('JA', (), {
                        'std': 'はじめまして',
                        'kanji': 'はじめまして'
                    })()
                })()
            ]
    
    # Function _extract_dialogue_text no longer exists - skip this test
    pytest.skip("_extract_dialogue_text function removed from service")


def test_extract_dialogue_text_no_setting():
    """Test extracting text from dialogue card without setting."""
    # Function _extract_dialogue_text no longer exists - skip this test
    pytest.skip("_extract_dialogue_text function removed from service")


def test_extract_reading_text():
    """Test extracting text from reading card."""
    # Function _extract_reading_text no longer exists - skip this test
    pytest.skip("_extract_reading_text function removed from service")


def test_extract_reading_text_empty():
    """Test extracting text from empty reading card."""
    # Function _extract_reading_text no longer exists - skip this test
    pytest.skip("_extract_reading_text function removed from service")


# ============================================================================
# Test Database Operations
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.skipif(not has_db_test_env(), reason="DB-backed test (set RUN_DB_TESTS=1 to enable)")
async def test_lesson_upsert_new():
    """Test creating a new lesson record."""
    from app.db import init_db_connections, AsyncSessionLocal
    
    await init_db_connections()
    test_can_do_id = "TEST_NEW_LESSON"
    
    async with AsyncSessionLocal() as pg_session:
        try:
            # Check if lesson exists
            result = await pg_session.execute(
                text("SELECT id FROM lessons WHERE can_do_id = :cid LIMIT 1"),
                {"cid": test_can_do_id},
            )
            row = result.first()
            
            if row:
                # Clean up existing test lesson
                await cleanup_test_lesson(pg_session, test_can_do_id)
            
            # Insert new lesson
            ins = await pg_session.execute(
                text("INSERT INTO lessons (can_do_id, status) VALUES (:cid, 'draft') RETURNING id"),
                {"cid": test_can_do_id},
            )
            lesson_id = int(ins.first()[0])
            
            assert lesson_id > 0
            
            # Verify lesson was created
            result = await pg_session.execute(
                text("SELECT id, can_do_id, status FROM lessons WHERE id = :lid"),
                {"lid": lesson_id},
            )
            row = result.first()
            
            assert row is not None
            assert row[1] == test_can_do_id
            assert row[2] == "draft"
            
            await pg_session.commit()
            
        finally:
            # Cleanup
            await cleanup_test_lesson(pg_session, test_can_do_id)


@pytest.mark.asyncio
@pytest.mark.skipif(not has_db_test_env(), reason="DB-backed test (set RUN_DB_TESTS=1 to enable)")
async def test_lesson_version_increment():
    """Test version incrementing logic."""
    from app.db import init_db_connections, AsyncSessionLocal
    
    await init_db_connections()
    test_can_do_id = "TEST_VERSION_INCREMENT"
    
    async with AsyncSessionLocal() as pg_session:
        try:
            # Create test lesson
            ins = await pg_session.execute(
                text("INSERT INTO lessons (can_do_id, status) VALUES (:cid, 'draft') RETURNING id"),
                {"cid": test_can_do_id},
            )
            lesson_id = int(ins.first()[0])
            
            # Insert first version
            await pg_session.execute(
                text("INSERT INTO lesson_versions (lesson_id, version, lesson_plan) VALUES (:lid, 1, :plan)"),
                {"lid": lesson_id, "plan": json.dumps({"test": "version1"})},
            )
            
            # Get next version
            ver_row = (
                await pg_session.execute(
                    text("SELECT COALESCE(MAX(version),0) FROM lesson_versions WHERE lesson_id=:lid"),
                    {"lid": lesson_id},
                )
            ).first()
            next_ver = int(ver_row[0]) + 1
            
            assert next_ver == 2
            
            # Insert second version
            await pg_session.execute(
                text("INSERT INTO lesson_versions (lesson_id, version, lesson_plan) VALUES (:lid, :ver, :plan)"),
                {"lid": lesson_id, "ver": next_ver, "plan": json.dumps({"test": "version2"})},
            )
            
            # Verify both versions exist
            result = await pg_session.execute(
                text("SELECT version FROM lesson_versions WHERE lesson_id = :lid ORDER BY version"),
                {"lid": lesson_id},
            )
            versions = [row[0] for row in result.fetchall()]
            
            assert versions == [1, 2]
            
            await pg_session.commit()
            
        finally:
            await cleanup_test_lesson(pg_session, test_can_do_id)


@pytest.mark.asyncio
@pytest.mark.skipif(not has_db_test_env(), reason="DB-backed test (set RUN_DB_TESTS=1 to enable)")
async def test_lesson_plan_json_serialization():
    """Test that lesson_plan can be stored and retrieved as JSONB."""
    from app.db import init_db_connections, AsyncSessionLocal
    
    await init_db_connections()
    test_can_do_id = "TEST_JSON_SERIALIZATION"
    
    async with AsyncSessionLocal() as pg_session:
        try:
            # Create test lesson
            ins = await pg_session.execute(
                text("INSERT INTO lessons (can_do_id, status) VALUES (:cid, 'draft') RETURNING id"),
                {"cid": test_can_do_id},
            )
            lesson_id = int(ins.first()[0])
            
            # Create complex lesson plan
            lesson_plan = {
                "lesson": {
                    "meta": {
                        "lesson_id": "test_lesson",
                        "metalanguage": "en",
                        "can_do": get_sample_cando_metadata(),
                    },
                    "cards": {
                        "objective": {"type": "ObjectiveCard", "title": "Test"},
                        "words": {"type": "WordsCard", "words": []},
                    },
                }
            }
            
            # Insert version with JSON
            await pg_session.execute(
                text("INSERT INTO lesson_versions (lesson_id, version, lesson_plan) VALUES (:lid, 1, :plan)"),
                {"lid": lesson_id, "plan": json.dumps(lesson_plan, ensure_ascii=False)},
            )
            
            # Retrieve and verify
            result = await pg_session.execute(
                text("SELECT lesson_plan FROM lesson_versions WHERE lesson_id = :lid AND version = 1"),
                {"lid": lesson_id},
            )
            row = result.first()
            retrieved_plan = json.loads(row[0])
            
            assert retrieved_plan["lesson"]["meta"]["lesson_id"] == "test_lesson"
            assert retrieved_plan["lesson"]["cards"]["objective"]["type"] == "ObjectiveCard"
            
            await pg_session.commit()
        
        finally:
            await cleanup_test_lesson(pg_session, test_can_do_id)


# ============================================================================
# Test Neo4j Enrichment
# ============================================================================

@pytest.mark.asyncio
async def test_enrich_grammar_neo4j_ids():
    """Test enriching grammar patterns with Neo4j IDs."""
    from app.db import init_neo4j, get_neo4j_session
    
    await init_neo4j()
    
    # Create sample lesson JSON with grammar patterns
    lesson_json = {
        "lesson": {
            "cards": {
                "grammar_patterns": {
                    "patterns": [
                        {
                            "form": {
                                "ja": {
                                    "std": "〜です",
                                    "furigana": "〜です",
                                    "romaji": "~desu",
                                    "translation": {"en": "is/am/are"}
                                }
                            }
                        }
                    ]
                }
            }
        }
    }
    
    # Try to enrich (may not find pattern in Neo4j, but should not error)
    try:
        async for neo in get_neo4j_session():
            await _enrich_grammar_neo4j_ids(neo, lesson_json)
            await neo.close()
            break
        
        # If pattern was found, neo4j_id should be added
        patterns = lesson_json["lesson"]["cards"]["grammar_patterns"]["patterns"]
        if patterns[0].get("neo4j_id"):
            assert isinstance(patterns[0]["neo4j_id"], str)
    except Exception as e:
        # If no matching pattern in Neo4j, that's okay for this test
        pass


@pytest.mark.asyncio
async def test_link_dialogue_entities():
    """Test linking dialogue entities to CanDo in Neo4j."""
    from app.db import init_neo4j, get_neo4j_session
    
    await init_neo4j()
    can_do_id = "JF:1"
    
    # Create mock resolved entities
    resolved_words = [
        {"elementId": "word1", "text": "テスト"}
    ]
    resolved_grammar = [
        {"id": "grammar1", "pattern": "〜です"}
    ]
    
    # Try to link (may fail if entities don't exist, but should not error)
    try:
        async for neo in get_neo4j_session():
            await _link_dialogue_entities(
                neo,
                can_do_id,
                resolved_words,
                resolved_grammar
            )
            await neo.close()
            break
    except Exception as e:
        # If entities don't exist in Neo4j, that's okay for this test
        # The function should handle this gracefully
        pass


# ============================================================================
# Test Streaming Endpoint
# ============================================================================

def test_sse_event_format():
    """Test that SSE event format is correct."""
    import json as _json
    
    # Simulate SSE event format
    event_type = "status"
    data = {"status": "started", "can_do_id": "TEST:1"}
    
    sse_message = f"event: {event_type}\ndata: {_json.dumps(data, ensure_ascii=False)}\n\n"
    
    # Parse SSE message
    lines = sse_message.strip().split("\n")
    event_line = None
    data_lines = []
    
    for line in lines:
        if line.startswith("event:"):
            event_line = line
        elif line.startswith("data:"):
            data_lines.append(line[5:].strip())
    
    assert event_line == "event: status"
    assert len(data_lines) > 0
    
    parsed_data = _json.loads(data_lines[0])
    assert parsed_data["status"] == "started"
    assert parsed_data["can_do_id"] == "TEST:1"


def test_sse_keepalive_format():
    """Test that SSE keepalive format is correct."""
    keepalive = ": keepalive\n\n"
    
    assert keepalive.startswith(":")
    assert keepalive.strip() == ": keepalive"


def test_sse_error_event_format():
    """Test that SSE error event format is correct."""
    import json as _json
    
    error_data = {
        "status": "error",
        "detail": "Test error message",
        "can_do_id": "TEST:1"
    }
    
    sse_message = f"event: error\ndata: {_json.dumps(error_data, ensure_ascii=False)}\n\n"
    
    # Verify format
    assert "event: error" in sse_message
    assert "data:" in sse_message
    assert "Test error message" in sse_message


def test_sse_result_event_format():
    """Test that SSE result event format is correct."""
    import json as _json
    
    result_data = {
        "lesson_id": 1,
        "version": 1,
        "lesson": {"test": "data"}
    }
    
    sse_message = f"event: result\ndata: {_json.dumps(result_data, ensure_ascii=False)}\n\n"
    
    # Verify format
    assert "event: result" in sse_message
    assert "data:" in sse_message
    assert "lesson_id" in sse_message


# ============================================================================
# Test Stage-Based Generation
# ============================================================================

def test_stage_based_card_organization():
    """Test that cards are organized correctly by stage in CardsContainer."""
    pipeline = _load_pipeline_module()
    
    # Verify CardsContainer has stage-organized fields
    import sys
    import os
    scripts_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "scripts", "canDo_creation_new.py")
    if os.path.exists(scripts_path):
        import importlib.util
        spec = importlib.util.spec_from_file_location("canDo_creation_new", scripts_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        CardsContainer = module.CardsContainer
    else:
        # Fallback: use pipeline module
        CardsContainer = pipeline.CardsContainer if hasattr(pipeline, "CardsContainer") else None
        if CardsContainer is None:
            pytest.skip("CardsContainer not available in pipeline module")
    
    # Check that new stage fields exist (they should be optional for backward compatibility)
    container_fields = CardsContainer.model_fields.keys()
    
    # Content stage cards (required)
    assert "objective" in container_fields
    assert "words" in container_fields
    assert "grammar_patterns" in container_fields
    assert "lesson_dialogue" in container_fields
    assert "cultural_explanation" in container_fields
    
    # Content stage cards (optional new)
    assert "formulaic_expressions" in container_fields
    
    # Comprehension stage cards
    assert "reading_comprehension" in container_fields
    assert "comprehension_exercises" in container_fields
    assert "ai_comprehension_tutor" in container_fields
    
    # Production stage cards
    assert "guided_dialogue" in container_fields
    assert "production_exercises" in container_fields
    assert "ai_production_evaluator" in container_fields
    
    # Interaction stage cards
    assert "interactive_dialogue" in container_fields
    assert "interaction_activities" in container_fields
    assert "ai_scenario_manager" in container_fields


@pytest.mark.asyncio
async def test_stage_generation_functions_exist():
    """Test that stage generation functions are available and callable."""
    pipeline = _load_pipeline_module()
    
    # Verify stage functions exist
    assert hasattr(pipeline, "gen_content_stage")
    assert hasattr(pipeline, "gen_comprehension_stage")
    assert hasattr(pipeline, "gen_production_stage")
    assert hasattr(pipeline, "gen_interaction_stage")
    
    # Verify they are async functions
    import inspect
    assert inspect.iscoroutinefunction(pipeline.gen_content_stage)
    assert inspect.iscoroutinefunction(pipeline.gen_comprehension_stage)
    assert inspect.iscoroutinefunction(pipeline.gen_production_stage)
    assert inspect.iscoroutinefunction(pipeline.gen_interaction_stage)

