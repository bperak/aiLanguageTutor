"""
Integration tests for LessonRoot compilation and guided dialogue.
"""
import pytest
import asyncio
from uuid import uuid4

# Requires Neo4j + Postgres schema + seeded data; skip by default.
pytestmark = [pytest.mark.asyncio, pytest.mark.integration]


async def test_compile_lessonroot_integration():
    """Test end-to-end LessonRoot compilation"""
    from app.db import init_db_connections, neo4j_driver, AsyncSessionLocal
    from app.services.cando_v2_compile_service import compile_lessonroot
    
    # Initialize connections
    await init_db_connections()
    
    # Use a known test CanDo
    test_can_do_id = "JF:21"
    
    async with neo4j_driver.session() as neo:
        async with AsyncSessionLocal() as pg:
            result = await compile_lessonroot(
                neo=neo,
                pg=pg,
                can_do_id=test_can_do_id,
                metalanguage="en",
                model="gpt-4o"
            )
            
            # Verify result structure
            assert result["status"] == "ok"
            assert "lesson_id" in result
            assert "version" in result
            assert result["can_do_id"] == test_can_do_id
            assert result["duration_sec"] > 0
            
            print(f"✓ Compiled lesson: {result['lesson_id']} v{result['version']}")


async def test_guided_dialogue_turn():
    """Test guided dialogue turn endpoint logic"""
    from app.db import init_db_connections, neo4j_driver, AsyncSessionLocal
    from sqlalchemy import text
    import json
    
    await init_db_connections()
    
    # This test requires an existing session with a compiled lesson
    # For now, we'll just verify the database schema is correct
    
    async with AsyncSessionLocal() as pg:
        result = await pg.execute(
            text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'lesson_sessions' 
                AND column_name IN ('guided_stage_idx', 'guided_state', 'guided_flushed_at')
            """)
        )
        
        columns = [row[0] for row in result.fetchall()]
        
        assert 'guided_stage_idx' in columns
        assert 'guided_state' in columns
        assert 'guided_flushed_at' in columns
        
        print("✓ Guided dialogue columns exist in lesson_sessions")


async def test_lesson_structure():
    """Test that compiled lessons have correct structure"""
    from app.db import init_db_connections, AsyncSessionLocal
    from sqlalchemy import text
    import json
    
    await init_db_connections()
    
    async with AsyncSessionLocal() as pg:
        # Fetch the most recent lesson
        result = await pg.execute(
            text("""
                SELECT lv.lesson_plan 
                FROM lesson_versions lv
                ORDER BY lv.id DESC
                LIMIT 1
            """)
        )
        
        row = result.fetchone()
        if not row:
            print("⚠ No lessons found in database, skipping structure test")
            return
            
        lesson_plan = row[0]
        if isinstance(lesson_plan, str):
            lesson_plan = json.loads(lesson_plan)
        
        # Verify structure
        assert "lesson" in lesson_plan
        lesson = lesson_plan["lesson"]
        
        assert "meta" in lesson
        assert "cards" in lesson
        
        cards = lesson["cards"]
        
        # Check all card types exist
        required_cards = [
            "objective",
            "words",
            "grammar_patterns",
            "lesson_dialogue",
            "reading_comprehension",
            "guided_dialogue",
            "exercises",
            "cultural_explanation",
            "drills_ai"
        ]
        
        for card_type in required_cards:
            assert card_type in cards, f"Missing card: {card_type}"
        
        # Verify guided_dialogue has stages
        guided = cards["guided_dialogue"]
        assert "stages" in guided
        assert len(guided["stages"]) > 0
        
        print(f"✓ Lesson structure valid with {len(guided['stages'])} guided stages")


if __name__ == "__main__":
    # Run tests manually
    print("Running LessonRoot Integration Tests...")
    print("=" * 60)
    
    try:
        asyncio.run(test_compile_lessonroot_integration())
    except Exception as e:
        print(f"✗ Compilation test failed: {e}")
    
    try:
        asyncio.run(test_guided_dialogue_turn())
    except Exception as e:
        print(f"✗ Guided dialogue schema test failed: {e}")
    
    try:
        asyncio.run(test_lesson_structure())
    except Exception as e:
        print(f"✗ Lesson structure test failed: {e}")
    
    print("=" * 60)
    print("Tests complete!")

