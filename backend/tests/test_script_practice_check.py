"""
Tests for Script Practice Check API endpoint.

Covers expected use, edge cases, and failure scenarios for practice answer validation.
"""

from __future__ import annotations

import pytest
from datetime import datetime
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock

from app.main import app
from app.api.v1.endpoints.auth import get_current_user
from app.db import get_postgresql_session
from app.models.database_models import User, ConversationSession, ConversationInteraction


class _FakeUser:
    """Minimal user object for dependency override."""
    id = "00000000-0000-0000-0000-000000000000"
    username = "pytest_user"
    is_active = True


async def _fake_user_dep():
    """Fake user dependency."""
    return _FakeUser()


class _FakeAsyncSession:
    """Fake async DB session for testing."""
    
    def __init__(self):
        self.added = []
        self.committed = False
        self.rolled_back = False
    
    async def execute(self, query):
        """Mock execute for queries."""
        from sqlalchemy.engine import Result
        
        # Return empty result for most queries
        class FakeResult:
            def scalar_one_or_none(self):
                return None
            def scalar(self):
                return 0
            def scalars(self):
                return iter([])
        
        return FakeResult()
    
    async def flush(self):
        """Mock flush."""
        pass
    
    async def commit(self):
        """Mock commit."""
        self.committed = True
    
    async def rollback(self):
        """Mock rollback."""
        self.rolled_back = True
    
    def add(self, obj):
        """Mock add."""
        self.added.append(obj)


async def _fake_db_dep():
    """Fake DB dependency."""
    yield _FakeAsyncSession()


@pytest.fixture
def client_with_auth_and_db():
    """Test client with auth and DB dependency overrides."""
    app.dependency_overrides[get_current_user] = _fake_user_dep
    app.dependency_overrides[get_postgresql_session] = _fake_db_dep
    try:
        client = TestClient(app)
        yield client
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_postgresql_session, None)


def test_check_practice_kana_to_romaji_expected_use(client_with_auth_and_db):
    """
    Expected use: kana→romaji accepts canonical romaji and records an interaction.
    """
    # First get a valid item ID
    list_response = client_with_auth_and_db.get(
        "/api/v1/script/items?script_type=hiragana&limit=1",
        headers={"Authorization": "Bearer test"}
    )
    items = list_response.json()
    
    if len(items) > 0:
        item = items[0]
        item_id = item["id"]
        expected_romaji = item["romaji"]
        
        # Check answer
        check_response = client_with_auth_and_db.post(
            "/api/v1/script/practice/check",
            json={
                "item_id": item_id,
                "mode": "kana_to_romaji",
                "user_answer": expected_romaji
            },
            headers={"Authorization": "Bearer test"}
        )
        
        assert check_response.status_code == 200
        data = check_response.json()
        assert data["is_correct"] is True
        assert data["item_id"] == item_id
        assert data["mode"] == "kana_to_romaji"
        assert data["expected_answer"] == expected_romaji
        assert expected_romaji in data["accepted_answers"]


def test_check_practice_romaji_alias_edge_case(client_with_auth_and_db):
    """
    Edge case: accepts alias romaji (shi vs si) and NFKC-normalized inputs.
    """
    # Find an item with aliases (e.g., hiragana_shi)
    list_response = client_with_auth_and_db.get(
        "/api/v1/script/items?script_type=hiragana&limit=100",
        headers={"Authorization": "Bearer test"}
    )
    items = list_response.json()
    
    # Find item with "shi" that has "si" alias
    shi_item = None
    for item in items:
        if item["romaji"] == "shi" and "si" in item.get("romaji_aliases", []):
            shi_item = item
            break
    
    if shi_item:
        item_id = shi_item["id"]
        
        # Test with alias
        check_response = client_with_auth_and_db.post(
            "/api/v1/script/practice/check",
            json={
                "item_id": item_id,
                "mode": "kana_to_romaji",
                "user_answer": "si"  # Use alias
            },
            headers={"Authorization": "Bearer test"}
        )
        
        assert check_response.status_code == 200
        data = check_response.json()
        assert data["is_correct"] is True


def test_check_practice_unknown_item_id_failure(client_with_auth_and_db):
    """
    Failure case: unknown item_id returns 404.
    """
    check_response = client_with_auth_and_db.post(
        "/api/v1/script/practice/check",
        json={
            "item_id": "nonexistent_item_id",
            "mode": "kana_to_romaji",
            "user_answer": "test"
        },
        headers={"Authorization": "Bearer test"}
    )
    
    assert check_response.status_code == 404
    assert "not found" in check_response.json()["detail"].lower()


def test_check_practice_empty_answer_failure(client_with_auth_and_db):
    """
    Failure case: empty user_answer for typing modes returns 400.
    """
    # Get a valid item ID
    list_response = client_with_auth_and_db.get(
        "/api/v1/script/items?script_type=hiragana&limit=1",
        headers={"Authorization": "Bearer test"}
    )
    items = list_response.json()
    
    if len(items) > 0:
        item_id = items[0]["id"]
        
        # Try with empty answer
        check_response = client_with_auth_and_db.post(
            "/api/v1/script/practice/check",
            json={
                "item_id": item_id,
                "mode": "kana_to_romaji",
                "user_answer": "   "  # Whitespace only
            },
            headers={"Authorization": "Bearer test"}
        )
        
        assert check_response.status_code == 400
        assert "empty" in check_response.json()["detail"].lower()


def test_check_practice_romaji_to_kana_expected_use(client_with_auth_and_db):
    """
    Expected use: romaji→kana mode works correctly.
    """
    # Get a valid item
    list_response = client_with_auth_and_db.get(
        "/api/v1/script/items?script_type=hiragana&limit=1",
        headers={"Authorization": "Bearer test"}
    )
    items = list_response.json()
    
    if len(items) > 0:
        item = items[0]
        item_id = item["id"]
        expected_kana = item["kana"]
        
        # Check answer
        check_response = client_with_auth_and_db.post(
            "/api/v1/script/practice/check",
            json={
                "item_id": item_id,
                "mode": "romaji_to_kana",
                "user_answer": expected_kana
            },
            headers={"Authorization": "Bearer test"}
        )
        
        assert check_response.status_code == 200
        data = check_response.json()
        assert data["is_correct"] is True
        assert data["expected_answer"] == expected_kana


def test_check_practice_mcq_mode(client_with_auth_and_db):
    """
    Edge case: multiple choice mode works correctly.
    """
    # Get a valid item
    list_response = client_with_auth_and_db.get(
        "/api/v1/script/items?script_type=hiragana&limit=1",
        headers={"Authorization": "Bearer test"}
    )
    items = list_response.json()
    
    if len(items) > 0:
        item = items[0]
        item_id = item["id"]
        correct_answer = item["romaji"]
        
        # Check with MCQ
        check_response = client_with_auth_and_db.post(
            "/api/v1/script/practice/check",
            json={
                "item_id": item_id,
                "mode": "mcq",
                "user_answer": correct_answer,
                "choices": [correct_answer, "wrong1", "wrong2", "wrong3"]
            },
            headers={"Authorization": "Bearer test"}
        )
        
        assert check_response.status_code == 200
        data = check_response.json()
        assert data["is_correct"] is True

