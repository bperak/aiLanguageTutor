import os
import io
import requests
from tests._helpers import request_with_retry

API_BASE_URL: str = os.getenv("API_BASE_URL", "http://localhost:8000")


def test_analyze_url_simple() -> None:
    payload = {
        "url": "https://example.com",
        "source": {"title": "Example", "language": "en"},
    }
    r = request_with_retry("POST", f"{API_BASE_URL}/api/v1/content/analyze-url", json=payload, timeout=15)
    assert r.status_code in (200, 400)


def test_analyze_upload_text() -> None:
    content = "これはテストです。"
    files = {
        "file": ("sample.txt", content.encode("utf-8"), "text/plain"),
    }
    data = {"title": "Upload Sample", "language": "ja"}
    r = request_with_retry(
        "POST",
        f"{API_BASE_URL}/api/v1/content/analyze-upload",
        files=files,
        data=data,
        timeout=15,
    )
    assert r.status_code == 200, r.text
    j = r.json()
    assert j.get("status") == "ok"
    assert j.get("processed_chars", 0) > 0


