import os
from typing import Dict

import requests
from tests._helpers import get_with_retry


API_BASE_URL: str = os.getenv("API_BASE_URL", "http://localhost:8000")


def test_health_root_ok() -> None:
    resp = get_with_retry(f"{API_BASE_URL}/health", timeout=10)
    assert resp.status_code == 200
    data: Dict[str, str] = resp.json()
    assert data.get("status") == "healthy"
    assert data.get("service") == "ai-language-tutor-backend"


def test_health_v1_ok() -> None:
    resp = get_with_retry(f"{API_BASE_URL}/api/v1/health", timeout=10)
    assert resp.status_code == 200
    data: Dict[str, str] = resp.json()
    assert data.get("status") == "healthy"


def test_health_detailed_ok() -> None:
    resp = get_with_retry(f"{API_BASE_URL}/api/v1/health/detailed", timeout=10)
    assert resp.status_code == 200
    data = resp.json()
    deps = data.get("dependencies", {})
    assert deps.get("postgresql") == "healthy"
    assert deps.get("neo4j") == "healthy"


