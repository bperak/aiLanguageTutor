import os
import uuid
import requests


API_BASE_URL: str = os.getenv("API_BASE_URL", "http://localhost:8000")


def _register_and_login() -> str:
    unique = uuid.uuid4().hex[:8]
    username = f"chart_{unique}"
    email = f"{username}@example.com"
    password = "StrongPass1A"

    requests.post(
        f"{API_BASE_URL}/api/v1/auth/register",
        json={
            "email": email,
            "username": username,
            "full_name": "Chart User",
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


def _seed_messages(headers: dict) -> None:
    # Create a session and add a couple of messages to produce chart data
    r = requests.post(
        f"{API_BASE_URL}/api/v1/conversations/sessions",
        json={"language_code": "ja", "ai_provider": "openai", "ai_model": "gpt-4o-mini", "title": "Chart Seed"},
        headers=headers,
        timeout=15,
    )
    assert r.status_code == 200, r.text
    sid = r.json()["id"]
    for txt in ("Hello", "How are you?", "Thanks"):
        rm = requests.post(
            f"{API_BASE_URL}/api/v1/conversations/sessions/{sid}/messages",
            json={"role": "user", "content": txt, "no_ai": True},
            headers=headers,
            timeout=15,
        )
        assert rm.status_code == 200, rm.text


def test_analytics_endpoints_available() -> None:
    token = _register_and_login()
    headers = {"Authorization": f"Bearer {token}"}
    _seed_messages(headers)

    r1 = requests.get(f"{API_BASE_URL}/api/v1/analytics/messages_per_day?days=14", headers=headers, timeout=15)
    assert r1.status_code == 200, r1.text
    data1 = r1.json()
    assert isinstance(data1, list)

    r2 = requests.get(f"{API_BASE_URL}/api/v1/analytics/sessions_per_week?weeks=8", headers=headers, timeout=15)
    assert r2.status_code == 200, r2.text
    data2 = r2.json()
    assert isinstance(data2, list)


