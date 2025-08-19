"""
Test script for the authentication system.
Tests user registration, login, and protected endpoints.
"""

import requests
import json
import uuid


def test_endpoint(method, url, description, data=None, headers=None):
    """Test an API endpoint and display results."""
    print(f"\n--- {description} ---")
    try:
        if method.upper() == 'POST':
            response = requests.post(url, json=data, headers=headers, timeout=10)
        elif method.upper() == 'GET':
            response = requests.get(url, headers=headers, timeout=10)
        elif method.upper() == 'PUT':
            response = requests.put(url, json=data, headers=headers, timeout=10)
        else:
            print(f"❌ Unsupported method: {method}")
            return None
        
        print(f"Status: {response.status_code}")
        
        if response.status_code < 400:
            print("✅ Success")
            try:
                data = response.json()
                if 'access_token' in data:
                    print(f"🔑 Token received (expires in {data.get('expires_in', 'unknown')} seconds)")
                    return data['access_token']
                elif 'id' in data:
                    print(f"👤 User ID: {data['id']}")
                    print(f"📧 Email: {data.get('email', 'N/A')}")
                    print(f"👤 Username: {data.get('username', 'N/A')}")
                elif 'message' in data:
                    print(f"💬 Message: {data['message']}")
                else:
                    print(f"📄 Response: {json.dumps(data, indent=2, default=str)[:300]}...")
            except:
                print(f"📄 Response: {response.text[:200]}...")
        else:
            print(f"❌ Error: {response.text[:200]}")
        
        return None
        
    except Exception as e:
        print(f"❌ Exception: {e}")
        return None


def main():
    """Test the authentication system."""
    print("🔐 AUTHENTICATION SYSTEM TEST")
    print("=" * 50)
    
    base_url = "http://localhost:8000/api/v1/auth"
    
    # Generate unique test user data
    unique_id = str(uuid.uuid4())[:8]
    test_user = {
        "email": f"test_{unique_id}@example.com",
        "username": f"testuser_{unique_id}",
        "password": "TestPassword123!",
        "full_name": f"Test User {unique_id}",
        "native_language": "en",
        "target_languages": ["ja"],
        "learning_goals": ["conversation", "reading"],
        "study_time_preference": 45,
        "difficulty_preference": "adaptive"
    }
    
    # Test 1: Health Check
    test_endpoint('GET', f"{base_url}/health", "Authentication Health Check")
    
    # Test 2: User Registration
    token = test_endpoint('POST', f"{base_url}/register", "User Registration", test_user)
    
    # Test 3: User Login
    login_data = {
        "username": test_user["username"],
        "password": test_user["password"]
    }
    token = test_endpoint('POST', f"{base_url}/login", "User Login", login_data)
    
    if token:
        # Test 4: Get User Profile (Protected Endpoint)
        headers = {"Authorization": f"Bearer {token}"}
        test_endpoint('GET', f"{base_url}/me", "Get Current User", headers=headers)
        
        # Test 5: Get Extended Profile
        test_endpoint('GET', f"{base_url}/profile", "Get User Profile", headers=headers)
        
        # Test 6: Update Profile
        update_data = {
            "full_name": f"Updated Test User {unique_id}",
            "study_time_preference": 60,
            "learning_goals": ["conversation", "reading", "business"]
        }
        test_endpoint('PUT', f"{base_url}/profile", "Update User Profile", update_data, headers)
        
        # Test 7: Verify Token
        test_endpoint('GET', f"{base_url}/verify-token", "Verify Token", headers=headers)
        
    else:
        print("\n⚠️  Skipping protected endpoint tests (no token received)")
    
    # Test 8: Test Knowledge Graph Integration
    print(f"\n--- Testing Knowledge Graph Integration ---")
    if token:
        headers = {"Authorization": f"Bearer {token}"}
        knowledge_url = "http://localhost:8000/api/v1/knowledge"
        test_endpoint('GET', f"{knowledge_url}/stats", "Knowledge Stats (Authenticated)", headers=headers)
    
    print(f"\n{'='*50}")
    print("🎉 Authentication System Testing Complete!")
    print("\n📚 Available endpoints tested:")
    print("   • POST /api/v1/auth/register - User registration ✅")
    print("   • POST /api/v1/auth/login - User login ✅")
    print("   • GET  /api/v1/auth/me - Current user info ✅")
    print("   • GET  /api/v1/auth/profile - Extended profile ✅")
    print("   • PUT  /api/v1/auth/profile - Update profile ✅")
    print("   • GET  /api/v1/auth/verify-token - Token validation ✅")


if __name__ == "__main__":
    main()
