"""
Validation tests for pre-lesson kit usage in compiled lessons.

Tests that verify kit elements are actually used in generated content
and that mandatory requirements are met.
"""

import pytest
from typing import Dict, Any, List


# ============================================================================
# Kit Usage Validation Utilities
# ============================================================================

def extract_text_from_lesson(lesson_json: Dict[str, Any]) -> str:
    """Extract all Japanese text from a lesson for analysis."""
    text_parts = []
    
    cards = lesson_json.get("lesson", {}).get("cards", {})
    
    # Extract from dialogue
    dialogue = cards.get("lesson_dialogue", {})
    if dialogue:
        turns = dialogue.get("turns", [])
        for turn in turns:
            jp = turn.get("japanese", {})
            if isinstance(jp, dict):
                text_parts.append(jp.get("kanji", "") or jp.get("std", "") or jp.get("romaji", ""))
            elif isinstance(jp, str):
                text_parts.append(jp)
    
    # Extract from reading
    reading = cards.get("reading_comprehension", {})
    if reading:
        reading_content = reading.get("reading", {})
        if reading_content:
            content = reading_content.get("content", {})
            if isinstance(content, dict):
                text_parts.append(content.get("kanji", "") or content.get("std", "") or content.get("romaji", ""))
            elif isinstance(content, str):
                text_parts.append(content)
    
    # Extract from words
    words = cards.get("words", {})
    if words:
        items = words.get("items", [])
        for item in items:
            jp = item.get("jp", {})
            if isinstance(jp, dict):
                text_parts.append(jp.get("kanji", "") or jp.get("std", "") or jp.get("romaji", ""))
            elif isinstance(jp, str):
                text_parts.append(jp)
    
    # Extract from grammar examples
    grammar = cards.get("grammar_patterns", {})
    if grammar:
        patterns = grammar.get("patterns", [])
        for pattern in patterns:
            examples = pattern.get("examples", [])
            for example in examples:
                jp = example.get("jp", {})
                if isinstance(jp, dict):
                    text_parts.append(jp.get("kanji", "") or jp.get("std", "") or jp.get("romaji", ""))
                elif isinstance(jp, str):
                    text_parts.append(jp)
    
    return " ".join(text_parts)


def count_kit_word_usage(lesson_text: str, kit_words: List[Dict[str, Any]]) -> int:
    """Count how many kit words appear in lesson text."""
    used_count = 0
    word_surfaces = [w.get("surface", "") for w in kit_words if w.get("surface")]
    
    for word in word_surfaces:
        if word and word in lesson_text:
            used_count += 1
    
    return used_count


def count_kit_grammar_usage(lesson_text: str, kit_grammar: List[Dict[str, Any]]) -> int:
    """Count how many kit grammar patterns appear in lesson text."""
    used_count = 0
    grammar_patterns = [g.get("pattern", "") for g in kit_grammar if g.get("pattern")]
    
    for pattern in grammar_patterns:
        if pattern and pattern in lesson_text:
            used_count += 1
    
    return used_count


def count_kit_phrase_usage(lesson_text: str, kit_phrases: List[Dict[str, Any]]) -> int:
    """Count how many kit phrases appear in lesson text."""
    used_count = 0
    
    for phrase_data in kit_phrases:
        phrase_obj = phrase_data.get("phrase", {})
        if isinstance(phrase_obj, dict):
            phrase_text = phrase_obj.get("kanji", "") or phrase_obj.get("romaji", "")
        elif isinstance(phrase_obj, str):
            phrase_text = phrase_obj
        else:
            continue
        
        if phrase_text and phrase_text in lesson_text:
            used_count += 1
    
    return used_count


