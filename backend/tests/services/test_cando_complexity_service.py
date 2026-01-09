"""
Tests for CanDo Complexity Service.

Tests AI-based complexity assessment for CanDo descriptors.
"""

import pytest
from unittest.mock import AsyncMock, patch

from app.services.cando_complexity_service import CanDoComplexityService


@pytest.fixture
def complexity_service():
    """Create CanDoComplexityService instance."""
    return CanDoComplexityService()


@pytest.fixture
def mock_cando():
    """Create mock CanDo descriptor."""
    return {
        "uid": "JF:1",
        "level": "A1",
        "descriptionEn": "Can introduce myself",
        "descriptionJa": "自己紹介ができる"
    }


def test_map_level_to_numeric(complexity_service):
    """Test CEFR level to numeric mapping."""
    assert complexity_service._map_level_to_numeric("A1") == 0.1
    assert complexity_service._map_level_to_numeric("A2") == 0.25
    assert complexity_service._map_level_to_numeric("B1") == 0.4
    assert complexity_service._map_level_to_numeric("B2") == 0.55
    assert complexity_service._map_level_to_numeric("C1") == 0.75
    assert complexity_service._map_level_to_numeric("C2") == 0.9
    assert complexity_service._map_level_to_numeric(None) == 0.0
    assert complexity_service._map_level_to_numeric("INVALID") == 0.0


@pytest.mark.asyncio
async def test_assess_complexity_success(complexity_service, mock_cando):
    """Test successful complexity assessment."""
    profile_context = {"current_level": "beginner_1"}
    
    # Mock AI service
    with patch.object(complexity_service.ai_service, 'generate_reply') as mock_ai:
        mock_ai.return_value = {
            "content": '{"complexity_score": 0.3}'
        }
        
        complexity = await complexity_service.assess_complexity(
            mock_cando,
            profile_context
        )
        
        assert 0.0 <= complexity <= 1.0
        assert complexity > 0.0  # Should have some complexity


@pytest.mark.asyncio
async def test_assess_complexity_fallback(complexity_service, mock_cando):
    """Test complexity assessment fallback to level-based."""
    profile_context = {"current_level": "beginner_1"}
    
    # Mock AI service failure
    with patch.object(complexity_service.ai_service, 'generate_reply') as mock_ai:
        mock_ai.side_effect = Exception("AI service error")
        
        complexity = await complexity_service.assess_complexity(
            mock_cando,
            profile_context
        )
        
        # Should fallback to level-based complexity
        assert complexity == 0.1  # A1 level


@pytest.mark.asyncio
async def test_compare_complexity(complexity_service, mock_cando):
    """Test comparing complexity of two CanDo descriptors."""
    cando1 = {**mock_cando, "level": "A1"}
    cando2 = {**mock_cando, "level": "A2", "uid": "JF:2"}
    
    # Mock AI service
    with patch.object(complexity_service.ai_service, 'generate_reply') as mock_ai:
        def ai_side_effect(*args, **kwargs):
            # Return different complexity based on level
            messages = kwargs.get("messages", [])
            if "A1" in str(messages):
                return {"content": '{"complexity_score": 0.2}'}
            else:
                return {"content": '{"complexity_score": 0.3}'}
        
        mock_ai.side_effect = ai_side_effect
        
        result = await complexity_service.compare_complexity(
            cando1,
            cando2,
            {"current_level": "beginner_1"}
        )
        
        # A1 should be less complex than A2
        assert result <= 0


@pytest.mark.asyncio
async def test_rank_by_complexity(complexity_service):
    """Test ranking CanDo descriptors by complexity."""
    candos = [
        {"uid": "JF:1", "level": "A2", "descriptionEn": "Test 1"},
        {"uid": "JF:2", "level": "A1", "descriptionEn": "Test 2"},
        {"uid": "JF:3", "level": "B1", "descriptionEn": "Test 3"}
    ]
    
    # Mock AI service
    with patch.object(complexity_service.ai_service, 'generate_reply') as mock_ai:
        def ai_side_effect(*args, **kwargs):
            messages = kwargs.get("messages", [])
            content = str(messages)
            if "A1" in content:
                return {"content": '{"complexity_score": 0.2}'}
            elif "A2" in content:
                return {"content": '{"complexity_score": 0.3}'}
            else:
                return {"content": '{"complexity_score": 0.5}'}
        
        mock_ai.side_effect = ai_side_effect
        
        ranked = await complexity_service.rank_by_complexity(
            candos,
            {"current_level": "beginner_1"}
        )
        
        assert len(ranked) == 3
        # Should be sorted by complexity (lowest first)
        assert ranked[0]["level"] == "A1"  # Lowest complexity
        assert ranked[-1]["level"] == "B1"  # Highest complexity

