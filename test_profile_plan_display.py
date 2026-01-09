#!/usr/bin/env python3
"""
Test script to reproduce the issue where learning plan is not shown after profile building.
This script simulates the user flow and checks if the plan appears correctly.
"""

import asyncio
import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, Any, Optional

import httpx
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    load_dotenv(env_path)

# Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
DEBUG_LOG_PATH = Path("/home/benedikt/.cursor/debug.log")

# Test user credentials (adjust as needed)
import uuid
unique_id = str(uuid.uuid4())[:8]
TEST_USERNAME = os.getenv("TEST_USERNAME", f"testuser_{unique_id}")
TEST_PASSWORD = os.getenv("TEST_PASSWORD", "TestPass123")
TEST_EMAIL = os.getenv("TEST_EMAIL", f"test_{unique_id}@example.com")


def log_debug(session_id: str, run_id: str, hypothesis_id: str, location: str, message: str, data: Dict[str, Any]):
    """Write debug log entry."""
    try:
        # Ensure directory exists
        DEBUG_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(DEBUG_LOG_PATH, "a") as f:
            f.write(json.dumps({
                "sessionId": session_id,
                "runId": run_id,
                "hypothesisId": hypothesis_id,
                "location": location,
                "message": message,
                "data": data,
                "timestamp": int(time.time() * 1000)
            }) + "\n")
    except Exception as e:
        # Silently fail - don't interrupt test flow
        pass


async def register_user(client: httpx.AsyncClient, username: str, email: str, password: str) -> Optional[str]:
    """Register a new user and return access token."""
    try:
        response = await client.post(
            f"{API_BASE_URL}/api/v1/auth/register",
            json={
                "username": username,
                "email": email,
                "password": password,
                "native_language": "en",
                "target_languages": ["ja"]
            }
        )
        if response.status_code == 201:
            data = response.json()
            return data.get("access_token")
        elif response.status_code == 400:
            # User might already exist, try to login
            print(f"User {username} might already exist, trying to login...")
            return await login_user(client, username, password)
        else:
            print(f"Registration failed: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"Registration error: {e}")
        return None


async def login_user(client: httpx.AsyncClient, username: str, password: str) -> Optional[str]:
    """Login user and return access token."""
    try:
        response = await client.post(
            f"{API_BASE_URL}/api/v1/auth/login",
            json={
                "username": username,
                "password": password
            }
        )
        if response.status_code == 200:
            data = response.json()
            return data.get("access_token")
        else:
            print(f"Login failed: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"Login error: {e}")
        return None


async def get_profile_status(client: httpx.AsyncClient, token: str) -> Dict[str, Any]:
    """Get profile completion status."""
    response = await client.get(
        f"{API_BASE_URL}/api/v1/profile/status",
        headers={"Authorization": f"Bearer {token}"}
    )
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Failed to get profile status: {response.status_code} - {response.text}")
        return {}


async def create_profile_building_session(client: httpx.AsyncClient, token: str) -> Optional[str]:
    """Create a profile building conversation session."""
    response = await client.post(
        f"{API_BASE_URL}/api/v1/conversations/sessions",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "title": "Profile Building",
            "language_code": "en",
            "session_type": "profile_building",
            "ai_provider": "openai",
            "ai_model": "gpt-4o-mini"
        }
    )
    if response.status_code in [200, 201]:
        data = response.json()
        return data.get("id")
    else:
        print(f"Failed to create session: {response.status_code} - {response.text}")
        return None


async def add_profile_messages(client: httpx.AsyncClient, token: str, session_id: str):
    """Add sample profile building messages."""
    messages = [
        "Hello! I'm ready to build my profile.",
        "I want to learn Japanese for travel. I'm a complete beginner with no prior experience.",
        "I prefer interactive learning methods like conversations and practice exercises.",
        "I'll use Japanese when traveling to Japan next year."
    ]
    
    for msg in messages:
        response = await client.post(
            f"{API_BASE_URL}/api/v1/conversations/sessions/{session_id}/messages",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "role": "user",
                "content": msg,
                "no_ai": True
            }
        )
        if response.status_code != 201:
            print(f"Failed to add message: {response.status_code}")
        await asyncio.sleep(0.5)  # Small delay between messages


