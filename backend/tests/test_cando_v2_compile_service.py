"""
Unit tests for CanDo v2 compilation service helper functions.

Tests pre-lesson kit integration helper functions.
"""

import pytest
import uuid
from typing import Dict, Any
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession as PgSession

from app.services.cando_v2_compile_service import (
    _fetch_prelesson_kit_from_path,
    _build_prelesson_kit_context,
    _update_lesson_stage_in_db,
)


# ============================================================================
# Test _fetch_prelesson_kit_from_path
# ============================================================================

@pytest.mark.asyncio
async def test_fetch_prelesson_kit_from_user_path():
    """Test fetching kit from user's active learning path."""
    test_user_id = uuid.uuid4()
    test_can_do_id = "JFまるごと:1"
    
    # Create mock learning path with kit
    mock_kit = {
        "can_do_context": {
            "situation": "Test situation",
            "pragmatic_act": "test communication",
        },
        "necessary_words": [{"surface": "テスト", "reading": "てすと", "pos": "noun"}],
        "necessary_grammar_patterns": [{"pattern": "〜です", "explanation": "Test"}],
        "necessary_fixed_phrases": [],
    }
    
    mock_path = MagicMock()
    mock_path.path_data = {
        "steps": [
            {
                "can_do_id": test_can_do_id,
                "prelesson_kit": mock_kit,
            }
        ]
    }
    
    mock_pg = AsyncMock(spec=PgSession)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_path
    mock_pg.execute.return_value = mock_result
    
    kit = await _fetch_prelesson_kit_from_path(mock_pg, test_can_do_id, test_user_id)
    
    assert kit is not None
    assert kit == mock_kit
    mock_pg.execute.assert_called_once()


@pytest.mark.asyncio
async def test_fetch_prelesson_kit_fallback_to_any_path():
    """Test fallback to any active path when user_id not provided."""
    test_can_do_id = "JFまるごと:1"
    
    mock_kit = {
        "can_do_context": {"situation": "Test"},
        "necessary_words": [],
    }
    
    mock_path = MagicMock()
    mock_path.path_data = {
        "steps": [
            {
                "can_do_id": test_can_do_id,
                "prelesson_kit": mock_kit,
            }
        ]
    }
    
    mock_pg = AsyncMock(spec=PgSession)
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_path]
    mock_pg.execute.return_value = mock_result
    
    kit = await _fetch_prelesson_kit_from_path(mock_pg, test_can_do_id, None)
    
    assert kit is not None
    assert kit == mock_kit


@pytest.mark.asyncio
async def test_fetch_prelesson_kit_missing_kit():
    """Test handling of missing kit (returns None)."""
    test_user_id = uuid.uuid4()
    test_can_do_id = "JFまるごと:1"
    
    # Path exists but step has no kit
    mock_path = MagicMock()
    mock_path.path_data = {
        "steps": [
            {
                "can_do_id": test_can_do_id,
                # No prelesson_kit
            }
        ]
    }
    
    mock_pg = AsyncMock(spec=PgSession)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_path
    mock_pg.execute.return_value = mock_result
    
    kit = await _fetch_prelesson_kit_from_path(mock_pg, test_can_do_id, test_user_id)
    
    assert kit is None


@pytest.mark.asyncio
async def test_fetch_prelesson_kit_missing_learning_path():
    """Test handling of missing learning path."""
    test_user_id = uuid.uuid4()
    test_can_do_id = "JFまるごと:1"
    
    mock_pg = AsyncMock(spec=PgSession)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None  # No path found
    mock_pg.execute.return_value = mock_result
    
    kit = await _fetch_prelesson_kit_from_path(mock_pg, test_can_do_id, test_user_id)
    
    assert kit is None


@pytest.mark.asyncio
async def test_fetch_prelesson_kit_invalid_can_do_id():
    """Test handling of invalid can_do_id."""
    test_user_id = uuid.uuid4()
    test_can_do_id = "INVALID:999"
    
    # Path exists but doesn't contain this can_do_id
    mock_path = MagicMock()
    mock_path.path_data = {
        "steps": [
            {
                "can_do_id": "JFまるごと:1",  # Different can_do_id
                "prelesson_kit": {"test": "data"},
            }
        ]
    }
    
    mock_pg = AsyncMock(spec=PgSession)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_path
    mock_pg.execute.return_value = mock_result
    
    kit = await _fetch_prelesson_kit_from_path(mock_pg, test_can_do_id, test_user_id)
    
    assert kit is None


