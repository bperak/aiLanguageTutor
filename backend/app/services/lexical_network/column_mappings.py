"""
Column Mappings for Dictionary Imports

Maps Google Sheets columns to Neo4j Word node properties.
Includes utilities for bunrui parsing and normalization.
"""

from typing import Dict, Optional, Tuple

# ===============================================
# Lee Dictionary (分類語彙表) Column Mapping
# ===============================================

LEE_DICT_URL = "https://docs.google.com/spreadsheets/d/1ephaTB0oA-cUB16Msak34ZW7IxT9SHv1/edit"

LEE_DICT_MAPPING: Dict[str, str] = {
    # Actual column names from the Lee Google Sheet
    "No": "lee_id",
    "Standard orthography (kanji or other) 標準的な表記": "standard_orthography",
    "Katakana reading 読み": "reading_katakana",
    "Level 語彙の難易度": "lee_difficulty_level",
    "品詞1": "pos_primary",
    "品詞2(詳細)": "pos_detailed",
    "語種": "etymology",
    # Alternative/legacy column names for fallback
    "語彙": "standard_orthography",
    "読み": "reading_hiragana",
    "難易度": "lee_difficulty_level",
    "品詞2": "pos_detailed",
    "翻訳": "translation",
    "分類番号": "bunrui_number",
}

# Enhanced Lee mapping including VDRJ fields (if present in sheet)
LEE_DICT_FULL_MAPPING: Dict[str, str] = {
    **LEE_DICT_MAPPING,
    # VDRJ columns (may be prefixed with vdrj_)
    "vdrj_old_jlpt_level": "vdrj_old_jlpt_level",
    "vdrj_word_origin": "vdrj_word_origin",
    "vdrj_frequency": "vdrj_frequency",
    "vdrj_general_learner_level": "vdrj_general_learner_level",
    "vdrj_general_learner_rank": "vdrj_general_learner_rank",
    "vdrj_international_student_level": "vdrj_international_student_level",
    "vdrj_written_japanese_level": "vdrj_written_japanese_level",
    "vdrj_academic_tier": "vdrj_academic_tier",
    "vdrj_usage_range": "vdrj_usage_range",
    "vdrj_literary_keyword": "vdrj_literary_keyword",
    "vdrj_standard_reading": "vdrj_standard_reading",
    "vdrj_dispersion_ranking": "vdrj_dispersion_ranking",
    "vdrj_frequency_ranking": "vdrj_frequency_ranking",
    "vdrj_corrected_frequency": "vdrj_corrected_frequency",
    "vdrj_lexeme": "vdrj_lexeme",
    "vdrj_pos": "vdrj_pos",
    "vdrj_standard_orthography": "vdrj_standard_orthography",
}

# ===============================================
# Matsushita Dictionary Column Mapping
# ===============================================

MATSUSHITA_DICT_URL = "https://docs.google.com/spreadsheets/d/1bKsWwz7G76PQQrv_1HbHz7TfOHWMNOMO/edit"

MATSUSHITA_DICT_MAPPING: Dict[str, str] = {
    "語彙": "standard_orthography",
    "読み": "reading_hiragana",
    "品詞": "pos_primary",
    "意味": "translation",
    "レベル": "matsushita_difficulty",
    "頻度": "matsushita_frequency_rank",
}

# Enhanced Matsushita mapping with etymology
MATSUSHITA_DICT_FULL_MAPPING: Dict[str, str] = {
    **MATSUSHITA_DICT_MAPPING,
    "語種": "etymology",  # Etymology if present
    "頻度順位": "matsushita_frequency_rank",  # Alternative column name
}

# ===============================================
# Difficulty Level Normalization
# ===============================================

# Lee difficulty (6-level system)
LEE_DIFFICULTY_NORMALIZATION: Dict[str, int] = {
    "1.初級前半": 1,
    "2.初級後半": 2,
    "3.中級前半": 3,
    "4.中級後半": 4,
    "5.上級前半": 5,
    "6.上級後半": 6,
    # Numeric strings
    "1": 1,
    "2": 2,
    "3": 3,
    "4": 4,
    "5": 5,
    "6": 6,
}

# Matsushita difficulty (3-level system)
MATSUSHITA_DIFFICULTY_NORMALIZATION: Dict[str, int] = {
    "初級": 1,
    "中級": 3,
    "上級": 5,
    # Numeric strings
    "1": 1,
    "2": 2,
    "3": 3,
}

# Legacy compatibility
DIFFICULTY_NORMALIZATION: Dict[str, int] = {
    **LEE_DIFFICULTY_NORMALIZATION,
    **MATSUSHITA_DIFFICULTY_NORMALIZATION,
}

# ===============================================
# POS Normalization
# ===============================================

POS_NORMALIZATION: Dict[str, str] = {
    # Common variations
    "名詞": "名詞",
    "形容詞": "形容詞",
    "形容動詞": "形容動詞",
    "動詞": "動詞",
    "副詞": "副詞",
    # English equivalents (if present)
    "noun": "名詞",
    "adjective": "形容詞",
    "na-adjective": "形容動詞",
    "verb": "動詞",
    "adverb": "副詞",
}

# ===============================================
# Etymology Normalization
# ===============================================

