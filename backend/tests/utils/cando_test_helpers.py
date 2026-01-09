"""
Test utilities and fixtures for CanDo compilation tests.

Provides mock LLM functions, test data fixtures, and database cleanup utilities.
"""

from typing import Any, Dict, List, Optional
import json
from pathlib import Path


# ============================================================================
# Mock LLM Function
# ============================================================================

def create_mock_llm_call(responses: Optional[Dict[str, str]] = None) -> callable:
    """
    Create a mock LLM call function that returns deterministic responses.
    
    Args:
        responses: Dictionary mapping card types to JSON responses.
                   If None, uses default responses.
    
    Returns:
        Function that matches the signature: (system: str, user: str) -> str
    """
    default_responses = {
        "domain_plan": json.dumps({
            "scenarios": [
                {
                    "label": "Test Scenario",
                    "description": "A test scenario for CanDo testing",
                    "roles": [{"label": "Person A", "description": "Test person"}]
                }
            ],
            "vocabulary": ["テスト", "練習"],
            "grammar_functions": [
                {"id": "g1", "pattern": "〜です", "description": "Test pattern"}
            ]
        }),
        "objective": json.dumps({
            "type": "ObjectiveCard",
            "title": {"std": "テスト目標", "furigana": "テストもくひょう", "romaji": "tesuto mokuhyou", "translation": {"en": "Test Objective"}},
            "goals": ["Goal 1", "Goal 2"]
        }),
        "dialogue": json.dumps({
            "type": "DialogueCard",
            "title": {"std": "テスト会話", "furigana": "テストかいわ", "romaji": "tesuto kaiwa", "translation": {"en": "Test Dialogue"}},
            "setting": "Test setting for dialogue",
            "characters": ["Person A", "Person B"],
            "turns": [
                {
                    "speaker": "Person A",
                    "ja": {
                        "std": "こんにちは",
                        "furigana": "こんにちは",
                        "romaji": "konnichiwa",
                        "translation": {"en": "Hello"}
                    }
                },
                {
                    "speaker": "Person B",
                    "ja": {
                        "std": "こんにちは",
                        "furigana": "こんにちは",
                        "romaji": "konnichiwa",
                        "translation": {"en": "Hello"}
                    }
                }
            ]
        }),
        "reading": json.dumps({
            "type": "ReadingCard",
            "title": {"std": "テスト読解", "furigana": "テストどっかい", "romaji": "tesuto dokkai", "translation": {"en": "Test Reading"}},
            "reading": {
                "std": "これはテストの読解文です。",
                "furigana": "これはテストのどっかいぶんです。",
                "romaji": "kore wa tesuto no dokkai bun desu.",
                "translation": {"en": "This is a test reading passage."}
            },
            "comprehension": [
                {"q": "Question 1", "a": "Answer 1"}
            ]
        }),
        "words": json.dumps({
            "type": "WordsCard",
            "title": {"std": "テスト単語", "furigana": "テストたんご", "romaji": "tesuto tango", "translation": {"en": "Test Words"}},
            "words": [
                {
                    "ja": {
                        "std": "テスト",
                        "furigana": "テスト",
                        "romaji": "tesuto",
                        "translation": {"en": "test"}
                    },
                    "pos": "noun"
                }
            ]
        }),
        "grammar": json.dumps({
            "type": "GrammarPatternsCard",
            "title": {"std": "テスト文法", "furigana": "テストぶんぽう", "romaji": "tesuto bunpou", "translation": {"en": "Test Grammar"}},
            "patterns": [
                {
                    "form": {
                        "ja": {
                            "std": "〜です",
                            "furigana": "〜です",
                            "romaji": "~desu",
                            "translation": {"en": "is/am/are"}
                        }
                    },
                    "explanation": "Test explanation",
                    "examples": [
                        {
                            "std": "これは本です",
                            "furigana": "これはほんです",
                            "romaji": "kore wa hon desu",
                            "translation": {"en": "This is a book"}
                        }
                    ]
                }
            ]
        }),
        "guided_dialogue": json.dumps({
            "type": "GuidedDialogueCard",
            "title": {"std": "テストガイド会話", "furigana": "テストガイドかいわ", "romaji": "tesuto gaido kaiwa", "translation": {"en": "Test Guided Dialogue"}},
            "stages": [
                {
                    "prompt": {"std": "テストプロンプト", "furigana": "テストプロンプト", "romaji": "tesuto puromputo", "translation": {"en": "Test prompt"}},
                    "expected": {"std": "テスト応答", "furigana": "テストおうとう", "romaji": "tesuto outou", "translation": {"en": "Test response"}}
                }
            ]
        }),
        "exercises": json.dumps({
            "type": "ExercisesCard",
            "title": {"std": "テスト練習", "furigana": "テストれんしゅう", "romaji": "tesuto renshuu", "translation": {"en": "Test Exercises"}},
            "exercises": [
                {
                    "question": {"std": "テスト問題", "furigana": "テストもんだい", "romaji": "tesuto mondai", "translation": {"en": "Test question"}},
                    "options": [
                        {"std": "選択肢1", "furigana": "せんたくし1", "romaji": "sentakushi 1", "translation": {"en": "Option 1"}},
                        {"std": "選択肢2", "furigana": "せんたくし2", "romaji": "sentakushi 2", "translation": {"en": "Option 2"}}
                    ],
                    "answer_en": "Option 1"
                }
            ]
        }),
        "culture": json.dumps({
            "type": "CultureCard",
            "title": {"std": "テスト文化", "furigana": "テストぶんか", "romaji": "tesuto bunka", "translation": {"en": "Test Culture"}},
            "content": {
                "std": "これはテストの文化説明です。",
                "furigana": "これはテストのぶんかせつめいです。",
                "romaji": "kore wa tesuto no bunka setsumei desu.",
                "translation": {"en": "This is a test culture explanation."}
            }
        }),
        "drills": json.dumps({
            "type": "DrillsCard",
            "title": {"std": "テストドリル", "furigana": "テストドリル", "romaji": "tesuto doriru", "translation": {"en": "Test Drills"}},
            "drills": [
                {
                    "instruction": {"std": "テスト指示", "furigana": "テストしじ", "romaji": "tesuto shiji", "translation": {"en": "Test instruction"}},
                    "items": [
                        {
                            "prompt": {"std": "テスト", "furigana": "テスト", "romaji": "tesuto", "translation": {"en": "test"}},
                            "response": {"std": "テスト", "furigana": "テスト", "romaji": "tesuto", "translation": {"en": "test"}}
                        }
                    ]
                }
            ]
        })
    }
    
    if responses:
        default_responses.update(responses)
    
    def mock_llm_call(system: str, user: str) -> str:
        """
        Mock LLM call function that returns deterministic responses based on user prompt.
        
        Detects card type from user prompt and returns appropriate mock response.
        """
        user_lower = user.lower()
        
        # Detect card type from prompt
        if "domain plan" in user_lower or "plan" in user_lower:
            return default_responses["domain_plan"]
        elif "objective" in user_lower:
            return default_responses["objective"]
        elif "dialogue" in user_lower and "guided" not in user_lower:
            return default_responses["dialogue"]
        elif "reading" in user_lower:
            return default_responses["reading"]
        elif "word" in user_lower:
            return default_responses["words"]
        elif "grammar" in user_lower:
            return default_responses["grammar"]
        elif "guided" in user_lower:
            return default_responses["guided_dialogue"]
        elif "exercise" in user_lower:
            return default_responses["exercises"]
        elif "culture" in user_lower:
            return default_responses["culture"]
        elif "drill" in user_lower:
            return default_responses["drills"]
        else:
            # Default to domain plan if unclear
            return default_responses["domain_plan"]
    
    return mock_llm_call


