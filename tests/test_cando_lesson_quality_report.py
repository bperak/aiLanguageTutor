"""
Tests for CanDo lesson quality reporting.

Tests cover:
- Expected: coverage detects kit usage and reports pass
- Edge: empty kit or missing fields → report still valid
- Failure: prompt-leak text triggers blocking issues
"""

import pytest
from app.services.cando_lesson_quality import (
    QualityMode,
    QualityReport,
    compute_quality_report,
    compute_kit_coverage,
    detect_prompt_leak,
    detect_topic_mismatch,
    validate_minimum_structure,
    flatten_lesson_text,
)


@pytest.fixture
def sample_master_lesson():
    """Sample master lesson with UI structure."""
    return {
        "ui": {
            "header": {
                "title": {"jp": "挨拶", "en": "Greeting"},
                "subtitle": {"jp": "丁寧な挨拶", "en": "Polite Greeting"}
            },
            "sections": [
                {
                    "id": "intro",
                    "type": "intro",
                    "title": {"jp": "導入", "en": "Introduction"},
                    "cards": [
                        {
                            "id": "card1",
                            "title": {"jp": "挨拶の基本", "en": "Basic Greetings"},
                            "body": {
                                "jp": "こんにちは。はじめまして。",
                                "en": "Hello. Nice to meet you."
                            }
                        }
                    ]
                },
                {
                    "id": "reading",
                    "type": "reading",
                    "title": {"jp": "読解", "en": "Reading"},
                    "cards": [
                        {
                            "id": "card2",
                            "body": {
                                "jp": "田中さんは学生です。",
                                "en": "Tanaka is a student."
                            }
                        }
                    ]
                }
            ]
        },
        "exercises": []
    }


@pytest.fixture
def sample_kit():
    """Sample PreLessonKit with words, grammar, and phrases."""
    return {
        "can_do_context": {
            "situation": "Meeting someone new",
            "pragmatic_act": "polite greeting",
            "notes": None
        },
        "necessary_words": [
            {"surface": "こんにちは", "reading": "こんにちは", "pos": "expression", "translation": "hello"},
            {"surface": "はじめまして", "reading": "はじめまして", "pos": "expression", "translation": "nice to meet you"},
            {"surface": "学生", "reading": "がくせい", "pos": "noun", "translation": "student"},
        ],
        "necessary_grammar_patterns": [
            {"pattern": "〜です", "explanation": "Polite copula"},
            {"pattern": "〜は〜です", "explanation": "X is Y"},
        ],
        "necessary_fixed_phrases": [
            {
                "phrase": {
                    "kanji": "こんにちは",
                    "romaji": "konnichiwa",
                    "translation": "hello"
                }
            }
        ]
    }


class TestFlattenLessonText:
    """Test text flattening for analysis."""
    
    def test_flatten_ui_structure(self, sample_master_lesson):
        """Test flattening UI structure format."""
        text = flatten_lesson_text(sample_master_lesson)
        assert "挨拶" in text
        assert "こんにちは" in text
        assert "田中さんは学生です" in text
    
    def test_flatten_stage1_structure(self):
        """Test flattening Stage1 format."""
        stage1_master = {
            "lessonPlan": [
                {"title": "導入", "contentJP": "今日の目標は挨拶です。"}
            ],
            "reading": {"title": "読解", "text": "田中さんは学生です。"},
            "dialogue": [
                {"speaker": "A", "text": "こんにちは。"}
            ]
        }
        text = flatten_lesson_text(stage1_master)
        assert "導入" in text
        assert "今日の目標は挨拶です" in text
        assert "田中さんは学生です" in text
        assert "こんにちは" in text


