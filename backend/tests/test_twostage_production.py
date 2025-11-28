"""
Integration tests for two-stage lesson generation in production.

Tests the complete two-stage pipeline:
- Stage 1: Simple content generation
- Stage 2: Multilingual enhancement  
- Merge: Final lesson structure

Run from backend directory:
    poetry run pytest tests/test_twostage_production.py -v
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from typing import Dict, Any

from app.services.cando_lesson_session_service import CanDoLessonSessionService


class TestTwoStageProduction:
    """Test suite for two-stage lesson generation."""
    
    @pytest.fixture
    def service(self):
        """Create service instance."""
        return CanDoLessonSessionService()
    
    @pytest.fixture
    def mock_neo4j_session(self):
        """Mock Neo4j session."""
        session = AsyncMock()
        return session
    
    @pytest.fixture
    def mock_pg_session(self):
        """Mock PostgreSQL session."""
        session = AsyncMock()
        return session
    
    @pytest.fixture
    def sample_stage1_content(self) -> Dict[str, Any]:
        """Sample Stage 1 output."""
        return {
            "lessonPlan": [
                {
                    "step": "Warm-up",
                    "teacherNotes": "Introduce the topic with simple questions.",
                    "studentTask": "Answer questions about food preferences."
                },
                {
                    "step": "Input",
                    "teacherNotes": "Present reading passage about Japanese food.",
                    "studentTask": "Read and identify key vocabulary."
                },
                {
                    "step": "Practice",
                    "teacherNotes": "Students practice using new vocabulary.",
                    "studentTask": "Complete fill-in-the-blank exercises."
                },
                {
                    "step": "Production",
                    "teacherNotes": "Students create their own dialogues.",
                    "studentTask": "Role-play ordering food at a restaurant."
                }
            ],
            "reading": {
                "title": "日本の食べ物",
                "text": "日本には美味しい食べ物がたくさんあります。寿司、天ぷら、ラーメンなどが有名です。"
            },
            "dialogue": [
                {"speaker": "健", "text": "お腹が空きました。"},
                {"speaker": "ゆみ", "text": "何を食べたいですか？"},
                {"speaker": "健", "text": "ラーメンを食べたいです。"},
                {"speaker": "ゆみ", "text": "いいですね。一緒に行きましょう。"}
            ],
            "grammar": [
                {
                    "pattern": "〜が〜です",
                    "explanation": "Used to state what something is.",
                    "examples": [
                        "これは寿司です。",
                        "私は学生です。"
                    ]
                }
            ],
            "practice": [
                {
                    "type": "cloze",
                    "instruction": "Fill in the blank with the correct particle.",
                    "content": "私___ラーメン___食べます。"
                }
            ],
            "culture": [
                {
                    "title": "日本の食事のマナー",
                    "content": "日本では食事の前に「いただきます」と言います。"
                }
            ]
        }
    
    @pytest.fixture
    def sample_enhanced_reading(self) -> Dict[str, Any]:
        """Sample Stage 2 enhanced reading."""
        return {
            "title": {
                "kanji": "日本の食べ物",
                "romaji": "nihon no tabemono",
                "furigana": [
                    {"text": "日本", "ruby": "にほん"},
                    {"text": "の"},
                    {"text": "食", "ruby": "た"},
                    {"text": "べ"},
                    {"text": "物", "ruby": "もの"}
                ],
                "translation": "Japanese Food"
            },
            "content": {
                "kanji": "日本には美味しい食べ物がたくさんあります。",
                "romaji": "nihon niwa oishii tabemono ga takusan arimasu.",
                "furigana": [
                    {"text": "日本", "ruby": "にほん"},
                    {"text": "には"},
                    {"text": "美味", "ruby": "おい"},
                    {"text": "しい"},
                    {"text": "食", "ruby": "た"},
                    {"text": "べ"},
                    {"text": "物", "ruby": "もの"},
                    {"text": "がたくさんあります。"}
                ],
                "translation": "Japan has lots of delicious food."
            },
            "comprehension_questions": [
                "What kind of food does Japan have?",
                "Name two famous Japanese dishes."
            ]
        }
    
    @pytest.mark.asyncio
    async def test_generate_simple_content_success(self, service):
        """Test Stage 1 content generation succeeds."""
        # Mock AI response
        mock_response = {
            "content": """{
                "lessonPlan": [{"step": "Warm-up", "teacherNotes": "Intro", "studentTask": "Answer"}],
                "reading": {"title": "食事", "text": "日本の食事は美味しいです。"},
                "dialogue": [{"speaker": "A", "text": "こんにちは"}],
                "grammar": [{"pattern": "です", "explanation": "copula", "examples": ["これです"]}],
                "practice": [{"type": "cloze", "instruction": "Fill", "content": "私___です"}],
                "culture": [{"title": "マナー", "content": "食事のマナーは大切です。"}]
            }"""
        }
        
        with patch.object(service._practice.ai_chat, 'generate_reply', new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = mock_response
            
            result = await service._generate_simple_content(
                can_do_id="JF:349",
                topic="食生活",
                level="A1",
                provider="openai",
                model="gpt-5",
                timeout=180
            )
            
            # Validate structure
            assert "lessonPlan" in result
            assert "reading" in result
            assert "dialogue" in result
            assert "grammar" in result
            assert "practice" in result
            assert "culture" in result
            
            # Validate counts
            assert len(result["lessonPlan"]) >= 1
            assert len(result["dialogue"]) >= 1
            assert len(result["grammar"]) >= 1
    
    @pytest.mark.asyncio
    async def test_enhance_reading_section_success(self, service, sample_stage1_content):
        """Test Stage 2 reading enhancement succeeds."""
        mock_response = {
            "content": """{
                "title": {
                    "kanji": "日本の食べ物",
                    "romaji": "nihon no tabemono",
                    "furigana": [{"text": "日本", "ruby": "にほん"}],
                    "translation": "Japanese Food"
                },
                "content": {
                    "kanji": "日本には美味しい食べ物がたくさんあります。",
                    "romaji": "nihon niwa oishii tabemono ga takusan arimasu.",
                    "furigana": [{"text": "日本", "ruby": "にほん"}],
                    "translation": "Japan has lots of delicious food."
                },
                "comprehension_questions": ["Question 1?"]
            }"""
        }
        
        with patch.object(service._practice.ai_chat, 'generate_reply', new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = mock_response
            
            result = await service._enhance_section_with_multilingual(
                section_name="reading",
                section_data=sample_stage1_content["reading"],
                provider="openai",
                model="gpt-4.1",
                timeout=60
            )
            
            # Validate success
            assert result["success"] is True
            assert "data" in result
            
            # Validate multilingual structure
            data = result["data"]
            assert "title" in data
            assert "kanji" in data["title"]
            assert "romaji" in data["title"]
            assert "furigana" in data["title"]
            assert "translation" in data["title"]
    
    @pytest.mark.asyncio
    async def test_enhance_dialogue_section_success(self, service, sample_stage1_content):
        """Test Stage 2 dialogue enhancement succeeds."""
        # Mock response for each dialogue turn
        mock_responses = [
            {
                "content": """{
                    "speaker": "健",
                    "japanese": {
                        "kanji": "お腹が空きました。",
                        "romaji": "onaka ga sukimashita.",
                        "furigana": [{"text": "お", "ruby": "お"}, {"text": "腹", "ruby": "なか"}],
                        "translation": "I'm hungry."
                    }
                }"""
            },
            {
                "content": """{
                    "speaker": "ゆみ",
                    "japanese": {
                        "kanji": "何を食べたいですか？",
                        "romaji": "nani o tabetai desu ka?",
                        "furigana": [{"text": "何", "ruby": "なに"}],
                        "translation": "What do you want to eat?"
                    }
                }"""
            }
        ]
        
        with patch.object(service._practice.ai_chat, 'generate_reply', new_callable=AsyncMock) as mock_gen:
            mock_gen.side_effect = mock_responses + mock_responses  # Handle all turns
            
            result = await service._enhance_section_with_multilingual(
                section_name="dialogue",
                section_data=sample_stage1_content["dialogue"][:2],  # Test with 2 turns
                provider="openai",
                model="gpt-4.1",
                timeout=60
            )
            
            # Validate success
            assert result["success"] is True
            assert "data" in result
            
            # Validate dialogue turns
            turns = result["data"]
            assert len(turns) >= 1
            assert "speaker" in turns[0]
            assert "japanese" in turns[0]
            assert "kanji" in turns[0]["japanese"]
    
    @pytest.mark.asyncio
    async def test_merge_enhanced_sections(self, service, sample_stage1_content, sample_enhanced_reading):
        """Test merging Stage 1 and Stage 2 results."""
        enhanced_sections = {
            "reading": sample_enhanced_reading
        }
        
        # Add metadata
        sample_stage1_content["canDoId"] = "JF:349"
        sample_stage1_content["originalLevel"] = 1
        sample_stage1_content["topic"] = "食生活"
        
        master = service._merge_enhanced_sections(
            sample_stage1_content,
            enhanced_sections
        )
        
        # Validate master structure
        assert "uiVersion" in master
        assert master["uiVersion"] == 2
        assert "canDoId" in master
        assert "ui" in master
        assert "sections" in master["ui"]
        
        # Validate sections exist
        sections = master["ui"]["sections"]
        section_ids = [s["id"] for s in sections]
        assert "lessonPlan" in section_ids
        assert "reading" in section_ids
        assert "culture" in section_ids
        
        # Validate reading section has enhanced content
        reading_section = next(s for s in sections if s["id"] == "reading")
        assert len(reading_section["cards"]) > 0
        reading_card = reading_section["cards"][0]
        assert reading_card["kind"] == "reading"
        assert "reading" in reading_card
    
    @pytest.mark.asyncio
    async def test_full_twostage_pipeline_integration(self, service):
        """Test complete two-stage pipeline with mocked AI responses."""
        # Mock Stage 1 response
        stage1_mock = {
            "content": """{
                "lessonPlan": [
                    {"step": "Warm-up", "teacherNotes": "Introduce topic", "studentTask": "Discuss food"},
                    {"step": "Input", "teacherNotes": "Present reading", "studentTask": "Read passage"},
                    {"step": "Practice", "teacherNotes": "Practice vocab", "studentTask": "Complete exercises"},
                    {"step": "Production", "teacherNotes": "Create dialogue", "studentTask": "Role-play"}
                ],
                "reading": {"title": "食事", "text": "日本の食事は美味しいです。健康的です。バランスが良いです。四季の食材を使います。"},
                "dialogue": [
                    {"speaker": "健", "text": "お腹が空きました。"},
                    {"speaker": "ゆみ", "text": "何を食べたいですか？"},
                    {"speaker": "健", "text": "ラーメンを食べたいです。"},
                    {"speaker": "ゆみ", "text": "いいですね。"},
                    {"speaker": "健", "text": "一緒に行きましょう。"},
                    {"speaker": "ゆみ", "text": "はい、行きましょう。"}
                ],
                "grammar": [
                    {"pattern": "〜を〜ます", "explanation": "Object marker and verb", "examples": ["ご飯を食べます", "水を飲みます"]},
                    {"pattern": "〜たいです", "explanation": "Want to do", "examples": ["食べたいです", "飲みたいです"]}
                ],
                "practice": [
                    {"type": "cloze", "instruction": "Fill in", "content": "私___ラーメン___食べます"},
                    {"type": "matching", "instruction": "Match words", "content": "Match food items"},
                    {"type": "dialogue", "instruction": "Practice", "content": "Order food"}
                ],
                "culture": [
                    {"title": "いただきます", "content": "日本では食事の前に「いただきます」と言います。食べ物への感謝を表します。"},
                    {"title": "箸の使い方", "content": "日本では箸を使って食事をします。正しい持ち方を学ぶことが大切です。"}
                ]
            }"""
        }
        
        # Mock Stage 2 responses (simplified for test)
        stage2_reading_mock = {
            "content": """{
                "title": {"kanji": "食事", "romaji": "shokuji", "furigana": [{"text": "食事", "ruby": "しょくじ"}], "translation": "Meal"},
                "content": {"kanji": "日本の食事は美味しいです。", "romaji": "nihon no shokuji wa oishii desu.", "furigana": [{"text": "日本", "ruby": "にほん"}], "translation": "Japanese meals are delicious."},
                "comprehension_questions": ["What is Japanese food like?"]
            }"""
        }
        
        stage2_dialogue_mocks = [
            {
                "content": """{
                    "speaker": "健",
                    "japanese": {"kanji": "お腹が空きました。", "romaji": "onaka ga sukimashita.", "furigana": [{"text": "腹", "ruby": "なか"}], "translation": "I'm hungry."}
                }"""
            }
        ] * 6  # Repeat for all dialogue turns
        
        stage2_grammar_mocks = [
            {
                "content": """{
                    "pattern": "〜を〜ます",
                    "explanation": "Object marker and verb",
                    "examples": [
                        {"kanji": "ご飯を食べます", "romaji": "gohan o tabemasu", "furigana": [{"text": "飯", "ruby": "はん"}], "translation": "I eat rice"}
                    ]
                }"""
            }
        ] * 2  # For each grammar point
        
        with patch.object(service._practice.ai_chat, 'generate_reply', new_callable=AsyncMock) as mock_gen:
            # Configure mock to return different responses in sequence
            mock_gen.side_effect = [stage1_mock, stage2_reading_mock] + stage2_dialogue_mocks + stage2_grammar_mocks
            
            result = await service._generate_master_lesson(
                can_do_id="JF:349",
                topic="食生活",
                original_level_str="A1",
                provider="openai",
                model="gpt-5",
                timeout=180,
                meta_extra={}
            )
            
            # Validate complete master lesson
            assert "uiVersion" in result
            assert result["uiVersion"] == 2
            assert "canDoId" in result
            assert result["canDoId"] == "JF:349"
            assert "metadata" in result
            assert result["metadata"]["multilingualVersion"] is True
            
            # Validate UI structure
            assert "ui" in result
            assert "sections" in result["ui"]
            sections = result["ui"]["sections"]
            assert len(sections) >= 4  # At least lessonPlan, reading, practice, culture
            
            # Find and validate reading section
            reading_sections = [s for s in sections if s["id"] == "reading"]
            assert len(reading_sections) > 0
            reading_section = reading_sections[0]
            assert len(reading_section["cards"]) > 0
            reading_card = reading_section["cards"][0]
            assert reading_card["kind"] == "reading"
            assert "reading" in reading_card
            assert "title" in reading_card["reading"]
            assert "kanji" in reading_card["reading"]["title"]
    
    @pytest.mark.asyncio
    async def test_stage2_partial_failure_continues(self, service, sample_stage1_content):
        """Test that if one Stage 2 section fails, others continue."""
        # Mock responses: reading succeeds, dialogue fails
        reading_success = {
            "content": """{
                "title": {"kanji": "食事", "romaji": "shokuji", "furigana": [{"text": "食事", "ruby": "しょくじ"}], "translation": "Meal"},
                "content": {"kanji": "美味しい", "romaji": "oishii", "furigana": [{"text": "美味", "ruby": "おい"}], "translation": "delicious"},
                "comprehension_questions": ["Question?"]
            }"""
        }
        
        dialogue_failure = {
            "content": "Invalid JSON {{"  # Malformed JSON
        }
        
        with patch.object(service._practice.ai_chat, 'generate_reply', new_callable=AsyncMock) as mock_gen:
            mock_gen.side_effect = [reading_success, dialogue_failure, dialogue_failure]  # Retries for dialogue
            
            # Reading should succeed
            reading_result = await service._enhance_section_with_multilingual(
                section_name="reading",
                section_data=sample_stage1_content["reading"],
                provider="openai",
                model="gpt-4.1",
                timeout=60
            )
            assert reading_result["success"] is True
            
            # Dialogue should fail gracefully
            dialogue_result = await service._enhance_section_with_multilingual(
                section_name="dialogue",
                section_data=sample_stage1_content["dialogue"][:1],
                provider="openai",
                model="gpt-4.1",
                timeout=60
            )
            assert dialogue_result["success"] is False
            assert "error" in dialogue_result
    
    @pytest.mark.asyncio
    async def test_pydantic_validation_catches_invalid_structure(self, service):
        """Test that Pydantic validation catches malformed content."""
        # Mock invalid response (missing required fields)
        invalid_response = {
            "content": """{
                "lessonPlan": [],
                "reading": {"title": "食事"},
                "dialogue": [],
                "grammar": [],
                "practice": [],
                "culture": []
            }"""
        }
        
        with patch.object(service._practice.ai_chat, 'generate_reply', new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = invalid_response
            
            # Should raise ValidationError (caught and converted to ValueError)
            with pytest.raises(Exception):  # Will be ValidationError from Pydantic
                await service._generate_simple_content(
                    can_do_id="JF:349",
                    topic="食生活",
                    level="A1",
                    provider="openai",
                    model="gpt-5",
                    timeout=180
                )


class TestDifferentLevelsAndTopics:
    """Test generation across different CanDo levels and topics."""
    
    @pytest.fixture
    def service(self):
        return CanDoLessonSessionService()
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("level,topic", [
        ("A1", "食生活"),
        ("A2", "旅行"),
        ("B1", "仕事"),
    ])
    async def test_generation_for_different_levels_and_topics(self, service, level, topic):
        """Test that generation works for different CEFR levels and topics."""
        # Mock successful Stage 1 response
        stage1_mock = {
            "content": f"""{{
                "lessonPlan": [
                    {{"step": "Warm-up", "teacherNotes": "Introduce {topic}", "studentTask": "Discuss"}},
                    {{"step": "Input", "teacherNotes": "Present", "studentTask": "Read"}},
                    {{"step": "Practice", "teacherNotes": "Practice", "studentTask": "Complete"}},
                    {{"step": "Production", "teacherNotes": "Create", "studentTask": "Produce"}}
                ],
                "reading": {{"title": "{topic}", "text": "これは{topic}についてのテキストです。"}},
                "dialogue": [
                    {{"speaker": "A", "text": "こんにちは"}},
                    {{"speaker": "B", "text": "元気ですか"}},
                    {{"speaker": "A", "text": "元気です"}},
                    {{"speaker": "B", "text": "良かった"}},
                    {{"speaker": "A", "text": "ありがとう"}},
                    {{"speaker": "B", "text": "どういたしまして"}}
                ],
                "grammar": [
                    {{"pattern": "です", "explanation": "Copula", "examples": ["これです", "それです"]}},
                    {{"pattern": "ます", "explanation": "Polite verb", "examples": ["行きます", "来ます"]}}
                ],
                "practice": [
                    {{"type": "cloze", "instruction": "Fill", "content": "Test"}},
                    {{"type": "matching", "instruction": "Match", "content": "Test"}},
                    {{"type": "production", "instruction": "Create", "content": "Test"}}
                ],
                "culture": [
                    {{"title": "Culture 1", "content": "Japanese culture note about {topic}."}},
                    {{"title": "Culture 2", "content": "Another cultural insight."}}
                ]
            }}"""
        }
        
        with patch.object(service._practice.ai_chat, 'generate_reply', new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = stage1_mock
            
            result = await service._generate_simple_content(
                can_do_id=f"JF:TEST-{level}",
                topic=topic,
                level=level,
                provider="openai",
                model="gpt-5",
                timeout=180
            )
            
            # Validate structure is maintained across levels/topics
            assert "lessonPlan" in result
            assert "reading" in result
            assert len(result["lessonPlan"]) == 4
            assert len(result["dialogue"]) >= 6
            assert len(result["grammar"]) >= 2

