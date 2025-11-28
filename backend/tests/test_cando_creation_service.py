"""
Tests for CanDoCreationService.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.cando_creation_service import CanDoCreationService


@pytest.fixture
def creation_service():
    """Fixture for CanDoCreationService."""
    return CanDoCreationService()


@pytest.fixture
def mock_neo4j_session():
    """Mock Neo4j session."""
    session = MagicMock()
    session.run = AsyncMock()
    return session


@pytest.mark.asyncio
async def test_translate_description_en_to_ja(creation_service):
    """Test translating English to Japanese."""
    with patch.object(creation_service.ai_service, 'generate_reply') as mock_reply:
        mock_reply.return_value = {"content": "基本的な旅行関連の語彙を理解し使用できる"}
        
        translated = await creation_service.translate_description(
            "Can understand and use basic travel-related vocabulary",
            "en",
            "ja"
        )
        
        assert len(translated) > 0
        mock_reply.assert_called_once()


@pytest.mark.asyncio
async def test_translate_description_ja_to_en(creation_service):
    """Test translating Japanese to English."""
    with patch.object(creation_service.ai_service, 'generate_reply') as mock_reply:
        mock_reply.return_value = {"content": "Can understand and use basic travel-related vocabulary"}
        
        translated = await creation_service.translate_description(
            "基本的な旅行関連の語彙を理解し使用できる",
            "ja",
            "en"
        )
        
        assert len(translated) > 0
        assert "travel" in translated.lower() or "vocabulary" in translated.lower()
        mock_reply.assert_called_once()


@pytest.mark.asyncio
async def test_infer_cando_fields(creation_service):
    """Test inferring CanDo fields from descriptions."""
    with patch.object(creation_service.ai_service, 'generate_reply') as mock_reply:
        mock_reply.return_value = {
            "content": '{"level": "A2", "primaryTopic": "旅行と交通", "primaryTopicEn": "Travel and Transportation", "skillDomain": "やりとり", "type": "言語活動"}'
        }
        
        fields = await creation_service.infer_cando_fields(
            description_en="Can talk about travel and transportation",
            description_ja="旅行と交通について話すことができる"
        )
        
        assert "level" in fields
        assert "primaryTopic" in fields
        assert "primaryTopicEn" in fields
        assert "skillDomain" in fields
        assert "type" in fields
        assert fields["level"] in ["A1", "A2", "B1", "B2", "C1", "C2"]


@pytest.mark.asyncio
async def test_create_cando_with_translation(creation_service, mock_neo4j_session):
    """Test creating CanDo with translation when only one description provided."""
    # Mock translation
    with patch.object(creation_service, 'translate_description') as mock_translate:
        mock_translate.return_value = "旅行と交通について話すことができる"
        
        # Mock field inference
        with patch.object(creation_service, 'infer_cando_fields') as mock_infer:
            mock_infer.return_value = {
                "level": "A2",
                "primaryTopic": "旅行と交通",
                "primaryTopicEn": "Travel and Transportation",
                "skillDomain": "やりとり",
                "type": "言語活動"
            }
            
            # Mock title generation
            with patch.object(creation_service.title_service, 'generate_titles') as mock_titles:
                mock_titles.return_value = {
                    "titleEn": "Can talk about travel",
                    "titleJa": "旅行について話すことができる"
                }
                
                # Mock UID generation
                with patch.object(creation_service, '_generate_uid') as mock_uid:
                    mock_uid.return_value = "manual:1234567890"
                    
                    # Mock embedding service
                    with patch.object(creation_service.embedding_service, 'update_cando_embedding') as mock_emb:
                        mock_emb.return_value = True
                        
                        # Mock similarity update
                        with patch.object(creation_service.embedding_service, 'update_similarity_for_cando') as mock_sim:
                            mock_sim.return_value = 10
                            
                            # Mock session.run for CREATE and RETURN
                            mock_neo4j_session.run.side_effect = [
                                AsyncMock(),  # CREATE
                                AsyncMock(single=AsyncMock(return_value={
                                    "uid": "manual:1234567890",
                                    "level": "A2",
                                    "primaryTopic": "旅行と交通",
                                    "primaryTopicEn": "Travel and Transportation",
                                    "skillDomain": "やりとり",
                                    "type": "言語活動",
                                    "descriptionEn": "Can talk about travel and transportation",
                                    "descriptionJa": "旅行と交通について話すことができる",
                                    "titleEn": "Can talk about travel",
                                    "titleJa": "旅行について話すことができる",
                                    "source": "manual"
                                }))  # RETURN
                            ]
                            
                            result = await creation_service.create_cando_with_auto_processing(
                                description_en="Can talk about travel and transportation",
                                description_ja=None,
                                session=mock_neo4j_session
                            )
                            
                            assert result["uid"] == "manual:1234567890"
                            assert result["level"] == "A2"
                            mock_translate.assert_called_once()
                            mock_infer.assert_called_once()
                            mock_titles.assert_called_once()


@pytest.mark.asyncio
async def test_create_cando_requires_description(creation_service, mock_neo4j_session):
    """Test that at least one description is required."""
    with pytest.raises(ValueError, match="At least one description"):
        await creation_service.create_cando_with_auto_processing(
            description_en=None,
            description_ja=None,
            session=mock_neo4j_session
        )


@pytest.mark.asyncio
async def test_generate_uid(creation_service, mock_neo4j_session):
    """Test UID generation."""
    # Mock session to return no existing UID
    mock_neo4j_session.run.return_value = AsyncMock(single=AsyncMock(return_value=None))
    
    uid = await creation_service._generate_uid(mock_neo4j_session)
    
    assert uid.startswith("manual:")
    assert len(uid) > 0

