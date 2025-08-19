"""
Test script for the knowledge graph API endpoints.
Runs inside the Docker environment to test our systems.
"""

import requests
import json
import sys


def test_endpoint(url, description):
    """Test an API endpoint and display results."""
    print(f"\n--- {description} ---")
    try:
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Success ({response.status_code})")
            
            # Pretty print the response
            if isinstance(data, dict):
                if 'total_nodes' in data:  # Stats endpoint
                    print(f"📊 Total Nodes: {data['total_nodes']:,}")
                    print(f"🔗 Total Relationships: {data['total_relationships']:,}")
                    print(f"📚 Words: {data['node_counts']['Word']:,}")
                elif 'status' in data:  # Health endpoint
                    print(f"🏥 Status: {data['status']}")
                    print(f"🔗 Neo4j: {data['neo4j']}")
                    print(f"🐘 PostgreSQL: {data['postgresql']}")
                elif 'results' in data:  # Search endpoint
                    print(f"🔍 Found: {data['total_found']} results in {data['search_time_ms']}ms")
                    for i, result in enumerate(data['results'][:3], 1):
                        kanji = result.get('kanji', 'N/A')
                        translation = result.get('translation', 'N/A')
                        difficulty = result.get('difficulty_level', 'N/A')
                        print(f"  {i}. {kanji} ({translation}) - {difficulty}")
                else:
                    print(json.dumps(data, indent=2, ensure_ascii=False)[:500] + "...")
            else:
                print(str(data)[:500] + "...")
                
        else:
            print(f"❌ Error ({response.status_code}): {response.text[:200]}")
            
    except Exception as e:
        print(f"❌ Exception: {e}")


def main():
    """Test the knowledge graph API."""
    print("🧠 KNOWLEDGE GRAPH API TEST")
    print("=" * 50)
    
    base_url = "http://localhost:8000/api/v1/knowledge"
    
    # Test endpoints
    endpoints = [
        (f"{base_url}/health", "Knowledge Services Health Check"),
        (f"{base_url}/stats", "Knowledge Graph Statistics"),
        ("http://localhost:8000/api/v1/health/detailed", "General Health Check")
    ]
    
    for url, description in endpoints:
        test_endpoint(url, description)
    
    print(f"\n{'='*50}")
    print("🎉 Knowledge Graph API Testing Complete!")
    print("\n📚 Available in your browser:")
    print("   • http://localhost:8000/docs - API Documentation")
    print("   • http://localhost:7474 - Neo4j Browser")
    print("   • http://localhost:8501 - Validation UI")


if __name__ == "__main__":
    main()