def validate_kit_usage_requirements(
    lesson_json: Dict[str, Any],
    kit: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Validate that kit usage requirements are met.
    
    Returns:
        Dictionary with validation results:
        - words_used: number of kit words found
        - words_required: minimum required
        - words_meets_requirement: bool
        - grammar_used: number of kit grammar patterns found
        - grammar_required: minimum required
        - grammar_meets_requirement: bool
        - phrases_used: number of kit phrases found
        - phrases_required: minimum required
        - phrases_meets_requirement: bool
        - all_requirements_met: bool
    """
    lesson_text = extract_text_from_lesson(lesson_json)
    
    kit_words = kit.get("necessary_words", [])
    kit_grammar = kit.get("necessary_grammar_patterns", [])
    kit_phrases = kit.get("necessary_fixed_phrases", [])
    
    # Calculate requirements
    min_words = max(6, int(len(kit_words) * 0.3)) if kit_words else 0
    min_grammar = max(2, int(len(kit_grammar) * 0.2)) if kit_grammar else 0
    min_phrases = max(2, int(len(kit_phrases) * 0.2)) if kit_phrases else 0
    
    # Count usage
    words_used = count_kit_word_usage(lesson_text, kit_words)
    grammar_used = count_kit_grammar_usage(lesson_text, kit_grammar)
    phrases_used = count_kit_phrase_usage(lesson_text, kit_phrases)
    
    # Check requirements
    words_meets = words_used >= min_words if min_words > 0 else True
    grammar_meets = grammar_used >= min_grammar if min_grammar > 0 else True
    phrases_meets = phrases_used >= min_phrases if min_phrases > 0 else True
    
    return {
        "words_used": words_used,
        "words_required": min_words,
        "words_total": len(kit_words),
        "words_meets_requirement": words_meets,
        "grammar_used": grammar_used,
        "grammar_required": min_grammar,
        "grammar_total": len(kit_grammar),
        "grammar_meets_requirement": grammar_meets,
        "phrases_used": phrases_used,
        "phrases_required": min_phrases,
        "phrases_total": len(kit_phrases),
        "phrases_meets_requirement": phrases_meets,
        "all_requirements_met": words_meets and grammar_meets and phrases_meets,
    }


# ============================================================================
# Validation Tests
# ============================================================================

def test_validate_minimum_word_usage():
    """Verify minimum word usage (30% or 6 words)."""
    # Test with 20 words - should require 6 words minimum
    kit_20_words = {
        "necessary_words": [{"surface": f"word{i}"} for i in range(20)],
        "necessary_grammar_patterns": [],
        "necessary_fixed_phrases": [],
    }
    
    # Mock lesson with 6 kit words
    lesson_with_6_words = {
        "lesson": {
            "cards": {
                "lesson_dialogue": {
                    "turns": [
                        {"japanese": {"kanji": "word0 word1 word2"}},
                        {"japanese": {"kanji": "word3 word4 word5"}},
                    ]
                }
            }
        }
    }
    
    result = validate_kit_usage_requirements(lesson_with_6_words, kit_20_words)
    assert result["words_used"] == 6
    assert result["words_required"] == 6  # max(6, 20*0.3) = 6
    assert result["words_meets_requirement"] is True
    
    # Test with lesson having only 5 words (should fail)
    lesson_with_5_words = {
        "lesson": {
            "cards": {
                "lesson_dialogue": {
                    "turns": [
                        {"japanese": {"kanji": "word0 word1 word2 word3 word4"}},
                    ]
                }
            }
        }
    }
    
    result = validate_kit_usage_requirements(lesson_with_5_words, kit_20_words)
    assert result["words_used"] == 5
    assert result["words_required"] == 6
    assert result["words_meets_requirement"] is False


def test_validate_minimum_grammar_usage():
    """Verify minimum grammar usage (20% or 2 patterns)."""
    # Test with 10 grammar patterns - should require 2 patterns minimum
    kit_10_grammar = {
        "necessary_words": [],
        "necessary_grammar_patterns": [{"pattern": f"pattern{i}"} for i in range(10)],
        "necessary_fixed_phrases": [],
    }
    
    # Mock lesson with 2 kit grammar patterns
    lesson_with_2_grammar = {
        "lesson": {
            "cards": {
                "grammar_patterns": {
                    "patterns": [
                        {"examples": [{"jp": {"kanji": "pattern0"}}]},
                        {"examples": [{"jp": {"kanji": "pattern1"}}]},
                    ]
                }
            }
        }
    }
    
    result = validate_kit_usage_requirements(lesson_with_2_grammar, kit_10_grammar)
    assert result["grammar_used"] == 2
    assert result["grammar_required"] == 2  # max(2, 10*0.2) = 2
    assert result["grammar_meets_requirement"] is True
    
    # Test with lesson having only 1 pattern (should fail)
    lesson_with_1_grammar = {
        "lesson": {
            "cards": {
                "grammar_patterns": {
                    "patterns": [
                        {"examples": [{"jp": {"kanji": "pattern0"}}]},
                    ]
                }
            }
        }
    }
    
    result = validate_kit_usage_requirements(lesson_with_1_grammar, kit_10_grammar)
    assert result["grammar_used"] == 1
    assert result["grammar_required"] == 2
    assert result["grammar_meets_requirement"] is False


def test_validate_minimum_phrase_usage():
    """Verify minimum phrase usage (20% or 2 phrases)."""
    # Test with 5 phrases - should require 2 phrases minimum
    kit_5_phrases = {
        "necessary_words": [],
        "necessary_grammar_patterns": [],
        "necessary_fixed_phrases": [
            {"phrase": {"kanji": f"phrase{i}"}} for i in range(5)
        ],
    }
    
    # Mock lesson with 2 kit phrases
    lesson_with_2_phrases = {
        "lesson": {
            "cards": {
                "lesson_dialogue": {
                    "turns": [
                        {"japanese": {"kanji": "phrase0 phrase1"}},
                    ]
                }
            }
        }
    }
    
    result = validate_kit_usage_requirements(lesson_with_2_phrases, kit_5_phrases)
    assert result["phrases_used"] == 2
    assert result["phrases_required"] == 2  # max(2, 5*0.2) = 2
    assert result["phrases_meets_requirement"] is True


def test_validate_with_various_kit_sizes():
    """Test validation with various kit sizes."""
    # Small kit (5 words, 2 grammar, 2 phrases)
    small_kit = {
        "necessary_words": [{"surface": f"w{i}"} for i in range(5)],
        "necessary_grammar_patterns": [{"pattern": f"g{i}"} for i in range(2)],
        "necessary_fixed_phrases": [{"phrase": {"kanji": f"p{i}"}} for i in range(2)],
    }
    
    # Requirements: max(6, 5*0.3)=6 words, max(2, 2*0.2)=2 grammar, max(2, 2*0.2)=2 phrases
    lesson_small = {
        "lesson": {
            "cards": {
                "lesson_dialogue": {"turns": [{"japanese": {"kanji": "w0 w1 w2 w3 w4 w0"}}]},
                "grammar_patterns": {"patterns": [{"examples": [{"jp": {"kanji": "g0 g1"}}]}]},
            }
        }
    }
    
    result = validate_kit_usage_requirements(lesson_small, small_kit)
    # Note: For small kits, requirements may be higher than kit size
    assert result["words_required"] == 6  # max(6, 1.5) = 6
    assert result["grammar_required"] == 2
    assert result["phrases_required"] == 2


def test_validate_content_quality_words():
    """Verify kit words appear naturally in dialogue."""
    kit = {
        "necessary_words": [
            {"surface": "レストラン", "reading": "れすとらん"},
            {"surface": "メニュー", "reading": "めにゅー"},
        ],
        "necessary_grammar_patterns": [],
        "necessary_fixed_phrases": [],
    }
    
    # Good: words appear in natural context
    good_lesson = {
        "lesson": {
            "cards": {
                "lesson_dialogue": {
                    "turns": [
                        {"japanese": {"kanji": "レストランでメニューを見ます"}},
                    ]
                }
            }
        }
    }
    
    result = validate_kit_usage_requirements(good_lesson, kit)
    assert result["words_used"] >= 2
    assert "レストラン" in extract_text_from_lesson(good_lesson)
    assert "メニュー" in extract_text_from_lesson(good_lesson)


def test_validate_content_quality_grammar():
    """Verify kit grammar patterns are used correctly."""
    kit = {
        "necessary_words": [],
        "necessary_grammar_patterns": [
            {"pattern": "〜をください", "explanation": "Please give me"},
        ],
        "necessary_fixed_phrases": [],
    }
    
    # Good: grammar pattern appears in examples
    good_lesson = {
        "lesson": {
            "cards": {
                "grammar_patterns": {
                    "patterns": [
                        {
                            "examples": [
                                {"jp": {"kanji": "コーヒーをください"}},
                            ]
                        }
                    ]
                }
            }
        }
    }
    
    result = validate_kit_usage_requirements(good_lesson, kit)
    assert result["grammar_used"] >= 1
    assert "〜をください" in extract_text_from_lesson(good_lesson) or "をください" in extract_text_from_lesson(good_lesson)


def test_validate_content_quality_phrases():
    """Verify kit phrases fit contextually."""
    kit = {
        "necessary_words": [],
        "necessary_grammar_patterns": [],
        "necessary_fixed_phrases": [
            {
                "phrase": {"kanji": "いらっしゃいませ", "romaji": "irasshaimase"},
                "usage_note": "Welcome greeting",
            }
        ],
    }
    
    # Good: phrase appears in appropriate context
    good_lesson = {
        "lesson": {
            "cards": {
                "lesson_dialogue": {
                    "turns": [
                        {"japanese": {"kanji": "いらっしゃいませ。何名様ですか？"}},
                    ]
                }
            }
        }
    }
    
    result = validate_kit_usage_requirements(good_lesson, kit)
    assert result["phrases_used"] >= 1
    assert "いらっしゃいませ" in extract_text_from_lesson(good_lesson)

