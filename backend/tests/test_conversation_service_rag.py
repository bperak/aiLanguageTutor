"""
Tests for conversation service RAG functionality.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from app.services.conversation_service import ConversationService


@pytest.fixture
def mock_postgresql_session():
    """Mock PostgreSQL session."""
    session = AsyncMock(spec=AsyncSession)
    session.execute = AsyncMock()
    return session


@pytest.fixture
def sample_user_id():
    """Sample user ID."""
    return uuid.uuid4()


@pytest.fixture
def sample_session_id():
    """Sample session ID."""
    return uuid.uuid4()


@pytest.mark.asyncio
async def test_search_similar_past_conversations(
    mock_postgresql_session, sample_user_id, sample_session_id
):
    """Test searching for similar past conversations."""
    query_embedding = [0.1] * 1536
    
    # Mock search result
    mock_row = MagicMock()
    mock_row.id = uuid.uuid4()
    mock_row.session_id = uuid.uuid4()
    mock_row.content = "Previous conversation about greetings"
    mock_row.role = "user"
    mock_row.created_at = "2024-01-01T00:00:00"
    mock_row.session_title = "Greetings Practice"
    mock_row.session_type = "home"
    mock_row.similarity = 0.82
    
    mock_result = MagicMock()
    mock_result.fetchall.return_value = [mock_row]
    mock_postgresql_session.execute.return_value = mock_result
    
    results = await ConversationService.search_similar_past_conversations(
        db=mock_postgresql_session,
        user_id=sample_user_id,
        query_embedding=query_embedding,
        current_session_id=sample_session_id,
        limit=5
    )
    
    assert len(results) == 1
    assert results[0]['content'] == "Previous conversation about greetings"
    assert results[0]['similarity'] == 0.82
    assert results[0]['session_type'] == "home"


@pytest.mark.asyncio
async def test_hybrid_search_past_conversations(
    mock_postgresql_session, sample_user_id, sample_session_id
):
    """Test hybrid search combining vector and full-text search."""
    query_text = "greetings"
    query_embedding = [0.1] * 1536
    
    # Mock hybrid search result
    mock_row = MagicMock()
    mock_row.id = uuid.uuid4()
    mock_row.session_id = uuid.uuid4()
    mock_row.content = "How to greet someone"
    mock_row.role = "user"
    mock_row.created_at = "2024-01-01T00:00:00"
    mock_row.session_title = "Greetings Lesson"
    mock_row.session_type = "chat"
    mock_row.score = 0.95
    
    mock_result = MagicMock()
    mock_result.fetchall.return_value = [mock_row]
    mock_postgresql_session.execute.return_value = mock_result
    
    results = await ConversationService.hybrid_search_past_conversations(
        db=mock_postgresql_session,
        user_id=sample_user_id,
        query_text=query_text,
        query_embedding=query_embedding,
        current_session_id=sample_session_id,
        limit=5
    )
    
    assert len(results) == 1
    assert results[0]['content'] == "How to greet someone"
    assert results[0]['score'] == 0.95


@pytest.mark.asyncio
async def test_search_with_no_results(mock_postgresql_session, sample_user_id):
    """Test search when no similar conversations are found."""
    query_embedding = [0.1] * 1536
    
    mock_result = MagicMock()
    mock_result.fetchall.return_value = []
    mock_postgresql_session.execute.return_value = mock_result
    
    results = await ConversationService.search_similar_past_conversations(
        db=mock_postgresql_session,
        user_id=sample_user_id,
        query_embedding=query_embedding,
        limit=5
    )
    
    assert len(results) == 0


@pytest.mark.asyncio
async def test_search_with_filters(mock_postgresql_session, sample_user_id):
    """Test search with session type and days_back filters."""
    query_embedding = [0.1] * 1536
    
    mock_result = MagicMock()
    mock_result.fetchall.return_value = []
    mock_postgresql_session.execute.return_value = mock_result
    
    results = await ConversationService.search_similar_past_conversations(
        db=mock_postgresql_session,
        user_id=sample_user_id,
        query_embedding=query_embedding,
        session_type="home",
        days_back=30,
        limit=5
    )
    
    # Verify the query was executed with filters
    mock_postgresql_session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_build_user_conversation_profile(mock_postgresql_session, sample_user_id):
    """Test building user conversation profile."""
    # Mock profile query results
    mock_row = MagicMock()
    mock_row.content_embedding = [0.1] * 1536
    mock_row.content = "User message"
    mock_row.created_at = "2024-01-01T00:00:00"
    mock_row.session_type = "home"
    mock_row.session_title = "Greetings"
    
    mock_result = MagicMock()
    mock_result.fetchall.return_value = [mock_row]
    
    # Mock average embedding query
    mock_avg_row = MagicMock()
    mock_avg_row.avg_embedding = [0.15] * 1536
    
    mock_avg_result = MagicMock()
    mock_avg_result.fetchone.return_value = mock_avg_row
    
    # Set up execute to return different results for different queries
    def execute_side_effect(query, *args, **kwargs):
        if "AVG" in str(query):
            return mock_avg_result
        return mock_result
    
    mock_postgresql_session.execute.side_effect = execute_side_effect
    
    profile = await ConversationService.build_user_conversation_profile(
        db=mock_postgresql_session,
        user_id=sample_user_id,
        days_back=90
    )
    
    assert profile['has_profile'] is True
    assert profile['message_count'] == 1
    assert 'avg_embedding' in profile
    assert 'home' in profile['session_types']


@pytest.mark.asyncio
async def test_build_profile_no_messages(mock_postgresql_session, sample_user_id):
    """Test building profile when user has no messages."""
    mock_result = MagicMock()
    mock_result.fetchall.return_value = []
    mock_postgresql_session.execute.return_value = mock_result
    
    profile = await ConversationService.build_user_conversation_profile(
        db=mock_postgresql_session,
        user_id=sample_user_id
    )
    
    assert profile['has_profile'] is False
    assert profile['message_count'] == 0

