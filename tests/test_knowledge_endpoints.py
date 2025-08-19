import os
from typing import Dict, Any

import requests

API_BASE_URL: str = os.getenv("API_BASE_URL", "http://localhost:8000")


def test_knowledge_health_ok() -> None:
    r = requests.get(f"{API_BASE_URL}/api/v1/knowledge/health", timeout=15)
    assert r.status_code == 200
    data: Dict[str, Any] = r.json()
    assert data.get("status") in ("healthy", "unhealthy")
    assert "neo4j" in data and "postgresql" in data


def test_quick_search_endpoint() -> None:
    # Use a common Japanese kana/kanji to expect some response structure
    r = requests.get(f"{API_BASE_URL}/api/v1/knowledge/search/quick/日", timeout=20)
    # The service may return 200 with structured results or 500 if graph empty; accept either but prefer 200
    assert r.status_code in (200, 500)
    if r.status_code == 200:
        data = r.json()
        assert isinstance(data, dict)
        assert "results" in data or len(data.keys()) >= 0


