import os
import uuid
import requests
from tests._helpers import post_with_retry, get_with_retry

API_BASE_URL: str = os.getenv("API_BASE_URL", "http://localhost:8000")


def _login_token() -> str:
    unique = uuid.uuid4().hex[:8]
    username = f"dash_{unique}"
    email = f"{username}@example.com"
    password = "StrongPass1A"

    # Register (ignore if already exists)
    post_with_retry(
        f"{API_BASE_URL}/api/v1/auth/register",
        json={
            "email": email,
            "username": username,
            "full_name": "Dash User",
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
        },
        timeout=15,
    )
    r2 = post_with_retry(
        f"{API_BASE_URL}/api/v1/auth/login",
        json={"username": username, "password": password},
        timeout=15,
    )
    r2.raise_for_status()
    return r2.json()["access_token"]


def test_learning_dashboard_minimal() -> None:
    token = _login_token()
    headers = {"Authorization": f"Bearer {token}"}
    r = get_with_retry(f"{API_BASE_URL}/api/v1/learning/dashboard", headers=headers, timeout=15)
    assert r.status_code == 200, r.text
    data = r.json()
    assert "user_id" in data
    assert "total_sessions" in data
    assert "total_messages" in data


