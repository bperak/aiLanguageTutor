#!/usr/bin/env python3
"""Simple connection test for unification script"""

import os
from pathlib import Path
from dotenv import load_dotenv
from neo4j import GraphDatabase

# Load environment variables
env_path = Path(__file__).parent.parent / '.env'
print(f"Looking for .env at: {env_path}")
print(f".env exists: {env_path.exists()}")

load_dotenv(env_path)

# Get connection details
URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
USER = os.getenv("NEO4J_USERNAME", "neo4j")
PASSWORD = os.getenv("NEO4J_PASSWORD", "testpassword123")

print(f"URI: {URI}")
print(f"USER: {USER}")
print(f"PASSWORD: {'***' if PASSWORD else 'NOT SET'}")

# Handle Docker container URIs
if URI.startswith("neo4j://neo4j:"):
    URI = URI.replace("neo4j://neo4j:", "bolt://localhost:")
elif URI.startswith("neo4j://"):
    URI = URI.replace("neo4j://", "bolt://localhost:")

print(f"Final URI: {URI}")

# Test connection
try:
    driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))
    with driver.session() as session:
        result = session.run("RETURN 'Connection successful' as status")
        status = result.single()['status']
        print(f"✅ {status}")
        
        # Test a simple query
        result = session.run("MATCH (w:Word) RETURN count(w) as count")
        count = result.single()['count']
        print(f"✅ Found {count:,} Word nodes")
        
    driver.close()
    print("✅ Connection test successful!")
    
except Exception as e:
    print(f"❌ Connection failed: {e}")
    if 'driver' in locals():
        driver.close()


