import os
import uuid
import requests

API_BASE_URL: str = os.getenv("API_BASE_URL", "http://localhost:8000")


def _login(username: str, email: str, password: str) -> str:
    requests.post(
        f"{API_BASE_URL}/api/v1/auth/register",
        json={
            "email": email,
            "username": username,
            "full_name": "Admin User",
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


def test_admin_health_requires_admin_prefix() -> None:
    # Non-admin user
    u1 = f"user_{uuid.uuid4().hex[:6]}"
    t1 = _login(u1, f"{u1}@example.com", "StrongPass1A")
    r = requests.get(
        f"{API_BASE_URL}/api/v1/admin/health",
        headers={"Authorization": f"Bearer {t1}"},
        timeout=10,
    )
    assert r.status_code == 403

    # Admin user
    u2 = f"admin_{uuid.uuid4().hex[:6]}"
    t2 = _login(u2, f"{u2}@example.com", "StrongPass1A")
    r2 = requests.get(
        f"{API_BASE_URL}/api/v1/admin/health",
        headers={"Authorization": f"Bearer {t2}"},
        timeout=10,
    )
    assert r2.status_code == 200
    assert r2.json().get("status") == "ok"


