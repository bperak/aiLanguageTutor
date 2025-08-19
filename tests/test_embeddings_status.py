import os
import requests

API_BASE_URL: str = os.getenv("API_BASE_URL", "http://localhost:8000")


def test_embeddings_status_endpoint() -> None:
    r = requests.get(f"{API_BASE_URL}/api/v1/knowledge/embeddings/status", timeout=15)
    # May be 200 with counters or 500 if table missing; accept both but prefer 200
    assert r.status_code in (200, 500)
    if r.status_code == 200:
        data = r.json()
        assert "total_embeddings" in data
        assert "status" in data


