import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_cando_lessons_start_contract(async_client: AsyncClient):
    # Use a known or generic id; endpoint should degrade gracefully
    resp = await async_client.post(
        "/api/v1/cando/lessons/start", params={"can_do_id": "JF:1", "phase": "lexicon_and_patterns"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "sessionId" in data and isinstance(data["sessionId"], str)
    assert "objective" in data
    assert isinstance(data.get("opening_turns", []), list)

