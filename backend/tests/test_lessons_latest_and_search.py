import os
import time
import json
import pytest
import requests


API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")


@pytest.mark.integration
def test_latest_endpoint_structure():
    can_do_id = os.getenv("TEST_CANDO_ID", "JF:21")
    # Try fetch latest; allow first call to be 404 if not persisted yet
    resp = requests.get(f"{API_BASE_URL}/api/v1/cando/lessons/latest", params={"can_do_id": can_do_id}, timeout=30)
    if resp.status_code == 404:
        pytest.skip("lesson not yet persisted for can_do_id; run pipeline first")
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("can_do_id") == can_do_id
    assert "master" in data and isinstance(data["master"], (dict, str))
    assert "entities" in data


@pytest.mark.integration
def test_search_endpoint_basic():
    payload = {"q": "駅", "k": 5}
    resp = requests.post(f"{API_BASE_URL}/api/v1/cando/lessons/search", json=payload, timeout=30)
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert isinstance(data["items"], list)
    # items may be empty if no embeddings yet; shape check when present
    if data["items"]:
        item = data["items"][0]
        for key in ("lesson_id", "version", "can_do_id", "section", "lang", "text", "similarity"):
            assert key in item


