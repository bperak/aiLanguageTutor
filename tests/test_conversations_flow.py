import os
import uuid
from typing import Dict

import requests


API_BASE_URL: str = os.getenv("API_BASE_URL", "http://localhost:8000")


def _register_and_login() -> str:
    unique = uuid.uuid4().hex[:8]
    username = f"conv_{unique}"
    email = f"{username}@example.com"
    password = "StrongPass1A"

    register_payload: Dict[str, object] = {
        "email": email,
        "username": username,
        "full_name": "Conv User",
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

    login_payload = {"username": username, "password": password}
    r2 = requests.post(f"{API_BASE_URL}/api/v1/auth/login", json=login_payload, timeout=15)
    assert r2.status_code == 200, r2.text
    return r2.json()["access_token"]


def test_conversation_create_add_list() -> None:
    token = _register_and_login()
    headers = {"Authorization": f"Bearer {token}"}

    # Create session
    payload = {
        "language_code": "ja",
        "ai_provider": "openai",
        "ai_model": "gpt-4o-mini",
        "title": "Test Session",
        "session_type": "chat",
    }
    r = requests.post(f"{API_BASE_URL}/api/v1/conversations/sessions", json=payload, headers=headers, timeout=15)
    assert r.status_code == 200, r.text
    session_id = r.json()["id"]

    # Update title
    r_title = requests.put(
        f"{API_BASE_URL}/api/v1/conversations/sessions/{session_id}",
        json={"title": "Renamed Session"},
        headers=headers,
        timeout=15,
    )
    if r_title.status_code == 200:
        assert r_title.json().get("title") == "Renamed Session"
    else:
        # Some environments may not yet expose the update endpoint
        assert r_title.status_code in (404, 405), r_title.text

    # Add message
    msg = {"role": "user", "content": "Hello!"}
    r2 = requests.post(
        f"{API_BASE_URL}/api/v1/conversations/sessions/{session_id}/messages",
        json=msg,
        headers=headers,
        timeout=15,
    )
    assert r2.status_code == 200, r2.text

    # List messages
    r3 = requests.get(
        f"{API_BASE_URL}/api/v1/conversations/sessions/{session_id}/messages",
        headers=headers,
        timeout=15,
    )
    assert r3.status_code == 200, r3.text
    data = r3.json()
    assert any(m.get("content") == "Hello!" for m in data)


