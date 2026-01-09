"""
Tests for Script Items API endpoints.

Covers expected use, edge cases, and failure scenarios for script item retrieval.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.api.v1.endpoints.auth import get_current_user
from app.models.database_models import User


class _FakeUser:
    """Minimal user object for dependency override."""
    id = "00000000-0000-0000-0000-000000000000"
    username = "pytest_user"
    is_active = True


async def _fake_user_dep():
    """Fake user dependency."""
    return _FakeUser()


@pytest.fixture
def client_with_auth():
    """Test client with auth dependency override."""
    app.dependency_overrides[get_current_user] = _fake_user_dep
    try:
        client = TestClient(app)
        yield client
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_get_script_items_expected_use(client_with_auth):
    """
    Expected use: list items filtered by script_type=hiragana returns non-empty
    and includes required fields.
    """
    response = client_with_auth.get(
        "/api/v1/script/items?script_type=hiragana&limit=10",
        headers={"Authorization": "Bearer test"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    
    # Check required fields
    item = data[0]
    assert "id" in item
    assert "script_type" in item
    assert item["script_type"] == "hiragana"
    assert "kana" in item
    assert "romaji" in item
    assert "romaji_aliases" in item
    assert "tags" in item


def test_get_script_items_pagination_edge_case(client_with_auth):
    """
    Edge case: pagination boundaries (limit=1, offset near end) returns stable results.
    """
    # Get total count first
    all_response = client_with_auth.get(
        "/api/v1/script/items?script_type=hiragana&limit=500",
        headers={"Authorization": "Bearer test"}
    )
    all_items = all_response.json()
    total = len(all_items)
    
    if total > 0:
        # Get last item
        last_response = client_with_auth.get(
            f"/api/v1/script/items?script_type=hiragana&limit=1&offset={total - 1}",
            headers={"Authorization": "Bearer test"}
        )
        assert last_response.status_code == 200
        last_items = last_response.json()
        assert len(last_items) <= 1
        
        if len(last_items) == 1:
            # Should match the last item from full list
            assert last_items[0]["id"] == all_items[-1]["id"]


def test_get_script_items_invalid_script_type_failure(client_with_auth):
    """
    Failure case: invalid script_type=foo returns 400.
    """
    response = client_with_auth.get(
        "/api/v1/script/items?script_type=foo",
        headers={"Authorization": "Bearer test"}
    )
    
    assert response.status_code == 400
    assert "Invalid script_type" in response.json()["detail"]


def test_get_script_item_by_id_expected_use(client_with_auth):
    """
    Expected use: get a specific item by ID returns the correct item.
    """
    # First get list to find a valid ID
    list_response = client_with_auth.get(
        "/api/v1/script/items?script_type=hiragana&limit=1",
        headers={"Authorization": "Bearer test"}
    )
    items = list_response.json()
    
    if len(items) > 0:
        item_id = items[0]["id"]
        
        # Get by ID
        get_response = client_with_auth.get(
            f"/api/v1/script/items/{item_id}",
            headers={"Authorization": "Bearer test"}
        )
        
        assert get_response.status_code == 200
        item = get_response.json()
        assert item["id"] == item_id
        assert "kana" in item
        assert "romaji" in item


def test_get_script_item_by_id_not_found_failure(client_with_auth):
    """
    Failure case: unknown item_id returns 404.
    """
    response = client_with_auth.get(
        "/api/v1/script/items/nonexistent_item_id",
        headers={"Authorization": "Bearer test"}
    )
    
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_get_script_items_with_search(client_with_auth):
    """
    Edge case: search functionality works correctly.
    """
    # Search for "a" in romaji
    response = client_with_auth.get(
        "/api/v1/script/items?search=a&limit=10",
        headers={"Authorization": "Bearer test"}
    )
    
    assert response.status_code == 200
    data = response.json()
    # Should find items with "a" in kana or romaji
    if len(data) > 0:
        found = False
        for item in data:
            if "a" in item["romaji"].lower() or "a" in item["kana"]:
                found = True
                break
        # At least one should match (hiragana_a or katakana_a)
        assert found


def test_get_script_items_with_tags_filter(client_with_auth):
    """
    Edge case: filtering by tags works correctly.
    """
    # Filter by "gojuon" tag
    response = client_with_auth.get(
        "/api/v1/script/items?tags=gojuon&limit=10",
        headers={"Authorization": "Bearer test"}
    )
    
    assert response.status_code == 200
    data = response.json()
    # All returned items should have "gojuon" tag
    for item in data:
        assert "gojuon" in item.get("tags", [])

