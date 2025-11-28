#!/usr/bin/env python3
"""
Test performance improvement after applying Neo4j indexes.

This script tests the lexical graph API endpoints to measure
performance improvements for Depth 1 and Depth 2 queries.
"""

import asyncio
import time
import aiohttp
import json


async def test_api_performance():
    """Test the API performance for different depth queries."""
    
    print("🧪 Testing API Performance After Index Optimization")
    print("=" * 60)
    
    # Test different search terms and depths
    test_cases = [
        {"term": "日本", "depth": 1, "description": "Depth 1 - Basic search"},
        {"term": "日本", "depth": 2, "description": "Depth 2 - Extended search"},
        {"term": "nihon", "depth": 1, "description": "Depth 1 - Romaji search"},
        {"term": "nihon", "depth": 2, "description": "Depth 2 - Romaji extended"},
    ]
    
    base_url = "http://localhost:8000/api/v1/lexical/graph"
    
    async with aiohttp.ClientSession() as session:
        for test_case in test_cases:
            print(f"\n📊 {test_case['description']}")
            print(f"   Term: '{test_case['term']}', Depth: {test_case['depth']}")
            
            # Build URL
            params = {
                "center": test_case["term"],
                "depth": test_case["depth"]
            }
            
            url = f"{base_url}?center={params['center']}&depth={params['depth']}"
            
            try:
                # Measure response time
                start_time = time.time()
                
                async with session.get(url) as response:
                    response_time = (time.time() - start_time) * 1000
                    
                    if response.status == 200:
                        data = await response.json()
                        nodes_count = len(data.get("nodes", []))
                        links_count = len(data.get("links", []))
                        
                        print(f"   ✅ Success: {response_time:.1f}ms")
                        print(f"   📊 Results: {nodes_count} nodes, {links_count} links")
                        
                        # Performance assessment
                        if test_case["depth"] == 1:
                            if response_time < 100:
                                print("   🚀 EXCELLENT performance!")
                            elif response_time < 500:
                                print("   ✅ GOOD performance")
                            else:
                                print("   ⚠️  NEEDS IMPROVEMENT")
                        else:  # Depth 2
                            if response_time < 1000:
                                print("   🚀 EXCELLENT performance!")
                            elif response_time < 5000:
                                print("   ✅ GOOD performance")
                            else:
                                print("   ⚠️  NEEDS IMPROVEMENT")
                    else:
                        print(f"   ❌ HTTP {response.status}: {await response.text()}")
                        
            except Exception as e:
                print(f"   ❌ Error: {e}")


async def test_frontend_accessibility():
    """Test if the frontend is accessible."""
    
    print("\n🌐 Testing Frontend Accessibility")
    print("=" * 40)
    
    try:
        async with aiohttp.ClientSession() as session:
            # Test main page
            start_time = time.time()
            async with session.get("http://localhost:3000") as response:
                response_time = (time.time() - start_time) * 1000
                
                if response.status == 200:
                    print(f"✅ Main page: {response_time:.1f}ms")
                else:
                    print(f"❌ Main page: HTTP {response.status}")
            
            # Test lexical graph page
            start_time = time.time()
            async with session.get("http://localhost:3000/lexical/graph") as response:
                response_time = (time.time() - start_time) * 1000
                
                if response.status == 200:
                    print(f"✅ Lexical graph page: {response_time:.1f}ms")
                else:
                    print(f"❌ Lexical graph page: HTTP {response.status}")
                    
    except Exception as e:
        print(f"❌ Frontend test error: {e}")


async def main():
    """Main test function."""
    print("🚀 Performance Improvement Test Suite")
    print("=" * 60)
    
    try:
        # Test frontend accessibility
        await test_frontend_accessibility()
        
        # Test API performance
        await test_api_performance()
        
        print("\n🎯 Performance Test Complete!")
        print("\n💡 Expected Results:")
        print("   - Depth 1 queries should be under 100ms (EXCELLENT)")
        print("   - Depth 2 queries should be under 1000ms (EXCELLENT)")
        print("   - If still slow, indexes may need more time to optimize")
        
        print("\n🚀 Next Steps:")
        print("   1. Open http://localhost:3000/lexical/graph")
        print("   2. Test Depth 2 search for 'nihon'")
        print("   3. Compare performance with before optimization")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")


if __name__ == "__main__":
    asyncio.run(main())
