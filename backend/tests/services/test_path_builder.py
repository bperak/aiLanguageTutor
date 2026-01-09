"""
Tests for Path Builder Service.

Tests the semantic path building algorithm.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.path_builder import PathBuilder


@pytest.fixture
def path_builder():
    """Create PathBuilder instance."""
    return PathBuilder()


@pytest.fixture
def mock_candos():
    """Create mock CanDo descriptors."""
    return [
        {
            "uid": "JF:1",
            "level": "A1",
            "descriptionEn": "Can introduce myself",
            "primaryTopicEn": "Self Introduction",
            "_complexity": 0.2
        },
        {
            "uid": "JF:2",
            "level": "A1",
            "descriptionEn": "Can greet people",
            "primaryTopicEn": "Greetings",
            "_complexity": 0.25
        },
        {
            "uid": "JF:3",
            "level": "A2",
            "descriptionEn": "Can order food",
            "primaryTopicEn": "Food",
            "_complexity": 0.4
        }
    ]


@pytest.fixture
def mock_profile_context():
    """Create mock profile context."""
    return {
        "current_level": "beginner_1",
        "learning_goals": ["conversation"]
    }


@pytest.mark.asyncio
async def test_find_next_semantic_cando_success(
    path_builder,
    mock_candos,
    mock_profile_context
):
    """Test finding next semantically related CanDo."""
    current = mock_candos[0]
    available = mock_candos
    visited = {current["uid"]}
    current_complexity = 0.2
    
    # Mock Neo4j session
    mock_neo4j = AsyncMock()
    
    # Mock embedding service
    with patch.object(path_builder.embedding_service, 'find_similar_candos') as mock_similar:
        mock_similar.return_value = [
            {
                "uid": "JF:2",
                "similarity": 0.8
            },
            {
                "uid": "JF:3",
                "similarity": 0.7
            }
        ]
        
        next_cando = await path_builder.find_next_semantic_cando(
            current_cando=current,
            available_candos=available,
            visited=visited,
            current_complexity=current_complexity,
            profile_context=mock_profile_context,
            neo4j_session=mock_neo4j
        )
        
        assert next_cando is not None
        assert next_cando["uid"] in ["JF:2", "JF:3"]
        assert next_cando["uid"] not in visited


@pytest.mark.asyncio
async def test_find_next_semantic_cando_no_candidates(
    path_builder,
    mock_candos,
    mock_profile_context
):
    """Test finding next CanDo when no suitable candidates exist."""
    current = mock_candos[2]  # A2 level
    available = mock_candos
    visited = {c["uid"] for c in mock_candos}
    current_complexity = 0.4
    
    # Mock Neo4j session
    mock_neo4j = AsyncMock()
    
    # Mock embedding service returning empty
    with patch.object(path_builder.embedding_service, 'find_similar_candos') as mock_similar:
        mock_similar.return_value = []
        
        next_cando = await path_builder.find_next_semantic_cando(
            current_cando=current,
            available_candos=available,
            visited=visited,
            current_complexity=current_complexity,
            profile_context=mock_profile_context,
            neo4j_session=mock_neo4j
        )
        
        assert next_cando is None


@pytest.mark.asyncio
async def test_build_semantic_path(
    path_builder,
    mock_candos,
    mock_profile_context
):
    """Test building a semantic path."""
    starting = mock_candos[:2]
    all_candos = mock_candos
    
    # Mock Neo4j session
    mock_neo4j = AsyncMock()
    
    # Mock complexity service
    with patch.object(path_builder.complexity_service, 'assess_complexity') as mock_complexity:
        # Return complexity from _complexity field
        async def assess_side_effect(cando, context):
            return cando.get("_complexity", 0.2)
        mock_complexity.side_effect = assess_side_effect
        
        # Mock embedding service
        with patch.object(path_builder.embedding_service, 'find_similar_candos') as mock_similar:
            mock_similar.return_value = [
                {"uid": "JF:2", "similarity": 0.8},
                {"uid": "JF:3", "similarity": 0.7}
            ]
            
            # Mock continuity check
            with patch.object(path_builder, 'ensure_continuity') as mock_continuity:
                mock_continuity.return_value = True
                
                path = await path_builder.build_semantic_path(
                    starting_candos=starting,
                    all_candos=all_candos,
                    profile_context=mock_profile_context,
                    neo4j_session=mock_neo4j
                )
                
                assert len(path) > 0
                assert all("_complexity" not in cando for cando in path)


@pytest.mark.asyncio
async def test_ensure_continuity_good(path_builder):
    """Test continuity verification with good path."""
    path_sequence = [
        {"uid": "JF:1"},
        {"uid": "JF:2"},
        {"uid": "JF:3"}
    ]
    
    # Mock Neo4j session
    mock_neo4j = AsyncMock()
    
    # Mock embedding service
    with patch.object(path_builder.embedding_service, 'find_similar_candos') as mock_similar:
        # Return next item as similar
        async def similar_side_effect(*, neo4j_session, can_do_uid, **kwargs):
            if can_do_uid == "JF:1":
                return [{"uid": "JF:2", "similarity": 0.8}]
            elif can_do_uid == "JF:2":
                return [{"uid": "JF:3", "similarity": 0.8}]
            return []
        
        mock_similar.side_effect = similar_side_effect
        
        result = await path_builder.ensure_continuity(path_sequence, mock_neo4j)
        
        assert result is True


@pytest.mark.asyncio
async def test_ensure_continuity_poor(path_builder):
    """Test continuity verification with poor path."""
    path_sequence = [
        {"uid": "JF:1"},
        {"uid": "JF:2"},
        {"uid": "JF:3"}
    ]
    
    # Mock Neo4j session
    mock_neo4j = AsyncMock()
    
    # Mock embedding service returning no matches
    with patch.object(path_builder.embedding_service, 'find_similar_candos') as mock_similar:
        mock_similar.return_value = []
        
        result = await path_builder.ensure_continuity(path_sequence, mock_neo4j)
        
        # Should be False due to poor continuity
        assert result is False

