import os
import uuid
import requests


API_BASE_URL: str = os.getenv("API_BASE_URL", "http://localhost:8000")


def _register_and_login() -> str:
    unique = uuid.uuid4().hex[:8]
    username = f"cors_{unique}"
    email = f"{username}@example.com"
    password = "StrongPass1A"

    # Register; ignore 400 if already exists
    requests.post(
        f"{API_BASE_URL}/api/v1/auth/register",
        json={
            "email": email,
            "username": username,
            "full_name": "Cors User",
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


def test_streaming_sets_cors_header():
    token = _register_and_login()
    headers = {"Authorization": f"Bearer {token}"}

    # Create a session
    r = requests.post(
        f"{API_BASE_URL}/api/v1/conversations/sessions",
        json={"language_code": "ja", "ai_provider": "openai", "ai_model": "gpt-4o-mini", "title": "CORS Test"},
        headers=headers,
        timeout=15,
    )
    assert r.status_code == 200, r.text
    session_id = r.json()["id"]

    # Add a user message with no_ai to trigger streaming path
    r2 = requests.post(
        f"{API_BASE_URL}/api/v1/conversations/sessions/{session_id}/messages",
        json={"role": "user", "content": "hello", "no_ai": True},
        headers=headers,
        timeout=15,
    )
    assert r2.status_code == 200, r2.text

    # Request stream with Origin header like the frontend
    stream_headers = {"Authorization": f"Bearer {token}", "Origin": "http://localhost:3000"}
    with requests.get(
        f"{API_BASE_URL}/api/v1/conversations/sessions/{session_id}/stream",
        headers=stream_headers,
        stream=True,
        timeout=30,
    ) as resp:
        assert resp.status_code == 200, resp.text
        # Validate echoed CORS header
        assert resp.headers.get("Access-Control-Allow-Origin") in ("*", "http://localhost:3000")
        # Read a few lines (may end quickly)
        for _ in range(10):
            try:
                line = next(resp.iter_lines(decode_unicode=True))
            except StopIteration:
                break
            if not line:
                continue
            # Either chunks or [DONE]
            if line.startswith("data: "):
                break


