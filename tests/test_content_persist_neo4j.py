import os
import uuid
import requests
from tests._helpers import request_with_retry, wait_for_health

API_BASE_URL: str = os.getenv("API_BASE_URL", "http://localhost:8000")


def test_analyze_persist_and_verify() -> None:
    # Prepare unique token to avoid collisions
    token = uuid.uuid4().hex[:6]
    text = f"{token} is a sample token"
    source = {"title": f"Source-{token}", "language": "en"}
    wait_for_health(API_BASE_URL, timeout_seconds=45)

    # Persist
    r = request_with_retry(
        "POST",
        f"{API_BASE_URL}/api/v1/content/analyze-persist",
        json={"text": text, "source": source},
        timeout=20,
    )
    assert r.status_code == 200, r.text
    j = r.json()
    assert j.get("persisted") in (True, False)

    # Verify via API wrapper over Neo4j
    r2 = request_with_retry(
        "GET",
        f"{API_BASE_URL}/api/v1/content/term",
        params={"value": token, "title": source["title"]},
        timeout=15,
    )
    assert r2.status_code == 200
    data = r2.json()
    # If neo4j available, should find; otherwise allow unavailable
    assert data.get("found") in (True, False)
    if j.get("persisted"):
        assert data.get("found") is True
        assert j.get("persisted_count", 0) >= 1