async def complete_profile(client: httpx.AsyncClient, token: str, conversation_id: str) -> Dict[str, Any]:
    """Complete the profile."""
    # First extract profile data
    extract_response = await client.post(
        f"{API_BASE_URL}/api/v1/profile/extract",
        headers={"Authorization": f"Bearer {token}"},
        json={"conversation_id": conversation_id}
    )
    
    if extract_response.status_code != 200:
        print(f"Failed to extract profile: {extract_response.status_code} - {extract_response.text}")
        return {}
    
    profile_data = extract_response.json().get("profile_data", {})
    
    # Then complete the profile
    complete_response = await client.post(
        f"{API_BASE_URL}/api/v1/profile/complete",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "conversation_id": conversation_id,
            "profile_data": profile_data
        }
    )
    
    if complete_response.status_code == 200:
        return complete_response.json()
    else:
        print(f"Failed to complete profile: {complete_response.status_code} - {complete_response.text}")
        return {}


async def get_home_status(client: httpx.AsyncClient, token: str) -> Dict[str, Any]:
    """Get home page status."""
    response = await client.get(
        f"{API_BASE_URL}/api/v1/home/status",
        headers={"Authorization": f"Bearer {token}"}
    )
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Failed to get home status: {response.status_code} - {response.text}")
        return {}


