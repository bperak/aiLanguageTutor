"""
Topic translations for CanDo descriptors.

Maps Japanese primary topics to English translations.
"""

TOPIC_TRANSLATIONS = {
    "人との関係": "Relationships with People",
    "仕事と職業": "Work and Occupation",
    "住まいと住環境": "Housing and Living Environment",
    "健康": "Health",
    "学校と教育": "School and Education",
    "旅行と交通": "Travel and Transportation",
    "生活と人生": "Life and Living",
    "社会": "Society",
    "科学技術": "Science and Technology",
    "自分と家族": "Self and Family",
    "自然と環境": "Nature and Environment",
    "自由時間と娯楽": "Leisure and Entertainment",
    "言語と文化": "Language and Culture",
    "買い物": "Shopping",
    "食生活": "Food and Dining",
}


def get_english_topic(japanese_topic: str) -> str:
    """
    Get English translation for a Japanese topic.
    
    Args:
        japanese_topic: Japanese topic name.
        
    Returns:
        English translation, or the original if not found.
    """
    return TOPIC_TRANSLATIONS.get(japanese_topic, japanese_topic)

