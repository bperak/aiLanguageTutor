import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_cando_lessons_turn_contract(async_client: AsyncClient):
    # Start session first
    s = await async_client.post(
        "/api/v1/cando/lessons/start", params={"can_do_id": "JF:1", "phase": "guided_dialogue"}
    )
    assert s.status_code == 200
    sid = s.json()["sessionId"]

    # Send user turn
    r = await async_client.post(
        "/api/v1/cando/lessons/turn", params={"session_id": sid, "message": "こんにちは。自己紹介します。"}
    )
    assert r.status_code == 200
    data = r.json()
    assert "turn" in data and "message" in data["turn"]
    assert isinstance(data.get("dialogue", []), list)

