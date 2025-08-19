"""
Tests for Grammar Service
========================

Comprehensive tests for the Marugoto grammar patterns service layer.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from typing import List, Dict, Any

from backend.app.services.grammar_service import GrammarService

@pytest.fixture
def mock_neo4j_session():
    """Mock Neo4j session for testing"""
    session = AsyncMock()
    return session

@pytest.fixture
def grammar_service(mock_neo4j_session):
    """Grammar service instance with mocked session"""
    return GrammarService(mock_neo4j_session)

class TestGrammarService:
    """Test cases for GrammarService"""
    
    @pytest.mark.asyncio
    async def test_get_patterns_no_filters(self, grammar_service, mock_neo4j_session):
        """Test getting patterns without filters"""
        # Mock response data
        mock_records = [
            {
                'id': 'grammar_001',
                'sequence_number': 1,
                'pattern': '～は～です',
                'pattern_romaji': '~wa~desu',
                'textbook': '入門(りかい)',
                'classification': '説明'
            },
            {
                'id': 'grammar_002', 
                'sequence_number': 2,
                'pattern': '～ができる',
                'pattern_romaji': '~ga dekiru',
                'textbook': '入門(りかい)',
                'classification': '可能・難易'
            }
        ]
        
        # Setup mock
        mock_result = AsyncMock()
        mock_result.__aiter__.return_value = iter(mock_records)
        mock_neo4j_session.run.return_value = mock_result
        
        # Test
        patterns = await grammar_service.get_patterns(limit=20, offset=0)
        
        # Assertions
        assert len(patterns) == 2
        assert patterns[0]['pattern'] == '～は～です'
        assert patterns[1]['pattern'] == '～ができる'
        mock_neo4j_session.run.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_pattern_by_id(self, grammar_service, mock_neo4j_session):
        """Test getting a specific pattern by ID"""
        mock_record = {
            'id': 'grammar_001',
            'pattern': '～は～です',
            'pattern_romaji': '~wa~desu'
        }
        
        mock_result = AsyncMock()
        mock_result.single.return_value = mock_record
        mock_neo4j_session.run.return_value = mock_result
        
        # Test
        pattern = await grammar_service.get_pattern_by_id('grammar_001')
        
        # Assertions
        assert pattern is not None
        assert pattern['pattern'] == '～は～です'
        mock_neo4j_session.run.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_similar_patterns(self, grammar_service, mock_neo4j_session):
        """Test getting similar patterns"""
        mock_records = [
            {
                'pattern': '～も',
                'pattern_romaji': '~mo',
                'textbook': '入門(りかい)',
                'similarity_reason': 'same_classification'
            }
        ]
        
        mock_result = AsyncMock()
        mock_result.__aiter__.return_value = iter(mock_records)
        mock_neo4j_session.run.return_value = mock_result
        
        # Test
        similar = await grammar_service.get_similar_patterns('grammar_001', limit=5)
        
        # Assertions
        assert len(similar) == 1
        assert similar[0]['pattern'] == '～も'
        assert similar[0]['similarity_reason'] == 'same_classification'

# Utility functions for test data
def create_mock_grammar_pattern(
    id: str = "grammar_001",
    pattern: str = "～は～です",
    textbook: str = "入門(りかい)"
) -> Dict[str, Any]:
    """Create mock grammar pattern data for testing"""
    return {
        'id': id,
        'sequence_number': 1,
        'pattern': pattern,
        'pattern_romaji': '~wa~desu',
        'textbook_form': 'N1はN2です',
        'textbook_form_romaji': 'N1 wa N2 desu',
        'example_sentence': '私はカーラです。',
        'example_romaji': 'Watashi wa Kaara desu.',
        'classification': '説明',
        'textbook': textbook,
        'topic': 'わたし',
        'lesson': 'どうぞよろしく',
        'jfs_category': '自分と家族'
    }
