import os
import uuid
import requests

API_BASE_URL: str = os.getenv("API_BASE_URL", "http://localhost:8000")


def test_register_weak_password_rejected() -> None:
    unique = uuid.uuid4().hex[:8]
    payload = {
        "email": f"weak_{unique}@example.com",
        "username": f"weak_{unique}",
        "full_name": "Weak User",
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
        # Weak password (no uppercase, no digit)
        "password": "weakpass",
    }
    r = requests.post(f"{API_BASE_URL}/api/v1/auth/register", json=payload, timeout=15)
    # Pydantic validation error should yield 422
    assert r.status_code == 422


def test_login_wrong_credentials_unauthorized() -> None:
    r = requests.post(
        f"{API_BASE_URL}/api/v1/auth/login",
        json={"username": "nonexistent_user", "password": "WrongPass1A"},
        timeout=10,
    )
    assert r.status_code == 401


