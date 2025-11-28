#!/usr/bin/env python3
"""
Test environment variables and Neo4j connection
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from root .env file
project_root = Path(__file__).parent.parent
load_dotenv(project_root / ".env")

print("Environment Variables:")
print(f"NEO4J_URI: {os.getenv('NEO4J_URI')}")
print(f"NEO4J_USERNAME: {os.getenv('NEO4J_USERNAME')}")
print(f"NEO4J_PASSWORD: {os.getenv('NEO4J_PASSWORD')}")
print(f"GEMINI_API_KEY: {'SET' if os.getenv('GEMINI_API_KEY') else 'NOT SET'}")

# Test Neo4j connection
try:
    from neo4j import AsyncGraphDatabase
    import asyncio
    
    async def test_neo4j():
        driver = AsyncGraphDatabase.driver(
            os.getenv('NEO4J_URI'),
            auth=(os.getenv('NEO4J_USERNAME'), os.getenv('NEO4J_PASSWORD'))
        )
        
        try:
            await driver.verify_connectivity()
            print("✅ Neo4j connection successful!")
            
            # Test a simple query
            async with driver.session() as session:
                result = await session.run("RETURN 'Hello Neo4j' as message")
                record = await result.single()
                print(f"Query result: {record['message']}")
                
        except Exception as e:
            print(f"❌ Neo4j connection failed: {e}")
        finally:
            await driver.close()
    
    asyncio.run(test_neo4j())
    
except ImportError as e:
    print(f"❌ Import error: {e}")
except Exception as e:
    print(f"❌ Error: {e}")
