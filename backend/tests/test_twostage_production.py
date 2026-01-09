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


def _jp_repeat(s: str, min_len: int) -> str:
    """
    Repeat a Japanese string until it reaches min_len characters.

    Args:
        s (str): Base string.
        min_len (int): Minimum length.

    Returns:
        str: Repeated string with length >= min_len.
    """
    out = (s or "").strip()
    if not out:
        out = "れんしゅう"
    while len(out) < min_len:
        out += out
    return out[: max(min_len, len(out))]


def _make_valid_stage1_content(topic: str = "食生活") -> Dict[str, Any]:
    """
    Create a Stage1Content-shaped dict that satisfies current Pydantic constraints.

    Args:
        topic (str): Lesson topic.

    Returns:
        Dict[str, Any]: Stage 1 content dict.
    """
    return {
        "objective": f"{topic}について、短い文で説明できる。",
        "topic": topic,
        "level": "A1",
        "lessonPlan": [
            {
                "title": "導入編",
                "contentJP": _jp_repeat(
                    f"今日は「{topic}」について学びます。まずは身近な例から考えましょう。"
                    "短い文で、好きなもの・苦手なものを言えるようにします。",
                    120,
                ),
                "goalsJP": "今日のテーマを理解し、自分の言葉で短く言える。",
            },
            {
                "title": "読解編",
                "contentJP": _jp_repeat(
                    "短い文章を読み、重要な言葉と意味を確認します。"
                    "内容をまとめる練習をします。",
                    120,
                ),
            },
            {
                "title": "会話編",
                "contentJP": _jp_repeat(
                    "会話の流れをまねして、相手に質問したり答えたりします。"
                    "ゆっくり、はっきり話す練習をします。",
                    120,
                ),
            },
            {
                "title": "ふり返り",
                "contentJP": _jp_repeat(
                    "最後に、今日できるようになったことを確認します。"
                    "次に練習したいことも一つ決めましょう。",
                    120,
                ),
            },
        ],
        "reading": {
            "title": f"{topic}のはなし",
            # Stage1Content requires min 250 chars
            "text": _jp_repeat(
                f"{topic}は毎日の生活と関係があります。"
                "あさごはん、ひるごはん、ばんごはんを食べます。"
                "やさいやくだものも食べます。"
                "水をのむことも大切です。"
                "自分の好きなたべものを言ってみましょう。",
                250,
            ),
            "questions": [
                {"q": "テーマは何ですか？", "a": topic},
                {"q": "何を食べますか？", "a": "あさごはん、ひるごはん、ばんごはん。"},
            ],
        },
        # 6 turns required (6-8)
        "dialogue": [
            {"speaker": "A", "text": "きょうは何をたべますか。"},
            {"speaker": "B", "text": "ラーメンをたべたいです。"},
            {"speaker": "A", "text": "どこでたべますか。"},
            {"speaker": "B", "text": "えきのちかくでたべます。"},
            {"speaker": "A", "text": "いっしょに行きましょう。"},
            {"speaker": "B", "text": "はい、行きましょう。"},
        ],
        # Exactly 3 points required
        "grammar": [
            {"pattern": "〜を", "explanation": "目的語を表します。", "examples": ["みずをのみます。", "パンをたべます。"]},
            {"pattern": "〜で", "explanation": "場所を表します。", "examples": ["いえでたべます。", "みせでのみます。"]},
            {"pattern": "〜たいです", "explanation": "希望を表します。", "examples": ["たべたいです。", "のみたいです。"]},
        ],
        # Exactly 3 cards required: cloze, matching, dialogueGap
        "practice": [
            {
                "type": "cloze",
                "instruction": "かっこに入ることばをえらんでください。",
                "items": [
                    {"prompt": "わたしは( )をのみます。", "choices": ["みず", "いえ", "で"], "answer": "みず"},
                    {"prompt": "みせ( )たべます。", "choices": ["を", "で", "たい"], "answer": "で"},
                    {"prompt": "ラーメンをたべ( )。", "choices": ["たいです", "を", "で"], "answer": "たいです"},
                ],
            },
            {
                "type": "matching",
                "instruction": "日本語と英語をむすんでください。",
                "pairs": [
                    {"jp": "みず", "en": "water", "id": "p1"},
                    {"jp": "パン", "en": "bread", "id": "p2"},
                    {"jp": "みせ", "en": "shop", "id": "p3"},
                    {"jp": "いえ", "en": "home", "id": "p4"},
                ],
            },
            {
                "type": "dialogueGap",
                "instruction": "会話の( )をうめてください。",
                "items": [
                    {"prompt": "A: きょうは何を( )ですか。\nB: ラーメンをたべたいです。", "given": ["たべ"], "answers": ["たべたい"]},
                    {"prompt": "A: どこでたべますか。\nB: えきの( )でたべます。", "given": ["ちか"], "answers": ["ちかく"]},
                ],
            },
        ],
        "culture": [
            {"title": "あいさつ", "content": _jp_repeat("食事の前に、短いあいさつをすることがあります。", 20)},
            {"title": "マナー", "content": _jp_repeat("食べる時は、相手を思いやる気持ちが大切です。", 20)},
        ],
    }


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
        return _make_valid_stage1_content("食生活")
    
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
            "comprehension": [
                {"q": "日本には何がありますか？", "a": "美味しい食べ物がたくさんあります。"},
            ],
        }
    
    @pytest.mark.asyncio
    async def test_generate_simple_content_success(self, service):
        """Test Stage 1 content generation succeeds."""
        # Mock AI response
        valid = _make_valid_stage1_content("食生活")
        # Serialize as JSON (service extracts balanced JSON from content string)
        import json
        mock_response = {"content": json.dumps(valid, ensure_ascii=False)}
        
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
            assert len(result["lessonPlan"]) == 4
            assert 6 <= len(result["dialogue"]) <= 8
            assert len(result["grammar"]) == 3
            assert len(result["practice"]) == 3
            assert 2 <= len(result["culture"]) <= 3
    
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
                "comprehension": [{"q": "何がありますか？", "a": "食べ物があります。"}]
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
        # Dialogue is processed in batch via Stage2DialogueTurnList: {"turns":[...]}
        mock_response = {
            "content": """{
              "turns": [
                {
                  "speaker": "A",
                  "japanese": {"kanji": "たべます。", "romaji": "tabemasu.", "furigana": [{"text": "たべます。"}], "translation": "I eat."}
                },
                {
                  "speaker": "B",
                  "japanese": {"kanji": "のみます。", "romaji": "nomimasu.", "furigana": [{"text": "のみます。"}], "translation": "I drink."}
                }
              ]
            }"""
        }
        
        with patch.object(service._practice.ai_chat, 'generate_reply', new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = mock_response
            
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
            assert len(turns) == 2
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
        # Patch at the service boundary to avoid nondeterminism from asyncio.gather ordering.
        stage1 = _make_valid_stage1_content("食生活")
        enhanced = {
            "reading": {
                "title": {"kanji": "たべもの", "romaji": "tabemono", "furigana": [{"text": "たべもの"}], "translation": "food"},
                "content": {"kanji": "おいしいです。", "romaji": "oishii desu.", "furigana": [{"text": "おいしいです。"}], "translation": "It's tasty."},
                "comprehension": [{"q": "どんなたべものですか？", "a": "おいしいです。"}],
            },
            "dialogue": [
                {"speaker": "A", "japanese": {"kanji": "たべます。", "romaji": "tabemasu.", "furigana": [{"text": "たべます。"}], "translation": "I eat."}},
                {"speaker": "B", "japanese": {"kanji": "のみます。", "romaji": "nomimasu.", "furigana": [{"text": "のみます。"}], "translation": "I drink."}},
            ],
            "grammar": [
                {"pattern": "〜を", "explanation": "目的語", "examples": [{"kanji": "みずをのみます。", "romaji": "mizu o nomimasu.", "furigana": [{"text": "みずをのみます。"}], "translation": "I drink water."},
                                                       {"kanji": "パンをたべます。", "romaji": "pan o tabemasu.", "furigana": [{"text": "パンをたべます。"}], "translation": "I eat bread."}]},
            ],
            "culture": [
                {"title": "あいさつ", "body": {"kanji": "いただきます。", "romaji": "itadakimasu.", "furigana": [{"text": "いただきます。"}], "translation": "Let's eat."}},
                {"title": "マナー", "body": {"kanji": "ゆっくりたべます。", "romaji": "yukkuri tabemasu.", "furigana": [{"text": "ゆっくりたべます。"}], "translation": "Eat slowly."}},
            ],
        }

        async def _fake_enhance(*, section_name: str, section_data: Any, **kwargs):
            return {"success": True, "data": enhanced.get(section_name)}

        with patch.object(service, "_generate_simple_content", new_callable=AsyncMock) as mock_stage1, \
             patch.object(service, "_enhance_section_with_multilingual", new=_fake_enhance):
            mock_stage1.return_value = stage1
            result = await service._generate_master_lesson(
                can_do_id="JF:349",
                topic="食生活",
                original_level_str="A1",
                provider="openai",
                model="gpt-5",
                timeout=180,
                meta_extra={},
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
                "comprehension": [{"q": "どうですか？", "a": "美味しいです。"}]
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
            assert dialogue_result["success"] is True
            assert dialogue_result.get("fallback") is True
    
    @pytest.mark.asyncio
    async def test_pydantic_validation_catches_invalid_structure(self, service):
        """Test that malformed Stage 1 content degrades gracefully via fallback."""
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
            
            result = await service._generate_simple_content(
                can_do_id="JF:349",
                topic="食生活",
                level="A1",
                provider="openai",
                model="gpt-5",
                timeout=180
            )
            assert result.get("__meta", {}).get("fallback_stage1") is True


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
        import json
        stage1_mock = {"content": json.dumps(_make_valid_stage1_content(topic), ensure_ascii=False)}
        
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
            assert 6 <= len(result["dialogue"]) <= 8
            assert len(result["grammar"]) == 3
            assert len(result["practice"]) == 3