ETYMOLOGY_NORMALIZATION: Dict[str, str] = {
    # Full forms (Lee, Matsushita)
    "和語": "和語",
    "漢語": "漢語",
    "外来語": "外来語",
    "混種語": "混種語",
    # Abbreviated forms (VDRJ, UNIDIC)
    "和": "和語",
    "漢": "漢語",
    "外": "外来語",
    "混": "混種語",
    # English equivalents
    "native": "和語",
    "sino-japanese": "漢語",
    "sino": "漢語",
    "loanword": "外来語",
    "loan": "外来語",
    "hybrid": "混種語",
}


def normalize_difficulty(value: str) -> int:
    """
    Normalize difficulty level to 1-6 scale.
    
    Args:
        value: Difficulty string from dictionary
        
    Returns:
        Integer 1-6, or 1 as default
    """
    if not value:
        return 1
    
    # Try direct lookup
    if value in DIFFICULTY_NORMALIZATION:
        return DIFFICULTY_NORMALIZATION[value]
    
    # Try numeric conversion
    try:
        num = int(float(value))
        if 1 <= num <= 6:
            return num
    except (ValueError, TypeError):
        pass
    
    # Default to 1
    return 1


def normalize_pos(value: str) -> str:
    """
    Normalize POS tag to standard format.
    
    Args:
        value: POS string from dictionary
        
    Returns:
        Normalized POS string
    """
    if not value:
        return "名詞"  # Default
    
    # Try direct lookup
    if value in POS_NORMALIZATION:
        return POS_NORMALIZATION[value]
    
    # Return as-is if already in Japanese format
    return value


def normalize_etymology(value: str, source: Optional[str] = None) -> Tuple[str, str]:
    """
    Normalize etymology to standard format and track source.
    
    Args:
        value: Etymology string from dictionary
        source: Source identifier ("lee", "matsushita", "vdrj", "unidic")
        
    Returns:
        Tuple of (normalized_value, source)
    """
    if not value:
        return ("", source or "")
    
    # Normalize the value
    normalized = ETYMOLOGY_NORMALIZATION.get(value, value)
    
    # Track source if provided
    etymology_source = source or ""
    
    return (normalized, etymology_source)


def normalize_lee_difficulty(value: str) -> int:
    """
    Normalize Lee difficulty level to 1-6 scale.
    
    Args:
        value: Difficulty string from Lee dictionary
        
    Returns:
        Integer 1-6, or 1 as default
    """
    if not value:
        return 1
    
    # Try direct lookup
    if value in LEE_DIFFICULTY_NORMALIZATION:
        return LEE_DIFFICULTY_NORMALIZATION[value]
    
    # Try numeric conversion
    try:
        num = int(float(value))
        if 1 <= num <= 6:
            return num
    except (ValueError, TypeError):
        pass
    
    # Default to 1
    return 1


def normalize_matsushita_difficulty(value: str) -> int:
    """
    Normalize Matsushita difficulty level to 1-3 scale.
    
    Args:
        value: Difficulty string from Matsushita dictionary
        
    Returns:
        Integer 1, 2, or 3 (mapped from 初級/中級/上級)
    """
    if not value:
        return 1
    
    # Try direct lookup
    if value in MATSUSHITA_DIFFICULTY_NORMALIZATION:
        return MATSUSHITA_DIFFICULTY_NORMALIZATION[value]
    
    # Try numeric conversion
    try:
        num = int(float(value))
        if 1 <= num <= 3:
            return num
    except (ValueError, TypeError):
        pass
    
    # Default to 1
    return 1


def parse_bunrui_hierarchy(bunrui_number: str) -> Dict[str, Optional[str]]:
    """
    Parse bunrui number into hierarchy levels.
    
    Examples:
        "1.1030.01" -> {class: "1", division: "1.1", section: "1.10", subsection: "1.1030"}
        "11030" -> {class: "1", division: "1.1", section: "1.10", subsection: "1.1030"}
        "1.1" -> {class: "1", division: "1.1", section: None, subsection: None}
    
    Args:
        bunrui_number: Full bunrui classification code
        
    Returns:
        Dictionary with parsed hierarchy levels
    """
    if not bunrui_number:
        return {}
    
    bunrui_str = str(bunrui_number).strip()
    result = {"bunrui_number": bunrui_str}
    
    # Handle different formats
    if "." in bunrui_str:
        # Format with dots: "1.1030.01"
        parts = bunrui_str.split(".")
        if len(parts) >= 1 and parts[0]:
            result["bunrui_class"] = parts[0]  # "1", "2", "3", or "4"
        
        if len(parts) >= 2 and parts[1]:
            # Division is first digit of second part
            if len(parts[1]) >= 1:
                result["bunrui_division"] = f"{parts[0]}.{parts[1][0]}"
            # Section is first two digits
            if len(parts[1]) >= 2:
                result["bunrui_section"] = f"{parts[0]}.{parts[1][:2]}"
            # Full subsection
            result["bunrui_subsection"] = f"{parts[0]}.{parts[1]}"
    else:
        # Compressed format: "11030"
        if len(bunrui_str) >= 1:
            result["bunrui_class"] = bunrui_str[0]
        if len(bunrui_str) >= 2:
            result["bunrui_division"] = f"{bunrui_str[0]}.{bunrui_str[1]}"
        if len(bunrui_str) >= 3:
            result["bunrui_section"] = f"{bunrui_str[0]}.{bunrui_str[1:3]}"
        if len(bunrui_str) >= 5:
            result["bunrui_subsection"] = f"{bunrui_str[0]}.{bunrui_str[1:5]}"
    
    return result
