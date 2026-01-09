"""
Lexical Relation Type Definitions

Defines all valid lexical relation types with their metadata, applicable POS,
and linguistic properties.
"""

from typing import Dict, List, Optional

# ===============================================
# POS-to-Relations Mapping
# ===============================================

NOUN_RELATIONS = [
    "SYNONYM",
    "ANTONYM",
    "HYPERNYM",
    "HYPONYM",
    "CO_HYPONYM",
    "MERONYM",
    "HOLONYM",
    "INSTANCE_OF",
    "COLLECTIVE",
]

ADJECTIVE_RELATIONS = [
    "SYNONYM",
    "NEAR_SYNONYM",
    "GRADABLE_ANTONYM",
    "COMPLEMENTARY_ANTONYM",
    "SCALAR_INTENSITY",
    "REGISTER_VARIANT",
    "DOMAIN_VARIANT",
]

VERB_RELATIONS = [
    "SYNONYM",
    "ANTONYM",
    "CONVERSE",
    "TROPONYM",
    "ENTAILMENT",
    "CAUSATIVE_PAIR",
    "ASPECT_PAIR",
    "HONORIFIC_VARIANT",
]

ADVERB_RELATIONS = [
    "SYNONYM",
    "ANTONYM",
    "INTENSITY_SCALE",
    "TEMPORAL_PAIR",
    "REGISTER_VARIANT",
]

# Universal relations that apply to all POS
UNIVERSAL_RELATIONS = [
    "SYNONYM",
    "ANTONYM",
    "NEAR_SYNONYM",
    "REGISTER_VARIANT",
]

POS_TO_RELATIONS: Dict[str, List[str]] = {
    "名詞": NOUN_RELATIONS,
    "形容詞": ADJECTIVE_RELATIONS,
    "形容動詞": ADJECTIVE_RELATIONS,  # Legacy format
    "形状詞": ADJECTIVE_RELATIONS,  # UniDic canonical format for na-adjectives
    "動詞": VERB_RELATIONS,
    "副詞": ADVERB_RELATIONS,
}

# ===============================================
# Symmetric vs Asymmetric Relations
# ===============================================

SYMMETRIC_RELATIONS = {
    "SYNONYM",
    "NEAR_SYNONYM",
    "ANTONYM",
    "GRADABLE_ANTONYM",
    "COMPLEMENTARY_ANTONYM",
    "CO_HYPONYM",
    "CONVERSE",
    "CAUSATIVE_PAIR",
    "ASPECT_PAIR",
    "TEMPORAL_PAIR",
}

ASYMMETRIC_RELATIONS = {
    "HYPERNYM",  # child → parent
    "HYPONYM",  # parent → child
    "MERONYM",  # part → whole
    "HOLONYM",  # whole → part
    "INSTANCE_OF",  # instance → class
    "TROPONYM",  # specific → general manner
    "ENTAILMENT",  # action → consequence
    "SCALAR_INTENSITY",  # lower → higher
    "INTENSITY_SCALE",  # lower → higher
    "HONORIFIC_VARIANT",  # plain → respectful
    "COLLECTIVE",  # individual → group
}

# ===============================================
# Relation Type Definitions
# ===============================================

