import os
import pytest
from httpx import AsyncClient

from app.main import app


def has_ai_keys() -> bool:
    return bool(os.getenv("OPENAI_API_KEY") or os.getenv("GEMINI_API_KEY"))


@pytest.mark.anyio
@pytest.mark.skipif(not has_ai_keys(), reason="AI keys not configured")
async def test_new_dialogue_minimal():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        resp = await ac.post(
            "/api/v1/cando/dialogue/new",
            json={"can_do_id": "JF_105", "num_turns": 2},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "dialogue_turns" in data
        assert "setting" in data


@pytest.mark.anyio
@pytest.mark.skipif(not has_ai_keys(), reason="AI keys not configured")
async def test_extend_dialogue_roundtrip():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        # First, new dialogue
        new_resp = await ac.post(
            "/api/v1/cando/dialogue/new",
            json={"can_do_id": "JF_105", "num_turns": 2},
        )
        assert new_resp.status_code == 200
        card = new_resp.json()
        # Then extend using returned turns
        ext_resp = await ac.post(
            "/api/v1/cando/dialogue/extend",
            json={
                "can_do_id": "JF_105",
                "setting": card.get("setting", ""),
                "dialogue_turns": card.get("dialogue_turns", []),
                "num_turns": 2,
            },
        )
        assert ext_resp.status_code == 200
        ext_card = ext_resp.json()
        assert len(ext_card.get("dialogue_turns", [])) >= len(card.get("dialogue_turns", []))


