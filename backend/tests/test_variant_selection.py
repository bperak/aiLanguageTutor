import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_variant_selection_level_param(async_client: AsyncClient):
    resp = await async_client.post(
        "/api/v1/cando/lessons/start",
        params={"can_do_id": "JF:1", "phase": "lexicon_and_patterns", "level": 5},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "variant" in data and isinstance(data["variant"], dict)
    assert data["variant"].get("level") == 5


@pytest.mark.anyio
async def test_variant_selection_bounds(async_client: AsyncClient):
    # lower bound clamps to 1
    r1 = await async_client.post(
        "/api/v1/cando/lessons/start",
        params={"can_do_id": "JF:1", "level": 0},
    )
    assert r1.status_code == 200
    assert r1.json()["variant"]["level"] == 1

    # upper bound clamps to 6
    r2 = await async_client.post(
        "/api/v1/cando/lessons/start",
        params={"can_do_id": "JF:1", "level": 10},
    )
    assert r2.status_code == 200
    assert r2.json()["variant"]["level"] == 6




