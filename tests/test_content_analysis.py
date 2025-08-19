import os
from typing import Dict, Any

import requests

API_BASE_URL: str = os.getenv("API_BASE_URL", "http://localhost:8000")


def test_content_analyze_minimal_ok() -> None:
    payload: Dict[str, Any] = {
        "text": "日本語の勉強を始めます。",
        "source": {
            "title": "Sample",
            "author": "Tester",
            "language": "ja",
        },
    }
    r = requests.post(f"{API_BASE_URL}/api/v1/content/analyze", json=payload, timeout=15)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data.get("status") == "ok"
    assert data.get("processed_chars") > 0
    assert isinstance(data.get("items"), list) and len(data["items"]) >= 1


def test_content_analyze_empty_text_400() -> None:
    payload: Dict[str, Any] = {"text": " ", "source": {"title": "Empty", "language": "ja"}}
    r = requests.post(f"{API_BASE_URL}/api/v1/content/analyze", json=payload, timeout=10)
    assert r.status_code == 400


