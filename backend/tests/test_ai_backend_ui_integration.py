"""
Integration test for AI → Backend → UI flow.

Tests the complete flow:
1. AI generates lesson content (comprehension exercises)
2. Backend API endpoint receives request and compiles lesson
3. Backend returns valid JSON structure
4. Response structure matches what frontend expects

NOTE: This test requires Docker containers to be running (Neo4j and PostgreSQL).
      If databases are not available, tests will be skipped gracefully.
      
To run:
    docker-compose up -d  # Start databases
    pytest tests/test_ai_backend_ui_integration.py -v
"""
import os
import sys
import time
import json
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

# Add backend to path
backend_path = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_path))

# Load .env file
from dotenv import load_dotenv
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

import pytest
from neo4j import AsyncSession
from sqlalchemy.ext.asyncio import AsyncSession as PgSession

from app.services.cando_v2_compile_service import compile_lessonroot, regenerate_lesson_stage
from app.db import get_neo4j_session, get_postgresql_session, init_neo4j, init_postgresql
from scripts.canDo_creation_new import LessonRoot, ComprehensionExercisesCard


def _validate_lesson_structure(lesson_data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Validate that lesson structure matches what frontend expects.
    
    Returns: (is_valid, error_message)
    """
    # Check top-level structure
    if "lesson" not in lesson_data:
        return False, "Missing 'lesson' key in response"
    
    lesson = lesson_data["lesson"]
    
    # compile_lessonroot returns: {"lesson_id": int, "version": int, "lesson": {...}}
    # The lesson object should have meta, cards, etc. (Lesson model structure)
    # But it might be nested as {"lesson": {"lesson": {...}}} or just {"lesson": {...}}
    # Let's check both possibilities
    
    # Unwrap if double-nested
    if "lesson" in lesson and isinstance(lesson["lesson"], dict):
        lesson = lesson["lesson"]
    
    # Check required top-level fields (Lesson model has meta, graph_bindings, ui_prefs, cards)
    if "meta" not in lesson:
        return False, f"Missing required field: meta. Available keys: {list(lesson.keys())[:10]}"
    
    if "cards" not in lesson:
        return False, f"Missing required field: cards. Available keys: {list(lesson.keys())[:10]}"
    
    # Check if we have stages structure (new format) or cards structure (old format)
    if "stages" in lesson:
        # New format with stages
        if not isinstance(lesson["stages"], list):
            return False, "stages must be a list"
    elif "cards" in lesson:
        # Old format with cards - this is also valid
        if not isinstance(lesson["cards"], dict):
            return False, "cards must be a dict"
    
    # Check if we have stages (new format) or cards (old format)
    if "stages" in lesson:
        # New format with stages
        if not isinstance(lesson["stages"], list):
            return False, "stages must be a list"
        
        # Check comprehension stage exists and has correct structure
        comprehension_stage = None
        for stage in lesson["stages"]:
            if stage.get("stage_id") == "comprehension":
                comprehension_stage = stage
                break
        
        if not comprehension_stage:
            return False, "Missing comprehension stage"
    elif "cards" in lesson:
        # Old format with cards - comprehension exercises are in cards
        comprehension_stage = {"comprehension_exercises": lesson["cards"].get("comprehension_exercises")}
    else:
        return False, "Lesson must have either 'stages' or 'cards' structure"
    
    # Check comprehension stage has required cards
    # Handle both new format (stages) and old format (cards)
    if "stages" in lesson:
        # New format with stages
        required_cards = ["comprehension_exercises", "ai_comprehension_tutor"]
        for card_name in required_cards:
            if card_name not in comprehension_stage:
                return False, f"Missing card in comprehension stage: {card_name}"
    else:
        # Old format with cards - check cards directly
        if "comprehension_exercises" not in lesson["cards"]:
            return False, "Missing card: comprehension_exercises"
        if "ai_comprehension_tutor" not in lesson["cards"]:
            return False, "Missing card: ai_comprehension_tutor"
        # Update comprehension_stage for validation below
        comprehension_stage = {
            "comprehension_exercises": lesson["cards"]["comprehension_exercises"],
            "ai_comprehension_tutor": lesson["cards"]["ai_comprehension_tutor"]
        }
    
    # Validate comprehension_exercises structure
    comp_exercises = comprehension_stage["comprehension_exercises"]
    if not isinstance(comp_exercises, dict):
        return False, "comprehension_exercises must be a dict"
    
    if comp_exercises.get("type") != "ComprehensionExercisesCard":
        return False, f"comprehension_exercises.type must be 'ComprehensionExercisesCard', got {comp_exercises.get('type')}"
    
    if "items" not in comp_exercises:
        return False, "comprehension_exercises must have 'items' field"
    
    if not isinstance(comp_exercises["items"], list):
        return False, "comprehension_exercises.items must be a list"
    
    if len(comp_exercises["items"]) == 0:
        return False, "comprehension_exercises.items must not be empty"
    
    # Validate first exercise item structure
    first_item = comp_exercises["items"][0]
    required_item_fields = ["id", "exercise_type", "instructions"]
    for field in required_item_fields:
        if field not in first_item:
            return False, f"Exercise item missing required field: {field}"
    
    # Validate JPText fields (question, answer, etc.)
    jptext_fields = ["question", "answer", "options", "text_passage"]
    for field in jptext_fields:
        if field in first_item:
            value = first_item[field]
            if isinstance(value, dict):
                # Check if it's a JPText structure
                if "std" in value and "translation" in value:
                    if not isinstance(value["translation"], dict):
                        return False, f"{field}.translation must be a dict"
                elif field == "options" and isinstance(value, list):
                    # Options is a list of JPText
                    for opt in value:
                        if isinstance(opt, dict) and "std" in opt:
                            if "translation" not in opt or not isinstance(opt["translation"], dict):
                                return False, f"{field}[].translation must be a dict"
    
    return True, None


@pytest.mark.asyncio
async def test_compile_lesson_comprehension_stage():
    """
    Test that backend can compile a lesson with comprehension stage.
    
    This tests the AI → Backend flow:
    1. Backend receives compilation request
    2. AI generates comprehension exercises
    3. Backend returns valid lesson structure
    """
    # Use a known CanDo ID - try to find one if the default doesn't exist
    can_do_id = "JF:1"  # Common CanDo ID format
    
    print(f"\n{'='*60}")
    print("Testing AI → Backend → UI Integration")
    print(f"{'='*60}")
    print(f"CanDo ID: {can_do_id}")
    print(f"Model: gpt-4.1")
    print()
    
    # Initialize databases first
    try:
        await init_neo4j()
        init_postgresql()  # Returns engine, not coroutine
    except Exception as e:
        pytest.skip(f"Could not initialize databases: {e}. Make sure Docker containers are running.")
    
    # Get database sessions - use context managers to ensure proper cleanup
    start_time = time.time()
    
    try:
        # Get Neo4j session
        neo_gen = get_neo4j_session()
        neo_session = await neo_gen.__anext__()
        
        # Get PostgreSQL session  
        pg_gen = get_postgresql_session()
        pg_session = await pg_gen.__anext__()
        
        try:
            # Compile lesson
            result = await compile_lessonroot(
                neo=neo_session,
                pg=pg_session,
                can_do_id=can_do_id,
                metalanguage="en",
                model="gpt-4.1",
            )
        finally:
            # Clean up sessions
            try:
                await neo_session.close()
            except Exception:
                pass
            try:
                await pg_session.close()
            except Exception:
                pass
        
        duration = time.time() - start_time
        
        print(f"\n✓ Compilation completed in {duration:.2f} seconds")
        print(f"  Lesson ID: {result.get('lesson_id', 'N/A')}")
        print(f"  Version: {result.get('version', 'N/A')}")
        
        # Validate response structure
        is_valid, error_msg = _validate_lesson_structure(result)
        
        if not is_valid:
            print(f"✗ Validation failed: {error_msg}")
            print(f"\nResponse structure (first 2000 chars):")
            print(json.dumps(result, indent=2, ensure_ascii=False)[:2000])
            pytest.fail(f"Lesson structure validation failed: {error_msg}")
        
        print(f"✓ Lesson structure is valid")
        
        # Check comprehension exercises count
        lesson = result["lesson"]
        # Unwrap if double-nested
        if "lesson" in lesson and isinstance(lesson["lesson"], dict):
            lesson = lesson["lesson"]
        
        # Get comprehension exercises based on format
        comp_exercises = None
        if "stages" in lesson:
            # New format with stages
            comprehension_stage = next(
                (s for s in lesson["stages"] if s.get("stage_id") == "comprehension"),
                None
            )
            if comprehension_stage:
                comp_exercises = comprehension_stage.get("comprehension_exercises")
        elif "cards" in lesson:
            # Old format with cards
            comp_exercises = lesson["cards"].get("comprehension_exercises")
        
        if comp_exercises:
            items = comp_exercises.get("items", [])
            print(f"✓ Comprehension exercises generated: {len(items)} items")
            if items:
                print(f"  Exercise types: {[item.get('exercise_type') for item in items[:5]]}")
        else:
            print("⚠ Warning: No comprehension exercises found in lesson")
        
        # Verify response can be serialized to JSON (frontend requirement)
        json_str = json.dumps(result, ensure_ascii=False)
        assert len(json_str) > 0, "Response must be serializable to JSON"
        print(f"✓ Response is JSON-serializable ({len(json_str)} bytes)")
        
        return result
        
    except ValueError as e:
        # CanDo not found - this is a valid test scenario
        if "not found" in str(e).lower() or "cando_not_found" in str(e).lower():
            pytest.skip(f"CanDo ID '{can_do_id}' not found in database. This is expected if the CanDo doesn't exist.")
        raise
    except Exception as e:
        duration = time.time() - start_time
        print(f"\n✗ Compilation failed after {duration:.2f} seconds")
        print(f"  Error: {e}")
        import traceback
        traceback.print_exc()
        raise


@pytest.mark.asyncio
async def test_regenerate_comprehension_stage():
    """
    Test regenerating comprehension stage only.
    
    This tests the regenerate-stage endpoint flow.
    """
    # First, compile a full lesson to get lesson_id and version
    can_do_id = "JF:1"  # Common CanDo ID format
    
    print(f"\n{'='*60}")
    print("Testing Regenerate Comprehension Stage")
    print(f"{'='*60}")
    
    # Initialize databases first
    try:
        await init_neo4j()
        init_postgresql()  # Returns engine, not coroutine
    except Exception as e:
        pytest.skip(f"Could not initialize databases: {e}. Make sure Docker containers are running.")
    
    # Get database sessions
    neo_session = None
    pg_session = None
    
    try:
        async for session in get_neo4j_session():
            neo_session = session
            break
    except Exception as e:
        pytest.skip(f"Could not connect to Neo4j: {e}. Make sure Docker containers are running.")
    
    try:
        async for session in get_postgresql_session():
            pg_session = session
            break
    except Exception as e:
        pytest.skip(f"Could not connect to PostgreSQL: {e}. Make sure Docker containers are running.")
    
    if not neo_session or not pg_session:
        pytest.skip("Could not get database sessions. Make sure Docker containers are running.")
    
    try:
        # Compile full lesson first
        result = await compile_lessonroot(
            neo=neo_session,
            pg=pg_session,
            can_do_id=can_do_id,
            metalanguage="en",
            model="gpt-4.1",
        )
        
        lesson_id = result.get("lesson_id")
        version = result.get("version")
        
        if not lesson_id or not version:
            pytest.skip("Could not get lesson_id and version from compilation")
        
        print(f"Lesson ID: {lesson_id}, Version: {version}")
        
        # Regenerate comprehension stage
        start_time = time.time()
        regenerate_result = await regenerate_lesson_stage(
            neo=neo_session,
            pg=pg_session,
            lesson_id=lesson_id,
            version=version,
            stage="comprehension",
            user_id=None,
        )
        
        duration = time.time() - start_time
        
        print(f"✓ Regeneration completed in {duration:.2f} seconds")
        print(f"  Status: {regenerate_result.get('status')}")
        print(f"  Stage: {regenerate_result.get('stage')}")
        
        assert regenerate_result.get("status") == "success"
        assert regenerate_result.get("stage") == "comprehension"
        
    except Exception as e:
        print(f"\n✗ Regeneration failed")
        print(f"  Error: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    # Run tests directly
    import asyncio
    
    async def run_tests():
        # Get sessions
        neo_session = None
        pg_session = None
        
        async for session in get_neo4j_session():
            neo_session = session
            break
        
        async for session in get_postgresql_session():
            pg_session = session
            break
        
        if not neo_session or not pg_session:
            print("✗ Could not get database sessions")
            return
        
        print("\n" + "="*60)
        print("Running AI → Backend → UI Integration Tests")
        print("="*60)
        
        # Test 1: Compile lesson
        try:
            result = await test_compile_lesson_comprehension_stage(neo_session, pg_session)
            print("\n✓ Test 1 passed: Compile lesson with comprehension stage")
        except Exception as e:
            print(f"\n✗ Test 1 failed: {e}")
            return
        
        # Test 2: Regenerate stage (optional, requires successful compilation)
        try:
            await test_regenerate_comprehension_stage(neo_session, pg_session)
            print("\n✓ Test 2 passed: Regenerate comprehension stage")
        except Exception as e:
            print(f"\n⚠ Test 2 skipped/failed: {e}")
        
        print("\n" + "="*60)
        print("All tests completed!")
        print("="*60)
    
    asyncio.run(run_tests())

