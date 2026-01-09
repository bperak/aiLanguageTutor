"""
Few-Shot Examples for Lexical Relation Generation

Curated examples for each POS and relation type to guide AI generation.
"""

from typing import Dict, List

# ===============================================
# System Prompt
# ===============================================

SYSTEM_PROMPT = """You are an expert Japanese lexicographer and computational linguist.
Your task is to identify and describe lexical relations between Japanese words.

CRITICAL RULES:
1. Output ONLY valid JSON arrays - no other text
2. Use EXACT relation types from the provided vocabulary
3. Respect POS-specific relation constraints
4. Provide evidence-based confidence scores (0.0-1.0)
5. Include nuanced distinctions in English explanations
6. For scalar relations, provide accurate scale positions (0.0-1.0)
7. For verb pairs, accurately identify transitivity and aspect
8. Consider register (neutral/colloquial/formal/literary/slang)
9. Do not hallucinate relations - only include high-confidence ones
10. Temperature is 0.0 - be deterministic and consistent"""

# ===============================================
# POS-Specific Instructions
# ===============================================

POS_INSTRUCTIONS: Dict[str, str] = {
    "形容詞": """
ADJECTIVE-SPECIFIC RULES:
- GRADABLE_ANTONYM: Identify the scale dimension (size, temperature, etc.)
- SCALAR_INTENSITY: Order from low to high intensity, provide scale_position (0.0-1.0)
- NEAR_SYNONYM: Explain subtle distinctions (register, domain, connotation)
- Consider i-adjective (形容詞) vs na-adjective (形容動詞) compatibility
- Examples:
  - GRADABLE_ANTONYM: 大きい ↔ 小さい (scale: size)
  - SCALAR_INTENSITY: 暖かい (0.6) < 熱い (0.9) (scale: temperature)
  - NEAR_SYNONYM: 美しい ≈ 綺麗 (美しい is more literary)""",
    
    "形容動詞": """
NA-ADJECTIVE-SPECIFIC RULES:
- Same rules as 形容詞 (i-adjectives)
- Note: 形容動詞 require な particle when modifying nouns
- Examples:
  - GRADABLE_ANTONYM: 静かな ↔ 賑やかな (scale: noise level)
  - NEAR_SYNONYM: 綺麗な ≈ 美しい (綺麗な is more common in speech)""",
    
    "動詞": """
VERB-SPECIFIC RULES:
- CONVERSE: Same event from different perspectives (教える ↔ 習う)
- CAUSATIVE_PAIR: Identify transitivity (自動詞/他動詞 pairs like 開く/開ける)
- TROPONYM: Manner of action (歩く → 走る → 駆ける)
- ENTAILMENT: X doing action implies Y state (殺す → 死ぬ)
- ASPECT_PAIR: Punctual vs stative (知る vs 知っている)
- HONORIFIC_VARIANT: Politeness levels (食べる → 召し上がる)
- Include transitivity_source/target for all pairs""",
    
    "名詞": """
NOUN-SPECIFIC RULES:
- HYPERNYM/HYPONYM: Build taxonomic hierarchies (犬 → 動物)
- MERONYM/HOLONYM: Part-whole relationships (指 → 手)
- CO_HYPONYM: Siblings sharing same parent (りんご ↔ みかん, both 果物)
- INSTANCE_OF: Named entity → class (富士山 → 山)
- COLLECTIVE: Individual → group (木 → 森)""",
    
    "副詞": """
ADVERB-SPECIFIC RULES:
- INTENSITY_SCALE: Order by degree (少し < かなり < とても < 非常に)
- TEMPORAL_PAIR: Temporal opposition (もう ↔ まだ)
- Consider which verbs/adjectives they typically modify""",
}

# ===============================================
# Few-Shot Examples by POS and Relation Type
# ===============================================

