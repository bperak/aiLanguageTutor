"""
Tests for Unified Dictionary Import Service

Tests bunrui parsing, etymology normalization, difficulty normalization,
and idempotent merge logic.
"""

import pytest
from app.services.lexical_network.column_mappings import (
    normalize_etymology,
    normalize_lee_difficulty,
    normalize_matsushita_difficulty,
    parse_bunrui_hierarchy,
)


class TestBunruiParsing:
    """Test bunrui hierarchy parsing."""
    
    def test_parse_dot_separated_format(self):
        """Test parsing dot-separated format like '1.1030.01'."""
        result = parse_bunrui_hierarchy("1.1030.01")
        assert result["bunrui_number"] == "1.1030.01"
        assert result["bunrui_class"] == "1"
        assert result["bunrui_division"] == "1.1"
        assert result["bunrui_section"] == "1.10"
        assert result["bunrui_subsection"] == "1.1030"
    
    def test_parse_compressed_format(self):
        """Test parsing compressed format like '11030'."""
        result = parse_bunrui_hierarchy("11030")
        assert result["bunrui_class"] == "1"
        assert result["bunrui_division"] == "1.1"
        assert result["bunrui_section"] == "1.10"
        assert result["bunrui_subsection"] == "1.1030"
    
    def test_parse_simple_format(self):
        """Test parsing simple format like '1.1'."""
        result = parse_bunrui_hierarchy("1.1")
        assert result["bunrui_class"] == "1"
        assert result["bunrui_division"] == "1.1"
        assert result.get("bunrui_section") is None
    
    def test_parse_empty(self):
        """Test parsing empty string."""
        result = parse_bunrui_hierarchy("")
        assert result == {}
    
    def test_parse_none(self):
        """Test parsing None."""
        result = parse_bunrui_hierarchy(None)
        assert result == {}


class TestEtymologyNormalization:
    """Test etymology normalization."""
    
    def test_normalize_full_forms(self):
        """Test normalizing full forms."""
        result, source = normalize_etymology("和語", "lee")
        assert result == "和語"
        assert source == "lee"
        
        result, source = normalize_etymology("漢語", "matsushita")
        assert result == "漢語"
        assert source == "matsushita"
    
    def test_normalize_abbreviated_forms(self):
        """Test normalizing abbreviated forms."""
        result, source = normalize_etymology("和", "vdrj")
        assert result == "和語"
        assert source == "vdrj"
        
        result, source = normalize_etymology("漢", "unidic")
        assert result == "漢語"
        assert source == "unidic"
    
    def test_normalize_english_forms(self):
        """Test normalizing English forms."""
        result, _ = normalize_etymology("native", "ai")
        assert result == "和語"
        
        result, _ = normalize_etymology("sino-japanese", "ai")
        assert result == "漢語"
    
    def test_normalize_unknown(self):
        """Test normalizing unknown value."""
        result, source = normalize_etymology("unknown_value", "test")
        assert result == "unknown_value"  # Returns as-is
        assert source == "test"
    
    def test_normalize_empty(self):
        """Test normalizing empty string."""
        result, source = normalize_etymology("", "test")
        assert result == ""
        assert source == "test"


class TestDifficultyNormalization:
    """Test difficulty normalization per source."""
    
    def test_normalize_lee_difficulty(self):
        """Test Lee difficulty normalization (6-level)."""
        assert normalize_lee_difficulty("1.初級前半") == 1
        assert normalize_lee_difficulty("2.初級後半") == 2
        assert normalize_lee_difficulty("6.上級後半") == 6
        assert normalize_lee_difficulty("3") == 3
        assert normalize_lee_difficulty("") == 1  # Default
    
    def test_normalize_matsushita_difficulty(self):
        """Test Matsushita difficulty normalization (3-level)."""
        assert normalize_matsushita_difficulty("初級") == 1
        assert normalize_matsushita_difficulty("中級") == 3
        assert normalize_matsushita_difficulty("上級") == 5
        assert normalize_matsushita_difficulty("") == 1  # Default


class TestSourcePriority:
    """Test source priority logic (conceptual - would need Neo4j for full test)."""
    
    def test_lee_owns_lee_fields(self):
        """Lee should own lee_difficulty fields."""
        # This would be tested in integration tests with actual Neo4j
        pass
    
    def test_matsushita_owns_matsushita_fields(self):
        """Matsushita should own matsushita_difficulty fields."""
        # This would be tested in integration tests with actual Neo4j
        pass
    
    def test_cascading_fill(self):
        """Translation should cascade (first non-null wins)."""
        # This would be tested in integration tests with actual Neo4j
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
