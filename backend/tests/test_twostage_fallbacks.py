import pytest
from unittest.mock import AsyncMock, patch

from app.services.cando_lesson_session_service import CanDoLessonSessionService


@pytest.mark.asyncio
async def test_stage2_dialogue_per_item_retry_then_fallback():
    svc = CanDoLessonSessionService()

    # Section data with two turns
    dialogue = [
        {"speaker": "A", "text": "こんにちは"},
        {"speaker": "B", "text": "はじめまして"},
    ]

    # Force batch validation to fail by raising ValidationError via model validation path
    async def fake_reply(*args, **kwargs):
        # Return malformed JSON to trigger validation failure
        return {"content": "{"}

    with patch.object(svc._practice.ai_chat, "generate_reply", new_callable=AsyncMock) as mock_gen:
        # First call (batch) returns invalid, then per-item calls alternate invalid/valid
        mock_gen.side_effect = [
            {"content": "{"},  # batch invalid
            {"content": '{"speaker":"A","japanese":{"kanji":"こんにちは","romaji":"konnichiwa","furigana":[{"text":"こん","ruby":"こん"},{"text":"にちは","ruby":null}],"translation":"hello"}}'},
            {"content": "{"},  # invalid triggers fallback for second
        ]

        result = await svc._enhance_section_with_multilingual(
            section_name="dialogue",
            section_data=dialogue,
            provider="openai",
            timeout=5,
        )

    assert result["success"] is True
    assert isinstance(result["data"], list) and len(result["data"]) == 2
    # Second item should be fallback generated dict with japanese field
    assert "japanese" in result["data"][1]


