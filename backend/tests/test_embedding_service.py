"""
Tests for embedding service, including message embedding generation.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.embedding_service import EmbeddingService


@pytest.fixture
def embedding_service():
    """Create EmbeddingService instance."""
    return EmbeddingService()


@pytest.fixture
def mock_postgresql_session():
    """Mock PostgreSQL session."""
    session = AsyncMock(spec=AsyncSession)
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    return session


@pytest.mark.asyncio
async def test_generate_content_embedding_openai(embedding_service):
    """Test generating embedding with OpenAI."""
    with patch.object(embedding_service.openai_client.embeddings, 'create') as mock_create:
        mock_response = MagicMock()
        mock_response.data = [MagicMock(embedding=[0.1, 0.2, 0.3] * 512)]  # 1536 dims
        mock_create.return_value = mock_response
        
        embedding = await embedding_service.generate_content_embedding("test text", "openai")
        
        assert len(embedding) == 1536
        assert embedding == [0.1, 0.2, 0.3] * 512
        mock_create.assert_called_once()


@pytest.mark.asyncio
async def test_generate_content_embedding_gemini(embedding_service):
    """Test generating embedding with Gemini."""
    if not embedding_service.genai_client:
        pytest.skip("Gemini client not configured")
    
    with patch.object(embedding_service.genai_client.models, 'embed_content') as mock_embed:
        mock_embed.return_value = MagicMock(embedding=[0.4, 0.5, 0.6] * 128)  # 384 dims
        
        embedding = await embedding_service.generate_content_embedding("test text", "gemini")
        
        assert len(embedding) == 384
        mock_embed.assert_called_once()


@pytest.mark.asyncio
async def test_generate_and_store_message_embedding(embedding_service, mock_postgresql_session):
    """Test generating and storing message embedding."""
    message_id = "123e4567-e89b-12d3-a456-426614174000"
    content = "Hello, how are you?"
    
    with patch.object(embedding_service, 'generate_content_embedding') as mock_gen:
        mock_gen.return_value = [0.1] * 1536
        
        # Mock execute result
        mock_result = MagicMock()
        mock_postgresql_session.execute.return_value = mock_result
        
        embedding = await embedding_service.generate_and_store_message_embedding(
            message_id=message_id,
            content=content,
            postgresql_session=mock_postgresql_session,
            provider="openai"
        )
        
        assert len(embedding) == 1536
        mock_postgresql_session.execute.assert_called_once()
        mock_postgresql_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_batch_generate_message_embeddings(embedding_service, mock_postgresql_session):
    """Test batch generating embeddings for messages."""
    # Mock the query result
    mock_row1 = MagicMock()
    mock_row1.id = "11111111-1111-1111-1111-111111111111"
    mock_row1.content = "Message 1"
    
    mock_row2 = MagicMock()
    mock_row2.id = "22222222-2222-2222-2222-222222222222"
    mock_row2.content = "Message 2"
    
    mock_result = MagicMock()
    mock_result.fetchall.side_effect = [
        [mock_row1, mock_row2],  # First batch
        []  # Empty second batch (terminates loop)
    ]
    
    mock_postgresql_session.execute.return_value = mock_result
    
    with patch.object(embedding_service, 'generate_and_store_message_embedding') as mock_store:
        mock_store.return_value = [0.1] * 1536
        
        stats = await embedding_service.batch_generate_message_embeddings(
            postgresql_session=mock_postgresql_session,
            batch_size=50,
            provider="openai"
        )
        
        assert stats['processed'] == 2
        assert stats['generated'] == 2
        assert stats['errors'] == 0


@pytest.mark.asyncio
async def test_semantic_search(embedding_service, mock_postgresql_session):
    """Test semantic search functionality."""
    query = "test query"
    mock_embedding = [0.1] * 1536
    
    with patch.object(embedding_service, 'generate_content_embedding') as mock_gen:
        mock_gen.return_value = mock_embedding
        
        # Mock search result
        mock_row = MagicMock()
        mock_row.neo4j_node_id = "node123"
        mock_row.node_type = "word"
        mock_row.content = "test content"
        mock_row.similarity = 0.85
        mock_row.language_code = "ja"
        
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [mock_row]
        mock_postgresql_session.execute.return_value = mock_result
        
        results = await embedding_service.semantic_search(
            query=query,
            postgresql_session=mock_postgresql_session,
            limit=10,
            similarity_threshold=0.7
        )
        
        assert len(results) == 1
        assert results[0]['neo4j_node_id'] == "node123"
        assert results[0]['similarity'] == 0.85

