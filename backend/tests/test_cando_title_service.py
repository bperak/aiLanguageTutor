"""
Tests for CanDoTitleService.
"""

import pytest
from unittest.mock import AsyncMock, patch
from app.services.cando_title_service import CanDoTitleService


@pytest.fixture
def title_service():
    """Fixture for CanDoTitleService."""
    return CanDoTitleService()


@pytest.mark.asyncio
async def test_generate_title_english(title_service):
    """Test generating English title."""
    with patch.object(title_service.ai_service, 'generate_reply') as mock_reply:
        mock_reply.return_value = {"content": "Can talk about travel and transportation"}
        
        title = await title_service.generate_title(
            description_en="Can understand and use basic travel-related vocabulary",
            description_ja="基本的な旅行関連の語彙を理解し使用できる",
            language="en"
        )
        
        assert title.startswith("Can")
        assert "travel" in title.lower() or "transportation" in title.lower()
        mock_reply.assert_called_once()


@pytest.mark.asyncio
async def test_generate_title_japanese(title_service):
    """Test generating Japanese title."""
    with patch.object(title_service.ai_service, 'generate_reply') as mock_reply:
        mock_reply.return_value = {"content": "旅行と交通について話すことができる"}
        
        title = await title_service.generate_title(
            description_en="Can understand and use basic travel-related vocabulary",
            description_ja="基本的な旅行関連の語彙を理解し使用できる",
            language="ja"
        )
        
        assert len(title) > 0
        mock_reply.assert_called_once()


@pytest.mark.asyncio
async def test_generate_titles_both(title_service):
    """Test generating both titles in parallel."""
    with patch.object(title_service, 'generate_title') as mock_gen:
        mock_gen.side_effect = [
            "Can talk about travel",
            "旅行について話すことができる"
        ]
        
        titles = await title_service.generate_titles(
            description_en="Can understand travel vocabulary",
            description_ja="旅行の語彙を理解できる"
        )
        
        assert "titleEn" in titles
        assert "titleJa" in titles
        assert titles["titleEn"] == "Can talk about travel"
        assert titles["titleJa"] == "旅行について話すことができる"
        assert mock_gen.call_count == 2


@pytest.mark.asyncio
async def test_generate_title_requires_description(title_service):
    """Test that at least one description is required."""
    with pytest.raises(ValueError, match="At least one description"):
        await title_service.generate_title(language="en")


@pytest.mark.asyncio
async def test_generate_title_invalid_language(title_service):
    """Test that invalid language raises error."""
    with pytest.raises(ValueError, match="Unsupported language"):
        await title_service.generate_title(
            description_en="Test",
            language="fr"
        )

