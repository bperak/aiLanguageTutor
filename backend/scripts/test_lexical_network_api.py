#!/usr/bin/env python3
"""
Test Lexical Network API endpoints.

Quick test script to verify API endpoints are working.
"""

import asyncio
import sys
from pathlib import Path

import httpx

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

BASE_URL = "http://localhost:8000"
API_BASE = f"{BASE_URL}/api/v1/lexical-network"


async def test_endpoints():
    """Test lexical network API endpoints."""
    print("=" * 60)
    print("Lexical Network API - Endpoint Tests")
    print("=" * 60)
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        # Test 1: List available models
        print("\n1. Testing GET /models")
        try:
            response = await client.get(f"{API_BASE}/models")
            if response.status_code == 200:
                models = response.json()
                print(f"   ✓ Found {len(models)} models")
                if models:
                    print(f"   Example: {models[0].get('model_key', 'unknown')} ({models[0].get('provider', 'unknown')})")
            else:
                print(f"   ⚠ Status: {response.status_code}")
        except Exception as e:
            print(f"   ✗ Error: {e}")
        
        # Test 2: Get network stats
        print("\n2. Testing GET /stats")
        try:
            response = await client.get(f"{API_BASE}/stats")
            if response.status_code == 200:
                stats = response.json()
                print(f"   ✓ Stats retrieved")
                print(f"   - Total words: {stats.get('total_words', 0)}")
                print(f"   - Total relations: {stats.get('total_relations', 0)}")
            elif response.status_code == 503:
                print(f"   ⚠ Neo4j unavailable (expected if not running)")
            else:
                print(f"   ⚠ Status: {response.status_code}")
        except Exception as e:
            print(f"   ✗ Error: {e}")
        
        # Test 3: List jobs
        print("\n3. Testing GET /jobs")
        try:
            response = await client.get(f"{API_BASE}/jobs?limit=5")
            if response.status_code == 200:
                jobs = response.json()
                print(f"   ✓ Found {len(jobs)} jobs")
            else:
                print(f"   ⚠ Status: {response.status_code}")
        except Exception as e:
            print(f"   ✗ Error: {e}")
        
        # Test 4: Get words by POS
        print("\n4. Testing GET /words-by-pos")
        try:
            response = await client.get(f"{API_BASE}/words-by-pos?pos=形容詞&limit=5")
            if response.status_code == 200:
                data = response.json()
                print(f"   ✓ Found {data.get('count', 0)} adjectives")
            elif response.status_code == 503:
                print(f"   ⚠ Neo4j unavailable (expected if not running)")
            else:
                print(f"   ⚠ Status: {response.status_code}")
        except Exception as e:
            print(f"   ✗ Error: {e}")
        
        # Test 5: Get centrality analysis
        print("\n5. Testing GET /centrality")
        try:
            response = await client.get(f"{API_BASE}/centrality?metric=degree&limit=5")
            if response.status_code == 200:
                data = response.json()
                print(f"   ✓ Centrality analysis retrieved")
                print(f"   - Words analyzed: {data.get('count', 0)}")
            elif response.status_code == 503:
                print(f"   ⚠ Neo4j unavailable (expected if not running)")
            else:
                print(f"   ⚠ Status: {response.status_code}")
        except Exception as e:
            print(f"   ✗ Error: {e}")
    
    print("\n" + "=" * 60)
    print("API endpoint tests completed")
    print("=" * 60)
    print("\nNote: Some endpoints may return 503 if Neo4j is not running.")
    print("This is expected and indicates the endpoints are properly configured.")


if __name__ == "__main__":
    print(f"\nTesting API at: {BASE_URL}")
    print("Make sure the backend server is running!\n")
    
    try:
        asyncio.run(test_endpoints())
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
