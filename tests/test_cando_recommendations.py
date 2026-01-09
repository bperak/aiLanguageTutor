"""
Tests for CanDo recommendation service.
"""

import pytest
from datetime import datetime, date
from uuid import uuid4
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.cando_recommendation_service import CanDoRecommendationService
from app.models.database_models import ConversationInteraction


@pytest.fixture
def recommendation_service():
    return CanDoRecommendationService()


@pytest.fixture
def mock_pg():
    return AsyncMock()


@pytest.fixture
def mock_neo4j():
    return AsyncMock()


@pytest.fixture
def sample_interactions():
    """Sample interactions for testing."""
    interaction1 = ConversationInteraction()
    interaction1.concept_id = "JF21"
    interaction1.concept_type = "cando_lesson"
    interaction1.is_correct = True
    interaction1.mastery_level = 3
    interaction1.created_at = datetime.utcnow()
    interaction1.evidence_metadata = {"stage": "content", "error_tags": []}
    
    interaction2 = ConversationInteraction()
    interaction2.concept_id = "JF21"
    interaction2.concept_type = "cando_lesson"
    interaction2.is_correct = False
    interaction2.mastery_level = 2
    interaction2.created_at = datetime.utcnow()
    interaction2.evidence_metadata = {"stage": "comprehension", "error_tags": ["form_error"]}
    
    interaction3 = ConversationInteraction()
    interaction3.concept_id = "JF22"
    interaction3.concept_type = "cando_lesson"
    interaction3.is_correct = True
    interaction3.mastery_level = 1
    interaction3.created_at = datetime.utcnow()
    interaction3.evidence_metadata = {"stage": "content", "error_tags": []}
    
    return [interaction1, interaction2, interaction3]


@pytest.mark.asyncio
async def test_get_recommendations_no_evidence(recommendation_service, mock_pg, mock_neo4j):
    """Test recommendations when user has no evidence."""
    user_id = str(uuid4())
    
    # Mock empty interactions
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_pg.execute = AsyncMock(return_value=mock_result)
    
    # Mock Neo4j query for all CanDo - need async iterable
    async def async_iter(_self=None):
        mock_record = MagicMock()
        mock_record.get = MagicMock(side_effect=lambda k, default=None: {"uid": "JF21", "title_en": "Test", "title_ja": None, "level": "A1", "topic": "greeting"}.get(k, default))
        yield mock_record
    
    mock_neo4j_result = AsyncMock()
    mock_neo4j_result.__aiter__ = async_iter
    mock_neo4j.run = AsyncMock(return_value=mock_neo4j_result)
    
    recommendations = await recommendation_service.get_recommendations(
        pg=mock_pg,
        neo4j_session=mock_neo4j,
        user_id=user_id,
        limit=5
    )
    
    assert recommendations["total_lessons_studied"] == 0
    assert recommendations["total_attempts"] == 0
    assert recommendations["next_lesson"] is not None  # Should recommend first CanDo


@pytest.mark.asyncio
async def test_get_recommendations_with_evidence(recommendation_service, mock_pg, mock_neo4j, sample_interactions):
    """Test recommendations with existing evidence."""
    user_id = str(uuid4())
    
    # Mock interactions
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = sample_interactions
    mock_pg.execute = AsyncMock(return_value=mock_result)
    
    # Mock Neo4j query - need async iterable
    async def async_iter(_self=None):
        mock_record = MagicMock()
        mock_record.get = MagicMock(side_effect=lambda k, default=None: {"uid": "JF23", "title_en": "New Lesson", "title_ja": None, "level": "A1", "topic": "greeting"}.get(k, default))
        yield mock_record
    
    mock_neo4j_result = AsyncMock()
    mock_neo4j_result.__aiter__ = async_iter
    mock_neo4j.run = AsyncMock(return_value=mock_neo4j_result)
    
    recommendations = await recommendation_service.get_recommendations(
        pg=mock_pg,
        neo4j_session=mock_neo4j,
        user_id=user_id,
        limit=5
    )
    
    assert recommendations["total_lessons_studied"] == 2  # JF21 and JF22
    assert recommendations["total_attempts"] == 3
    assert len(recommendations["review_items"]) > 0  # Should include low mastery
    assert len(recommendations["focus_areas"]) > 0  # Should identify focus areas
    assert "form_error" in recommendations["common_errors"]


@pytest.mark.asyncio
async def test_get_recommendations_finds_unstudied(recommendation_service, mock_pg, mock_neo4j, sample_interactions):
    """Test that recommendations prioritize unstudied CanDo."""
    user_id = str(uuid4())
    
    # Mock interactions (only JF21 and JF22 studied)
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = sample_interactions
    mock_pg.execute = AsyncMock(return_value=mock_result)
    
    # Mock Neo4j query returning unstudied CanDo - need async iterable
    async def async_iter(_self=None):
        mock_record1 = MagicMock()
        mock_record1.get = MagicMock(side_effect=lambda k, default=None: {"uid": "JF23", "title_en": "Unstudied", "title_ja": None, "level": "A1", "topic": "greeting"}.get(k, default))
        yield mock_record1
        mock_record2 = MagicMock()
        mock_record2.get = MagicMock(side_effect=lambda k, default=None: {"uid": "JF24", "title_en": "Another", "title_ja": None, "level": "A1", "topic": "greeting"}.get(k, default))
        yield mock_record2
    
    mock_neo4j_result = AsyncMock()
    mock_neo4j_result.__aiter__ = async_iter
    mock_neo4j.run = AsyncMock(return_value=mock_neo4j_result)
    
    recommendations = await recommendation_service.get_recommendations(
        pg=mock_pg,
        neo4j_session=mock_neo4j,
        user_id=user_id,
        limit=5
    )
    
    assert recommendations["next_lesson"] is not None
    assert recommendations["next_lesson"]["can_do_id"] == "JF23"  # First unstudied
    assert recommendations["next_lesson"]["reason"] == "not_studied"


@pytest.mark.asyncio
async def test_get_recommendations_error_handling(recommendation_service, mock_pg, mock_neo4j):
    """Test that errors are handled gracefully."""
    user_id = str(uuid4())
    
    # Mock error
    mock_pg.execute.side_effect = Exception("Database error")
    
    recommendations = await recommendation_service.get_recommendations(
        pg=mock_pg,
        neo4j_session=mock_neo4j,
        user_id=user_id,
        limit=5
    )
    
    # Should return empty recommendations, not raise
    assert recommendations["next_lesson"] is None
    assert recommendations["total_lessons_studied"] == 0

