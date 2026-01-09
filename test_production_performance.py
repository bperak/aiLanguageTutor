#!/usr/bin/env python3
"""
Test performance of production site APIs
"""

import asyncio
import time
import json
from pathlib import Path
import httpx

PRODUCTION_URL = "https://ailanguagetutor.syntagent.com"
DEBUG_LOG_PATH = Path("/home/benedikt/.cursor/debug.log")


def log_debug(session_id: str, run_id: str, hypothesis_id: str, location: str, message: str, data: dict):
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


async def test_home_page(client: httpx.AsyncClient):
    """Test home page load time."""
    print("\n[1] Testing HOME PAGE load...")
    log_debug("debug-session", "prod-perf", "P1", "test_production_performance.py:test_home_page", "Home page request starting", {})
    
    start = time.time()
    try:
        response = await client.get(f"{PRODUCTION_URL}/", timeout=30.0, follow_redirects=True)
        duration = (time.time() - start) * 1000
        log_debug("debug-session", "prod-perf", "P1", "test_production_performance.py:test_home_page", "Home page loaded", {
            "duration_ms": duration,
            "status": response.status_code,
            "content_length": len(response.text)
        })
        print(f"   Status: {response.status_code}, Duration: {duration:.2f}ms, Size: {len(response.text)} bytes")
        return duration
    except Exception as e:
        duration = (time.time() - start) * 1000
        log_debug("debug-session", "prod-perf", "P1", "test_production_performance.py:test_home_page", "Home page failed", {
            "duration_ms": duration,
            "error": str(e)
        })
        print(f"   Error: {e}")
        return None


async def test_login_page(client: httpx.AsyncClient):
    """Test login page load time."""
    print("\n[2] Testing LOGIN PAGE load...")
    log_debug("debug-session", "prod-perf", "P3", "test_production_performance.py:test_login_page", "Login page request starting", {})
    
    start = time.time()
    try:
        response = await client.get(f"{PRODUCTION_URL}/login", timeout=30.0, follow_redirects=True)
        duration = (time.time() - start) * 1000
        log_debug("debug-session", "prod-perf", "P3", "test_production_performance.py:test_login_page", "Login page loaded", {
            "duration_ms": duration,
            "status": response.status_code,
            "content_length": len(response.text),
            "has_form": "form" in response.text.lower()
        })
        print(f"   Status: {response.status_code}, Duration: {duration:.2f}ms, Size: {len(response.text)} bytes")
        return duration
    except Exception as e:
        duration = (time.time() - start) * 1000
        log_debug("debug-session", "prod-perf", "P3", "test_production_performance.py:test_login_page", "Login page failed", {
            "duration_ms": duration,
            "error": str(e)
        })
        print(f"   Error: {e}")
        return None


async def test_register_page(client: httpx.AsyncClient):
    """Test register page load time."""
    print("\n[3] Testing REGISTER PAGE load...")
    log_debug("debug-session", "prod-perf", "P4", "test_production_performance.py:test_register_page", "Register page request starting", {})
    
    start = time.time()
    try:
        response = await client.get(f"{PRODUCTION_URL}/register", timeout=30.0, follow_redirects=True)
        duration = (time.time() - start) * 1000
        log_debug("debug-session", "prod-perf", "P4", "test_production_performance.py:test_register_page", "Register page loaded", {
            "duration_ms": duration,
            "status": response.status_code,
            "content_length": len(response.text),
            "has_form": "form" in response.text.lower()
        })
        print(f"   Status: {response.status_code}, Duration: {duration:.2f}ms, Size: {len(response.text)} bytes")
        return duration
    except Exception as e:
        duration = (time.time() - start) * 1000
        log_debug("debug-session", "prod-perf", "P4", "test_production_performance.py:test_register_page", "Register page failed", {
            "duration_ms": duration,
            "error": str(e)
        })
        print(f"   Error: {e}")
        return None


async def test_api_endpoint(client: httpx.AsyncClient, endpoint: str, method: str = "GET", data: dict = None):
    """Test API endpoint performance."""
    url = f"{PRODUCTION_URL}{endpoint}"
    print(f"\n[API] Testing {method} {endpoint}...")
    log_debug("debug-session", "prod-perf", "P2", "test_production_performance.py:test_api_endpoint", "API request starting", {
        "endpoint": endpoint,
        "method": method
    })
    
    start = time.time()
    try:
        if method == "GET":
            response = await client.get(url, timeout=30.0)
        elif method == "POST":
            response = await client.post(url, json=data, timeout=30.0)
        else:
            response = await client.request(method, url, json=data, timeout=30.0)
        
        duration = (time.time() - start) * 1000
        log_debug("debug-session", "prod-perf", "P2", "test_production_performance.py:test_api_endpoint", "API request completed", {
            "endpoint": endpoint,
            "method": method,
            "duration_ms": duration,
            "status": response.status_code
        })
        print(f"   Status: {response.status_code}, Duration: {duration:.2f}ms")
        return duration, response.status_code
    except Exception as e:
        duration = (time.time() - start) * 1000
        log_debug("debug-session", "prod-perf", "P2", "test_production_performance.py:test_api_endpoint", "API request failed", {
            "endpoint": endpoint,
            "method": method,
            "duration_ms": duration,
            "error": str(e)
        })
        print(f"   Error: {e}")
        return None, None


async def main():
    """Main test flow."""
    print("=" * 80)
    print("PRODUCTION PERFORMANCE TEST")
    print(f"Testing: {PRODUCTION_URL}")
    print("=" * 80)
    
    # Create HTTP client with longer timeout
    timeout = httpx.Timeout(60.0, connect=30.0)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        # Test page loads
        home_duration = await test_home_page(client)
        await asyncio.sleep(1)
        
        login_duration = await test_login_page(client)
        await asyncio.sleep(1)
        
        register_duration = await test_register_page(client)
        await asyncio.sleep(1)
        
        # Test API endpoints (if accessible)
        # Note: These may require authentication, but we can still measure response time
        api_durations = []
        
        # Test health endpoint if available
        health_duration, health_status = await test_api_endpoint(client, "/api/v1/health/")
        if health_duration:
            api_durations.append(health_duration)
        
        await asyncio.sleep(1)
        
        # Summary
        print("\n" + "=" * 80)
        print("PERFORMANCE SUMMARY")
        print("=" * 80)
        if home_duration:
            print(f"Home Page: {home_duration:.2f}ms")
            if home_duration > 2000:
                print("  ⚠️  SLOW (>2s)")
        if login_duration:
            print(f"Login Page: {login_duration:.2f}ms")
            if login_duration > 2000:
                print("  ⚠️  SLOW (>2s)")
        if register_duration:
            print(f"Register Page: {register_duration:.2f}ms")
            if register_duration > 2000:
                print("  ⚠️  SLOW (>2s)")
        if api_durations:
            avg_api = sum(api_durations) / len(api_durations)
            print(f"API Endpoints (avg): {avg_api:.2f}ms")
            if avg_api > 1000:
                print("  ⚠️  SLOW (>1s)")
        
        log_debug("debug-session", "prod-perf", "P1", "test_production_performance.py:main", "Performance test completed", {
            "home_ms": home_duration,
            "login_ms": login_duration,
            "register_ms": register_duration,
            "api_avg_ms": sum(api_durations) / len(api_durations) if api_durations else None
        })


if __name__ == "__main__":
    if DEBUG_LOG_PATH.exists():
        DEBUG_LOG_PATH.unlink()
        print(f"Cleared debug log: {DEBUG_LOG_PATH}")
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        print(f"\n\nTest failed with error: {e}")
        import traceback
        traceback.print_exc()