# ============================================================================
# Test Data Fixtures
# ============================================================================

def get_sample_cando_metadata() -> Dict[str, Any]:
    """Return sample CanDo metadata for testing."""
    return {
        "uid": "JFまるごと:1",
        "level": "A1",
        "primaryTopic": "自己紹介",
        "primaryTopicEn": "Self Introduction",
        "skillDomain": "会話",
        "type": "表現",
        "descriptionEn": "Can introduce oneself",
        "descriptionJa": "自己紹介ができる",
        "titleEn": "Self Introduction",
        "titleJa": "自己紹介",
        "source": "JFまるごと"
    }


def get_sample_domain_plan() -> Dict[str, Any]:
    """Return sample domain plan for testing."""
    return {
        "scenarios": [
            {
                "label": "Meeting Someone New",
                "description": "Introducing yourself to someone for the first time",
                "roles": [
                    {"label": "Speaker", "description": "Person introducing themselves"},
                    {"label": "Listener", "description": "Person being introduced to"}
                ]
            }
        ],
        "vocabulary": ["こんにちは", "はじめまして", "よろしく"],
        "grammar_functions": [
            {
                "id": "g1",
                "pattern": "〜です",
                "description": "Copula for stating identity or characteristics"
            }
        ]
    }


def get_sample_cando_input() -> Dict[str, Any]:
    """Return sample CanDo input structure for testing."""
    meta = get_sample_cando_metadata()
    return {
        "uid": meta["uid"],
        "level": meta["level"],
        "primaryTopic": meta["primaryTopic"],
        "primaryTopicEn": meta["primaryTopicEn"],
        "skillDomain": meta["skillDomain"],
        "type": meta["type"],
        "descriptionEn": meta["descriptionEn"],
        "descriptionJa": meta["descriptionJa"],
        "titleEn": meta["titleEn"],
        "titleJa": meta["titleJa"],
        "source": meta["source"]
    }