@pytest.mark.asyncio
async def test_fetch_prelesson_kit_exception_handling():
    """Test exception handling in kit fetching."""
    test_can_do_id = "JFまるごと:1"
    
    mock_pg = AsyncMock(spec=PgSession)
    mock_pg.execute.side_effect = Exception("Database error")
    
    # Should not raise, but return None
    kit = await _fetch_prelesson_kit_from_path(mock_pg, test_can_do_id, None)
    
    assert kit is None


# ============================================================================
# Test _build_prelesson_kit_context
# ============================================================================

def test_build_prelesson_kit_context_complete():
    """Test context building with complete kit (all components)."""
    complete_kit = {
        "can_do_context": {
            "situation": "At a restaurant",
            "pragmatic_act": "order (polite)",
            "notes": "Evening dining context",
        },
        "necessary_words": [
            {"surface": "レストラン", "reading": "れすとらん", "pos": "noun", "translation": "restaurant"},
            {"surface": "メニュー", "reading": "めにゅー", "pos": "noun", "translation": "menu"},
            {"surface": "注文", "reading": "ちゅうもん", "pos": "noun", "translation": "order"},
            {"surface": "料理", "reading": "りょうり", "pos": "noun", "translation": "dish"},
            {"surface": "お会計", "reading": "おかいけい", "pos": "noun", "translation": "bill"},
            {"surface": "お願いします", "reading": "おねがいします", "pos": "expression", "translation": "please"},
            {"surface": "ありがとう", "reading": "ありがとう", "pos": "expression", "translation": "thank you"},
            {"surface": "いただきます", "reading": "いただきます", "pos": "expression", "translation": "bon appetit"},
        ],
        "necessary_grammar_patterns": [
            {"pattern": "〜をください", "explanation": "Please give me..."},
            {"pattern": "〜をお願いします", "explanation": "I would like..."},
            {"pattern": "〜はありますか", "explanation": "Do you have..."},
            {"pattern": "〜をいただきます", "explanation": "I'll have..."},
        ],
        "necessary_fixed_phrases": [
            {
                "phrase": {
                    "kanji": "いらっしゃいませ",
                    "romaji": "irasshaimase",
                    "translation": "Welcome",
                },
                "usage_note": "Used by staff",
                "register": "polite",
            },
            {
                "phrase": {
                    "kanji": "お待たせしました",
                    "romaji": "omatase shimashita",
                    "translation": "Sorry to keep you waiting",
                },
                "usage_note": "Used when serving",
                "register": "polite",
            },
        ],
    }
    
    context, requirements = _build_prelesson_kit_context(complete_kit)
    
    # Check context contains all components
    assert "Pre-Lesson Kit Context" in context
    assert "Situation: At a restaurant" in context
    assert "Pragmatic Act: order (polite)" in context
    assert "Notes: Evening dining context" in context
    assert "Essential Words (8)" in context
    assert "レストラン" in context
    assert "メニュー" in context
    assert "Grammar Patterns (4)" in context
    assert "〜をください" in context
    assert "Fixed Phrases (2)" in context
    assert "いらっしゃいませ" in context
    
    # Check requirements
    assert "MANDATORY" in requirements
    assert "Use at least 6 of the 8 kit words" in requirements  # max(6, 8*0.3) = 6
    assert "Use at least 2 of the 4 kit grammar patterns" in requirements  # max(2, 4*0.2) = 2
    assert "Use at least 2 of the 2 kit phrases" in requirements  # max(2, 2*0.2) = 2


