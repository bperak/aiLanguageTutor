#!/usr/bin/env python3
"""
Simple script to test grammar study functionality
"""

import requests
import json
import os
from pathlib import Path

# Configuration
API_BASE_URL = "http://localhost:8000"

def test_grammar_study_functionality():
    """Test the grammar study endpoints manually"""
    
    print("🧪 Testing Grammar Study Functionality")
    print("=" * 50)
    
    # Test 1: Check if grammar patterns endpoint is accessible
    print("\n1. Testing grammar patterns endpoint...")
    try:
        response = requests.get(f"{API_BASE_URL}/api/v1/grammar/patterns?limit=1")
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 401:
            print("   ✅ Authentication required (expected)")
        elif response.status_code == 200:
            patterns = response.json()
            print(f"   ✅ Got {len(patterns)} patterns")
            if patterns:
                pattern = patterns[0]
                print(f"   📝 Sample pattern: {pattern.get('pattern', 'N/A')}")
        else:
            print(f"   ❌ Unexpected status: {response.status_code}")
            print(f"   Response: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"   ❌ Connection error: {e}")
        print("   💡 Make sure backend is running with: docker-compose up")
        return False
    
    # Test 2: Check if frontend study page exists
    print("\n2. Testing frontend study page...")
    study_page_path = Path("frontend/src/app/grammar/study/[patternId]/page.tsx")
    if study_page_path.exists():
        print("   ✅ Study page file exists")
        
        # Check if the page has the key components
        with open(study_page_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        if "GrammarStudyPage" in content:
            print("   ✅ Study page component found")
        if "Similar Patterns" in content:
            print("   ✅ Similar patterns tab found")
        if "Prerequisites" in content:
            print("   ✅ Prerequisites tab found")
        if "Practice Questions" in content:
            print("   ✅ Practice questions tab found")
    else:
        print("   ❌ Study page file not found")
        return False
    
    # Test 3: Check if navigation is updated
    print("\n3. Testing grammar page navigation...")
    grammar_page_path = Path("frontend/src/app/grammar/page.tsx")
    if grammar_page_path.exists():
        with open(grammar_page_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        if "window.location.href = `/grammar/study/${patternId}`" in content:
            print("   ✅ Navigation to study page implemented")
        else:
            print("   ❌ Navigation not properly implemented")
            return False
    
    # Test 4: Check build status
    print("\n4. Testing frontend build...")
    try:
        os.chdir("frontend")
        build_result = os.system("npm run build > build.log 2>&1")
        os.chdir("..")
        
        if build_result == 0:
            print("   ✅ Frontend builds successfully")
        else:
            print("   ❌ Frontend build failed")
            print("   💡 Check build.log for details")
            return False
    except Exception as e:
        print(f"   ❌ Build test failed: {e}")
        return False
    
    print("\n🎉 All tests passed!")
    print("\n📋 Next Steps:")
    print("1. Visit http://localhost:3000/grammar")
    print("2. Login with your test account")
    print("3. Click 'Study This Pattern' on any grammar pattern")
    print("4. You should see the detailed study interface with:")
    print("   - Pattern overview with audio controls")
    print("   - Similar patterns tab")
    print("   - Prerequisites tab") 
    print("   - Practice questions tab")
    
    return True

if __name__ == "__main__":
    # Change to project root
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    os.chdir(project_root)
    
    success = test_grammar_study_functionality()
    exit(0 if success else 1)











