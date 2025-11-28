#!/usr/bin/env python3
"""Test with correct Neo4j credentials from docker-compose.yml"""

from neo4j import GraphDatabase

# Correct credentials from docker-compose.yml
URI = "bolt://localhost:7687"
USER = "neo4j"
PASSWORD = "testpassword123"

print(f"Testing with correct credentials:")
print(f"URI: {URI}")
print(f"User: {USER}")
print(f"Password: {PASSWORD}")

try:
    driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))
    with driver.session() as session:
        result = session.run("RETURN 'Connection successful' as status")
        status = result.single()['status']
        print(f"✅ {status}")
        
        # Test a simple query
        result = session.run("MATCH (n) RETURN count(n) as node_count")
        node_count = result.single()['node_count']
        print(f"✅ Total nodes in database: {node_count}")
        
        # Test relationship count
        result = session.run("MATCH ()-[r]->() RETURN count(r) as rel_count")
        rel_count = result.single()['rel_count']
        print(f"✅ Total relationships in database: {rel_count}")
        
    driver.close()
    print("✅ Connection test successful!")
    
except Exception as e:
    print(f"❌ Connection failed: {e}")
    if 'driver' in locals():
        driver.close()


