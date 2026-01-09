"""
Tests for Grammar Study Interface
=================================

Tests to verify the grammar study functionality works properly,
including pattern details, study navigation, and related features.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from uuid import uuid4

@pytest.fixture(scope="module")
def client() -> TestClient:
    """Create a TestClient with proper startup/shutdown lifecycle."""
    with TestClient(app) as c:
        yield c

def _register_test_user(client: TestClient) -> dict[str, str]:
    """
    Register a new test user via the API.

    Returns:
        dict[str, str]: A dict with keys: username, password.
    """
    username = f"testuser_{uuid4().hex[:10]}"
    password = "Testpassword123"  # Must satisfy password strength validators

    payload = {
        "email": f"{username}@example.com",
        "username": username,
        "password": password,
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code in (200, 201), response.text

    return {"username": username, "password": password}


def _get_auth_headers(client: TestClient, username: str, password: str) -> dict[str, str]:
    """
    Log in via the API and return Authorization headers.

    Args:
        username (str): Username.
        password (str): Password.

    Returns:
        dict[str, str]: Authorization header dict.
    """
    response = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def auth_headers(client: TestClient) -> dict[str, str]:
    """
    Create an authenticated user once for this module.

    Returns:
        dict[str, str]: Authorization header dict.
    """
    user = _register_test_user(client)
    return _get_auth_headers(client, user["username"], user["password"])


def test_grammar_patterns_endpoint(client: TestClient, auth_headers: dict[str, str]):
    """Test that grammar patterns endpoint returns data"""
    # Test patterns endpoint
    response = client.get("/api/v1/grammar/patterns?limit=5", headers=auth_headers)
    
    assert response.status_code == 200
    patterns = response.json()
    assert isinstance(patterns, list)
    
    if patterns:  # If we have patterns
        pattern = patterns[0]
        required_fields = [
            "id", "sequence_number", "pattern", "pattern_romaji",
            "textbook_form", "textbook_form_romaji", "example_sentence",
            "example_romaji", "classification", "textbook", "topic", "lesson", "jfs_category"
        ]
        
        for field in required_fields:
            assert field in pattern, f"Missing field: {field}"
        
        # Test individual pattern endpoint
        pattern_id = pattern["id"]
        detail_response = client.get(f"/api/v1/grammar/patterns/{pattern_id}", headers=auth_headers)
        assert detail_response.status_code == 200
        
        pattern_detail = detail_response.json()
        assert pattern_detail["id"] == pattern_id
        assert pattern_detail["pattern"] == pattern["pattern"]

def test_grammar_similar_patterns(client: TestClient, auth_headers: dict[str, str]):
    """Test similar patterns endpoint"""
    # Get a pattern first
    patterns_response = client.get("/api/v1/grammar/patterns?limit=1", headers=auth_headers)
    assert patterns_response.status_code == 200
    patterns = patterns_response.json()
    
    if patterns:
        pattern_id = patterns[0]["id"]
        
        # Test similar patterns endpoint
        similar_response = client.get(f"/api/v1/grammar/patterns/{pattern_id}/similar", headers=auth_headers)
        assert similar_response.status_code == 200
        
        similar_patterns = similar_response.json()
        assert isinstance(similar_patterns, list)
        # Similar patterns might be empty, which is fine

def test_grammar_prerequisites(client: TestClient, auth_headers: dict[str, str]):
    """Test prerequisites endpoint"""
    # Get a pattern first
    patterns_response = client.get("/api/v1/grammar/patterns?limit=1", headers=auth_headers)
    assert patterns_response.status_code == 200
    patterns = patterns_response.json()
    
    if patterns:
        pattern_id = patterns[0]["id"]
        
        # Test prerequisites endpoint
        prereq_response = client.get(f"/api/v1/grammar/patterns/{pattern_id}/prerequisites", headers=auth_headers)
        assert prereq_response.status_code == 200
        
        prerequisites = prereq_response.json()
        assert isinstance(prerequisites, list)
        # Prerequisites might be empty, which is fine

def test_grammar_learning_path(client: TestClient, auth_headers: dict[str, str]):
    """Test learning path generation"""
    # Get a pattern first
    patterns_response = client.get("/api/v1/grammar/patterns?limit=1", headers=auth_headers)
    assert patterns_response.status_code == 200
    patterns = patterns_response.json()
    
    if patterns:
        pattern_id = patterns[0]["id"]
        target_level = "初級1(りかい)"
        
        # Test learning path endpoint
        path_response = client.get(
            f"/api/v1/grammar/learning-path?from_pattern={pattern_id}&to_level={target_level}",
            headers=auth_headers
        )
        assert path_response.status_code == 200
        
        learning_paths = path_response.json()
        assert isinstance(learning_paths, list)

def test_grammar_filter_options(client: TestClient, auth_headers: dict[str, str]):
    """Test that filter option endpoints work"""
    # Test levels endpoint
    levels_response = client.get("/api/v1/grammar/levels", headers=auth_headers)
    assert levels_response.status_code == 200
    levels = levels_response.json()
    assert isinstance(levels, list)
    
    # Test classifications endpoint
    classifications_response = client.get("/api/v1/grammar/classifications", headers=auth_headers)
    assert classifications_response.status_code == 200
    classifications = classifications_response.json()
    assert isinstance(classifications, list)
    
    # Test JFS categories endpoint
    categories_response = client.get("/api/v1/grammar/jfs-categories", headers=auth_headers)
    assert categories_response.status_code == 200
    categories = categories_response.json()
    assert isinstance(categories, list)

def test_grammar_pattern_not_found(client: TestClient, auth_headers: dict[str, str]):
    """Test 404 handling for non-existent patterns"""
    # Test with non-existent pattern ID
    response = client.get("/api/v1/grammar/patterns/non-existent-id", headers=auth_headers)
    assert response.status_code == 404
    
    error_detail = response.json()
    assert "detail" in error_detail
    assert "not found" in error_detail["detail"].lower()

def test_grammar_patterns_unauthorized(client: TestClient):
    """Test that grammar endpoints require authentication"""
    # Test without authentication
    response = client.get("/api/v1/grammar/patterns")
    assert response.status_code == 401
    
    error_detail = response.json()
    assert "detail" in error_detail
    assert "authenticated" in error_detail["detail"].lower()











