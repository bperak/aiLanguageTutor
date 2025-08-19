import os
import requests

API_BASE_URL: str = os.getenv("API_BASE_URL", "http://localhost:8000")


def test_srs_schedule_basic() -> None:
    r = requests.post(
        f"{API_BASE_URL}/api/v1/srs/schedule",
        json={"item_id": "word:日本", "last_interval_days": 1, "grade": "good"},
        timeout=10,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["item_id"] == "word:日本"
    assert data["next_interval_days"] >= 1
    assert data["next_review_at"]


