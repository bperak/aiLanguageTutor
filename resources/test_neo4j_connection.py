#!/usr/bin/env python3
"""Simple Neo4j connection test"""

import os
from pathlib import Path
from dotenv import load_dotenv
from neo4j import GraphDatabase

# Load environment variables
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

# Get connection details
URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
USER = os.getenv("NEO4J_USERNAME", "neo4j")
PASSWORD = os.getenv("NEO4J_PASSWORD")

print(f"Testing connection to: {URI}")
print(f"Username: {USER}")
print(f"Password length: {len(PASSWORD) if PASSWORD else 0}")

# Try different connection variations
test_configs = [
    {"uri": URI, "user": USER, "password": PASSWORD},
    {"uri": "bolt://localhost:7687", "user": "neo4j", "password": PASSWORD},
    {"uri": "bolt://localhost:7687", "user": "neo4j", "password": "testpassword123"},
    {"uri": "bolt://localhost:7687", "user": "neo4j", "password": "neo4j"},
]

for i, config in enumerate(test_configs, 1):
    print(f"\n--- Test {i} ---")
    print(f"URI: {config['uri']}")
    print(f"User: {config['user']}")
    print(f"Password: {'***' if config['password'] else 'None'}")
    
    try:
        driver = GraphDatabase.driver(config['uri'], auth=(config['user'], config['password']))
        with driver.session() as session:
            result = session.run("RETURN 'Connection successful' as status")
            status = result.single()['status']
            print(f"✅ {status}")
            driver.close()
            break
    except Exception as e:
        print(f"❌ Failed: {e}")
        if driver:
            driver.close()


