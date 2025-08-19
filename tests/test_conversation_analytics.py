import os
import uuid
import requests

API_BASE_URL: str = os.getenv("API_BASE_URL", "http://localhost:8000")


def _login_token() -> str:
    unique = uuid.uuid4().hex[:6]
    username = f"stat_{unique}"
    email = f"{username}@example.com"
    password = "StrongPass1A"
    requests.post(
        f"{API_BASE_URL}/api/v1/auth/register",
        json={
            "email": email,
            "username": username,
            "full_name": "Stats User",
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
    r2 = requests.post(
        f"{API_BASE_URL}/api/v1/auth/login",
        json={"username": username, "password": password},
        timeout=15,
    )
    r2.raise_for_status()
    return r2.json()["access_token"]


def test_conversation_summary() -> None:
    token = _login_token()
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.get(f"{API_BASE_URL}/api/v1/analytics/summary", headers=headers, timeout=15)
    assert r.status_code == 200
    data = r.json()
    assert "total_sessions" in data
    assert "total_messages" in data
    assert "avg_messages_per_session" in data


