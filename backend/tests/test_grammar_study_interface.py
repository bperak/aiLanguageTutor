"""
Tests for Grammar Study Interface
=================================

Tests to verify the grammar study functionality works properly,
including pattern details, study navigation, and related features.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from tests._helpers import create_test_user, get_auth_headers

client = TestClient(app)

@pytest.mark.asyncio
async def test_grammar_patterns_endpoint():
    """Test that grammar patterns endpoint returns data"""
    # Create test user and get auth headers
    user_data = await create_test_user()
    headers = await get_auth_headers(user_data["username"], "testpassword123")
    
    # Test patterns endpoint
    response = client.get("/api/v1/grammar/patterns?limit=5", headers=headers)
    
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
        detail_response = client.get(f"/api/v1/grammar/patterns/{pattern_id}", headers=headers)
        assert detail_response.status_code == 200
        
        pattern_detail = detail_response.json()
        assert pattern_detail["id"] == pattern_id
        assert pattern_detail["pattern"] == pattern["pattern"]

@pytest.mark.asyncio
async def test_grammar_similar_patterns():
    """Test similar patterns endpoint"""
    user_data = await create_test_user()
    headers = await get_auth_headers(user_data["username"], "testpassword123")
    
    # Get a pattern first
    patterns_response = client.get("/api/v1/grammar/patterns?limit=1", headers=headers)
    assert patterns_response.status_code == 200
    patterns = patterns_response.json()
    
    if patterns:
        pattern_id = patterns[0]["id"]
        
        # Test similar patterns endpoint
        similar_response = client.get(f"/api/v1/grammar/patterns/{pattern_id}/similar", headers=headers)
        assert similar_response.status_code == 200
        
        similar_patterns = similar_response.json()
        assert isinstance(similar_patterns, list)
        # Similar patterns might be empty, which is fine

@pytest.mark.asyncio
async def test_grammar_prerequisites():
    """Test prerequisites endpoint"""
    user_data = await create_test_user()
    headers = await get_auth_headers(user_data["username"], "testpassword123")
    
    # Get a pattern first
    patterns_response = client.get("/api/v1/grammar/patterns?limit=1", headers=headers)
    assert patterns_response.status_code == 200
    patterns = patterns_response.json()
    
    if patterns:
        pattern_id = patterns[0]["id"]
        
        # Test prerequisites endpoint
        prereq_response = client.get(f"/api/v1/grammar/patterns/{pattern_id}/prerequisites", headers=headers)
        assert prereq_response.status_code == 200
        
        prerequisites = prereq_response.json()
        assert isinstance(prerequisites, list)
        # Prerequisites might be empty, which is fine

@pytest.mark.asyncio
async def test_grammar_learning_path():
    """Test learning path generation"""
    user_data = await create_test_user()
    headers = await get_auth_headers(user_data["username"], "testpassword123")
    
    # Get a pattern first
    patterns_response = client.get("/api/v1/grammar/patterns?limit=1", headers=headers)
    assert patterns_response.status_code == 200
    patterns = patterns_response.json()
    
    if patterns:
        pattern_id = patterns[0]["id"]
        target_level = "初級1(りかい)"
        
        # Test learning path endpoint
        path_response = client.get(
            f"/api/v1/grammar/learning-path?from_pattern={pattern_id}&to_level={target_level}",
            headers=headers
        )
        assert path_response.status_code == 200
        
        learning_paths = path_response.json()
        assert isinstance(learning_paths, list)

@pytest.mark.asyncio
async def test_grammar_filter_options():
    """Test that filter option endpoints work"""
    user_data = await create_test_user()
    headers = await get_auth_headers(user_data["username"], "testpassword123")
    
    # Test levels endpoint
    levels_response = client.get("/api/v1/grammar/levels", headers=headers)
    assert levels_response.status_code == 200
    levels = levels_response.json()
    assert isinstance(levels, list)
    
    # Test classifications endpoint
    classifications_response = client.get("/api/v1/grammar/classifications", headers=headers)
    assert classifications_response.status_code == 200
    classifications = classifications_response.json()
    assert isinstance(classifications, list)
    
    # Test JFS categories endpoint
    categories_response = client.get("/api/v1/grammar/jfs-categories", headers=headers)
    assert categories_response.status_code == 200
    categories = categories_response.json()
    assert isinstance(categories, list)

@pytest.mark.asyncio
async def test_grammar_pattern_not_found():
    """Test 404 handling for non-existent patterns"""
    user_data = await create_test_user()
    headers = await get_auth_headers(user_data["username"], "testpassword123")
    
    # Test with non-existent pattern ID
    response = client.get("/api/v1/grammar/patterns/non-existent-id", headers=headers)
    assert response.status_code == 404
    
    error_detail = response.json()
    assert "detail" in error_detail
    assert "not found" in error_detail["detail"].lower()

def test_grammar_patterns_unauthorized():
    """Test that grammar endpoints require authentication"""
    # Test without authentication
    response = client.get("/api/v1/grammar/patterns")
    assert response.status_code == 401
    
    error_detail = response.json()
    assert "detail" in error_detail
    assert "authenticated" in error_detail["detail"].lower()











