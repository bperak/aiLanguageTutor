"""
Simple test for home chat streaming endpoint.
Tests the fixed /api/v1/home/sessions/{session_id}/stream endpoint.
"""
import os
import uuid
import requests

API_BASE_URL: str = os.getenv("API_BASE_URL", "http://localhost:8000")


def _register_and_login() -> str:
    """Register a test user and return auth token."""
    unique = uuid.uuid4().hex[:8]
    username = f"homechat_{unique}"
    email = f"{username}@example.com"
    password = "StrongPass1A"

    register_payload = {
        "email": email,
        "username": username,
        "full_name": "Home Chat Test User",
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
    assert r.status_code in (201, 400), f"Registration failed: {r.text}"

    r2 = requests.post(
        f"{API_BASE_URL}/api/v1/auth/login",
        json={"username": username, "password": password},
        timeout=15,
    )
    assert r2.status_code == 200, f"Login failed: {r.text}"
    return r2.json()["access_token"]


def test_home_chat_stream():
    """Test home chat streaming endpoint - the fix we just implemented."""
    token = _register_and_login()
    headers = {"Authorization": f"Bearer {token}"}

    # Get or create home session
    r = requests.get(f"{API_BASE_URL}/api/v1/home/sessions", headers=headers, timeout=15)
    assert r.status_code == 200, f"Failed to get home sessions: {r.text}"
    
    sessions = r.json()
    if not sessions or len(sessions) == 0:
        # Create a new home session
        create_payload = {
            "session_name": "home",
            "greeting": "Hello! Let's practice Japanese.",
            "user_actions": {
                "recent_lessons": [],
                "progress": {},
                "next_step": None
            }
        }
        r_create = requests.post(
            f"{API_BASE_URL}/api/v1/home/sessions",
            json=create_payload,
            headers=headers,
            timeout=15,
        )
        assert r_create.status_code == 200, f"Failed to create home session: {r_create.text}"
        session_id = r_create.json()["id"]
    else:
        session_id = sessions[0]["id"]

    # Send a user message (without immediate AI response)
    msg_payload = {
        "role": "user",
        "content": "Hello! Can you help me learn Japanese?",
        "no_ai": True,
    }
    r_msg = requests.post(
        f"{API_BASE_URL}/api/v1/home/sessions/{session_id}/messages",
        json=msg_payload,
        headers=headers,
        timeout=15,
    )
    assert r_msg.status_code == 200, f"Failed to send message: {r_msg.text}"

    # Test streaming endpoint - this is what we fixed!
    print(f"Testing streaming endpoint for session {session_id}...")
    with requests.get(
        f"{API_BASE_URL}/api/v1/home/sessions/{session_id}/stream",
        headers=headers,
        stream=True,
        timeout=30,
    ) as resp:
        # Should not return 500 error (our fix)
        assert resp.status_code == 200, f"Stream endpoint returned {resp.status_code}: {resp.text}"
        
        # Check content type
        assert resp.headers.get("content-type", "").startswith("text/event-stream"), \
            "Expected text/event-stream content type"
        
        # Read streaming response
        found_data = False
        found_done = False
        chunks = []
        
        for line in resp.iter_lines(decode_unicode=True):
            if not line:
                continue
            
            # Parse SSE format
            if line.startswith("data: "):
                data = line[6:]  # Remove "data: " prefix
                if data == "[DONE]":
                    found_done = True
                    break
                if data and data != "streaming_failed":
                    chunks.append(data)
                    found_data = True
            elif line.startswith("event: error"):
                # Check next line for error data
                continue
        
        # Verify we got some data or at least a done signal
        assert found_data or found_done, "No streaming data received"
        
        if chunks:
            print(f"✓ Received {len(chunks)} chunks of streaming data")
            print(f"✓ First chunk preview: {chunks[0][:50]}...")
        else:
            print("✓ Stream completed with [DONE] signal")
        
        print("✓ Home chat streaming test passed!")


if __name__ == "__main__":
    test_home_chat_stream()
    print("\n✅ All tests passed!")