RELATION_DEFINITIONS: Dict[str, Dict] = {
    # Universal Relations
    "SYNONYM": {
        "ja": "類義語",
        "en": "Synonym",
        "description": "Words with the same or very similar meaning",
        "example_ja": "車 ↔ 自動車",
        "symmetric": True,
        "applicable_pos": ["名詞", "形容詞", "形容動詞", "形状詞", "動詞", "副詞"],
    },
    "ANTONYM": {
        "ja": "対義語",
        "en": "Antonym",
        "description": "Words with opposite meanings",
        "example_ja": "男 ↔ 女, 大きい ↔ 小さい",
        "symmetric": True,
        "applicable_pos": ["名詞", "形容詞", "形容動詞", "形状詞", "動詞", "副詞"],
    },
    "NEAR_SYNONYM": {
        "ja": "準類義語",
        "en": "Near-synonym",
        "description": "Words with similar meaning but subtle differences",
        "example_ja": "美しい ≈ 綺麗",
        "symmetric": True,
        "applicable_pos": ["形容詞", "形容動詞", "動詞", "副詞"],
    },
    "REGISTER_VARIANT": {
        "ja": "位相変異",
        "en": "Register Variant",
        "description": "Same meaning, different formality level",
        "example_ja": "うまい (俗) ↔ おいしい (標準)",
        "symmetric": True,
        "applicable_pos": ["形容詞", "形容動詞", "動詞", "副詞"],
    },
    
    # Noun Relations
    "HYPERNYM": {
        "ja": "上位語",
        "en": "Hypernym",
        "description": "More general category (parent)",
        "example_ja": "犬 → 動物",
        "symmetric": False,
        "inverse": "HYPONYM",
        "applicable_pos": ["名詞"],
    },
    "HYPONYM": {
        "ja": "下位語",
        "en": "Hyponym",
        "description": "More specific type (child)",
        "example_ja": "動物 → 犬",
        "symmetric": False,
        "inverse": "HYPERNYM",
        "applicable_pos": ["名詞"],
    },
    "CO_HYPONYM": {
        "ja": "並列語",
        "en": "Co-hyponym",
        "description": "Words sharing the same hypernym",
        "example_ja": "りんご ↔ みかん (both are 果物)",
        "symmetric": True,
        "applicable_pos": ["名詞"],
    },
    "MERONYM": {
        "ja": "部分語",
        "en": "Meronym",
        "description": "Part-of relationship",
        "example_ja": "指 → 手",
        "symmetric": False,
        "inverse": "HOLONYM",
        "applicable_pos": ["名詞"],
    },
    "HOLONYM": {
        "ja": "全体語",
        "en": "Holonym",
        "description": "Contains-part relationship",
        "example_ja": "手 → 指",
        "symmetric": False,
        "inverse": "MERONYM",
        "applicable_pos": ["名詞"],
    },
    "INSTANCE_OF": {
        "ja": "事例",
        "en": "Instance Of",
        "description": "Specific named entity → general class",
        "example_ja": "富士山 → 山",
        "symmetric": False,
        "applicable_pos": ["名詞"],
    },
    "COLLECTIVE": {
        "ja": "集合語",
        "en": "Collective",
        "description": "Individual → group",
        "example_ja": "木 → 森",
        "symmetric": False,
        "applicable_pos": ["名詞"],
    },
    
    # Adjective Relations
    "GRADABLE_ANTONYM": {
        "ja": "程度対義語",
        "en": "Gradable Antonym",
        "description": "Opposites on a continuous scale",
        "example_ja": "大きい ↔ 小さい",
        "symmetric": True,
        "applicable_pos": ["形容詞", "形容動詞", "形状詞"],
    },
    "COMPLEMENTARY_ANTONYM": {
        "ja": "相補対義語",
        "en": "Complementary Antonym",
        "description": "Binary opposites (no middle ground)",
        "example_ja": "生きている ↔ 死んでいる",
        "symmetric": True,
        "applicable_pos": ["形容詞", "形容動詞", "形状詞"],
    },
    "SCALAR_INTENSITY": {
        "ja": "程度関係",
        "en": "Scalar Intensity",
        "description": "Ordered by intensity on same dimension",
        "example_ja": "暖かい (0.6) < 熱い (0.9)",
        "symmetric": False,
        "applicable_pos": ["形容詞", "形容動詞", "形状詞"],
    },
    "DOMAIN_VARIANT": {
        "ja": "領域変異",
        "en": "Domain Variant",
        "description": "Same word used in different semantic domains",
        "example_ja": "高い (値段) ↔ 高い (身長)",
        "symmetric": True,
        "applicable_pos": ["形容詞", "形容動詞", "形状詞"],
    },
    
    # Verb Relations
    "CONVERSE": {
        "ja": "逆関係",
        "en": "Converse",
        "description": "Same event from different perspectives",
        "example_ja": "教える ↔ 習う, 貸す ↔ 借りる",
        "symmetric": True,
        "applicable_pos": ["動詞"],
    },
    "TROPONYM": {
        "ja": "様態動詞",
        "en": "Troponym",
        "description": "More specific manner of action",
        "example_ja": "歩く → 走る → 駆ける",
        "symmetric": False,
        "applicable_pos": ["動詞"],
    },
    "ENTAILMENT": {
        "ja": "含意関係",
        "en": "Entailment",
        "description": "Action X implies consequence Y",
        "example_ja": "殺す → 死ぬ",
        "symmetric": False,
        "applicable_pos": ["動詞"],
    },
    "CAUSATIVE_PAIR": {
        "ja": "使役対",
        "en": "Causative Pair",
        "description": "Intransitive/transitive or causative pairs",
        "example_ja": "開く (自動) ↔ 開ける (他動)",
        "symmetric": True,
        "applicable_pos": ["動詞"],
    },
    "ASPECT_PAIR": {
        "ja": "相対",
        "en": "Aspect Pair",
        "description": "Different aspectual forms",
        "example_ja": "知る ↔ 知っている",
        "symmetric": True,
        "applicable_pos": ["動詞"],
    },
    "HONORIFIC_VARIANT": {
        "ja": "敬語変異",
        "en": "Honorific Variant",
        "description": "Different politeness levels",
        "example_ja": "食べる → 召し上がる",
        "symmetric": False,
        "applicable_pos": ["動詞"],
    },
    
    # Adverb Relations
    "INTENSITY_SCALE": {
        "ja": "程度尺度",
        "en": "Intensity Scale",
        "description": "Ordered by degree/intensity",
        "example_ja": "少し < かなり < とても < 非常に",
        "symmetric": False,
        "applicable_pos": ["副詞"],
    },
    "TEMPORAL_PAIR": {
        "ja": "時間対",
        "en": "Temporal Pair",
        "description": "Temporal opposition",
        "example_ja": "もう ↔ まだ",
        "symmetric": True,
        "applicable_pos": ["副詞"],
    },
}