# ============================================================================
# Database Cleanup Utilities
# ============================================================================

async def cleanup_test_lesson(
    pg_session,
    can_do_id: str,
    test_prefix: str = "TEST_"
) -> None:
    """
    Clean up test lessons from database.
    
    Args:
        pg_session: PostgreSQL async session
        can_do_id: CanDo ID to clean up (only if it starts with test_prefix)
        test_prefix: Prefix to identify test lessons (default: "TEST_")
    """
    from sqlalchemy import text
    
    if not can_do_id.startswith(test_prefix):
        # Safety check: don't delete non-test lessons
        return
    
    try:
        # Find lesson ID
        result = await pg_session.execute(
            text("SELECT id FROM lessons WHERE can_do_id = :cid LIMIT 1"),
            {"cid": can_do_id}
        )
        row = result.first()
        if row:
            lesson_id = int(row[0])
            # Delete versions first (foreign key constraint)
            await pg_session.execute(
                text("DELETE FROM lesson_versions WHERE lesson_id = :lid"),
                {"lid": lesson_id}
            )
            # Delete lesson
            await pg_session.execute(
                text("DELETE FROM lessons WHERE id = :lid"),
                {"lid": lesson_id}
            )
            await pg_session.commit()
    except Exception as e:
        # Log but don't fail on cleanup errors
        print(f"Warning: Failed to cleanup test lesson {can_do_id}: {e}")
        await pg_session.rollback()


async def cleanup_all_test_lessons(
    pg_session,
    test_prefix: str = "TEST_"
) -> None:
    """
    Clean up all test lessons from database.
    
    Args:
        pg_session: PostgreSQL async session
        test_prefix: Prefix to identify test lessons (default: "TEST_")
    """
    from sqlalchemy import text
    
    try:
        # Find all test lesson IDs
        result = await pg_session.execute(
            text("SELECT id FROM lessons WHERE can_do_id LIKE :prefix || '%'"),
            {"prefix": test_prefix}
        )
        lesson_ids = [int(row[0]) for row in result.fetchall()]
        
        if lesson_ids:
            # Delete versions first
            await pg_session.execute(
                text("DELETE FROM lesson_versions WHERE lesson_id = ANY(:ids)"),
                {"ids": lesson_ids}
            )
            # Delete lessons
            await pg_session.execute(
                text("DELETE FROM lessons WHERE id = ANY(:ids)"),
                {"ids": lesson_ids}
            )
            await pg_session.commit()
    except Exception as e:
        print(f"Warning: Failed to cleanup test lessons: {e}")
        await pg_session.rollback()


# ============================================================================
# Validation Helpers
# ============================================================================

def validate_lesson_structure(lesson_json: Dict[str, Any]) -> List[str]:
    """
    Validate lesson structure and return list of validation errors.
    
    Args:
        lesson_json: Lesson JSON to validate
    
    Returns:
        List of error messages (empty if valid)
    """
    errors = []
    
    # Check top-level structure
    if "lesson" not in lesson_json:
        errors.append("Missing 'lesson' key in root")
        return errors
    
    lesson = lesson_json["lesson"]
    
    # Check metadata
    if "meta" not in lesson:
        errors.append("Missing 'meta' in lesson")
    else:
        meta = lesson["meta"]
        required_meta_fields = ["lesson_id", "metalanguage", "can_do"]
        for field in required_meta_fields:
            if field not in meta:
                errors.append(f"Missing '{field}' in meta")
    
    # Check cards
    if "cards" not in lesson:
        errors.append("Missing 'cards' in lesson")
    else:
        cards = lesson["cards"]
        required_cards = [
            "objective", "words", "grammar_patterns", "lesson_dialogue",
            "reading_comprehension", "guided_dialogue", "exercises",
            "cultural_explanation", "drills_ai"
        ]
        for card_type in required_cards:
            if card_type not in cards:
                errors.append(f"Missing card type '{card_type}' in cards")
    
    return errors


def validate_card_type(card: Dict[str, Any], expected_type: str) -> List[str]:
    """
    Validate that a card has the correct type.
    
    Args:
        card: Card dictionary
        expected_type: Expected card type (e.g., "DialogueCard")
    
    Returns:
        List of error messages (empty if valid)
    """
    errors = []
    
    if "type" not in card:
        errors.append(f"Card missing 'type' field")
    elif card["type"] != expected_type:
        errors.append(f"Card type mismatch: expected '{expected_type}', got '{card.get('type')}'")
    
    return errors

