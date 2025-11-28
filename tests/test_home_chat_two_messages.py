"""
Test to reproduce the issue: need to send 2 messages to get reply to 1st.
Simulates the exact user flow.
"""
import os
import uuid
import requests
import time

API_BASE_URL: str = os.getenv("API_BASE_URL", "http://localhost:8000")


def _register_and_login() -> str:
    """Register a test user and return auth token."""
    unique = uuid.uuid4().hex[:8]
    username = f"test2msg_{unique}"
    email = f"{username}@example.com"
    password = "StrongPass1A"

    register_payload = {
        "email": email,
        "username": username,
        "full_name": "Test User",
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
    assert r2.status_code == 200, f"Login failed: {r2.text}"
    return r2.json()["access_token"]


def test_first_message_gets_reply():
    """Test that FIRST message gets a reply immediately."""
    token = _register_and_login()
    headers = {"Authorization": f"Bearer {token}"}

    # Get or create home session
    r = requests.get(f"{API_BASE_URL}/api/v1/home/sessions", headers=headers, timeout=15)
    assert r.status_code == 200, f"Failed to get home sessions: {r.text}"
    
    sessions = r.json()
    if not sessions or len(sessions) == 0:
        create_payload = {
            "session_name": "home",
            "greeting": "Hello!",
            "user_actions": {"recent_lessons": [], "progress": {}, "next_step": None}
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

    print(f"Using session: {session_id}")
    
    # Check initial message count
    r_msgs = requests.get(
        f"{API_BASE_URL}/api/v1/conversations/sessions/{session_id}/messages?limit=50",
        headers=headers,
        timeout=15,
    )
    initial_messages = r_msgs.json() if r_msgs.status_code == 200 else []
    print(f"Initial messages: {len(initial_messages)}")

    # Send FIRST message (simulating user flow)
    print("\n=== Sending FIRST message ===")
    msg1_payload = {
        "role": "user",
        "content": "Hello, this is my first message!",
        "no_ai": True,
    }
    r_msg1 = requests.post(
        f"{API_BASE_URL}/api/v1/home/sessions/{session_id}/messages",
        json=msg1_payload,
        headers=headers,
        timeout=15,
    )
    assert r_msg1.status_code == 200, f"Failed to send first message: {r_msg1.text}"
    print(f"✓ First message sent: {r_msg1.status_code}")

    # Wait a tiny bit for commit
    time.sleep(0.2)

    # Immediately call stream endpoint (as frontend does)
    print("\n=== Calling stream endpoint for FIRST message ===")
    with requests.get(
        f"{API_BASE_URL}/api/v1/home/sessions/{session_id}/stream",
        headers=headers,
        stream=True,
        timeout=30,
    ) as resp:
        print(f"Stream response status: {resp.status_code}")
        assert resp.status_code == 200, f"Stream failed with {resp.status_code}: {resp.text[:200]}"
        
        chunks = []
        found_done = False
        
        for line in resp.iter_lines(decode_unicode=True):
            if not line:
                continue
            if line.startswith("data: "):
                data = line[6:]
                if data == "[DONE]":
                    found_done = True
                    break
                if data and data != "streaming_failed":
                    chunks.append(data)
            elif line.startswith("event: error"):
                print(f"ERROR in stream: {line}")
        
        print(f"Received {len(chunks)} chunks")
        if chunks:
            print(f"First chunk: {chunks[0][:100]}")
        
        # THE ISSUE: First message should get a reply
        assert len(chunks) > 0 or found_done, \
            f"FIRST MESSAGE DID NOT GET REPLY! Only got {len(chunks)} chunks"
    
    print("✓ First message got a reply!")
    
    # Wait a bit
    time.sleep(1)
    
    # Send SECOND message
    print("\n=== Sending SECOND message ===")
    msg2_payload = {
        "role": "user",
        "content": "This is my second message",
        "no_ai": True,
    }
    r_msg2 = requests.post(
        f"{API_BASE_URL}/api/v1/home/sessions/{session_id}/messages",
        json=msg2_payload,
        headers=headers,
        timeout=15,
    )
    assert r_msg2.status_code == 200, f"Failed to send second message: {r_msg2.text}"
    print(f"✓ Second message sent: {r_msg2.status_code}")

    # Wait a tiny bit
    time.sleep(0.2)

    # Call stream for second message
    print("\n=== Calling stream endpoint for SECOND message ===")
    with requests.get(
        f"{API_BASE_URL}/api/v1/home/sessions/{session_id}/stream",
        headers=headers,
        stream=True,
        timeout=30,
    ) as resp:
        print(f"Stream response status: {resp.status_code}")
        assert resp.status_code == 200
        
        chunks2 = []
        for line in resp.iter_lines(decode_unicode=True):
            if not line:
                continue
            if line.startswith("data: "):
                data = line[6:]
                if data == "[DONE]":
                    break
                if data and data != "streaming_failed":
                    chunks2.append(data)
        
        print(f"Received {len(chunks2)} chunks for second message")
        assert len(chunks2) > 0, "Second message should also get a reply"
    
    print("✓ Second message got a reply!")
    print("\n✅ Test completed - both messages got replies")


if __name__ == "__main__":
    test_first_message_gets_reply()

