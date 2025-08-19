import os
import uuid
import requests


API_BASE_URL: str = os.getenv("API_BASE_URL", "http://localhost:8000")


def _register_and_login() -> str:
    unique = uuid.uuid4().hex[:8]
    username = f"search_{unique}"
    email = f"{username}@example.com"
    password = "StrongPass1A"

    requests.post(
        f"{API_BASE_URL}/api/v1/auth/register",
        json={
            "email": email,
            "username": username,
            "full_name": "Search User",
            "native_language": "en",
            "target_languages": ["ja"],
            "current_level": "beginner",
            "learning_goals": ["conversation"],
            "study_time_preference": 15,
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
        f"{API_BASE_URL}/api/v1/auth/login", json={"username": username, "password": password}, timeout=15
    )
    assert r2.status_code == 200, r2.text
    return r2.json()["access_token"]


def test_search_messages_basic() -> None:
    token = _register_and_login()
    headers = {"Authorization": f"Bearer {token}"}
    # Seed
    r = requests.post(
        f"{API_BASE_URL}/api/v1/conversations/sessions",
        json={"language_code": "ja", "ai_provider": "openai", "ai_model": "gpt-4o-mini", "title": "Search Test"},
        headers=headers,
        timeout=15,
    )
    sid = r.json()["id"]
    requests.post(
        f"{API_BASE_URL}/api/v1/conversations/sessions/{sid}/messages",
        json={"role": "user", "content": "This is a unique-needle"},
        headers=headers,
        timeout=15,
    )

    q = "needle"
    rs = requests.get(f"{API_BASE_URL}/api/v1/conversations/search?q={q}", headers=headers, timeout=15)
    assert rs.status_code == 200, rs.text
    items = rs.json().get("items", [])
    assert any("unique-needle" in it.get("content", "") for it in items)