class TestKitCoverage:
    """Test PreLessonKit coverage computation."""
    
    def test_compute_coverage_with_kit(self, sample_kit):
        """Test coverage computation when kit components are used."""
        text = "こんにちは。はじめまして。田中さんは学生です。"
        coverage = compute_kit_coverage(text, sample_kit)
        
        assert coverage.words_total == 3
        assert coverage.words_hit >= 2  # At least こんにちは and はじめまして
        assert coverage.words_ratio > 0.5
        
        assert coverage.grammar_total == 2
        assert "です" in text  # Should match grammar pattern
        assert coverage.grammar_ratio > 0.0
        
        assert coverage.phrases_total == 1
        assert coverage.phrases_hit >= 0
    
    def test_compute_coverage_empty_kit(self):
        """Test coverage with empty kit."""
        text = "Some lesson text"
        coverage = compute_kit_coverage(text, None)
        
        assert coverage.words_total == 0
        assert coverage.words_hit == 0
        assert coverage.words_ratio == 0.0
    
    def test_compute_coverage_no_usage(self, sample_kit):
        """Test coverage when kit components are not used."""
        text = "完全に異なるテキスト。"
        coverage = compute_kit_coverage(text, sample_kit)
        
        assert coverage.words_total == 3
        assert coverage.words_hit == 0
        assert coverage.words_ratio == 0.0


class TestPromptLeakDetection:
    """Test prompt leak detection."""
    
    def test_detect_prompt_leak_blocking(self):
        """Test detection of blocking prompt leaks."""
        text = "Output JSON schema: { ... }"
        issues = detect_prompt_leak(text)
        
        assert len(issues) > 0
        assert any(i.severity == "blocking" for i in issues)
        assert any(i.category == "prompt_leak" for i in issues)
    
    def test_detect_prompt_leak_template_placeholder(self):
        """Test detection of template placeholders."""
        text = "Lesson ID: {{lessonId}}"
        issues = detect_prompt_leak(text)
        
        assert len(issues) > 0
        assert any("lessonId" in i.message for i in issues)
    
    def test_detect_prompt_leak_no_issues(self):
        """Test that normal text doesn't trigger leak detection."""
        text = "こんにちは。今日は良い天気です。"
        issues = detect_prompt_leak(text)
        
        assert len(issues) == 0


class TestTopicMismatchDetection:
    """Test topic mismatch detection."""
    
    def test_detect_topic_mismatch_generic_travel(self):
        """Test detection of generic travel content when topic isn't travel."""
        text = "駅での案内所で道を聞くことができます。"
        meta = {
            "primaryTopic": "自己紹介",
            "description": "Introduce yourself"
        }
        issues = detect_topic_mismatch(text, meta)
        
        assert len(issues) > 0
        assert any(i.severity == "blocking" for i in issues)
        assert any(i.category == "topic_mismatch" for i in issues)
    
    def test_detect_topic_mismatch_travel_ok(self):
        """Test that travel content is OK when topic is travel."""
        text = "駅での案内所で道を聞くことができます。"
        meta = {
            "primaryTopic": "旅行と交通",
            "description": "Travel and transportation"
        }
        issues = detect_topic_mismatch(text, meta)
        
        # Should not have blocking issues for travel content when topic is travel
        blocking_issues = [i for i in issues if i.severity == "blocking"]
        assert len(blocking_issues) == 0
    
    def test_detect_topic_mismatch_no_meta(self):
        """Test that missing meta doesn't cause errors."""
        text = "Some lesson text"
        issues = detect_topic_mismatch(text, None)
        
        assert isinstance(issues, list)
        assert len(issues) == 0