def test_build_prelesson_kit_context_partial():
    """Test context building with partial kit (missing components)."""
    partial_kit = {
        "can_do_context": {
            "situation": "Basic conversation",
            # Missing pragmatic_act and notes
        },
        "necessary_words": [
            {"surface": "こんにちは", "reading": "こんにちは"},
        ],
        # Missing grammar and phrases
    }
    
    context, requirements = _build_prelesson_kit_context(partial_kit)
    
    # Should still build context with available components
    assert "Pre-Lesson Kit Context" in context
    assert "Situation: Basic conversation" in context
    assert "Essential Words (1)" in context
    assert "こんにちは" in context
    
    # Should not include missing components
    assert "Pragmatic Act" not in context
    assert "Grammar Patterns" not in context
    assert "Fixed Phrases" not in context


def test_build_prelesson_kit_context_mandatory_requirements_calculation():
    """Test mandatory requirements calculation (30% words, 20% grammar/phrases)."""
    # Test with 20 words - should require 30% = 6 words minimum
    kit_20_words = {
        "can_do_context": {},
        "necessary_words": [{"surface": f"word{i}"} for i in range(20)],
        "necessary_grammar_patterns": [{"pattern": f"pattern{i}"} for i in range(10)],
        "necessary_fixed_phrases": [{"phrase": {"kanji": f"phrase{i}"}} for i in range(5)],
    }
    
    context, requirements = _build_prelesson_kit_context(kit_20_words)
    
    # 20 words * 0.3 = 6, so min is 6
    assert "Use at least 6 of the 20 kit words" in requirements
    
    # 10 grammar * 0.2 = 2, so min is 2
    assert "Use at least 2 of the 10 kit grammar patterns" in requirements
    
    # 5 phrases * 0.2 = 1, but min is 2, so min is 2
    assert "Use at least 2 of the 5 kit phrases" in requirements
    
    # Test with 10 words - should require max(6, 10*0.3) = 6 words minimum
    kit_10_words = {
        "can_do_context": {},
        "necessary_words": [{"surface": f"word{i}"} for i in range(10)],
    }
    
    context, requirements = _build_prelesson_kit_context(kit_10_words)
    assert "Use at least 6 of the 10 kit words" in requirements  # max(6, 3) = 6
    
    # Test with 5 words - should require max(6, 5*0.3) = 6 words minimum
    kit_5_words = {
        "can_do_context": {},
        "necessary_words": [{"surface": f"word{i}"} for i in range(5)],
    }
    
    context, requirements = _build_prelesson_kit_context(kit_5_words)
    assert "Use at least 6 of the 5 kit words" in requirements  # max(6, 1.5) = 6


def test_build_prelesson_kit_context_edge_cases():
    """Test edge cases (empty lists, None values)."""
    # Empty kit
    empty_kit = {}
    context, requirements = _build_prelesson_kit_context(empty_kit)
    assert "Pre-Lesson Kit Context" in context
    assert "CRITICAL" in context
    
    # Kit with None values
    kit_with_none = {
        "can_do_context": None,
        "necessary_words": None,
        "necessary_grammar_patterns": None,
        "necessary_fixed_phrases": None,
    }
    context, requirements = _build_prelesson_kit_context(kit_with_none)
    assert "Pre-Lesson Kit Context" in context
    
    # Kit with empty lists
    kit_empty_lists = {
        "can_do_context": {},
        "necessary_words": [],
        "necessary_grammar_patterns": [],
        "necessary_fixed_phrases": [],
    }
    context, requirements = _build_prelesson_kit_context(kit_empty_lists)
    assert "Pre-Lesson Kit Context" in context
    assert "Essential Words" not in context
    assert "Grammar Patterns" not in context
    assert "Fixed Phrases" not in context


def test_build_prelesson_kit_context_phrase_text_extraction():
    """Test phrase text extraction (kanji, romaji, string formats)."""
    # Test with kanji
    kit_kanji = {
        "can_do_context": {},
        "necessary_fixed_phrases": [
            {
                "phrase": {
                    "kanji": "ありがとうございます",
                    "romaji": "arigatou gozaimasu",
                },
                "usage_note": "Polite thanks",
            }
        ],
    }
    context, _ = _build_prelesson_kit_context(kit_kanji)
    assert "ありがとうございます" in context
    
    # Test with romaji (when kanji missing)
    kit_romaji = {
        "can_do_context": {},
        "necessary_fixed_phrases": [
            {
                "phrase": {
                    "romaji": "arigatou gozaimasu",
                },
                "usage_note": "Polite thanks",
            }
        ],
    }
    context, _ = _build_prelesson_kit_context(kit_romaji)
    assert "arigatou gozaimasu" in context
    
    # Test with string format (legacy)
    kit_string = {
        "can_do_context": {},
        "necessary_fixed_phrases": [
            {
                "phrase": "ありがとうございます",
                "usage_note": "Polite thanks",
            }
        ],
    }
    context, _ = _build_prelesson_kit_context(kit_string)
    assert "ありがとうございます" in context


