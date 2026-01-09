"""
Tests for PreLessonKitService

Covers:
- Expected use: kit generation returns schema-valid payload
- Edge case: LLM returns partial/invalid JSON → fallback output is still schema-valid
- Failure case: service handles errors gracefully
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.prelesson_kit_service import prelesson_kit_service
from app.schemas.profile import PreLessonKit


@pytest.mark.asyncio
async def test_generate_kit_expected_use():
    """Test that kit generation returns schema-valid payload with proper structure."""
    can_do_id = "JF:21"
    
    # Mock AI response with valid JSON
    mock_ai_response = {
        "content": """{
  "necessary_words": [
    {"surface": "レストラン", "reading": "れすとらん", "pos": "noun", "translation": "restaurant"},
    {"surface": "メニュー", "reading": "めにゅー", "pos": "noun", "translation": "menu"}
  ],
  "necessary_grammar_patterns": [
    {
      "pattern": "〜たいです",
      "explanation": "Expresses desire (want to...)",
      "examples": [
        {
          "kanji": "食べたいです",
          "romaji": "tabetai desu",
          "furigana": [{"text": "食べ", "ruby": "たべ"}, {"text": "たい", "ruby": "たい"}, {"text": "です"}],
          "translation": "I want to eat"
        }
      ]
    }
  ],
  "necessary_fixed_phrases": [
    {
      "phrase": {
        "kanji": "いらっしゃいませ",
        "romaji": "irasshaimase",
        "furigana": [{"text": "いらっしゃい", "ruby": "いらっしゃい"}, {"text": "ませ"}],
        "translation": "Welcome (to a store/restaurant)"
      },
      "usage_note": "Used by staff to greet customers",
      "register": "polite"
    }
  ]
}"""
    }
    
    with patch.object(prelesson_kit_service.ai_service, "generate_reply", new_callable=AsyncMock) as mock_generate:
        mock_generate.return_value = mock_ai_response
        
        # Mock Neo4j session
        mock_neo4j = AsyncMock()
        mock_result = AsyncMock()
        mock_result.single.return_value = None
        mock_neo4j.run.return_value = mock_result
        
        kit = await prelesson_kit_service.generate_kit(
            can_do_id=can_do_id,
            learner_level="intermediate_1",
            neo4j_session=mock_neo4j
        )
        
        # Validate structure
        assert isinstance(kit, PreLessonKit)
        assert len(kit.necessary_words) == 2
        assert len(kit.necessary_grammar_patterns) == 1
        assert len(kit.necessary_fixed_phrases) == 1
        
        # Validate word structure
        word = kit.necessary_words[0]
        assert "surface" in word
        assert "reading" in word
        assert "pos" in word
        assert "translation" in word
        
        # Validate grammar structure
        grammar = kit.necessary_grammar_patterns[0]
        assert "pattern" in grammar
        assert "explanation" in grammar
        assert "examples" in grammar
        assert len(grammar["examples"]) > 0
        
        # Validate phrase structure
        phrase = kit.necessary_fixed_phrases[0]
        assert "phrase" in phrase
        assert "usage_note" in phrase
        assert "register" in phrase


@pytest.mark.asyncio
async def test_generate_kit_fallback_on_invalid_json():
    """Test that fallback kit is returned when LLM returns invalid JSON."""
    can_do_id = "JF:21"
    
    # Mock AI response with invalid JSON
    mock_ai_response = {
        "content": "This is not valid JSON at all! {broken"
    }
    
    with patch.object(prelesson_kit_service.ai_service, "generate_reply", new_callable=AsyncMock) as mock_generate:
        mock_generate.return_value = mock_ai_response
        
        # Mock Neo4j session
        mock_neo4j = AsyncMock()
        mock_result = AsyncMock()
        mock_result.single.return_value = None
        mock_neo4j.run.return_value = mock_result
        
        kit = await prelesson_kit_service.generate_kit(
            can_do_id=can_do_id,
            learner_level="beginner_1",
            neo4j_session=mock_neo4j
        )
        
        # Should return fallback kit (still schema-valid)
        assert isinstance(kit, PreLessonKit)
        assert len(kit.necessary_words) > 0
        assert len(kit.necessary_grammar_patterns) > 0
        assert len(kit.necessary_fixed_phrases) > 0


@pytest.mark.asyncio
async def test_generate_kit_fallback_on_partial_data():
    """Test that service handles partial/incomplete data gracefully."""
    can_do_id = "JF:21"
    
    # Mock AI response with partial data (missing examples in grammar)
    mock_ai_response = {
        "content": """{
  "necessary_words": [
    {"surface": "レストラン", "reading": "れすとらん", "pos": "noun", "translation": "restaurant"}
  ],
  "necessary_grammar_patterns": [
    {
      "pattern": "〜たいです",
      "explanation": "Expresses desire"
    }
  ],
  "necessary_fixed_phrases": []
}"""
    }
    
    with patch.object(prelesson_kit_service.ai_service, "generate_reply", new_callable=AsyncMock) as mock_generate:
        mock_generate.return_value = mock_ai_response
        
        # Mock Neo4j session
        mock_neo4j = AsyncMock()
        mock_result = AsyncMock()
        mock_result.single.return_value = None
        mock_neo4j.run.return_value = mock_result
        
        kit = await prelesson_kit_service.generate_kit(
            can_do_id=can_do_id,
            learner_level="beginner_1",
            neo4j_session=mock_neo4j
        )
        
        # Should handle partial data gracefully
        assert isinstance(kit, PreLessonKit)
        # Words should be present
        assert len(kit.necessary_words) >= 1
        # Grammar without examples should be filtered out or handled
        # (service filters invalid entries)


@pytest.mark.asyncio
async def test_generate_kit_fallback_on_exception():
    """Test that service returns fallback kit when exception occurs."""
    can_do_id = "JF:21"
    
    # Mock AI service to raise exception
    with patch.object(prelesson_kit_service.ai_service, "generate_reply", new_callable=AsyncMock) as mock_generate:
        mock_generate.side_effect = Exception("AI service unavailable")
        
        # Mock Neo4j session
        mock_neo4j = AsyncMock()
        mock_result = AsyncMock()
        mock_result.single.return_value = None
        mock_neo4j.run.return_value = mock_result
        
        kit = await prelesson_kit_service.generate_kit(
            can_do_id=can_do_id,
            learner_level="beginner_1",
            neo4j_session=mock_neo4j
        )
        
        # Should return fallback kit
        assert isinstance(kit, PreLessonKit)
        assert len(kit.necessary_words) > 0
        assert len(kit.necessary_grammar_patterns) > 0
        assert len(kit.necessary_fixed_phrases) > 0


@pytest.mark.asyncio
async def test_fallback_kit_schema_valid():
    """Test that fallback kit is always schema-valid."""
    can_do_id = "JF:21"
    level = "B1"
    
    kit = prelesson_kit_service._create_fallback_kit(can_do_id, level)
    
    # Validate it's a PreLessonKit
    assert isinstance(kit, PreLessonKit)
    
    # Validate structure
    assert len(kit.necessary_words) > 0
    assert len(kit.necessary_grammar_patterns) > 0
    assert len(kit.necessary_fixed_phrases) > 0
    
    # Validate word entries have required fields
    for word in kit.necessary_words:
        assert "surface" in word
        assert "reading" in word
        assert "pos" in word
        assert "translation" in word
    
    # Validate grammar entries have required fields
    for grammar in kit.necessary_grammar_patterns:
        assert "pattern" in grammar
        assert "explanation" in grammar
        assert "examples" in grammar


@pytest.mark.asyncio
async def test_kit_includes_cando_context():
    """Test that generated kit includes can_do_context (component 0)."""
    can_do_id = "JF:21"
    
    # Mock AI response with can_do_context
    mock_ai_response_kit = {
        "content": """{
  "necessary_words": [
    {"surface": "レストラン", "reading": "れすとらん", "pos": "noun", "translation": "restaurant"}
  ],
  "necessary_grammar_patterns": [],
  "necessary_fixed_phrases": []
}"""
    }
    
    mock_ai_response_context = {
        "content": """{
  "situation": "Ordering food at a restaurant",
  "pragmatic_act": "request (polite)",
  "notes": "Polite requests are important in restaurant settings"
}"""
    }
    
    with patch.object(prelesson_kit_service.ai_service, "generate_reply", new_callable=AsyncMock) as mock_generate:
        # First call for context, second for kit
        mock_generate.side_effect = [mock_ai_response_context, mock_ai_response_kit]
        
        # Mock Neo4j session
        mock_neo4j = AsyncMock()
        mock_result = AsyncMock()
        mock_result.single.return_value = None
        mock_neo4j.run.return_value = mock_result
        
        # Mock pragmatics service to return empty (triggers AI generation)
        with patch("app.services.prelesson_kit_service.pragmatics_service") as mock_pragmatics:
            mock_pragmatics.get_pragmatics = AsyncMock(return_value=[])
            
            kit = await prelesson_kit_service.generate_kit(
                can_do_id=can_do_id,
                learner_level="intermediate_1",
                neo4j_session=mock_neo4j
            )
        
        # Validate can_do_context is present
        assert kit.can_do_context is not None
        assert kit.can_do_context.situation
        assert kit.can_do_context.pragmatic_act


@pytest.mark.asyncio
async def test_fallback_kit_includes_cando_context():
    """Test that fallback kit includes minimal can_do_context."""
    can_do_id = "JF:21"
    level = "B1"
    
    kit = prelesson_kit_service._create_fallback_kit(can_do_id, level)
    
    # Validate can_do_context is present even in fallback
    assert kit.can_do_context is not None
    assert isinstance(kit.can_do_context.situation, str)
    assert isinstance(kit.can_do_context.pragmatic_act, str)
    assert len(kit.can_do_context.situation) > 0
    assert len(kit.can_do_context.pragmatic_act) > 0


@pytest.mark.asyncio
async def test_kit_backwards_compatible_without_context():
    """Test that kits without can_do_context still validate (backwards compatibility)."""
    from app.schemas.profile import PreLessonKit
    
    # Create a kit dict without can_do_context (old format)
    kit_dict = {
        "necessary_words": [
            {"surface": "こんにちは", "reading": "こんにちは", "pos": "expression", "translation": "Hello"}
        ],
        "necessary_grammar_patterns": [],
        "necessary_fixed_phrases": []
    }
    
    # Should validate successfully (can_do_context is optional)
    kit = PreLessonKit(**kit_dict)
    assert kit.can_do_context is None
    assert len(kit.necessary_words) == 1

