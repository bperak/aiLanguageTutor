"""
Grammar Integration Service Test
===============================

Test to verify the grammar integration service is working properly.
"""

import os
import uuid
import requests
from typing import Dict, Any

API_BASE_URL: str = os.getenv("API_BASE_URL", "http://localhost:8000")


def _register_and_login() -> str:
    """Helper function to register and login a test user"""
    unique = uuid.uuid4().hex[:8]
    username = f"grammar_test_{unique}"
    email = f"{username}@example.com"
    password = "TestPass123"

    # Register
    register_payload: Dict[str, Any] = {
        "email": email,
        "username": username,
        "full_name": "Grammar Test User",
        "native_language": "en",
        "target_languages": ["ja"],
        "current_level": "beginner",
        "learning_goals": ["conversation"],
        "study_time_preference": 30,
        "difficulty_preference": "adaptive",
        "preferred_ai_provider": "openai",
        "conversation_style": "balanced",
        "max_conversation_length": 50,
        "auto_save_conversations": True,
        "password": password,
    }
    
    r = requests.post(f"{API_BASE_URL}/api/v1/auth/register", json=register_payload, timeout=15)
    # User might already exist, continue to login
    
    # Login
    login_payload = {"username": username, "password": password}
    r2 = requests.post(f"{API_BASE_URL}/api/v1/auth/login", json=login_payload, timeout=15)
    assert r2.status_code == 200, r2.text
    return r2.json()["access_token"]


def test_grammar_patterns_endpoint() -> None:
    """Test basic grammar patterns endpoint"""
    token = _register_and_login()
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test getting grammar patterns
    r = requests.get(f"{API_BASE_URL}/api/v1/grammar/patterns?limit=5", headers=headers, timeout=15)
    assert r.status_code == 200, r.text
    
    data = r.json()
    assert isinstance(data, list)
    
    if data:  # If we have patterns
        pattern = data[0]
        assert "id" in pattern
        assert "pattern" in pattern
        assert "pattern_romaji" in pattern
        assert "textbook" in pattern
        print(f"✅ Found grammar pattern: {pattern['pattern']} ({pattern['pattern_romaji']})")


def test_grammar_levels_endpoint() -> None:
    """Test grammar levels endpoint"""
    token = _register_and_login()
    headers = {"Authorization": f"Bearer {token}"}
    
    r = requests.get(f"{API_BASE_URL}/api/v1/grammar/levels", headers=headers, timeout=15)
    assert r.status_code == 200, r.text
    
    data = r.json()
    assert isinstance(data, list)
    print(f"✅ Found {len(data)} textbook levels")


def test_grammar_classifications_endpoint() -> None:
    """Test grammar classifications endpoint"""
    token = _register_and_login()
    headers = {"Authorization": f"Bearer {token}"}
    
    r = requests.get(f"{API_BASE_URL}/api/v1/grammar/classifications", headers=headers, timeout=15)
    assert r.status_code == 200, r.text
    
    data = r.json()
    assert isinstance(data, list)
    print(f"✅ Found {len(data)} grammar classifications")


def test_grammar_stats_endpoint() -> None:
    """Test grammar statistics endpoint"""
    token = _register_and_login()
    headers = {"Authorization": f"Bearer {token}"}
    
    r = requests.get(f"{API_BASE_URL}/api/v1/grammar/stats", headers=headers, timeout=15)
    assert r.status_code == 200, r.text
    
    data = r.json()
    assert isinstance(data, dict)
    assert "nodes" in data or "relationships" in data
    print(f"✅ Grammar stats retrieved successfully")


def test_grammar_search() -> None:
    """Test grammar pattern search functionality"""
    token = _register_and_login()
    headers = {"Authorization": f"Bearer {token}"}
    
    # Search for common Japanese pattern
    r = requests.get(
        f"{API_BASE_URL}/api/v1/grammar/patterns?search=です&limit=3", 
        headers=headers, 
        timeout=15
    )
    assert r.status_code == 200, r.text
    
    data = r.json()
    assert isinstance(data, list)
    print(f"✅ Grammar search returned {len(data)} results")


if __name__ == "__main__":
    print("🧪 Testing Grammar Integration Service...")
    
    try:
        test_grammar_patterns_endpoint()
        test_grammar_levels_endpoint()
        test_grammar_classifications_endpoint()
        test_grammar_stats_endpoint()
        test_grammar_search()
        print("\n🎉 All grammar integration tests passed!")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        raise
