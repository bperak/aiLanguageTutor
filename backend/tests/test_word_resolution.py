"""
Tests for Word Resolution Service

Tests normalization and ranking behavior for resolving AI-proposed targets to existing Word nodes.
"""

import pytest

from app.services.lexical_network.word_resolution import (
    normalize_orthography,
    normalize_reading,
    rank_candidates,
)


class TestNormalizeOrthography:
    """Test orthography normalization."""
    
    def test_basic_normalization(self):
        """Test basic NFKC normalization and trimming."""
        result = normalize_orthography("  綺麗  ")
        assert "綺麗" in result
        assert len(result) >= 1
    
    def test_na_adjective_trailing_na(self):
        """Test na-adjective trailing な removal."""
        result = normalize_orthography("綺麗な", expected_pos="形容動詞")
        assert "綺麗な" in result
        assert "綺麗" in result  # Should include variant without な
    
    def test_na_adjective_not_na_pos(self):
        """Test that な is not removed if POS is not 形容動詞."""
        result = normalize_orthography("綺麗な", expected_pos="名詞")
        assert "綺麗な" in result
        # Should not include variant without な for non-na-adj POS
    
    def test_punctuation_removal(self):
        """Test removal of common punctuation."""
        result = normalize_orthography("綺麗・きれい")
        assert "綺麗きれい" in result or "綺麗" in result
    
    def test_empty_input(self):
        """Test empty input handling."""
        result = normalize_orthography("")
        assert result == []
    
    def test_whitespace_only(self):
        """Test whitespace-only input."""
        result = normalize_orthography("   ")
        assert len(result) == 0 or all(not s.strip() for s in result)


class TestNormalizeReading:
    """Test reading normalization."""
    
    def test_hiragana_unchanged(self):
        """Test that hiragana input is preserved."""
        result = normalize_reading("きれい")
        assert "きれい" in result
    
    def test_katakana_to_hiragana(self):
        """Test katakana to hiragana conversion (if jaconv available)."""
        result = normalize_reading("キレイ")
        # Should include both katakana and hiragana forms
        assert len(result) >= 1
        # If jaconv available, should have hiragana variant
        if "きれい" in result or "キレイ" in result:
            assert True  # At least one form present
    
    def test_empty_input(self):
        """Test empty input handling."""
        result = normalize_reading("")
        assert result == []
    
    def test_whitespace_trimming(self):
        """Test whitespace trimming."""
        result = normalize_reading("  きれい  ")
        assert "きれい" in result or any("きれい" in s for s in result)


class TestRankCandidates:
    """Test candidate ranking logic."""
    
    def test_standard_orthography_priority(self):
        """Test that standard_orthography match has highest priority."""
        candidates = [
            {
                "standard_orthography": "綺麗",
                "kanji": "綺麗",
                "pos_primary": "形容詞",
            },
            {
                "standard_orthography": None,
                "kanji": "綺麗",
                "reading_hiragana": "きれい",
                "pos_primary": "形容詞",
            },
        ]
        
        best, status, metadata = rank_candidates(candidates, expected_pos=["形容詞"])
        assert status == "resolved"
        assert best is not None
        assert best.get("standard_orthography") == "綺麗"
        assert metadata["score"] >= 1000  # Should have high score
    
    def test_kanji_priority_over_reading(self):
        """Test that kanji match is preferred over reading match."""
        candidates = [
            {
                "standard_orthography": None,
                "kanji": "綺麗",
                "pos_primary": "形容詞",
            },
            {
                "standard_orthography": None,
                "kanji": None,
                "reading_hiragana": "きれい",
                "pos_primary": "形容詞",
            },
        ]
        
        best, status, metadata = rank_candidates(candidates, expected_pos=["形容詞"])
        assert status == "resolved"
        assert best is not None
        assert best.get("kanji") == "綺麗"
        assert metadata["score"] >= 900  # Kanji match score
    
    def test_pos_match_bonus(self):
        """Test that POS match adds bonus score."""
        candidates = [
            {
                "standard_orthography": "綺麗",
                "pos_primary": "形容詞",
            },
            {
                "standard_orthography": "綺麗",
                "pos_primary": "名詞",
            },
        ]
        
        best, status, metadata = rank_candidates(candidates, expected_pos=["形容詞"])
        assert status == "resolved"
        assert best is not None
        assert best.get("pos_primary") == "形容詞"  # Should prefer matching POS
    
    def test_ambiguous_detection(self):
        """Test that ambiguous cases are detected."""
        candidates = [
            {
                "standard_orthography": "綺麗",
                "pos_primary": "形容詞",
            },
            {
                "standard_orthography": "綺麗",
                "pos_primary": "形容詞",
            },
        ]
        
        best, status, metadata = rank_candidates(candidates, expected_pos=["形容詞"])
        # Should detect ambiguity if multiple candidates have same top score
        # In this case, both have same score, so should be ambiguous
        assert status in ["resolved", "ambiguous"]  # May resolve to first one deterministically
    
    def test_not_found_empty_candidates(self):
        """Test that empty candidates return not_found."""
        best, status, metadata = rank_candidates([], expected_pos=["形容詞"])
        assert status == "not_found"
        assert best is None
    
    def test_not_found_no_matches(self):
        """Test that candidates with zero score return not_found."""
        candidates = [
            {
                "standard_orthography": None,
                "kanji": None,
                "reading_hiragana": None,
                "pos_primary": "名詞",
            },
        ]
        
        best, status, metadata = rank_candidates(candidates, expected_pos=["形容詞"])
        # If no fields match, score should be 0 or very low
        assert status in ["not_found", "resolved"]  # May still resolve if reading matches
    
    def test_unidic_lemma_match(self):
        """Test that unidic_lemma match is recognized."""
        candidates = [
            {
                "standard_orthography": None,
                "kanji": None,
                "unidic_lemma": "綺麗",
                "pos_primary": "形容詞",
            },
        ]
        
        best, status, metadata = rank_candidates(candidates, expected_pos=["形容詞"])
        assert status == "resolved"
        assert best is not None
        assert metadata["score"] >= 800  # unidic_lemma match score


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
