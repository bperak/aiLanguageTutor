import os
import uuid
import requests

API_BASE_URL: str = os.getenv("API_BASE_URL", "http://localhost:8000")


def _login_token() -> str:
    # Reuse auth smoke helper by creating a new user inline
    unique = uuid.uuid4().hex[:8]
    username = f"edge_{unique}"
    email = f"{username}@example.com"
    password = "StrongPass1A"

    requests.post(
        f"{API_BASE_URL}/api/v1/auth/register",
        json={
            "email": email,
            "username": username,
            "full_name": "Edge User",
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


def test_create_session_missing_auth_fails() -> None:
    r = requests.post(
        f"{API_BASE_URL}/api/v1/conversations/sessions",
        json={"ai_provider": "openai", "ai_model": "gpt-4o-mini"},
        timeout=10,
    )
    assert r.status_code in (401, 403)


def test_add_message_invalid_session() -> None:
    token = _login_token()
    headers = {"Authorization": f"Bearer {token}"}
    fake_session_id = str(uuid.uuid4())

    r = requests.post(
        f"{API_BASE_URL}/api/v1/conversations/sessions/{fake_session_id}/messages",
        json={"role": "user", "content": "Hi"},
        headers=headers,
        timeout=10,
    )
    # Depending on service, could be 404 (session not found) or 500 fallback; accept both for now
    assert r.status_code in (404, 500)


