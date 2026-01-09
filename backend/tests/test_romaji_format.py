"""
Tests for Romaji Formatting Utilities
=====================================

Tests for prettify_romaji_template function that formats grammar-template 
romaji strings for better readability.
"""

import pytest
from app.utils.romaji import prettify_romaji_template


class TestPrettifyRomajiTemplate:
    """Test cases for prettify_romaji_template function."""

    # === Expected Use Cases ===
    
    def test_textbook_template_with_parentheses(self):
        """Test formatting of textbook-style template with parentheses."""
        # The user's original example
        input_str = "N(kotoba)gadekimasu(ka) Nhadekimasen"
        result = prettify_romaji_template(input_str)
        
        # Should have spaces around parentheses and between particles
        assert "(" in result
        assert ")" in result
        assert " ga " in result.lower() or "ga " in result.lower()
        assert " dekimasu" in result.lower()
        assert " dekimasen" in result.lower()
        # Should not have parentheses directly attached to letters
        assert ")g" not in result.lower()
        assert ")n" not in result.lower()

    def test_basic_particle_separation(self):
        """Test that common particles get separated."""
        input_str = "watashiwagakuseidesu"
        result = prettify_romaji_template(input_str)
        
        # Should split common particles
        assert " wa " in result.lower() or result.lower().startswith("watashi wa") or "shi wa" in result.lower()
        assert " desu" in result.lower()

    def test_tilde_placeholder_formatting(self):
        """Test formatting of tilde placeholders."""
        input_str = "~wa~desu"
        result = prettify_romaji_template(input_str)
        
        # Should have space between tilde patterns
        assert "~wa " in result.lower() or "~ wa" in result.lower()
        assert "~desu" in result.lower() or "~ desu" in result.lower()

    def test_uppercase_placeholder_separation(self):
        """Test that uppercase placeholders get separated from lowercase."""
        input_str = "Nwadesu"
        result = prettify_romaji_template(input_str)
        
        # N should be separated from wa
        assert "N " in result or "N wa" in result

    def test_masu_form_separation(self):
        """Test separation of masu/masen verb endings."""
        input_str = "tabemasu tabemasen"
        result = prettify_romaji_template(input_str)
        
        # Should preserve existing spaces and add where needed
        assert " masu" in result.lower()
        assert " masen" in result.lower()

    # === Edge Cases ===
    
    def test_already_well_spaced_romaji(self):
        """Test that already well-formatted romaji is not broken."""
        input_str = "Watashi wa gakusei desu"
        result = prettify_romaji_template(input_str)
        
        # Should not add extra spaces or break existing formatting
        assert "watashi" in result.lower()
        assert "gakusei" in result.lower()
        # No double spaces
        assert "  " not in result

    def test_single_word_input(self):
        """Test handling of single word input."""
        input_str = "desu"
        result = prettify_romaji_template(input_str)
        
        # Should return the word, possibly with minor formatting
        assert "desu" in result.lower()

    def test_complex_template_with_multiple_placeholders(self):
        """Test complex template with multiple placeholders."""
        input_str = "N1waN2desu"
        result = prettify_romaji_template(input_str)
        
        # Should have spaces between major components
        assert "N1" in result or "N 1" in result
        assert "N2" in result or "N 2" in result
        assert " wa " in result.lower() or "wa " in result.lower()

    def test_preserves_spaces_in_middle(self):
        """Test that existing spaces are preserved."""
        input_str = "kore wa hon desu"
        result = prettify_romaji_template(input_str)
        
        # Should keep existing structure
        assert "kore" in result.lower()
        assert "hon" in result.lower()
        assert "desu" in result.lower()

    # === Failure Cases ===
    
    def test_empty_string_returns_empty(self):
        """Test that empty string returns empty string."""
        result = prettify_romaji_template("")
        assert result == ""

    def test_none_input_returns_empty(self):
        """Test that None input returns empty string."""
        result = prettify_romaji_template(None)
        assert result == ""

    def test_whitespace_only_returns_empty(self):
        """Test that whitespace-only input returns empty string."""
        result = prettify_romaji_template("   ")
        assert result == ""

    def test_non_string_input_returns_empty(self):
        """Test that non-string input returns empty string."""
        result = prettify_romaji_template(123)  # type: ignore
        assert result == ""

    def test_normalizes_multiple_spaces(self):
        """Test that multiple spaces are normalized to single spaces."""
        input_str = "watashi   wa    desu"
        result = prettify_romaji_template(input_str)
        
        # No double spaces in output
        assert "  " not in result


class TestRomajiParticlePatterns:
    """Additional tests for specific particle patterns."""

    def test_ga_particle(self):
        """Test ga particle separation."""
        result = prettify_romaji_template("koregahondesu")
        assert " ga " in result.lower()

    def test_de_particle(self):
        """Test de particle separation."""
        result = prettify_romaji_template("gakkoudebenkyoushimasu")
        assert " de " in result.lower()

    def test_ni_particle(self):
        """Test ni particle separation."""
        result = prettify_romaji_template("nihonniikmasu")
        assert " ni " in result.lower()

    def test_mo_particle(self):
        """Test mo particle separation."""
        result = prettify_romaji_template("koremohondesu")
        assert " mo " in result.lower()

    def test_ka_question_marker(self):
        """Test ka question marker."""
        result = prettify_romaji_template("desuka")
        assert " ka" in result.lower() or result.lower().endswith("ka")

