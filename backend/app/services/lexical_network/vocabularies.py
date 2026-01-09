"""
Controlled Vocabularies for Lexical Relations

Defines domain vocabularies, context vocabularies, register vocabularies,
and scale dimensions used in lexical relation feature vectors.
"""

from typing import Dict, List

# ===============================================
# Domain Vocabulary
# ===============================================

DOMAIN_VOCABULARY = [
    "aesthetics",
    "cleanliness",
    "evaluation",
    "emotion",
    "social",
    "ethics",
    "intensity",
    "quality",
    "taste_smell",
    "sound",
    "visual",
    "physical",
    "temporal",
    "spatial",
    "mental",
    "abstract",
    "concrete",
    "natural",
    "artificial",
    "human",
    "animal",
    "plant",
    "object",
    "action",
    "state",
]

# ===============================================
# Context Vocabulary
# ===============================================

CONTEXT_VOCABULARY = [
    "people_appearance",
    "people_character",
    "places_rooms",
    "nature_scenery",
    "art_design",
    "food_taste",
    "sound_music",
    "behavior_act",
    "writing_language",
    "events_experiences",
    "objects_products",
    "performance_result",
    "weather_seasons",
    "ceremony_formality",
    "fashion_style",
    "emotion_expression",
    "thought_opinion",
    "communication",
    "movement_travel",
    "work_business",
    "education_learning",
    "health_medical",
    "family_relationships",
    "time_period",
    "quantity_amount",
]

# ===============================================
# Register Vocabulary
# ===============================================

REGISTER_VOCABULARY = [
    "neutral",
    "colloquial",
    "formal",
    "literary",
    "slang",
]

# ===============================================
# Scale Dimensions
# ===============================================

SCALE_DIMENSIONS: Dict[str, Dict] = {
    "intensity": {
        "ja": "強度",
        "en": "Intensity",
        "examples": ["弱い", "中程度", "強い", "激しい"],
        "applicable_pos": ["形容詞", "形容動詞", "副詞"],
    },
    "size": {
        "ja": "大きさ",
        "en": "Size",
        "examples": ["小さい", "中くらい", "大きい", "巨大な"],
        "applicable_pos": ["形容詞", "形容動詞"],
    },
    "temperature": {
        "ja": "温度",
        "en": "Temperature",
        "examples": ["冷たい", "涼しい", "暖かい", "熱い"],
        "applicable_pos": ["形容詞", "形容動詞"],
    },
    "speed": {
        "ja": "速度",
        "en": "Speed",
        "examples": ["遅い", "普通", "速い", "超速い"],
        "applicable_pos": ["形容詞", "形容動詞", "副詞"],
    },
    "frequency": {
        "ja": "頻度",
        "en": "Frequency",
        "examples": ["稀に", "時々", "よく", "いつも"],
        "applicable_pos": ["副詞"],
    },
    "degree": {
        "ja": "程度",
        "en": "Degree",
        "examples": ["少し", "まあまあ", "かなり", "とても", "非常に", "極めて"],
        "applicable_pos": ["副詞"],
    },
    "age": {
        "ja": "年齢",
        "en": "Age",
        "examples": ["若い", "中年", "年老いた"],
        "applicable_pos": ["形容詞", "形容動詞"],
    },
    "quality": {
        "ja": "品質",
        "en": "Quality",
        "examples": ["悪い", "普通", "良い", "素晴らしい"],
        "applicable_pos": ["形容詞", "形容動詞"],
    },
    "brightness": {
        "ja": "明るさ",
        "en": "Brightness",
        "examples": ["暗い", "薄暗い", "明るい", "眩しい"],
        "applicable_pos": ["形容詞", "形容動詞"],
    },
    "weight": {
        "ja": "重さ",
        "en": "Weight",
        "examples": ["軽い", "普通", "重い", "非常に重い"],
        "applicable_pos": ["形容詞", "形容動詞"],
    },
}

# ===============================================
# Validation Functions
# ===============================================


def validate_domain_tag(tag: str) -> bool:
    """Check if domain tag is in controlled vocabulary."""
    return tag in DOMAIN_VOCABULARY


def validate_context_tag(tag: str) -> bool:
    """Check if context tag is in controlled vocabulary."""
    return tag in CONTEXT_VOCABULARY


def validate_register_tag(tag: str) -> bool:
    """Check if register tag is in controlled vocabulary."""
    return tag in REGISTER_VOCABULARY


def validate_scale_dimension(dimension: str) -> bool:
    """Check if scale dimension is defined."""
    return dimension in SCALE_DIMENSIONS


def get_scale_dimension_for_pos(dimension: str, pos: str) -> bool:
    """Check if scale dimension is applicable to POS."""
    if dimension not in SCALE_DIMENSIONS:
        return False
    applicable = SCALE_DIMENSIONS[dimension].get("applicable_pos", [])
    return pos in applicable


def validate_aligned_arrays(tags: List[str], weights: List[float]) -> bool:
    """
    Validate that tags and weights arrays are aligned (same length).
    
    Args:
        tags: List of tag strings
        weights: List of weight floats
        
    Returns:
        True if aligned, False otherwise
    """
    if len(tags) != len(weights):
        return False
    
    # Validate all weights are in [0.0, 1.0]
    for weight in weights:
        if not (0.0 <= weight <= 1.0):
            return False
    
    return True