# ===============================================
# Helper Functions
# ===============================================


def get_valid_relations_for_pos(pos: str) -> List[str]:
    """
    Get valid relation types for a given POS.
    
    Args:
        pos: Part of speech (名詞, 形容詞, 形容動詞, 形状詞, 動詞, 副詞)
            Supports both legacy (形容動詞) and canonical UniDic (形状詞) formats
        
    Returns:
        List of valid relation type strings
    """
    return POS_TO_RELATIONS.get(pos, UNIVERSAL_RELATIONS)


def is_symmetric_relation(relation_type: str) -> bool:
    """
    Check if a relation type is symmetric (bidirectional).
    
    Args:
        relation_type: Relation type string
        
    Returns:
        True if symmetric, False if asymmetric
    """
    return relation_type in SYMMETRIC_RELATIONS


def get_inverse_relation(relation_type: str) -> Optional[str]:
    """
    Get the inverse of an asymmetric relation.
    
    Args:
        relation_type: Relation type string
        
    Returns:
        Inverse relation type or None if no inverse exists
    """
    meta = RELATION_DEFINITIONS.get(relation_type, {})
    return meta.get("inverse")


def validate_relation_for_pos(relation_type: str, pos: str) -> bool:
    """
    Validate that a relation type is valid for the given POS.
    
    Args:
        relation_type: Relation type string
        pos: Part of speech
        
    Returns:
        True if valid, False otherwise
    """
    valid_relations = get_valid_relations_for_pos(pos)
    return relation_type in valid_relations


def get_relation_metadata(relation_type: str) -> Optional[Dict]:
    """
    Get full metadata for a relation type.
    
    Args:
        relation_type: Relation type string
        
    Returns:
        Dictionary with metadata or None if not found
    """
    return RELATION_DEFINITIONS.get(relation_type)