ADJECTIVE_EXAMPLES: Dict[str, List[Dict]] = {
    "GRADABLE_ANTONYM": [
        {
            "source_word": "大きい",
            "target_orthography": "小さい",
            "target_reading": "ちいさい",
            "target_word": "小さい",  # Backward compatibility
            "relation_type": "GRADABLE_ANTONYM",
            "relation_category": "adjective",
            "weight": 0.95,
            "confidence": 0.98,
            "is_symmetric": True,
            "shared_meaning_en": "size dimension",
            "distinction_en": "Opposite ends of the size scale",
            "usage_context_en": "大きい for large objects/size, 小さい for small objects/size",
            "when_prefer_source_en": "When describing large size",
            "when_prefer_target_en": "When describing small size",
            "register_source": "neutral",
            "register_target": "neutral",
            "formality_difference": "same",
            "scale_dimension": "size",
            "scale_position_source": 0.8,
            "scale_position_target": 0.2,
            "domain_tags": ["physical"],
            "domain_weights": [0.9],
            "context_tags": ["objects_products"],
            "context_weights": [0.8],
        }
    ],
    "SCALAR_INTENSITY": [
        {
            "source_word": "暖かい",
            "target_orthography": "熱い",
            "target_reading": "あつい",
            "target_word": "熱い",  # Backward compatibility
            "relation_type": "SCALAR_INTENSITY",
            "relation_category": "adjective",
            "weight": 0.85,
            "confidence": 0.92,
            "is_symmetric": False,
            "shared_meaning_en": "high temperature",
            "distinction_en": "熱い is more intense than 暖かい on temperature scale",
            "usage_context_en": "暖かい for pleasant warmth, 熱い for hot/uncomfortable heat",
            "when_prefer_source_en": "When describing pleasant warmth",
            "when_prefer_target_en": "When describing intense heat",
            "register_source": "neutral",
            "register_target": "neutral",
            "formality_difference": "same",
            "scale_dimension": "temperature",
            "scale_position_source": 0.6,
            "scale_position_target": 0.9,
            "domain_tags": ["physical"],
            "domain_weights": [0.8],
            "context_tags": ["weather_seasons"],
            "context_weights": [0.7],
        }
    ],
    "NEAR_SYNONYM": [
        {
            "source_word": "美しい",
            "target_orthography": "綺麗",
            "target_reading": "きれい",
            "target_word": "綺麗",  # Backward compatibility
            "relation_type": "NEAR_SYNONYM",
            "relation_category": "adjective",
            "weight": 0.88,
            "confidence": 0.90,
            "is_symmetric": True,
            "shared_meaning_en": "beautiful, pretty",
            "distinction_en": "美しい is more literary/poetic, 綺麗 is more common in speech",
            "usage_context_en": "Both describe beauty, but 美しい is more formal/literary",
            "when_prefer_source_en": "In literary or formal contexts",
            "when_prefer_target_en": "In everyday speech",
            "register_source": "literary",
            "register_target": "neutral",
            "formality_difference": "source_higher",
            "domain_tags": ["aesthetics"],
            "domain_weights": [0.9],
            "context_tags": ["people_appearance", "nature_scenery"],
            "context_weights": [0.8, 0.7],
        }
    ],
}

VERB_EXAMPLES: Dict[str, List[Dict]] = {
    "CAUSATIVE_PAIR": [
        {
            "source_word": "開く",
            "target_orthography": "開ける",
            "target_reading": "あける",
            "target_word": "開ける",  # Backward compatibility
            "relation_type": "CAUSATIVE_PAIR",
            "relation_category": "verb",
            "weight": 0.95,
            "confidence": 0.99,
            "is_symmetric": True,
            "shared_meaning_en": "opening action",
            "distinction_en": "開く is intransitive (door opens), 開ける is transitive (someone opens door)",
            "usage_context_en": "開く for automatic opening, 開ける for intentional opening",
            "when_prefer_source_en": "When describing automatic opening (intransitive)",
            "when_prefer_target_en": "When describing intentional opening (transitive)",
            "register_source": "neutral",
            "register_target": "neutral",
            "formality_difference": "same",
            "transitivity_source": "intransitive",
            "transitivity_target": "transitive",
            "domain_tags": ["action"],
            "domain_weights": [0.9],
            "context_tags": ["behavior_act"],
            "context_weights": [0.8],
        }
    ],
    "CONVERSE": [
        {
            "source_word": "教える",
            "target_orthography": "習う",
            "target_reading": "ならう",
            "target_word": "習う",  # Backward compatibility
            "relation_type": "CONVERSE",
            "relation_category": "verb",
            "weight": 0.92,
            "confidence": 0.95,
            "is_symmetric": True,
            "shared_meaning_en": "teaching/learning event",
            "distinction_en": "Same event from teacher vs learner perspective",
            "usage_context_en": "教える from teacher's view, 習う from student's view",
            "when_prefer_source_en": "When describing teaching action",
            "when_prefer_target_en": "When describing learning action",
            "register_source": "neutral",
            "register_target": "neutral",
            "formality_difference": "same",
            "transitivity_source": "transitive",
            "transitivity_target": "transitive",
            "domain_tags": ["action", "education_learning"],
            "domain_weights": [0.8, 0.9],
            "context_tags": ["behavior_act", "education_learning"],
            "context_weights": [0.8, 0.9],
        }
    ],
}

