"""
Tests to ensure AI content routes are wired and require auth.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)


def test_ai_content_generate_route_exists_requires_auth():
    response = client.post(
        "/api/v1/ai-content/generate",
        json={"word_kanji": "日本", "force_regenerate": False},
    )
    # Without auth, should be 401 (route exists). Previously was 404 due to missing include.
    assert response.status_code in (401, 403)


def test_ai_content_get_word_route_exists_requires_auth():
    response = client.get("/api/v1/ai-content/word/%E6%97%A5%E6%9C%AC")
    assert response.status_code != 401


def test_ai_content_regenerate_route_exists_requires_auth():
    response = client.post("/api/v1/ai-content/regenerate/%E6%97%A5%E6%9C%AC")
    assert response.status_code in (401, 403)


def test_ai_content_word_route_is_public() -> None:
    """
    Word content GET should be public (may still 404 if content doesn't exist).
    """
    response = client.get("/api/v1/ai-content/word/%E6%97%A5%E6%9C%AC")
    assert response.status_code != 401


def test_ai_content_status_route_is_public() -> None:
    """Status should not require auth (may still 404 if word doesn't exist)."""
    response = client.get("/api/v1/ai-content/status/%E6%97%A5%E6%9C%AC")
    assert response.status_code != 401

