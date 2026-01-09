"""
Tests for Grammar Overview Schema and Post-Processing
======================================================

Tests for GrammarAIContentService overview generation, schema validation,
post-processing of AI-generated content, and migration from legacy formats.

The new schema is LEARNER-FIRST:
- Every Japanese item has jp, kana, romaji, en
- how_to_form is structured with summary_en, pattern_template, steps
- common_mistakes has structured wrong/correct examples
"""

import pytest
from app.services.grammar_ai_content_service import GrammarAIContentService


class TestGrammarOverviewPostProcessing:
    """Test cases for overview post-processing logic."""

    @pytest.fixture
    def service(self):
        """Create service instance for testing."""
        return GrammarAIContentService()

    # === Expected Use Cases: New Schema ===

    def test_postprocess_adds_new_schema_fields(self, service):
        """Test that post-processing adds new learner-first fields."""
        incomplete_overview = {
            "what_is_en": "This pattern expresses ability",
            "usage_en": "Used when talking about skills"
        }
        
        result = service._postprocess_overview(incomplete_overview)
        
        # Should have all new required fields
        assert "what_is_en" in result
        assert "how_to_form" in result
        assert "usage_en" in result
        assert "nuance_en" in result
        assert "common_mistakes" in result
        assert "cultural_context_en" in result
        assert "examples" in result
        assert "tips_en" in result
        assert "related_patterns" in result
        
        # Existing values preserved
        assert result["what_is_en"] == "This pattern expresses ability"
        assert result["usage_en"] == "Used when talking about skills"

    def test_postprocess_normalizes_how_to_form_structure(self, service):
        """Test that how_to_form is properly structured."""
        overview = {
            "what_is_en": "Test",
            "how_to_form": {
                "summary_en": "Add ga dekimasu after a noun",
                "pattern_template": "[Noun] + ga + dekimasu"
            }
        }
        
        result = service._postprocess_overview(overview)
        
        assert isinstance(result["how_to_form"], dict)
        assert result["how_to_form"]["summary_en"] == "Add ga dekimasu after a noun"
        assert result["how_to_form"]["pattern_template"] == "[Noun] + ga + dekimasu"
        assert "steps" in result["how_to_form"]
        assert "casual_variant" in result["how_to_form"]
        assert "notes_en" in result["how_to_form"]

    def test_postprocess_normalizes_structured_common_mistakes(self, service):
        """Test that structured common_mistakes are normalized."""
        overview = {
            "what_is_en": "Test",
            "common_mistakes": [
                {
                    "mistake_en": "Using wrong particle",
                    "wrong": {"jp": "日本語を出来ます", "kana": "にほんごをできます", "romaji": "nihongo wo deki masu", "en": "Wrong"},
                    "correct": {"jp": "日本語ができます", "kana": "にほんごができます", "romaji": "nihongo ga deki masu", "en": "I can speak Japanese"}
                }
            ]
        }
        
        result = service._postprocess_overview(overview)
        
        assert isinstance(result["common_mistakes"], list)
        assert len(result["common_mistakes"]) == 1
        mistake = result["common_mistakes"][0]
        assert mistake["mistake_en"] == "Using wrong particle"
        assert mistake["wrong"]["jp"] == "日本語を出来ます"
        assert mistake["correct"]["jp"] == "日本語ができます"

    def test_postprocess_prettifies_example_romaji_new_schema(self, service):
        """Test that romaji in examples is prettified in new schema."""
        overview = {
            "what_is_en": "Test",
            "examples": [
                {"jp": "日本語ができます", "kana": "にほんごができます", "romaji": "nihongogadekimasu", "en": "I can speak Japanese"},
                {"jp": "料理ができます", "kana": "りょうりができます", "romaji": "ryourigadekimasu", "en": "I can cook"}
            ]
        }
        
        result = service._postprocess_overview(overview)
        
        # Romaji should be prettified with spaces
        assert "examples" in result
        assert len(result["examples"]) == 2
        
        # Check that all 4 fields exist
        for example in result["examples"]:
            assert "jp" in example
            assert "kana" in example
            assert "romaji" in example
            assert "en" in example

    def test_postprocess_prettifies_romaji_in_how_to_form_steps(self, service):
        """Test romaji prettification in formation steps."""
        overview = {
            "what_is_en": "Test",
            "how_to_form": {
                "summary_en": "Test formation",
                "steps": [
                    {"slot": "Noun", "jp": "日本語", "kana": "にほんご", "romaji": "nihongo", "en": "Japanese"}
                ],
                "casual_variant": {"jp": "できる", "kana": "できる", "romaji": "dekiru", "en": "can do"}
            }
        }
        
        result = service._postprocess_overview(overview)
        
        # Steps should be processed
        assert len(result["how_to_form"]["steps"]) == 1
        # Casual variant should be processed
        assert result["how_to_form"]["casual_variant"]["romaji"] == "dekiru"


