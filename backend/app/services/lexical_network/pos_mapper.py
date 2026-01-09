"""
POS Mapper: Normalize POS tags from Lee/Matsushita to UniDic canonical format

Maps various POS representations to UniDic-style hierarchical POS (pos1-pos4)
and derives normalized primary POS for app use.
"""

from typing import Dict, Optional, Tuple


# ===============================================
# UniDic Primary POS Categories
# ===============================================

UNIDIC_PRIMARY_POS = {
    "名詞": "noun",
    "動詞": "verb",
    "形容詞": "i-adjective",
    "形状詞": "na-adjective",
    "副詞": "adverb",
    "助詞": "particle",
    "助動詞": "auxiliary",
    "接頭辞": "prefix",
    "接尾辞": "suffix",
    "記号": "symbol",
    "感動詞": "interjection",
    "連体詞": "adnominal",
    "接続詞": "conjunction",
    "代名詞": "pronoun",
    "フィラー": "filler",
    "その他": "other",
}


# ===============================================
# Lee POS → UniDic Mapping
# ===============================================

LEE_TO_UNIDIC_MAPPING: Dict[str, Dict[str, str]] = {
    # Primary POS mappings
    "イ形容詞": {
        "pos1": "形容詞",
        "pos2": "一般",
        "pos3": None,
        "pos4": None,
        "pos_primary_norm": "形容詞",
    },
    "ナ形容詞": {
        "pos1": "形状詞",
        "pos2": "一般",
        "pos3": None,
        "pos4": None,
        "pos_primary_norm": "形状詞",
    },
    "名詞": {
        "pos1": "名詞",
        "pos2": "普通名詞",
        "pos3": "一般",
        "pos4": None,
        "pos_primary_norm": "名詞",
    },
    "動詞1類": {
        "pos1": "動詞",
        "pos2": "一般",
        "pos3": None,
        "pos4": None,
        "pos_primary_norm": "動詞",
    },
    "動詞2類": {
        "pos1": "動詞",
        "pos2": "一般",
        "pos3": None,
        "pos4": None,
        "pos_primary_norm": "動詞",
    },
    "動詞3類": {
        "pos1": "動詞",
        "pos2": "一般",
        "pos3": None,
        "pos4": None,
        "pos_primary_norm": "動詞",
    },
    "副詞": {
        "pos1": "副詞",
        "pos2": "一般",
        "pos3": None,
        "pos4": None,
        "pos_primary_norm": "副詞",
    },
    "代名詞": {
        "pos1": "代名詞",
        "pos2": None,
        "pos3": None,
        "pos4": None,
        "pos_primary_norm": "代名詞",
    },
    "接頭辞": {
        "pos1": "接頭辞",
        "pos2": None,
        "pos3": None,
        "pos4": None,
        "pos_primary_norm": "接頭辞",
    },
    "接尾辞": {
        "pos1": "接尾辞",
        "pos2": "名詞的",
        "pos3": "一般",
        "pos4": None,
        "pos_primary_norm": "接尾辞",
    },
    "接続詞": {
        "pos1": "接続詞",
        "pos2": None,
        "pos3": None,
        "pos4": None,
        "pos_primary_norm": "接続詞",
    },
    "連体詞": {
        "pos1": "連体詞",
        "pos2": None,
        "pos3": None,
        "pos4": None,
        "pos_primary_norm": "連体詞",
    },
    "感動詞": {
        "pos1": "感動詞",
        "pos2": "一般",
        "pos3": None,
        "pos4": None,
        "pos_primary_norm": "感動詞",
    },
    "定型表現": {
        "pos1": "名詞",
        "pos2": "普通名詞",
        "pos3": "一般",
        "pos4": None,
        "pos_primary_norm": "名詞",
    },
    # Mixed categories
    "名詞・ナ形容詞": {
        "pos1": "名詞",
        "pos2": "普通名詞",
        "pos3": "形状詞可能",
        "pos4": None,
        "pos_primary_norm": "名詞",  # Primary is noun, but can function as na-adj
    },
    "副詞・ナ形容詞": {
        "pos1": "副詞",
        "pos2": "一般",
        "pos3": None,
        "pos4": None,
        "pos_primary_norm": "副詞",  # Primary is adverb, but can function as na-adj
    },
    "接頭辞・ナ形容詞": {
        "pos1": "接頭辞",
        "pos2": None,
        "pos3": None,
        "pos4": None,
        "pos_primary_norm": "接頭辞",
    },
    "接頭辞・名詞": {
        "pos1": "接頭辞",
        "pos2": None,
        "pos3": None,
        "pos4": None,
        "pos_primary_norm": "接頭辞",
    },
    "接尾辞・名詞": {
        "pos1": "接尾辞",
        "pos2": "名詞的",
        "pos3": "一般",
        "pos4": None,
        "pos_primary_norm": "接尾辞",
    },
    "感動詞・副詞": {
        "pos1": "感動詞",
        "pos2": "一般",
        "pos3": None,
        "pos4": None,
        "pos_primary_norm": "感動詞",
    },
    "感動詞・接頭辞": {
        "pos1": "感動詞",
        "pos2": "一般",
        "pos3": None,
        "pos4": None,
        "pos_primary_norm": "感動詞",
    },
}


