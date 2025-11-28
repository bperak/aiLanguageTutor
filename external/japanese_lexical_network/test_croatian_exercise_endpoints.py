"""
Test script for Croatian exercise endpoints
"""

import json
import requests
import time
import sys

def test_croatian_exercise_endpoints():
    """Test Croatian exercise endpoints"""
    base_url = "http://localhost:5000"
    
    print("Testing Croatian Exercise Endpoints")
    print("=" * 50)
    
    # Test data
    node_id = "ljubav-NOUN"
    level = 2
    mode = "exercise"
    
    # Test 1: Generate Croatian exercise
    print(f"🧪 Test 1: Generate Croatian exercise for {node_id}")
    try:
        response = requests.get(f"{base_url}/generate-croatian-exercise", params={
            "node_id": node_id,
            "level": level,
            "mode": mode
        })
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Success! Status: {response.status_code}")
            print(f"📚 Available: {data.get('available', 'Unknown')}")
            
            if 'exercise' in data:
                exercise = data['exercise']
                print(f"🎯 Exercise mode: {exercise.get('mode', 'Unknown')}")
                print(f"📝 Exercise level: {exercise.get('level', 'Unknown')}")
                print(f"🔤 Croatian word: {exercise.get('croatian_word', 'Unknown')}")
                print(f"🌍 Translation: {exercise.get('translation', 'Unknown')}")
                print(f"💬 Content preview: {exercise.get('content', '')[:200]}...")
                
                # Store exercise for continuation test
                initial_exercise = exercise
                
            if 'node_context' in data:
                context = data['node_context']
                print(f"📋 Node context available: {not context.get('fallback', True)}")
                
        else:
            print(f"❌ Failed! Status: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    # Test 2: Continue Croatian exercise
    print(f"\n🧪 Test 2: Continue Croatian exercise")
    try:
        # Create a mock session history
        session_history = [
            {"user": "Zdravo! Kako si?", "tutor": "Zdravo! Odličan sam, hvala!"}
        ]
        
        response = requests.post(f"{base_url}/continue-croatian-exercise", json={
            "node_id": node_id,
            "level": level,
            "mode": mode,
            "session_history": session_history
        })
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Success! Status: {response.status_code}")
            print(f"📚 Available: {data.get('available', 'Unknown')}")
            
            if 'exercise' in data:
                exercise = data['exercise']
                print(f"💬 Continuation preview: {exercise.get('content', '')[:200]}...")
                
        else:
            print(f"❌ Failed! Status: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    # Test 3: Test with conversation mode
    print(f"\n🧪 Test 3: Generate Croatian conversation")
    try:
        response = requests.get(f"{base_url}/generate-croatian-exercise", params={
            "node_id": node_id,
            "level": level,
            "mode": "conversation"
        })
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Success! Status: {response.status_code}")
            
            if 'exercise' in data:
                exercise = data['exercise']
                print(f"🎯 Mode: {exercise.get('mode', 'Unknown')}")
                print(f"💬 Conversation preview: {exercise.get('content', '')[:200]}...")
                
        else:
            print(f"❌ Failed! Status: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    print(f"\n✅ All Croatian exercise endpoint tests passed!")
    return True

if __name__ == "__main__":
    # Wait a moment for the server to start
    print("Waiting for server to start...")
    time.sleep(3)
    
    success = test_croatian_exercise_endpoints()
    
    if success:
        print("\n🎉 Croatian exercise endpoints are working correctly!")
        sys.exit(0)
    else:
        print("\n💥 Some tests failed!")
        sys.exit(1) 