async def main():
    """Main test flow."""
    run_id = f"test_{int(time.time())}"
    session_id = "debug-session"
    
    print("=" * 80)
    print("Testing Profile Building -> Learning Plan Display Flow")
    print("=" * 80)
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        # Step 1: Authenticate
        print("\n[1] Authenticating user...")
        token = await register_user(client, TEST_USERNAME, TEST_EMAIL, TEST_PASSWORD)
        if not token:
            token = await login_user(client, TEST_USERNAME, TEST_PASSWORD)
        
        if not token:
            print("❌ Failed to authenticate. Exiting.")
            return
        
        print("✅ Authenticated successfully")
        log_debug(session_id, run_id, "A", "test_profile_plan_display.py:main", "User authenticated", {"username": TEST_USERNAME})
        
        # Step 2: Check profile status
        print("\n[2] Checking profile status...")
        profile_status = await get_profile_status(client, token)
        log_debug(session_id, run_id, "A", "test_profile_plan_display.py:main", "Profile status checked", profile_status)
        
        is_completed = profile_status.get("profile_completed", False)
        print(f"   Profile completed: {is_completed}")
        
        # Step 3: Complete profile if not completed
        if not is_completed:
            print("\n[3] Profile not completed. Creating profile building session...")
            session_id_profile = await create_profile_building_session(client, token)
            
            if not session_id_profile:
                print("❌ Failed to create profile building session. Exiting.")
                return
            
            print(f"✅ Created session: {session_id_profile}")
            log_debug(session_id, run_id, "A", "test_profile_plan_display.py:main", "Profile building session created", {"session_id": session_id_profile})
            
            print("\n[4] Adding profile building messages...")
            await add_profile_messages(client, token, session_id_profile)
            print("✅ Messages added")
            
            print("\n[5] Completing profile...")
            complete_result = await complete_profile(client, token, session_id_profile)
            log_debug(session_id, run_id, "A", "test_profile_plan_display.py:main", "Profile completion attempted", complete_result)
            
            if complete_result:
                print("✅ Profile completed")
                if complete_result.get("learning_path"):
                    print("   ✅ Learning path generated during completion")
                else:
                    print("   ⚠️  Learning path NOT generated during completion")
            else:
                print("❌ Failed to complete profile")
                return
            
            # Wait a bit for any background processing
            print("\n[6] Waiting 3 seconds for background processing...")
            await asyncio.sleep(3)
        else:
            print("\n[3] Profile already completed. Skipping profile building.")
        
        # Step 4: Check home status immediately after completion
        print("\n[7] Checking home status (first check)...")
        home_status_1 = await get_home_status(client, token)
        log_debug(session_id, run_id, "B", "test_profile_plan_display.py:main", "Home status check 1", {
            "path_generating": home_status_1.get("path_generating"),
            "has_next_step": bool(home_status_1.get("next_learning_step")),
            "next_steps_count": len(home_status_1.get("next_steps", [])),
            "greeting_preview": home_status_1.get("greeting", "")[:200] if home_status_1.get("greeting") else None
        })
        
        print(f"   path_generating: {home_status_1.get('path_generating')}")
        print(f"   has_next_step: {bool(home_status_1.get('next_learning_step'))}")
        print(f"   next_steps_count: {len(home_status_1.get('next_steps', []))}")
        greeting_1 = home_status_1.get("greeting", "")
        print(f"   greeting (first 200 chars): {greeting_1[:200] if greeting_1 else 'None'}")
        
        # Check if greeting contains "building" or "..."
        if greeting_1:
            contains_building = "building" in greeting_1.lower() or "..." in greeting_1
            print(f"   ⚠️  Greeting contains 'building' or '...': {contains_building}")
            log_debug(session_id, run_id, "C", "test_profile_plan_display.py:main", "Greeting analysis 1", {
                "contains_building": contains_building,
                "greeting_length": len(greeting_1)
            })
        
        # Step 5: Wait and check again
        print("\n[8] Waiting 5 seconds and checking home status again...")
        await asyncio.sleep(5)
        
        home_status_2 = await get_home_status(client, token)
        log_debug(session_id, run_id, "B", "test_profile_plan_display.py:main", "Home status check 2", {
            "path_generating": home_status_2.get("path_generating"),
            "has_next_step": bool(home_status_2.get("next_learning_step")),
            "next_steps_count": len(home_status_2.get("next_steps", [])),
            "greeting_preview": home_status_2.get("greeting", "")[:200] if home_status_2.get("greeting") else None
        })
        
        print(f"   path_generating: {home_status_2.get('path_generating')}")
        print(f"   has_next_step: {bool(home_status_2.get('next_learning_step'))}")
        print(f"   next_steps_count: {len(home_status_2.get('next_steps', []))}")
        greeting_2 = home_status_2.get("greeting", "")
        print(f"   greeting (first 200 chars): {greeting_2[:200] if greeting_2 else 'None'}")
        
        # Step 6: Summary
        print("\n" + "=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)
        
        issue_detected = False
        
        if home_status_1.get("path_generating") or home_status_2.get("path_generating"):
            print("⚠️  ISSUE DETECTED: path_generating is True")
            issue_detected = True
        
        if not home_status_1.get("next_learning_step") and not home_status_2.get("next_learning_step"):
            print("⚠️  ISSUE DETECTED: No next_learning_step found")
            issue_detected = True
        
        if greeting_1 and ("building" in greeting_1.lower() or "..." in greeting_1):
            if greeting_2 and ("building" in greeting_2.lower() or "..." in greeting_2):
                print("⚠️  ISSUE DETECTED: Greeting still shows 'building in background' after wait")
                issue_detected = True
        
        if not issue_detected:
            print("✅ No issues detected - learning plan is displayed correctly")
        else:
            print("❌ Issues detected - check logs for details")
        
        print("\nFull home status (first check):")
        print(json.dumps(home_status_1, indent=2, default=str))
        print("\nFull home status (second check):")
        print(json.dumps(home_status_2, indent=2, default=str))
        
        log_debug(session_id, run_id, "C", "test_profile_plan_display.py:main", "Test completed", {
            "issue_detected": issue_detected,
            "path_generating_1": home_status_1.get("path_generating"),
            "path_generating_2": home_status_2.get("path_generating"),
            "has_next_step_1": bool(home_status_1.get("next_learning_step")),
            "has_next_step_2": bool(home_status_2.get("next_learning_step"))
        })


if __name__ == "__main__":
    # Clear debug log before starting
    if DEBUG_LOG_PATH.exists():
        DEBUG_LOG_PATH.unlink()
        print(f"Cleared debug log: {DEBUG_LOG_PATH}")
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nTest failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

