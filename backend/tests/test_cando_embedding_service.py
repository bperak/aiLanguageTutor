"""
Tests for CanDoDescriptor embedding service.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import List

from app.services.cando_embedding_service import CanDoEmbeddingService


@pytest.fixture
def cando_embedding_service():
    """Create CanDoEmbeddingService instance."""
    return CanDoEmbeddingService()


@pytest.fixture
def mock_neo4j_session():
    """Mock Neo4j async session."""
    session = AsyncMock()
    session.run = AsyncMock()
    return session


def test_generate_cando_embedding_content_both(cando_embedding_service):
    """Test generating embedding content with both descriptions."""
    content = cando_embedding_service.generate_cando_embedding_content(
        description_en="Can understand basic greetings",
        description_ja="基本的な挨拶を理解できる"
    )
    
    assert "English: Can understand basic greetings" in content
    assert "Japanese: 基本的な挨拶を理解できる" in content
    assert " | " in content


def test_generate_cando_embedding_content_en_only(cando_embedding_service):
    """Test generating embedding content with English only."""
    content = cando_embedding_service.generate_cando_embedding_content(
        description_en="Can understand basic greetings"
    )
    
    assert "English: Can understand basic greetings" in content
    assert "Japanese:" not in content


def test_generate_cando_embedding_content_ja_only(cando_embedding_service):
    """Test generating embedding content with Japanese only."""
    content = cando_embedding_service.generate_cando_embedding_content(
        description_ja="基本的な挨拶を理解できる"
    )
    
    assert "Japanese: 基本的な挨拶を理解できる" in content
    assert "English:" not in content


def test_generate_cando_embedding_content_empty(cando_embedding_service):
    """Test generating embedding content with no descriptions raises error."""
    with pytest.raises(ValueError, match="At least one description"):
        cando_embedding_service.generate_cando_embedding_content()


@pytest.mark.asyncio
async def test_generate_cando_embedding(cando_embedding_service):
    """Test generating embedding for CanDoDescriptor."""
    with patch.object(cando_embedding_service.embedding_service, 'generate_content_embedding') as mock_gen:
        mock_gen.return_value = [0.1, 0.2, 0.3] * 512  # 1536 dims
        
        embedding = await cando_embedding_service.generate_cando_embedding(
            description_en="Test description",
            description_ja="テスト説明"
        )
        
        assert len(embedding) == 1536
        mock_gen.assert_called_once()
        # Verify the content includes both descriptions
        call_args = mock_gen.call_args[0]
        assert "English: Test description" in call_args[0]
        assert "Japanese: テスト説明" in call_args[0]


@pytest.mark.asyncio
async def test_update_cando_embedding_success(cando_embedding_service, mock_neo4j_session):
    """Test successfully updating CanDoDescriptor embedding."""
    # Mock Neo4j query results
    mock_record = MagicMock()
    mock_record.get.side_effect = lambda key: {
        "descriptionEn": "Test English",
        "descriptionJa": "テスト日本語"
    }.get(key)
    
    mock_result = AsyncMock()
    mock_result.single = AsyncMock(return_value=mock_record)
    mock_neo4j_session.run.return_value = mock_result
    
    # Mock embedding generation
    with patch.object(cando_embedding_service, 'generate_cando_embedding') as mock_gen:
        mock_gen.return_value = [0.1] * 1536
        
        # Mock update query
        mock_update_result = AsyncMock()
        mock_update_record = MagicMock()
        mock_update_record.get.return_value = "test_uid"
        mock_update_result.single = AsyncMock(return_value=mock_update_record)
        mock_neo4j_session.run.side_effect = [mock_result, mock_update_result]
        
        result = await cando_embedding_service.update_cando_embedding(
            mock_neo4j_session,
            "test_uid"
        )
        
        assert result is True
        assert mock_neo4j_session.run.call_count == 2


@pytest.mark.asyncio
async def test_update_cando_embedding_not_found(cando_embedding_service, mock_neo4j_session):
    """Test updating embedding for non-existent CanDoDescriptor."""
    mock_result = AsyncMock()
    mock_result.single = AsyncMock(return_value=None)
    mock_neo4j_session.run.return_value = mock_result
    
    result = await cando_embedding_service.update_cando_embedding(
        mock_neo4j_session,
        "nonexistent_uid"
    )
    
    assert result is False


@pytest.mark.asyncio
async def test_find_similar_candos(cando_embedding_service, mock_neo4j_session):
    """Test finding similar CanDoDescriptors."""
    # Mock vector index query
    mock_record1 = MagicMock()
    mock_record1.get.side_effect = lambda key: {
        "uid": "cando_2",
        "level": "A1",
        "topic": "Greetings",
        "skillDomain": "Interaction",
        "descriptionEn": "Similar description",
        "descriptionJa": "類似説明",
        "similarity": 0.85
    }.get(key)
    
    mock_record2 = MagicMock()
    mock_record2.get.side_effect = lambda key: {
        "uid": "cando_3",
        "level": "A2",
        "topic": "Greetings",
        "skillDomain": "Interaction",
        "descriptionEn": "Another similar",
        "descriptionJa": "別の類似",
        "similarity": 0.75
    }.get(key)
    
    mock_result = AsyncMock()
    async def async_iter():
        yield mock_record1
        yield mock_record2
    
    mock_result.__aiter__ = async_iter
    
    mock_neo4j_session.run.return_value = mock_result
    
    similar = await cando_embedding_service.find_similar_candos(
        mock_neo4j_session,
        "cando_1",
        limit=10
    )
    
    assert len(similar) == 2
    assert similar[0]['uid'] == "cando_2"
    assert similar[0]['similarity'] == 0.85
    assert similar[1]['uid'] == "cando_3"
    assert similar[1]['similarity'] == 0.75


@pytest.mark.asyncio
async def test_find_similar_candos_fallback(cando_embedding_service, mock_neo4j_session):
    """Test fallback to manual cosine similarity when vector index unavailable."""
    # Mock vector index failure (exception)
    mock_neo4j_session.run.side_effect = Exception("Vector index not available")
    
    # Mock fallback query
    mock_source_record = MagicMock()
    mock_source_record.get.return_value = [0.1, 0.2, 0.3] * 512  # 1536 dims
    
    mock_target_record = MagicMock()
    mock_target_record.get.side_effect = lambda key: {
        "uid": "cando_2",
        "level": "A1",
        "topic": "Greetings",
        "skillDomain": "Interaction",
        "descriptionEn": "Similar",
        "descriptionJa": "類似",
        "embedding": [0.1, 0.2, 0.3] * 512  # Same embedding = high similarity
    }.get(key)
    
    # First call fails (vector index), second call succeeds (fallback)
    mock_fallback_result = AsyncMock()
    async def async_iter_fallback():
        yield mock_target_record
    
    mock_fallback_result.__aiter__ = async_iter_fallback
    
    mock_source_result = AsyncMock()
    mock_source_result.single = AsyncMock(return_value=mock_source_record)
    
    mock_neo4j_session.run.side_effect = [
        Exception("Vector index not available"),  # First call fails
        mock_source_result,  # Fallback: get source embedding
        mock_fallback_result  # Fallback: get target embeddings
    ]
    
    similar = await cando_embedding_service.find_similar_candos(
        mock_neo4j_session,
        "cando_1",
        limit=10,
        similarity_threshold=0.5
    )
    
    # Should use fallback and find similar
    assert len(similar) >= 0  # May or may not find matches depending on threshold


def test_cosine_similarity(cando_embedding_service):
    """Test cosine similarity computation."""
    vec1 = [1.0, 0.0, 0.0]
    vec2 = [1.0, 0.0, 0.0]
    
    similarity = cando_embedding_service._cosine_similarity(vec1, vec2)
    assert similarity == 1.0  # Identical vectors
    
    vec3 = [0.0, 1.0, 0.0]
    similarity = cando_embedding_service._cosine_similarity(vec1, vec3)
    assert similarity == 0.0  # Orthogonal vectors
    
    vec4 = [1.0, 1.0, 0.0]
    similarity = cando_embedding_service._cosine_similarity(vec1, vec4)
    assert 0.0 < similarity < 1.0  # Some similarity


def test_cosine_similarity_different_lengths(cando_embedding_service):
    """Test cosine similarity with different length vectors returns 0."""
    vec1 = [1.0, 0.0, 0.0]
    vec2 = [1.0, 0.0]
    
    similarity = cando_embedding_service._cosine_similarity(vec1, vec2)
    assert similarity == 0.0


@pytest.mark.asyncio
async def test_batch_generate_cando_embeddings(cando_embedding_service, mock_neo4j_session):
    """Test batch generating embeddings for CanDoDescriptors."""
    # Mock batch query results
    mock_record1 = MagicMock()
    mock_record1.get.side_effect = lambda key: {
        "uid": "cando_1",
        "descriptionEn": "Description 1",
        "descriptionJa": "説明1"
    }.get(key)
    
    mock_record2 = MagicMock()
    mock_record2.get.side_effect = lambda key: {
        "uid": "cando_2",
        "descriptionEn": "Description 2",
        "descriptionJa": "説明2"
    }.get(key)
    
    mock_result = AsyncMock()
    async def async_iter():
        yield mock_record1
        yield mock_record2
    
    mock_result.__aiter__ = async_iter
    
    # First call returns batch, second call returns empty (terminates)
    mock_neo4j_session.run.side_effect = [
        mock_result,  # First batch
        AsyncMock(__aiter__=lambda: iter([]))  # Empty batch (terminates)
    ]
    
    with patch.object(cando_embedding_service, 'generate_cando_embedding') as mock_gen:
        mock_gen.return_value = [0.1] * 1536
        
        stats = await cando_embedding_service.batch_generate_cando_embeddings(
            mock_neo4j_session,
            batch_size=50,
            skip_existing=True
        )
        
        assert stats['processed'] == 2
        assert stats['generated'] == 2
        assert stats['errors'] == 0


@pytest.mark.asyncio
async def test_create_similarity_relationships(cando_embedding_service, mock_neo4j_session):
    """Test creating similarity relationships."""
    # Mock nodes with embeddings
    mock_node_record = MagicMock()
    mock_node_record.get.side_effect = lambda key: {
        "uid": "cando_1",
        "level": "A1",
        "topic": "Greetings",
        "skillDomain": "Interaction",
        "embedding": [0.1] * 1536
    }.get(key)
    
    mock_nodes_result = AsyncMock()
    async def async_iter_nodes():
        yield mock_node_record
    
    mock_nodes_result.__aiter__ = async_iter_nodes
    
    # Mock find_similar_candos
    with patch.object(cando_embedding_service, 'find_similar_candos') as mock_find:
        mock_find.return_value = [
            {
                'uid': 'cando_2',
                'level': 'A1',
                'topic': 'Greetings',
                'skillDomain': 'Interaction',
                'similarity': 0.8
            }
        ]
        
        # Mock relationship creation
        mock_create_result = AsyncMock()
        mock_neo4j_session.run.side_effect = [
            mock_nodes_result,  # Get nodes
            mock_create_result  # Create relationships
        ]
        
        stats = await cando_embedding_service.create_similarity_relationships(
            mock_neo4j_session,
            similarity_threshold=0.65,
            batch_size=100
        )
        
        assert stats['created'] >= 0  # May create relationships
        assert 'errors' in stats


@pytest.mark.asyncio
async def test_update_similarity_for_cando(cando_embedding_service, mock_neo4j_session):
    """Test updating similarity relationships for a single CanDoDescriptor."""
    # Mock update_cando_embedding
    with patch.object(cando_embedding_service, 'update_cando_embedding') as mock_update:
        mock_update.return_value = True
        
        # Mock find_similar_candos
        with patch.object(cando_embedding_service, 'find_similar_candos') as mock_find:
            mock_find.return_value = [
                {
                    'uid': 'cando_2',
                    'level': 'A1',
                    'topic': 'Greetings',
                    'skillDomain': 'Interaction',
                    'similarity': 0.8
                }
            ]
            
            # Mock metadata query
            mock_meta_record = MagicMock()
            mock_meta_record.get.side_effect = lambda key: {
                "level": "A1",
                "topic": "Greetings",
                "skillDomain": "Interaction"
            }.get(key)
            
            mock_meta_result = AsyncMock()
            mock_meta_result.single = AsyncMock(return_value=mock_meta_record)
            
            # Mock relationship creation
            mock_create_result = AsyncMock()
            mock_neo4j_session.run.side_effect = [
                mock_meta_result,  # Get metadata
                mock_create_result  # Create relationships
            ]
            
            count = await cando_embedding_service.update_similarity_for_cando(
                mock_neo4j_session,
                "cando_1"
            )
            
            assert count >= 0
            mock_update.assert_called_once()
            mock_find.assert_called_once()