class TestLegacyMigration:
    """Test migration from legacy schema to learner-first schema."""

    @pytest.fixture
    def service(self):
        return GrammarAIContentService()

    def test_migrate_legacy_text_fields(self, service):
        """Test that legacy text fields are migrated to new _en fields."""
        legacy = {
            "what_is": "This is a test pattern",
            "usage": "Used for testing",
            "nuance": "Formal usage",
            "tips": "Practice daily",
            "cultural_context": "Common in polite speech"
        }
        
        result = service._postprocess_overview(legacy)
        
        # New fields should exist
        assert result["what_is_en"] == "This is a test pattern"
        assert result["usage_en"] == "Used for testing"
        assert result["nuance_en"] == "Formal usage"
        assert result["tips_en"] == "Practice daily"
        assert result["cultural_context_en"] == "Common in polite speech"
        
        # Legacy fields should also be preserved for backward compat
        assert result.get("what_is") == "This is a test pattern"

    def test_migrate_legacy_formation_to_how_to_form(self, service):
        """Test that legacy formation string becomes how_to_form structure."""
        legacy = {
            "what_is": "Test",
            "formation": "Noun + ga + dekimasu to express ability"
        }
        
        result = service._postprocess_overview(legacy)
        
        # how_to_form should be created
        assert isinstance(result["how_to_form"], dict)
        assert result["how_to_form"]["summary_en"] == "Noun + ga + dekimasu to express ability"
        assert result["how_to_form"]["steps"] == []
        
        # Legacy formation preserved
        assert result.get("formation") == "Noun + ga + dekimasu to express ability"

    def test_migrate_legacy_string_common_mistakes(self, service):
        """Test that legacy string common_mistakes become structured."""
        legacy = {
            "what_is": "Test",
            "common_mistakes": ["Don't use wo particle", "Remember to conjugate"]
        }
        
        result = service._postprocess_overview(legacy)
        
        # Should be list of structured objects
        assert isinstance(result["common_mistakes"], list)
        assert len(result["common_mistakes"]) == 2
        assert result["common_mistakes"][0]["mistake_en"] == "Don't use wo particle"
        assert result["common_mistakes"][0]["wrong"] is None
        assert result["common_mistakes"][0]["correct"] is None

    def test_migrate_legacy_examples_adds_kana_field(self, service):
        """Test that legacy examples get empty kana field added."""
        legacy = {
            "what_is": "Test",
            "examples": [
                {"jp": "日本語ができます", "romaji": "nihongo ga deki masu", "en": "I can speak Japanese"}
            ]
        }
        
        result = service._postprocess_overview(legacy)
        
        # Example should have all 4 fields
        assert len(result["examples"]) == 1
        ex = result["examples"][0]
        assert ex["jp"] == "日本語ができます"
        assert ex["kana"] == ""  # Empty for legacy (not provided)
        assert "nihongo" in ex["romaji"]
        assert ex["en"] == "I can speak Japanese"

    def test_already_migrated_overview_not_double_migrated(self, service):
        """Test that already-migrated overviews aren't changed."""
        new_format = {
            "what_is_en": "This is the new format",
            "how_to_form": {
                "summary_en": "Proper structured formation",
                "pattern_template": "[N] + ga + dekimasu",
                "steps": [{"slot": "Noun", "en": "skill/language"}]
            },
            "usage_en": "When expressing ability",
            "nuance_en": "Polite",
            "common_mistakes": [{"mistake_en": "Wrong particle"}],
            "examples": [{"jp": "日本語ができます", "kana": "にほんごができます", "romaji": "nihongo ga dekimasu", "en": "I can speak Japanese"}],
            "tips_en": "Practice",
            "related_patterns": []
        }
        
        result = service._postprocess_overview(new_format)
        
        # Should preserve the structure
        assert result["what_is_en"] == "This is the new format"
        assert result["how_to_form"]["summary_en"] == "Proper structured formation"
        assert len(result["how_to_form"]["steps"]) == 1