NOUN_EXAMPLES: Dict[str, List[Dict]] = {
    "HYPERNYM": [
        {
            "source_word": "犬",
            "target_orthography": "動物",
            "target_reading": "どうぶつ",
            "target_word": "動物",  # Backward compatibility
            "relation_type": "HYPERNYM",
            "relation_category": "noun",
            "weight": 0.98,
            "confidence": 0.99,
            "is_symmetric": False,
            "shared_meaning_en": "taxonomic hierarchy",
            "distinction_en": "動物 is the general category, 犬 is a specific type",
            "usage_context_en": "動物 for general reference, 犬 for specific reference",
            "when_prefer_source_en": "When referring to dogs specifically",
            "when_prefer_target_en": "When referring to animals in general",
            "register_source": "neutral",
            "register_target": "neutral",
            "formality_difference": "same",
            "domain_tags": ["natural", "animal"],
            "domain_weights": [0.9, 0.95],
            "context_tags": ["nature_scenery"],
            "context_weights": [0.7],
        }
    ],
    "CO_HYPONYM": [
        {
            "source_word": "りんご",
            "target_orthography": "みかん",
            "target_reading": "みかん",
            "target_word": "みかん",  # Backward compatibility
            "relation_type": "CO_HYPONYM",
            "relation_category": "noun",
            "weight": 0.85,
            "confidence": 0.90,
            "is_symmetric": True,
            "shared_meaning_en": "both are fruits (果物)",
            "distinction_en": "Different types of fruit sharing the same parent category",
            "usage_context_en": "Both are specific fruit types",
            "when_prefer_source_en": "When referring to apples",
            "when_prefer_target_en": "When referring to oranges/mandarins",
            "register_source": "neutral",
            "register_target": "neutral",
            "formality_difference": "same",
            "domain_tags": ["natural", "plant"],
            "domain_weights": [0.8, 0.9],
            "context_tags": ["food_taste"],
            "context_weights": [0.9],
        }
    ],
}

ADVERB_EXAMPLES: Dict[str, List[Dict]] = {
    "INTENSITY_SCALE": [
        {
            "source_word": "少し",
            "target_orthography": "とても",
            "target_reading": "とても",
            "target_word": "とても",  # Backward compatibility
            "relation_type": "INTENSITY_SCALE",
            "relation_category": "adverb",
            "weight": 0.90,
            "confidence": 0.95,
            "is_symmetric": False,
            "shared_meaning_en": "degree/intensity",
            "distinction_en": "とても is much more intense than 少し",
            "usage_context_en": "少し for small degree, とても for high degree",
            "when_prefer_source_en": "When describing small degree",
            "when_prefer_target_en": "When describing high degree",
            "register_source": "neutral",
            "register_target": "neutral",
            "formality_difference": "same",
            "scale_dimension": "degree",
            "scale_position_source": 0.2,
            "scale_position_target": 0.8,
            "domain_tags": ["intensity"],
            "domain_weights": [0.9],
            "context_tags": [],
            "context_weights": [],
        }
    ],
    "TEMPORAL_PAIR": [
        {
            "source_word": "もう",
            "target_word": "まだ",
            "relation_type": "TEMPORAL_PAIR",
            "relation_category": "adverb",
            "weight": 0.88,
            "confidence": 0.93,
            "is_symmetric": True,
            "shared_meaning_en": "temporal state",
            "distinction_en": "もう means already/done, まだ means not yet/still",
            "usage_context_en": "もう for completed states, まだ for ongoing/incomplete states",
            "when_prefer_source_en": "When something is already done",
            "when_prefer_target_en": "When something is not yet done",
            "register_source": "neutral",
            "register_target": "neutral",
            "formality_difference": "same",
            "domain_tags": ["temporal"],
            "domain_weights": [0.9],
            "context_tags": ["events_experiences"],
            "context_weights": [0.7],
        }
    ],
}


def get_few_shot_examples(pos: str, relation_types: List[str]) -> List[Dict]:
    """
    Get few-shot examples for a POS and relation types.
    
    Args:
        pos: Part of speech
        relation_types: List of relation types to get examples for
        
    Returns:
        List of example dictionaries
    """
    examples = []
    
    if pos in ["形容詞", "形容動詞"]:
        for rel_type in relation_types:
            if rel_type in ADJECTIVE_EXAMPLES:
                examples.extend(ADJECTIVE_EXAMPLES[rel_type])
    elif pos == "動詞":
        for rel_type in relation_types:
            if rel_type in VERB_EXAMPLES:
                examples.extend(VERB_EXAMPLES[rel_type])
    elif pos == "名詞":
        for rel_type in relation_types:
            if rel_type in NOUN_EXAMPLES:
                examples.extend(NOUN_EXAMPLES[rel_type])
    elif pos == "副詞":
        for rel_type in relation_types:
            if rel_type in ADVERB_EXAMPLES:
                examples.extend(ADVERB_EXAMPLES[rel_type])
    
    return examples[:5]  # Limit to 5 examples to avoid token bloat