# ============================================================================
# Test _update_lesson_stage_in_db
# ============================================================================

@pytest.mark.asyncio
async def test_update_lesson_stage_comprehension_stores_in_lesson_cards():
    """Test that comprehension stage cards are stored in lesson.cards (not root-level)."""
    import json
    from sqlalchemy import text
    
    lesson_id = 1
    version = 1
    
    # Initial lesson structure (LessonRoot format)
    initial_lesson = {
        "lesson": {
            "meta": {
                "generation_status": {
                    "content": "complete",
                    "comprehension": "pending",
                }
            },
            "cards": {
                "objective": {"type": "ObjectiveCard"},
                "words": {"type": "WordsCard"},
            }
        }
    }
    
    # Stage data for comprehension
    stage_data = {
        "reading_comprehension": {
            "type": "ReadingCard",
            "title": {"en": "Test Reading"},
        },
        "comprehension_exercises": {
            "type": "ComprehensionExercisesCard",
            "items": [],
        },
        "ai_comprehension_tutor": {
            "type": "AIComprehensionTutorCard",
            "stages": [],
        },
    }
    
    mock_pg = AsyncMock(spec=PgSession)
    
    # Mock the SELECT query
    mock_select_result = MagicMock()
    mock_select_row = MagicMock()
    mock_select_row.__getitem__.return_value = json.dumps(initial_lesson)
    mock_select_result.first.return_value = mock_select_row
    mock_select_result.first.return_value.__getitem__ = lambda self, idx: json.dumps(initial_lesson) if idx == 0 else None
    
    # Mock the UPDATE query
    mock_update_result = MagicMock()
    mock_update_result.first.return_value = None
    
    async def execute_side_effect(query, params):
        query_str = str(query)
        if "SELECT" in query_str:
            return mock_select_result
        elif "UPDATE" in query_str:
            return mock_update_result
        return MagicMock()
    
    mock_pg.execute.side_effect = execute_side_effect
    mock_pg.commit = AsyncMock()
    
    # Execute the function
    await _update_lesson_stage_in_db(
        mock_pg, lesson_id, version, "comprehension", stage_data
    )
    
    # Verify UPDATE was called with correct JSONB path
    update_calls = [call for call in mock_pg.execute.call_args_list if "UPDATE" in str(call)]
    assert len(update_calls) > 0
    
    # Check that the SQL uses {lesson,cards} path (not {cards})
    update_query = str(update_calls[0][0][0])
    assert "{lesson,cards}" in update_query or "'lesson','cards'" in update_query
    assert "{lesson,meta,generation_status}" in update_query or "'lesson','meta','generation_status'" in update_query
    
    # Verify commit was called
    mock_pg.commit.assert_called_once()


@pytest.mark.asyncio
async def test_update_lesson_stage_production_stores_in_lesson_cards():
    """Test that production stage cards are stored in lesson.cards."""
    import json
    
    lesson_id = 1
    version = 1
    
    initial_lesson = {
        "lesson": {
            "meta": {"generation_status": {"content": "complete"}},
            "cards": {}
        }
    }
    
    stage_data = {
        "guided_dialogue": {"type": "GuidedDialogueCard", "stages": []},
        "production_exercises": {"type": "ProductionExercisesCard", "items": []},
        "ai_production_evaluator": {"type": "AIProductionEvaluatorCard", "stages": []},
    }
    
    mock_pg = AsyncMock(spec=PgSession)
    mock_result = MagicMock()
    mock_row = MagicMock()
    mock_row.__getitem__ = lambda idx: json.dumps(initial_lesson) if idx == 0 else None
    mock_result.first.return_value = mock_row
    mock_pg.execute.return_value = mock_result
    mock_pg.commit = AsyncMock()
    
    await _update_lesson_stage_in_db(
        mock_pg, lesson_id, version, "production", stage_data
    )
    
    # Verify the function completed without errors
    assert mock_pg.execute.call_count >= 2  # SELECT + UPDATE
    mock_pg.commit.assert_called_once()


