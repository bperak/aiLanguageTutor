"""
Unit tests for CanDoLessonSessionService.

Tests cover:
- Session creation and storage in Postgres
- Entity resolution with fallback mechanisms
- Phase gating (completion and score modes)
- Session cleanup and expiry
- Error handling (session not found, invalid LLM responses)
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timedelta

from app.services.cando_lesson_session_service import (
    CanDoLessonSessionService,
    ConversationScenario,
    DialogueTurn,
)
from app.services.lexical_lessons_service import lexical_lessons


@pytest.fixture
def service():
    """Create a CanDoLessonSessionService instance."""
    return CanDoLessonSessionService()


@pytest.fixture
def mock_neo4j_session():
    """Mock Neo4j AsyncSession."""
    session = AsyncMock()
    return session


@pytest.fixture
def mock_pg_session():
    """Mock Postgres AsyncSession."""
    session = AsyncMock()
    return session


@pytest.fixture
def sample_cando_meta():
    """Sample CanDo metadata."""
    return {
        "uid": "JF21",
        "primaryTopic": "greeting",
        "level": "A1",
        "type": "polite",
        "skillDomain": "speaking",
        "exampleSentence": "こんにちは",
        "description": "Learn to greet politely",
        "descriptionEn": "Greeting in formal context",
        "descriptionJa": "丁寧な挨拶",
    }


@pytest.fixture
def sample_master_lesson():
    """Sample master lesson JSON."""
    return {
        "uiVersion": 1,
        "lessonId": str(uuid4()),
        "canDoId": "JF21",
        "originalLevel": 1,
        "metadata": {
            "topic": "greeting",
            "languageCode": "ja",
            "createdAt": int(datetime.utcnow().timestamp()),
            "estimatedDurationMin": 20,
            "tags": ["greeting"],
        },
        "learningObjectives": ["Learn polite greeting"],
        "variantGuidelines": {
            "1": {"scaffolding": "high", "aids": ["romaji", "furigana"], "notes": []},
        },
        "ui": {
            "header": {"title": "Greeting", "subtitle": "Polite forms", "chips": ["objective", "level", "topic"]},
            "sections": [
                {
                    "id": str(uuid4()),
                    "type": "intro",
                    "title": "Introduction",
                    "cards": [
                        {
                            "id": str(uuid4()),
                            "kind": "text",
                            "title": "Welcome",
                            "body": {"jp": "こんにちは", "meta": "Say hello politely."},
                        }
                    ],
                }
            ],
        },
        "exercises": [],
        "extractedEntities": {"words": [], "grammarPatterns": []},
        "readability": {"jlptEstimate": "N5", "metrics": {"chars": 0, "sentences": 0}},
        "pdf": {"renderTemplate": "default-a4", "assetPaths": []},
    }


@pytest.fixture
def sample_conversation_scenario():
    """Sample conversation scenario."""
    return ConversationScenario(
        scenario_id="greeting_introduction_intermediate",
        pattern_id="JF21",
        pattern="こんにちは",
        context="introduction",
        situation="Meeting someone new in a formal setting",
        learning_objective="Learn polite greeting",
        ai_character="Japanese teacher",
        user_role="Student",
        difficulty_level="intermediate",
        dialogue_turns=[
            DialogueTurn(speaker="ai", message="こんにちは。はじめまして。"),
            DialogueTurn(speaker="user", message="こんにちは。"),
        ],
    )


class TestStartLessonBasic:
    """Test basic lesson startup and session creation."""

    @pytest.mark.asyncio
    async def test_start_lesson_basic(
        self, service, mock_neo4j_session, mock_pg_session, sample_cando_meta, sample_master_lesson, sample_conversation_scenario
    ):
        """Verify session creation with valid inputs; schema compliance."""
        # Mock Neo4j metadata fetch
        meta_result = AsyncMock()
        meta_result.single = AsyncMock(return_value=sample_cando_meta)
        mock_neo4j_session.run = AsyncMock(return_value=meta_result)

        # Mock LLM calls
        with patch.object(service._practice, "generate_conversation_scenario", new_callable=AsyncMock) as mock_scenario:
            with patch.object(service, "_generate_master_lesson", new_callable=AsyncMock) as mock_master:
                with patch.object(service, "_render_variant", new_callable=AsyncMock) as mock_variant:
                    with patch.object(service, "_fetch_lesson_package", new_callable=AsyncMock) as mock_package:
                        # Set up mocks
                        mock_scenario.return_value = sample_conversation_scenario
                        mock_master.return_value = sample_master_lesson
                        mock_variant.return_value = {"lessonId": sample_master_lesson["lessonId"], "level": 1, "ui": {}, "exercises": []}
                        mock_package.return_value = None

                        # Mock Postgres session store
                        mock_pg_session.execute = AsyncMock()
                        mock_pg_session.commit = AsyncMock()

                        # Call start_lesson
                        result = await service.start_lesson(
                            graph=mock_neo4j_session,
                            pg=mock_pg_session,
                            can_do_id="JF21",
                            phase="lexicon_and_patterns",
                            provider="openai",
                            learner_level=1,
                        )

                        # Assertions
                        assert "sessionId" in result
                        assert result["objective"] == sample_conversation_scenario.learning_objective
                        assert result["ai_character"] == sample_conversation_scenario.ai_character
                        assert result["user_role"] == sample_conversation_scenario.user_role
                        assert result["master"] is not None
                        assert result["variant"] is not None
                        assert "opening_turns" in result
                        
                        # Verify Postgres was called to store session
                        assert mock_pg_session.execute.called
                        assert mock_pg_session.commit.called


class TestEntityResolutionFallback:
    """Test entity resolution fallback mechanisms."""

    @pytest.mark.asyncio
    async def test_entity_resolution_fallback_words(
        self, service, mock_neo4j_session, mock_pg_session, sample_cando_meta, sample_master_lesson, sample_conversation_scenario
    ):
        """Verify deterministic extraction kicks in when < 8 words found."""
        # Mock Neo4j
        meta_result = AsyncMock()
        meta_result.single = AsyncMock(return_value=sample_cando_meta)
        mock_neo4j_session.run = AsyncMock(return_value=meta_result)

        # Mock LLM calls
        with patch.object(service._practice, "generate_conversation_scenario", new_callable=AsyncMock) as mock_scenario:
            with patch.object(service, "_generate_master_lesson", new_callable=AsyncMock) as mock_master:
                with patch.object(service, "_render_variant", new_callable=AsyncMock) as mock_variant:
                    with patch.object(service, "_fetch_lesson_package", new_callable=AsyncMock) as mock_package:
                        with patch.object(service, "_extract_entities_from_text", new_callable=AsyncMock) as mock_extract:
                            with patch.object(service, "_resolve_words", new_callable=AsyncMock) as mock_resolve_words:
                                with patch.object(service, "_deterministic_words", new_callable=AsyncMock) as mock_det_words:
                                    with patch.object(service, "_resolve_grammar", new_callable=AsyncMock) as mock_resolve_gram:
                                        with patch.object(service, "_deterministic_grammar", new_callable=AsyncMock) as mock_det_gram:
                                            # Set up mocks
                                            mock_scenario.return_value = sample_conversation_scenario
                                            mock_master.return_value = sample_master_lesson
                                            mock_variant.return_value = {"lessonId": sample_master_lesson["lessonId"], "level": 1, "ui": {}, "exercises": []}
                                            mock_package.return_value = None

                                            # Extract returns minimal entities
                                            mock_extract.return_value = {"words": [{"text": "こんにちは"}], "grammarPatterns": []}
                                            # Initial resolve returns only 3 words (< 8 threshold)
                                            mock_resolve_words.return_value = [{"text": "こんにちは"}, {"text": "は"}, {"text": "です"}]
                                            # Deterministic returns 10 words
                                            mock_det_words.return_value = [
                                                {"text": f"word{i}", "kanji": f"単語{i}"} for i in range(10)
                                            ]
                                            mock_resolve_gram.return_value = []
                                            mock_det_gram.return_value = []

                                            mock_pg_session.execute = AsyncMock()
                                            mock_pg_session.commit = AsyncMock()

                                            # Call start_lesson
                                            result = await service.start_lesson(
                                                graph=mock_neo4j_session,
                                                pg=mock_pg_session,
                                                can_do_id="JF21",
                                                provider="openai",
                                            )

                                            # Verify deterministic extraction was called (fallback)
                                            assert mock_det_words.called, "Deterministic word extraction should be called when < 8 words"
                                            # Verify final master has deterministically extracted words
                                            assert len(result["master"]["extractedEntities"]["words"]) >= 10


class TestPhaseGating:
    """Test phase gating logic (completion and score modes)."""

    @pytest.mark.asyncio
    async def test_phase_gating_completion_mode(self, service, mock_pg_session):
        """Verify phase advances after GATING_N turns in completion mode."""
        # Mock settings for completion mode
        with patch("app.services.lexical_lessons_service.settings.GATING_MODE", "completion"):
            with patch("app.services.lexical_lessons_service.settings.GATING_N", 2):
                # Test phase advancement
                result1 = lexical_lessons.compute_next_phase(
                    current_phase="lexicon_and_patterns",
                    completed_count=1,
                    score=None,
                )
                assert result1["phase"] == "lexicon_and_patterns"
                assert result1["advanced"] is False

                result2 = lexical_lessons.compute_next_phase(
                    current_phase="lexicon_and_patterns",
                    completed_count=2,
                    score=None,
                )
                assert result2["phase"] == "guided_dialogue"
                assert result2["advanced"] is True

    @pytest.mark.asyncio
    async def test_phase_gating_score_mode(self, service, mock_pg_session):
        """Verify phase advances when score >= 0.70 in score mode."""
        # Mock settings for score mode
        with patch("app.services.lexical_lessons_service.settings.GATING_MODE", "score"):
            # Test low score
            result1 = lexical_lessons.compute_next_phase(
                current_phase="lexicon_and_patterns",
                completed_count=5,
                score=0.65,
            )
            assert result1["phase"] == "lexicon_and_patterns"
            assert result1["advanced"] is False

            # Test passing score
            result2 = lexical_lessons.compute_next_phase(
                current_phase="lexicon_and_patterns",
                completed_count=5,
                score=0.75,
            )
            assert result2["phase"] == "guided_dialogue"
            assert result2["advanced"] is True


class TestSessionCleanup:
    """Test session cleanup and expiry."""

    @pytest.mark.asyncio
    async def test_session_cleanup(self, service, mock_pg_session):
        """Verify expired sessions are removed from Postgres."""
        mock_pg_session.execute = AsyncMock()
        mock_pg_session.commit = AsyncMock()

        # Call cleanup
        await service._cleanup_expired_sessions(mock_pg_session)

        # Verify execute was called with DELETE query
        assert mock_pg_session.execute.called
        call_args = mock_pg_session.execute.call_args
        assert "DELETE" in str(call_args)
        assert "expires_at" in str(call_args)
        assert mock_pg_session.commit.called

    @pytest.mark.asyncio
    async def test_session_store_and_retrieve(self, service, mock_pg_session):
        """Verify session storage and retrieval from Postgres."""
        session_id = str(uuid4())
        session_data = {
            "can_do_id": "JF21",
            "phase": "lexicon_and_patterns",
            "completed_count": 2,
            "scenario": {"scenario_id": "test", "pattern_id": "JF21", "pattern": "test"},
            "master": {"lessonId": str(uuid4())},
            "variant": {"lessonId": str(uuid4()), "level": 1},
            "package": None,
        }

        # Mock execute for store
        mock_pg_session.execute = AsyncMock()
        mock_pg_session.commit = AsyncMock()

        # Store session
        await service._store_session(mock_pg_session, session_id, session_data)
        assert mock_pg_session.execute.called
        assert mock_pg_session.commit.called

        # Mock retrieve
        mock_result = MagicMock()
        mock_result.first = MagicMock(
            return_value=(
                session_id,  # id
                "JF21",  # can_do_id
                "lexicon_and_patterns",  # phase
                2,  # completed_count
                json.dumps(session_data["scenario"]),  # scenario_json
                json.dumps(session_data["master"]),  # master_json
                json.dumps(session_data["variant"]),  # variant_json
                None,  # package_json
                (datetime.utcnow() + timedelta(hours=1)).isoformat(),  # expires_at
            )
        )
        mock_pg_session.execute = AsyncMock(return_value=mock_result)

        # Retrieve session
        retrieved = await service._retrieve_session(mock_pg_session, session_id)
        assert retrieved is not None
        assert retrieved["can_do_id"] == "JF21"
        assert retrieved["phase"] == "lexicon_and_patterns"
        assert retrieved["completed_count"] == 2


class TestErrorHandling:
    """Test error handling and edge cases."""

    @pytest.mark.asyncio
    async def test_session_not_found(self, service, mock_pg_session):
        """Verify graceful handling when session not found."""
        session_id = str(uuid4())
        mock_result = MagicMock()
        mock_result.first = MagicMock(return_value=None)
        mock_pg_session.execute = AsyncMock(return_value=mock_result)

        # Retrieve non-existent session
        retrieved = await service._retrieve_session(mock_pg_session, session_id)
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_invalid_llm_response(self, service, mock_neo4j_session, mock_pg_session, sample_cando_meta):
        """Verify graceful fallback when LLM returns invalid JSON."""
        # Mock Neo4j
        meta_result = AsyncMock()
        meta_result.single = AsyncMock(return_value=sample_cando_meta)
        mock_neo4j_session.run = AsyncMock(return_value=meta_result)

        # Mock scenario generation to fail
        with patch.object(service._practice, "generate_conversation_scenario", new_callable=AsyncMock) as mock_scenario:
            mock_scenario.side_effect = ValueError("Invalid LLM response")

            mock_pg_session.execute = AsyncMock()
            mock_pg_session.commit = AsyncMock()

            # Call start_lesson should propagate error (non-recoverable at this level)
            with pytest.raises(ValueError):
                await service.start_lesson(
                    graph=mock_neo4j_session,
                    pg=mock_pg_session,
                    can_do_id="JF21",
                    provider="openai",
                )

    @pytest.mark.asyncio
    async def test_entity_extraction_non_fatal(
        self, service, mock_neo4j_session, mock_pg_session, sample_cando_meta, sample_master_lesson, sample_conversation_scenario
    ):
        """Verify entity extraction failure is non-fatal; lesson still renders."""
        # Mock Neo4j
        meta_result = AsyncMock()
        meta_result.single = AsyncMock(return_value=sample_cando_meta)
        mock_neo4j_session.run = AsyncMock(return_value=meta_result)

        # Mock LLM calls
        with patch.object(service._practice, "generate_conversation_scenario", new_callable=AsyncMock) as mock_scenario:
            with patch.object(service, "_generate_master_lesson", new_callable=AsyncMock) as mock_master:
                with patch.object(service, "_render_variant", new_callable=AsyncMock) as mock_variant:
                    with patch.object(service, "_fetch_lesson_package", new_callable=AsyncMock) as mock_package:
                        with patch.object(service, "_extract_entities_from_text", new_callable=AsyncMock) as mock_extract:
                            # Entity extraction fails
                            mock_extract.side_effect = RuntimeError("Neo4j error")

                            mock_scenario.return_value = sample_conversation_scenario
                            mock_master.return_value = sample_master_lesson
                            mock_variant.return_value = {"lessonId": sample_master_lesson["lessonId"], "level": 1, "ui": {}, "exercises": []}
                            mock_package.return_value = None

                            mock_pg_session.execute = AsyncMock()
                            mock_pg_session.commit = AsyncMock()

                            # Call start_lesson - should still succeed despite entity extraction failure
                            result = await service.start_lesson(
                                graph=mock_neo4j_session,
                                pg=mock_pg_session,
                                can_do_id="JF21",
                                provider="openai",
                            )

                            # Lesson still created
                            assert "sessionId" in result
                            assert result["master"] is not None
