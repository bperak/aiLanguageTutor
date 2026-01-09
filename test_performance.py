#!/usr/bin/env python3
"""
Test script to measure performance of login, register, and page loads
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

# Test user credentials
import uuid
unique_id = str(uuid.uuid4())[:8]
TEST_USERNAME = f"perftest_{unique_id}"
TEST_PASSWORD = "TestPass123"
TEST_EMAIL = f"perftest_{unique_id}@example.com"


def log_debug(session_id: str, run_id: str, hypothesis_id: str, location: str, message: str, data: Dict[str, Any]):
    """Write debug log entry."""
    try:
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
    except Exception:
        pass


async def register_user(client: httpx.AsyncClient, username: str, email: str, password: str) -> Optional[str]:
    """Register a new user and return access token."""
    try:
        log_debug("debug-session", "perf1", "P4", "test_performance.py:register_user", "Register API call starting", {"username": username})
        start = time.time()
        response = await client.post(
            f"{API_BASE_URL}/api/v1/auth/register",
            json={
                "username": username,
                "email": email,
                "password": password,
                "native_language": "en",
                "target_languages": ["ja"]
            },
            timeout=30.0
        )
        duration = (time.time() - start) * 1000
        log_debug("debug-session", "perf1", "P4", "test_performance.py:register_user", "Register API call completed", {"duration_ms": duration, "status": response.status_code})
        
        if response.status_code == 201:
            return None  # Need to login separately
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
        log_debug("debug-session", "perf1", "P3", "test_performance.py:login_user", "Login API call starting", {"username": username})
        start = time.time()
        response = await client.post(
            f"{API_BASE_URL}/api/v1/auth/login",
            json={
                "username": username,
                "password": password
            },
            timeout=30.0
        )
        duration = (time.time() - start) * 1000
        log_debug("debug-session", "perf1", "P3", "test_performance.py:login_user", "Login API call completed", {"duration_ms": duration, "status": response.status_code})
        
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
    log_debug("debug-session", "perf1", "P2", "test_performance.py:get_profile_status", "Profile status API call starting", {})
    start = time.time()
    response = await client.get(
        f"{API_BASE_URL}/api/v1/profile/status",
        headers={"Authorization": f"Bearer {token}"},
        timeout=30.0
    )
    duration = (time.time() - start) * 1000
    log_debug("debug-session", "perf1", "P2", "test_performance.py:get_profile_status", "Profile status API call completed", {"duration_ms": duration, "status": response.status_code})
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Failed to get profile status: {response.status_code} - {response.text}")
        return {}


async def main():
    """Main test flow."""
    run_id = f"perf_{int(time.time())}"
    session_id = "debug-session"
    
    print("=" * 80)
    print("Performance Test: Login, Register, Profile Status")
    print("=" * 80)
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        # Test 1: Register
        print("\n[1] Testing REGISTER performance...")
        register_start = time.time()
        await register_user(client, TEST_USERNAME, TEST_EMAIL, TEST_PASSWORD)
        register_duration = (time.time() - register_start) * 1000
        print(f"   Register took: {register_duration:.2f}ms")
        
        # Test 2: Login
        print("\n[2] Testing LOGIN performance...")
        login_start = time.time()
        token = await login_user(client, TEST_USERNAME, TEST_PASSWORD)
        login_duration = (time.time() - login_start) * 1000
        print(f"   Login took: {login_duration:.2f}ms")
        
        if not token:
            print("❌ Failed to get token. Exiting.")
            return
        
        # Test 3: Profile Status (called on every home page load)
        print("\n[3] Testing PROFILE STATUS performance (called on home page load)...")
        for i in range(3):
            status_start = time.time()
            status = await get_profile_status(client, token)
            status_duration = (time.time() - status_start) * 1000
            print(f"   Profile status call {i+1} took: {status_duration:.2f}ms")
            await asyncio.sleep(0.5)
        
        # Summary
        print("\n" + "=" * 80)
        print("PERFORMANCE SUMMARY")
        print("=" * 80)
        print(f"Register: {register_duration:.2f}ms")
        print(f"Login: {login_duration:.2f}ms")
        print(f"Profile Status (avg): {status_duration:.2f}ms")
        
        if register_duration > 2000:
            print("⚠️  Register is SLOW (>2s)")
        if login_duration > 1000:
            print("⚠️  Login is SLOW (>1s)")
        if status_duration > 500:
            print("⚠️  Profile Status is SLOW (>500ms)")
        
        log_debug(session_id, run_id, "P1", "test_performance.py:main", "Performance test completed", {
            "register_ms": register_duration,
            "login_ms": login_duration,
            "profile_status_ms": status_duration
        })


if __name__ == "__main__":
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