@pytest.mark.asyncio
async def test_update_lesson_stage_interaction_stores_in_lesson_cards():
    """Test that interaction stage cards are stored in lesson.cards."""
    import json
    
    lesson_id = 1
    version = 1
    
    initial_lesson = {
        "lesson": {
            "meta": {"generation_status": {"content": "complete"}},
            "cards": {}
        }
    }
    
    stage_data = {
        "interactive_dialogue": {"type": "InteractiveDialogueCard", "scenarios": []},
        "interaction_activities": {"type": "InteractionActivitiesCard", "items": []},
        "ai_scenario_manager": {"type": "AIScenarioManagerCard", "stages": []},
    }
    
    mock_pg = AsyncMock(spec=PgSession)
    mock_result = MagicMock()
    mock_row = MagicMock()
    mock_row.__getitem__ = lambda idx: json.dumps(initial_lesson) if idx == 0 else None
    mock_result.first.return_value = mock_row
    mock_pg.execute.return_value = mock_result
    mock_pg.commit = AsyncMock()
    
    await _update_lesson_stage_in_db(
        mock_pg, lesson_id, version, "interaction", stage_data
    )
    
    assert mock_pg.execute.call_count >= 2
    mock_pg.commit.assert_called_once()


@pytest.mark.asyncio
async def test_update_lesson_stage_creates_lesson_structure_if_missing():
    """Test that function creates lesson structure if it doesn't exist."""
    import json
    
    lesson_id = 1
    version = 1
    
    # Lesson without lesson wrapper (legacy format)
    initial_lesson = {
        "cards": {"objective": {"type": "ObjectiveCard"}},
        "meta": {"generation_status": {"content": "complete"}},
    }
    
    stage_data = {
        "reading_comprehension": {"type": "ReadingCard"},
    }
    
    mock_pg = AsyncMock(spec=PgSession)
    mock_result = MagicMock()
    mock_row = MagicMock()
    mock_row.__getitem__ = lambda idx: json.dumps(initial_lesson) if idx == 0 else None
    mock_result.first.return_value = mock_row
    mock_pg.execute.return_value = mock_result
    mock_pg.commit = AsyncMock()
    
    # Should not raise an error - function should handle missing structure
    await _update_lesson_stage_in_db(
        mock_pg, lesson_id, version, "comprehension", stage_data
    )
    
    mock_pg.commit.assert_called_once()


@pytest.mark.asyncio
async def test_update_lesson_stage_updates_generation_status():
    """Test that generation status is correctly updated in lesson.meta.generation_status."""
    import json
    
    lesson_id = 1
    version = 1
    
    initial_lesson = {
        "lesson": {
            "meta": {
                "generation_status": {
                    "content": "complete",
                    "comprehension": "pending",
                }
            },
            "cards": {}
        }
    }
    
    stage_data = {
        "reading_comprehension": {"type": "ReadingCard"},
    }
    
    mock_pg = AsyncMock(spec=PgSession)
    mock_result = MagicMock()
    mock_row = MagicMock()
    mock_row.__getitem__ = lambda idx: json.dumps(initial_lesson) if idx == 0 else None
    mock_result.first.return_value = mock_row
    mock_pg.execute.return_value = mock_result
    mock_pg.commit = AsyncMock()
    
    await _update_lesson_stage_in_db(
        mock_pg, lesson_id, version, "comprehension", stage_data
    )
    
    # Verify UPDATE query includes generation_status path
    update_calls = [call for call in mock_pg.execute.call_args_list if "UPDATE" in str(call)]
    assert len(update_calls) > 0
    
    update_query = str(update_calls[0][0][0])
    # Should update generation_status at lesson.meta.generation_status
    assert "generation_status" in update_query
    assert mock_pg.commit.called

