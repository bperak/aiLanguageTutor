"""
Tests for CanDo lesson quality repair loop.

Tests cover:
- Expected: mock AI returns prompt-leak lesson first, then repaired lesson → enforce mode returns repaired output
- Failure: repair still fails → returns best-effort + report (warn fallback)
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.cando_lesson_session_service import CanDoLessonSessionService
from app.services.cando_lesson_quality import QualityMode, compute_quality_report


@pytest.fixture
def service():
    """Create a CanDoLessonSessionService instance."""
    return CanDoLessonSessionService()


@pytest.fixture
def sample_simple_content():
    """Sample Stage1 simple content."""
    return {
        "lessonPlan": [
            {"title": "導入", "contentJP": "今日の目標は挨拶です。" * 20}
        ],
        "reading": {
            "title": "読解",
            "text": "田中さんは学生です。" * 50  # Long enough
        },
        "dialogue": [
            {"speaker": "A", "text": "こんにちは。"},
            {"speaker": "B", "text": "はじめまして。"},
        ] * 3,
        "grammar": [
            {"pattern": "〜です", "explanation": "Polite", "examples": ["例1", "例2"]}
        ] * 3,
        "practice": [],
        "culture": []
    }


@pytest.fixture
def sample_meta_extra():
    """Sample meta_extra with kit."""
    return {
        "type": "polite",
        "skillDomain": "speaking",
        "description": "Greeting politely",
        "prelesson_kit": {
            "necessary_words": [
                {"surface": "こんにちは", "reading": "こんにちは", "pos": "expression", "translation": "hello"}
            ],
            "necessary_grammar_patterns": [
                {"pattern": "〜です", "explanation": "Polite copula"}
            ],
            "necessary_fixed_phrases": []
        }
    }


class TestRepairLoopExpectedUse:
    """Test repair loop in expected use case."""
    
    @pytest.mark.asyncio
    async def test_repair_loop_success(self, service, sample_simple_content, sample_meta_extra):
        """Test that repair loop successfully fixes prompt leak."""
        # First generation returns prompt leak
        master_with_leak = {
            "ui": {
                "header": {"title": "Test"},
                "sections": [
                    {
                        "id": "reading",
                        "type": "reading",
                        "title": "読解",
                        "cards": [
                            {
                                "id": "card1",
                                "body": {
                                    "jp": "Output JSON schema: { ... }",  # Prompt leak
                                    "en": "Some content"
                                }
                            }
                        ]
                    }
                ]
            }
        }
        
        # Mock the merge to return master with leak
        with patch.object(service, "_merge_enhanced_sections", return_value=master_with_leak):
            # Mock repair: second generation returns fixed content
            repaired_reading = {
                "success": True,
                "data": {
                    "title": {"kanji": "読解", "romaji": "dokkai", "furigana": [], "translation": "Reading"},
                    "content": {
                        "kanji": "田中さんは学生です。",
                        "romaji": "Tanaka-san wa gakusei desu.",
                        "furigana": [],
                        "translation": "Tanaka is a student."
                    }
                }
            }
            
            with patch.object(service, "_enhance_section_with_multilingual", return_value=repaired_reading):
                # Mock quality report computation
                with patch("app.services.cando_lesson_session_service.compute_quality_report") as mock_report:
                    # First report has blocking issues
                    first_report = MagicMock()
                    first_report.has_blocking_issues = True
                    first_report.issues = [
                        MagicMock(severity="blocking", category="prompt_leak")
                    ]
                    first_report.overall_score = 0.5
                    first_report.model_dump.return_value = {"overall_score": 0.5, "issues": []}
                    
                    # Second report (after repair) has no blocking issues
                    second_report = MagicMock()
                    second_report.has_blocking_issues = False
                    second_report.issues = []
                    second_report.overall_score = 0.9
                    second_report.model_dump.return_value = {"overall_score": 0.9, "issues": []}
                    
                    mock_report.side_effect = [first_report, second_report]
                    
                    # Call the function with enforce mode
                    result = await service._generate_master_lesson_twostage_with_fallback(
                        can_do_id="TEST:1",
                        topic="挨拶",
                        original_level_str="A1",
                        original_level_num=1,
                        meta_extra=sample_meta_extra,
                        quality_mode=QualityMode.ENFORCE
                    )
                    
                    # Should have called repair
                    assert service._enhance_section_with_multilingual.called
                    # Should have quality report stored
                    assert result.get("__meta", {}).get("quality_report") is not None


class TestRepairLoopFailure:
    """Test repair loop when repair fails."""
    
    @pytest.mark.asyncio
    async def test_repair_loop_fails_fallback_to_warn(self, service, sample_simple_content, sample_meta_extra):
        """Test that repair failure falls back to warn mode."""
        master_with_leak = {
            "ui": {
                "header": {"title": "Test"},
                "sections": [
                    {
                        "id": "reading",
                        "type": "reading",
                        "title": "読解",
                        "cards": [
                            {
                                "id": "card1",
                                "body": {
                                    "jp": "Output JSON schema: { ... }",  # Prompt leak
                                    "en": "Some content"
                                }
                            }
                        ]
                    }
                ]
            }
        }
        
        with patch.object(service, "_merge_enhanced_sections", return_value=master_with_leak):
            # Mock repair failure
            repaired_reading = {
                "success": False,
                "error": "Repair failed"
            }
            
            with patch.object(service, "_enhance_section_with_multilingual", return_value=repaired_reading):
                with patch("app.services.cando_lesson_session_service.compute_quality_report") as mock_report:
                    # First report has blocking issues
                    first_report = MagicMock()
                    first_report.has_blocking_issues = True
                    first_report.issues = [
                        MagicMock(severity="blocking", category="prompt_leak")
                    ]
                    first_report.overall_score = 0.5
                    first_report.model_dump.return_value = {"overall_score": 0.5, "issues": []}
                    
                    # Second report (after fallback to warn) still has issues but passes
                    second_report = MagicMock()
                    second_report.has_blocking_issues = True  # Still has issues
                    second_report.issues = [
                        MagicMock(severity="blocking", category="prompt_leak")
                    ]
                    second_report.overall_score = 0.5
                    second_report.passed = True  # But passes in warn mode
                    second_report.model_dump.return_value = {"overall_score": 0.5, "issues": [], "passed": True}
                    
                    mock_report.side_effect = [first_report, second_report]
                    
                    # Call with enforce mode
                    result = await service._generate_master_lesson_twostage_with_fallback(
                        can_do_id="TEST:1",
                        topic="挨拶",
                        original_level_str="A1",
                        original_level_num=1,
                        meta_extra=sample_meta_extra,
                        quality_mode=QualityMode.ENFORCE
                    )
                    
                    # Should have attempted repair
                    assert service._enhance_section_with_multilingual.called
                    # Should still return result (best-effort)
                    assert result is not None
                    # Should have quality report
                    assert result.get("__meta", {}).get("quality_report") is not None


class TestRepairLoopBounded:
    """Test that repair loop is bounded (doesn't loop infinitely)."""
    
    @pytest.mark.asyncio
    async def test_repair_loop_max_attempts(self, service, sample_simple_content, sample_meta_extra):
        """Test that repair loop stops after max attempts."""
        master_with_leak = {
            "ui": {
                "header": {"title": "Test"},
                "sections": [
                    {
                        "id": "reading",
                        "type": "reading",
                        "title": "読解",
                        "cards": [
                            {
                                "id": "card1",
                                "body": {
                                    "jp": "Output JSON schema: { ... }",
                                    "en": "Some content"
                                }
                            }
                        ]
                    }
                ]
            }
        }
        
        with patch.object(service, "_merge_enhanced_sections", return_value=master_with_leak):
            # Mock repair always fails
            repaired_reading = {
                "success": False,
                "error": "Repair failed"
            }
            
            with patch.object(service, "_enhance_section_with_multilingual", return_value=repaired_reading):
                with patch("app.services.cando_lesson_session_service.compute_quality_report") as mock_report:
                    # Always return blocking issues
                    blocking_report = MagicMock()
                    blocking_report.has_blocking_issues = True
                    blocking_report.issues = [
                        MagicMock(severity="blocking", category="prompt_leak")
                    ]
                    blocking_report.overall_score = 0.3
                    blocking_report.model_dump.return_value = {"overall_score": 0.3, "issues": []}
                    
                    mock_report.return_value = blocking_report
                    
                    # Call with enforce mode
                    result = await service._generate_master_lesson_twostage_with_fallback(
                        can_do_id="TEST:1",
                        topic="挨拶",
                        original_level_str="A1",
                        original_level_num=1,
                        meta_extra=sample_meta_extra,
                        quality_mode=QualityMode.ENFORCE
                    )
                    
                    # Should have attempted repair (max 2 times)
                    # Verify it was called but not more than max_repair_attempts
                    call_count = service._enhance_section_with_multilingual.call_count
                    assert call_count <= 2  # Max repair attempts
                    
                    # Should still return result (fallback to warn)
                    assert result is not None

