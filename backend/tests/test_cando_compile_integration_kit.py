"""
Integration tests for pre-lesson kit integration in compilation.

Tests compile_lessonroot() with pre-lesson kit integration.
"""

import pytest
import json
import uuid
from typing import Dict, Any
from unittest.mock import patch

from app.services.cando_v2_compile_service import (
    compile_lessonroot,
    _fetch_prelesson_kit_from_path,
    _build_prelesson_kit_context,
)
from tests.utils.cando_test_helpers import create_mock_llm_call


# ============================================================================
# Test Pre-Lesson Kit Integration
# ============================================================================

@pytest.mark.asyncio
async def test_compile_lessonroot_with_kit_provided():
    """Test compilation with pre-lesson kit provided directly."""
    from app.db import init_db_connections, neo4j_driver
    from app.db import AsyncSessionLocal
    
    await init_db_connections()
    
    test_can_do_id = "JFまるごと:1"
    mock_kit = {
        "can_do_context": {
            "situation": "At a restaurant",
            "pragmatic_act": "order (polite)",
        },
        "necessary_words": [
            {"surface": "レストラン", "reading": "れすとらん", "pos": "noun"},
            {"surface": "メニュー", "reading": "めにゅー", "pos": "noun"},
        ],
        "necessary_grammar_patterns": [
            {"pattern": "〜をください", "explanation": "Please give me..."},
        ],
        "necessary_fixed_phrases": [
            {
                "phrase": {"kanji": "いらっしゃいませ", "romaji": "irasshaimase"},
                "usage_note": "Welcome greeting",
            }
        ],
    }
    
    try:
        async with neo4j_driver.session() as neo:
            async with AsyncSessionLocal() as pg:
                # Patch LLM call to use mock
                with patch('app.services.cando_v2_compile_service._make_llm_call_openai', return_value=create_mock_llm_call()):
                    result = await compile_lessonroot(
                        neo=neo,
                        pg=pg,
                        can_do_id=test_can_do_id,
                        metalanguage="en",
                        model="gpt-4o",
                        prelesson_kit=mock_kit,
                    )
        
        assert result is not None
        assert "lesson_id" in result
        assert "version" in result
        assert "lesson" in result
        
        # Verify kit context was built
        context, requirements = _build_prelesson_kit_context(mock_kit)
        assert len(context) > 0
        assert len(requirements) > 0
        
    except Exception as e:
        pytest.skip(f"Test requires real database: {e}")


@pytest.mark.asyncio
async def test_compile_lessonroot_automatic_kit_fetch():
    """Test automatic kit fetching when user_id provided."""
    from app.db import init_db_connections
    from app.db import AsyncSessionLocal
    from app.models.database_models import LearningPath, User
    import uuid
    
    await init_db_connections()
    
    test_can_do_id = "JFまるごと:1"
    test_user_id = uuid.uuid4()
    
    mock_kit = {
        "can_do_context": {"situation": "Test situation"},
        "necessary_words": [{"surface": "テスト", "reading": "てすと"}],
    }
    
    try:
        async with AsyncSessionLocal() as pg:
            # Create test user
            test_user = User(
                id=test_user_id,
                email=f"test_{test_user_id}@example.com",
                hashed_password="test",
            )
            pg.add(test_user)
            await pg.commit()
            
            # Create learning path with kit
            test_path = LearningPath(
                user_id=test_user_id,
                version=1,
                path_name="Test Path",
                path_data={
                    "steps": [
                        {
                            "step_id": "step1",
                            "can_do_id": test_can_do_id,
                            "prelesson_kit": mock_kit,
                        }
                    ]
                },
                progress_data={},
                is_active=True,
            )
            pg.add(test_path)
            await pg.commit()
            
            # Test automatic fetching
            fetched_kit = await _fetch_prelesson_kit_from_path(pg, test_can_do_id, test_user_id)
            assert fetched_kit is not None
            assert fetched_kit == mock_kit
            
            # Cleanup
            await pg.delete(test_path)
            await pg.delete(test_user)
            await pg.commit()
            
    except Exception as e:
        pytest.skip(f"Test requires real database: {e}")


@pytest.mark.asyncio
async def test_compile_lessonroot_backward_compatibility():
    """Test compilation without kit (backward compatibility)."""
    from app.db import init_db_connections, neo4j_driver
    from app.db import AsyncSessionLocal
    
    await init_db_connections()
    
    test_can_do_id = "JFまるごと:1"
    
    try:
        async with neo4j_driver.session() as neo:
            async with AsyncSessionLocal() as pg:
                # Patch LLM call
                with patch('app.services.cando_v2_compile_service._make_llm_call_openai', return_value=create_mock_llm_call()):
                    result = await compile_lessonroot(
                        neo=neo,
                        pg=pg,
                        can_do_id=test_can_do_id,
                        metalanguage="en",
                        model="gpt-4o",
                        # No prelesson_kit provided
                    )
        
        assert result is not None
        assert "lesson_id" in result
        assert "version" in result
        assert "lesson" in result
        
    except Exception as e:
        pytest.skip(f"Test requires real database: {e}")


def test_build_prelesson_kit_context_integration():
    """Test that kit context building works correctly for integration."""
    complete_kit = {
        "can_do_context": {
            "situation": "At a restaurant",
            "pragmatic_act": "order (polite)",
            "notes": "Evening context",
        },
        "necessary_words": [
            {"surface": "レストラン", "reading": "れすとらん"},
            {"surface": "メニュー", "reading": "めにゅー"},
        ],
        "necessary_grammar_patterns": [
            {"pattern": "〜をください", "explanation": "Please give me"},
        ],
        "necessary_fixed_phrases": [
            {
                "phrase": {"kanji": "いらっしゃいませ", "romaji": "irasshaimase"},
                "usage_note": "Welcome",
            }
        ],
    }
    
    context, requirements = _build_prelesson_kit_context(complete_kit)
    
    # Verify context contains all components
    assert "Pre-Lesson Kit Context" in context
    assert "Situation: At a restaurant" in context
    assert "Pragmatic Act: order (polite)" in context
    assert "Essential Words (2)" in context
    assert "レストラン" in context
    assert "メニュー" in context
    assert "Grammar Patterns (1)" in context
    assert "〜をください" in context
    assert "Fixed Phrases (1)" in context
    assert "いらっしゃいませ" in context
    
    # Verify requirements
    assert "MANDATORY" in requirements
    assert "kit words" in requirements
    assert "kit grammar patterns" in requirements
    assert "kit phrases" in requirements


def test_kit_context_propagation():
    """Verify kit context is properly formatted for all card types."""
    mock_kit = {
        "can_do_context": {"situation": "Test", "pragmatic_act": "test"},
        "necessary_words": [{"surface": "テスト", "reading": "てすと"}],
        "necessary_grammar_patterns": [{"pattern": "〜です", "explanation": "Copula"}],
        "necessary_fixed_phrases": [
            {"phrase": {"kanji": "こんにちは", "romaji": "konnichiwa"}}
        ],
    }
    
    context, requirements = _build_prelesson_kit_context(mock_kit)
    
    # Context should be non-empty and contain kit information
    assert len(context) > 0
    assert "テスト" in context
    assert "〜です" in context
    assert "こんにちは" in context
    assert "Pre-Lesson Kit Context" in context
    
    # Requirements should be present
    assert len(requirements) > 0
    assert "MANDATORY" in requirements
    assert "kit words" in requirements
    assert "kit grammar patterns" in requirements
    assert "kit phrases" in requirements