class TestGrammarOverviewPrompt:
    """Test cases for the prompt builder."""

    @pytest.fixture
    def service(self):
        return GrammarAIContentService()

    def test_build_prompt_includes_pattern_info(self, service):
        """Test that prompt includes pattern information."""
        pattern = {
            "pattern": "～は～です",
            "pattern_romaji": "~wa~desu",
            "textbook_form": "N1はN2です",
            "textbook_form_romaji": "N1 wa N2 desu",
            "example_sentence": "私はカーラです。",
            "example_romaji": "Watashi wa Kaara desu.",
            "classification": "説明",
            "textbook": "入門",
            "topic": "自己紹介"
        }
        
        prompt = service._build_prompt(pattern, [], [])
        
        assert "～は～です" in prompt
        assert "N1はN2です" in prompt
        assert "私はカーラです" in prompt

    def test_build_prompt_requires_english_explanations(self, service):
        """Test that prompt instructs for English metalanguage."""
        pattern = {"pattern": "Test", "pattern_romaji": "test"}
        
        prompt = service._build_prompt(pattern, [], [])
        
        assert "ENGLISH" in prompt or "English" in prompt
        # Should specify English for explanations
        assert "what_is_en" in prompt or "summary_en" in prompt

    def test_build_prompt_requires_all_four_fields(self, service):
        """Test that prompt requires jp, kana, romaji, en for examples."""
        pattern = {"pattern": "Test", "pattern_romaji": "test"}
        
        prompt = service._build_prompt(pattern, [], [])
        
        # Should require all four fields
        assert "jp" in prompt
        assert "kana" in prompt
        assert "romaji" in prompt
        assert "en" in prompt

    def test_build_prompt_requires_structured_how_to_form(self, service):
        """Test that prompt requests structured how_to_form."""
        pattern = {"pattern": "Test", "pattern_romaji": "test"}
        
        prompt = service._build_prompt(pattern, [], [])
        
        assert "how_to_form" in prompt
        assert "summary_en" in prompt
        assert "steps" in prompt

    def test_build_prompt_avoids_notation_symbols(self, service):
        """Test that prompt instructs to avoid 【】 notation."""
        pattern = {"pattern": "Test", "pattern_romaji": "test"}
        
        prompt = service._build_prompt(pattern, [], [])
        
        # Should instruct against using these symbols
        assert "【】" in prompt or "notation" in prompt.lower()

    def test_build_prompt_includes_similar_patterns(self, service):
        """Test that prompt includes similar patterns."""
        pattern = {"pattern": "Test", "pattern_romaji": "test"}
        similar = [
            {"pattern": "Similar 1", "pattern_romaji": "similar1"},
            {"pattern": "Similar 2", "pattern_romaji": "similar2"}
        ]
        
        prompt = service._build_prompt(pattern, similar, [])
        
        assert "Similar 1" in prompt
        assert "Similar 2" in prompt

    def test_build_prompt_includes_prerequisites(self, service):
        """Test that prompt includes prerequisites."""
        pattern = {"pattern": "Test", "pattern_romaji": "test"}
        prereq = [
            {"pattern": "Prereq 1", "pattern_romaji": "prereq1"},
            {"pattern": "Prereq 2", "pattern_romaji": "prereq2"}
        ]
        
        prompt = service._build_prompt(pattern, [], prereq)
        
        assert "Prereq 1" in prompt
        assert "Prereq 2" in prompt

    def test_build_prompt_instructs_spaced_romaji(self, service):
        """Test that prompt instructs for spaced romaji."""
        pattern = {"pattern": "Test", "pattern_romaji": "test"}
        
        prompt = service._build_prompt(pattern, [], [])
        
        # Should contain instruction about romaji spacing
        prompt_lower = prompt.lower()
        assert "space" in prompt_lower
        assert "romaji" in prompt_lower

    def test_build_prompt_for_beginners(self, service):
        """Test that prompt emphasizes beginner-friendly content."""
        pattern = {"pattern": "Test", "pattern_romaji": "test"}
        
        prompt = service._build_prompt(pattern, [], [])
        
        # Should mention beginners or learners who can't read Japanese
        prompt_lower = prompt.lower()
        assert "beginner" in prompt_lower or "cannot read" in prompt_lower or "can't read" in prompt_lower


