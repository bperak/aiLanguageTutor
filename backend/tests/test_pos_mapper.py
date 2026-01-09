"""
Tests for POS Mapper: UniDic normalization and mapping
"""

import pytest

from app.services.lexical_network.pos_mapper import (
    parse_unidic_pos,
    map_lee_pos_to_unidic,
    map_matsushita_pos_to_unidic,
    get_pos_priority,
    should_update_canonical_pos,
)


class TestParseUnidicPos:
    """Test parsing UniDic-style POS strings."""
    
    def test_parse_full_hierarchy(self):
        """Test parsing full 4-level hierarchy."""
        result = parse_unidic_pos("名詞-普通名詞-一般")
        assert result["pos1"] == "名詞"
        assert result["pos2"] == "普通名詞"
        assert result["pos3"] == "一般"
        assert result["pos4"] is None
        assert result["pos_primary_norm"] == "名詞"
    
    def test_parse_3_level(self):
        """Test parsing 3-level hierarchy."""
        result = parse_unidic_pos("形容詞-一般")
        assert result["pos1"] == "形容詞"
        assert result["pos2"] == "一般"
        assert result["pos3"] is None
        assert result["pos4"] is None
        assert result["pos_primary_norm"] == "形容詞"
    
    def test_parse_2_level(self):
        """Test parsing 2-level hierarchy."""
        result = parse_unidic_pos("形状詞-タリ")
        assert result["pos1"] == "形状詞"
        assert result["pos2"] == "タリ"
        assert result["pos_primary_norm"] == "形状詞"
    
    def test_parse_empty(self):
        """Test parsing empty string."""
        result = parse_unidic_pos("")
        assert result["pos1"] is None
        assert result["pos_primary_norm"] is None
    
    def test_parse_none(self):
        """Test parsing None."""
        result = parse_unidic_pos(None)
        assert result["pos1"] is None


class TestMapLeePosToUnidic:
    """Test mapping Lee POS to UniDic format."""
    
    def test_map_i_adjective(self):
        """Test mapping イ形容詞."""
        result = map_lee_pos_to_unidic("イ形容詞")
        assert result["pos1"] == "形容詞"
        assert result["pos2"] == "一般"
        assert result["pos_primary_norm"] == "形容詞"
    
    def test_map_na_adjective(self):
        """Test mapping ナ形容詞."""
        result = map_lee_pos_to_unidic("ナ形容詞")
        assert result["pos1"] == "形状詞"
        assert result["pos2"] == "一般"
        assert result["pos_primary_norm"] == "形状詞"
    
    def test_map_verb_class_1(self):
        """Test mapping 動詞1類."""
        result = map_lee_pos_to_unidic("動詞1類")
        assert result["pos1"] == "動詞"
        assert result["pos2"] == "一般"
        assert result["pos_primary_norm"] == "動詞"
    
    def test_map_noun_na_adjective_mixed(self):
        """Test mapping mixed category 名詞・ナ形容詞."""
        result = map_lee_pos_to_unidic("名詞・ナ形容詞")
        assert result["pos1"] == "名詞"
        assert result["pos2"] == "普通名詞"
        assert result["pos3"] == "形状詞可能"
        assert result["pos_primary_norm"] == "名詞"
    
    def test_map_with_detailed_pos(self):
        """Test mapping with detailed POS (UniDic-style)."""
        result = map_lee_pos_to_unidic("名詞", "名詞-固有名詞-人名-一般")
        assert result["pos1"] == "名詞"
        assert result["pos2"] == "固有名詞"
        assert result["pos3"] == "人名"
        assert result["pos4"] == "一般"
    
    def test_map_unknown_pos(self):
        """Test mapping unknown POS."""
        result = map_lee_pos_to_unidic("未知の品詞")
        assert result["pos1"] == "未知の品詞"
        assert result["pos_primary_norm"] == "未知の品詞"


class TestMapMatsushitaPosToUnidic:
    """Test mapping Matsushita POS to UniDic format."""
    
    def test_map_noun_common(self):
        """Test mapping common noun."""
        result = map_matsushita_pos_to_unidic("名詞-普通名詞-一般")
        assert result["pos1"] == "名詞"
        assert result["pos2"] == "普通名詞"
        assert result["pos3"] == "一般"
        assert result["pos_primary_norm"] == "名詞"
    
    def test_map_adjective(self):
        """Test mapping adjective."""
        result = map_matsushita_pos_to_unidic("形容詞-一般")
        assert result["pos1"] == "形容詞"
        assert result["pos2"] == "一般"
        assert result["pos_primary_norm"] == "形容詞"
    
    def test_map_shape_word(self):
        """Test mapping shape word (na-adjective)."""
        result = map_matsushita_pos_to_unidic("形状詞-一般")
        assert result["pos1"] == "形状詞"
        assert result["pos2"] == "一般"
        assert result["pos_primary_norm"] == "形状詞"
    
    def test_map_non_independent(self):
        """Test mapping non-independent adjective."""
        result = map_matsushita_pos_to_unidic("形容詞-非自立可能")
        assert result["pos1"] == "形容詞"
        assert result["pos2"] == "非自立可能"
        assert result["pos_primary_norm"] == "形容詞"


class TestPosPriority:
    """Test POS source priority."""
    
    def test_priority_order(self):
        """Test priority order is correct."""
        assert get_pos_priority("unidic") == 4
        assert get_pos_priority("matsushita") == 3
        assert get_pos_priority("lee") == 2
        assert get_pos_priority("ai") == 1
    
    def test_priority_unknown(self):
        """Test unknown source has priority 0."""
        assert get_pos_priority("unknown") == 0
    
    def test_priority_case_insensitive(self):
        """Test priority is case-insensitive."""
        assert get_pos_priority("UNIDIC") == 4
        assert get_pos_priority("Lee") == 2


class TestShouldUpdateCanonicalPos:
    """Test logic for updating canonical POS."""
    
    def test_update_when_none(self):
        """Test update when no existing source."""
        assert should_update_canonical_pos(None, "lee") is True
        assert should_update_canonical_pos(None, "ai") is True
    
    def test_update_higher_priority(self):
        """Test update when new source has higher priority."""
        assert should_update_canonical_pos("ai", "lee") is True
        assert should_update_canonical_pos("lee", "matsushita") is True
        assert should_update_canonical_pos("matsushita", "unidic") is True
    
    def test_no_update_lower_priority(self):
        """Test no update when new source has lower priority."""
        assert should_update_canonical_pos("unidic", "matsushita") is False
        assert should_update_canonical_pos("matsushita", "lee") is False
        assert should_update_canonical_pos("lee", "ai") is False
    
    def test_no_update_same_priority(self):
        """Test no update when same priority."""
        assert should_update_canonical_pos("unidic", "unidic") is False
        assert should_update_canonical_pos("lee", "lee") is False
