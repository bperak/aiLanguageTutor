"""
Simple test to debug authentication issue.
"""

import requests
import json

def test_simple_registration():
    """Test basic user registration with minimal data."""
    print("🔐 SIMPLE AUTHENTICATION TEST")
    print("=" * 40)
    
    base_url = "http://localhost:8000/api/v1/auth"
    
    # Test 1: Check health
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        print(f"Health Check: {response.status_code}")
        if response.status_code == 200:
            print("✅ Auth service is healthy")
        else:
            print("❌ Auth service issue")
            return
    except Exception as e:
        print(f"❌ Cannot connect to auth service: {e}")
        return
    
    # Test 2: Simple registration
    test_user = {
        "email": "simple@test.com",
        "username": "simpleuser",
        "password": "SimplePass123!"
    }
    
    try:
        print(f"\n📝 Testing registration...")
        response = requests.post(f"{base_url}/register", json=test_user, timeout=10)
        print(f"Registration Status: {response.status_code}")
        print(f"Response: {response.text[:200]}")
        
        if response.status_code == 201:
            print("✅ Registration successful!")
            
            # Test login
            login_data = {
                "username": test_user["username"],
                "password": test_user["password"]
            }
            
            print(f"\n🔑 Testing login...")
            response = requests.post(f"{base_url}/login", json=login_data, timeout=10)
            print(f"Login Status: {response.status_code}")
            
            if response.status_code == 200:
                print("✅ Login successful!")
                token_data = response.json()
                print(f"Token received: {token_data.get('access_token', 'None')[:50]}...")
            else:
                print(f"❌ Login failed: {response.text}")
                
        else:
            print(f"❌ Registration failed")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")

if __name__ == "__main__":
    test_simple_registration()