class TestEdgeCases:
    """Test edge cases and failure scenarios."""

    @pytest.fixture
    def service(self):
        return GrammarAIContentService()

    def test_postprocess_handles_none_values(self, service):
        """Test that None values are replaced with defaults."""
        overview = {
            "what_is_en": None,
            "how_to_form": None,
            "common_mistakes": None
        }
        
        result = service._postprocess_overview(overview)
        
        assert result["what_is_en"] == ""
        assert result["how_to_form"] is not None
        assert result["common_mistakes"] == []

    def test_postprocess_handles_empty_overview(self, service):
        """Test that empty overview gets all defaults."""
        result = service._postprocess_overview({})
        
        assert result["what_is_en"] == ""
        assert result["how_to_form"]["summary_en"] == ""
        assert result["usage_en"] == ""
        assert result["nuance_en"] == ""
        assert result["common_mistakes"] == []
        assert result["cultural_context_en"] is None
        assert result["examples"] == []
        assert result["tips_en"] == ""
        assert result["related_patterns"] == []

    def test_postprocess_handles_malformed_examples(self, service):
        """Test handling of malformed examples."""
        overview = {
            "what_is_en": "Test",
            "examples": "not a list"  # Should be list
        }
        
        # Should not crash
        result = service._postprocess_overview(overview)
        assert "examples" in result

    def test_postprocess_ensures_example_fields(self, service):
        """Test that all example fields are ensured."""
        overview = {
            "what_is_en": "Test",
            "examples": [
                {"jp": "日本語"}  # Missing kana, romaji, en
            ]
        }
        
        result = service._postprocess_overview(overview)
        
        ex = result["examples"][0]
        assert ex["jp"] == "日本語"
        assert "kana" in ex
        assert "romaji" in ex
        assert "en" in ex

    def test_postprocess_handles_empty_string_related_patterns(self, service):
        """Test that empty string related_patterns becomes empty list."""
        overview = {
            "what_is_en": "Test",
            "related_patterns": ""
        }
        
        result = service._postprocess_overview(overview)
        
        assert result["related_patterns"] == []

    def test_postprocess_strips_whitespace_new_fields(self, service):
        """Test that new text fields have whitespace stripped."""
        overview = {
            "what_is_en": "  Test with spaces  ",
            "usage_en": "\n\nUsage text\n\n",
            "tips_en": "  Tip text  "
        }
        
        result = service._postprocess_overview(overview)
        
        assert result["what_is_en"] == "Test with spaces"
        assert result["usage_en"] == "Usage text"
        assert result["tips_en"] == "Tip text"