class TestStructureValidation:
    """Test minimum structure validation."""
    
    def test_validate_structure_valid_ui(self, sample_master_lesson):
        """Test validation of valid UI structure."""
        issues = validate_minimum_structure(sample_master_lesson)
        
        # Should have no blocking issues for valid structure
        blocking_issues = [i for i in issues if i.severity == "blocking"]
        assert len(blocking_issues) == 0
    
    def test_validate_structure_missing_sections(self):
        """Test validation fails when sections are missing."""
        master = {
            "ui": {
                "header": {"title": "Test"},
                "sections": []  # Empty sections
            }
        }
        issues = validate_minimum_structure(master)
        
        assert len(issues) > 0
        assert any(i.severity == "blocking" for i in issues)
        assert any(i.category == "structure" for i in issues)
    
    def test_validate_structure_stage1_valid(self):
        """Test validation of valid Stage1 structure."""
        master = {
            "lessonPlan": [
                {"title": "Step 1", "contentJP": "Content 1"},
                {"title": "Step 2", "contentJP": "Content 2"},
                {"title": "Step 3", "contentJP": "Content 3"},
                {"title": "Step 4", "contentJP": "Content 4"},
            ],
            "reading": {"title": "Reading", "text": "Long reading text here..."},
            "dialogue": [
                {"speaker": "A", "text": "Turn 1"},
                {"speaker": "B", "text": "Turn 2"},
                {"speaker": "A", "text": "Turn 3"},
                {"speaker": "B", "text": "Turn 4"},
                {"speaker": "A", "text": "Turn 5"},
                {"speaker": "B", "text": "Turn 6"},
            ],
            "grammar": [
                {"pattern": "Pattern 1", "explanation": "Exp 1", "examples": ["Ex1", "Ex2"]},
                {"pattern": "Pattern 2", "explanation": "Exp 2", "examples": ["Ex1", "Ex2"]},
                {"pattern": "Pattern 3", "explanation": "Exp 3", "examples": ["Ex1", "Ex2"]},
            ]
        }
        issues = validate_minimum_structure(master)
        
        # Should have no blocking issues
        blocking_issues = [i for i in issues if i.severity == "blocking"]
        assert len(blocking_issues) == 0


class TestQualityReport:
    """Test complete quality report computation."""
    
    def test_compute_report_expected_use(self, sample_master_lesson, sample_kit):
        """Test quality report for expected use case."""
        text = "こんにちは。はじめまして。田中さんは学生です。"
        # Update master to include this text
        sample_master_lesson["ui"]["sections"][0]["cards"][0]["body"]["jp"] = text
        
        report = compute_quality_report(
            master=sample_master_lesson,
            kit=sample_kit,
            meta={"primaryTopic": "挨拶", "description": "Greeting"},
            quality_mode=QualityMode.WARN
        )
        
        assert isinstance(report, QualityReport)
        assert 0.0 <= report.overall_score <= 1.0
        assert report.kit_coverage is not None
        assert report.kit_coverage.words_total > 0
    
    def test_compute_report_empty_kit(self, sample_master_lesson):
        """Test quality report with empty kit."""
        report = compute_quality_report(
            master=sample_master_lesson,
            kit=None,
            meta={"primaryTopic": "挨拶"},
            quality_mode=QualityMode.WARN
        )
        
        assert isinstance(report, QualityReport)
        assert report.kit_coverage is None
        # Should still pass (no blocking issues from missing kit)
        assert report.passed
    
    def test_compute_report_prompt_leak_blocking(self, sample_master_lesson):
        """Test quality report detects prompt leak as blocking."""
        # Inject prompt leak into master
        sample_master_lesson["ui"]["sections"][0]["cards"][0]["body"]["jp"] = "Output JSON schema: { ... }"
        
        report = compute_quality_report(
            master=sample_master_lesson,
            kit=None,
            meta=None,
            quality_mode=QualityMode.ENFORCE
        )
        
        assert report.has_blocking_issues
        assert not report.passed
        assert any(i.category == "prompt_leak" for i in report.issues)
    
    def test_compute_report_warn_mode_allows_blocking(self, sample_master_lesson):
        """Test that warn mode allows blocking issues (doesn't fail)."""
        sample_master_lesson["ui"]["sections"][0]["cards"][0]["body"]["jp"] = "Output JSON schema: { ... }"
        
        report = compute_quality_report(
            master=sample_master_lesson,
            kit=None,
            meta=None,
            quality_mode=QualityMode.WARN
        )
        
        assert report.has_blocking_issues
        # In warn mode, should still pass (not block)
        assert report.passed
    
    def test_compute_report_off_mode(self, sample_master_lesson):
        """Test that off mode doesn't compute detailed checks."""
        report = compute_quality_report(
            master=sample_master_lesson,
            kit=None,
            meta=None,
            quality_mode=QualityMode.OFF
        )
        
        assert isinstance(report, QualityReport)
        # Off mode should still compute but not enforce
        assert report.passed