def parse_unidic_pos(pos_string: str) -> Dict[str, Optional[str]]:
    """
    Parse UniDic-style POS string into hierarchical components.
    
    Examples:
        "名詞-普通名詞-一般" -> {pos1: "名詞", pos2: "普通名詞", pos3: "一般", pos4: None}
        "形容詞-一般" -> {pos1: "形容詞", pos2: "一般", pos3: None, pos4: None}
        "形状詞-タリ" -> {pos1: "形状詞", pos2: "タリ", pos3: None, pos4: None}
    
    Args:
        pos_string: UniDic-style POS tag (e.g., "名詞-普通名詞-一般")
        
    Returns:
        Dictionary with pos1, pos2, pos3, pos4, and pos_primary_norm
    """
    if not pos_string:
        return {
            "pos1": None,
            "pos2": None,
            "pos3": None,
            "pos4": None,
            "pos_primary_norm": None,
        }
    
    parts = [p.strip() for p in str(pos_string).split("-") if p.strip()]
    
    result = {
        "pos1": parts[0] if len(parts) > 0 else None,
        "pos2": parts[1] if len(parts) > 1 else None,
        "pos3": parts[2] if len(parts) > 2 else None,
        "pos4": parts[3] if len(parts) > 3 else None,
        "pos_primary_norm": parts[0] if len(parts) > 0 else None,
    }
    
    return result


def map_lee_pos_to_unidic(lee_pos: str, lee_pos_detailed: Optional[str] = None) -> Dict[str, Optional[str]]:
    """
    Map Lee dictionary POS to UniDic canonical format.
    
    Args:
        lee_pos: Lee primary POS (品詞1) - e.g., "イ形容詞", "名詞", "動詞1類"
        lee_pos_detailed: Lee detailed POS (品詞2) - optional, UniDic-style string
        
    Returns:
        Dictionary with pos1, pos2, pos3, pos4, and pos_primary_norm
    """
    if not lee_pos:
        return {
            "pos1": None,
            "pos2": None,
            "pos3": None,
            "pos4": None,
            "pos_primary_norm": None,
        }
    
    # If detailed POS is available and looks like UniDic format, use it
    if lee_pos_detailed and "-" in lee_pos_detailed:
        # Parse the detailed POS (it's already UniDic-style)
        parsed = parse_unidic_pos(lee_pos_detailed)
        # But override pos_primary_norm from the primary POS if it's a mixed category
        if "・" in lee_pos:
            # Mixed category - use mapping for primary_norm
            if lee_pos in LEE_TO_UNIDIC_MAPPING:
                parsed["pos_primary_norm"] = LEE_TO_UNIDIC_MAPPING[lee_pos]["pos_primary_norm"]
        return parsed
    
    # Use direct mapping for primary POS
    if lee_pos in LEE_TO_UNIDIC_MAPPING:
        return LEE_TO_UNIDIC_MAPPING[lee_pos].copy()
    
    # Fallback: try to parse as UniDic-style if it contains "-"
    if "-" in lee_pos:
        return parse_unidic_pos(lee_pos)
    
    # Unknown POS - return minimal mapping
    return {
        "pos1": lee_pos,
        "pos2": None,
        "pos3": None,
        "pos4": None,
        "pos_primary_norm": lee_pos,
    }


def map_matsushita_pos_to_unidic(matsushita_pos: str) -> Dict[str, Optional[str]]:
    """
    Map Matsushita dictionary POS to UniDic canonical format.
    
    Matsushita POS is already in UniDic format, so we just parse it.
    
    Args:
        matsushita_pos: Matsushita POS (already UniDic-style) - e.g., "名詞-普通名詞-一般"
        
    Returns:
        Dictionary with pos1, pos2, pos3, pos4, and pos_primary_norm
    """
    return parse_unidic_pos(matsushita_pos)


def get_pos_priority(pos_source: str) -> int:
    """
    Get priority for POS source (higher = more authoritative).
    
    Priority order:
    1. unidic (highest - direct morphological analysis)
    2. matsushita (UniDic-style from authoritative dictionary)
    3. lee (mapped from Lee's classification)
    4. ai (lowest - AI gap-fill)
    
    Args:
        pos_source: Source identifier
        
    Returns:
        Priority integer (1-4)
    """
    priority_map = {
        "unidic": 4,
        "matsushita": 3,
        "lee": 2,
        "ai": 1,
    }
    return priority_map.get(pos_source.lower(), 0)


def should_update_canonical_pos(
    existing_source: Optional[str],
    new_source: str,
) -> bool:
    """
    Determine if canonical POS should be updated based on source priority.
    
    Args:
        existing_source: Current pos_source value
        new_source: Proposed new pos_source
        
    Returns:
        True if new_source has higher priority than existing_source
    """
    if not existing_source:
        return True
    
    existing_priority = get_pos_priority(existing_source)
    new_priority = get_pos_priority(new_source)
    
    return new_priority > existing_priority
