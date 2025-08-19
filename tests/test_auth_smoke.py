import os
import uuid
from typing import Dict

import requests

API_BASE_URL: str = os.getenv("API_BASE_URL", "http://localhost:8000")


def test_auth_register_and_login() -> None:
    # Unique user
    unique = uuid.uuid4().hex[:8]
    username = f"user_{unique}"
    email = f"{username}@example.com"
    password = "StrongPass1A"

    # Register
    register_payload: Dict[str, object] = {
        "email": email,
        "username": username,
        "full_name": "Test User",
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
    assert r.status_code in (201, 400), r.text
    # If user already exists from a previous run, 400 may be returned; continue to login

    # Login
    login_payload = {"username": username, "password": password}
    r2 = requests.post(f"{API_BASE_URL}/api/v1/auth/login", json=login_payload, timeout=15)
    assert r2.status_code == 200, r2.text
    token = r2.json().get("access_token")
    assert token

    # Verify token
    headers = {"Authorization": f"Bearer {token}"}
    r3 = requests.get(f"{API_BASE_URL}/api/v1/auth/verify-token", headers=headers, timeout=10)
    assert r3.status_code == 200, r3.text


