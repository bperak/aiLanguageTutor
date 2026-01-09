#!/usr/bin/env python3
"""
Import Neo4j data from cypher dump, skipping index/constraint creation.
"""
import asyncio
import os
from neo4j import AsyncGraphDatabase
from dotenv import load_dotenv

load_dotenv()

async def import_data():
    """Import data from cypher file, skipping schema creation."""
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    username = os.getenv("NEO4J_USERNAME", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "")
    
    driver = AsyncGraphDatabase.driver(uri, auth=(username, password))
    
    try:
        async with driver.session() as session:
            # Clear database first
            await session.run("MATCH (n) DETACH DELETE n")
            print("Database cleared")
            
            # Read the dump file
            with open("neo4j_backup.cypher", "r", encoding="utf-8") as f:
                content = f.read()
            
            # Split by transactions
            transactions = content.split(":commit")
            
            imported = 0
            skipped = 0
            
            for i, trans in enumerate(transactions):
                if not trans.strip() or trans.strip() == ":begin":
                    continue
                
                # Skip first transaction (index/constraint creation)
                if i == 0:
                    skipped += 1
                    continue
                
                # Remove :begin if present
                trans = trans.replace(":begin", "").strip()
                if not trans:
                    continue
                
                try:
                    # Execute transaction
                    result = await session.run(trans)
                    await result.consume()
                    imported += 1
                    if imported % 100 == 0:
                        print(f"Imported {imported} transactions...")
                except Exception as e:
                    print(f"Error in transaction {i}: {str(e)[:100]}")
                    # Continue with next transaction
                    continue
            
            print(f"\nImport complete: {imported} transactions imported, {skipped} skipped")
            
            # Verify
            result = await session.run("MATCH (n:Word) RETURN count(n) as count")
            record = await result.single()
            print(f"Word nodes in database: {record['count'] if record else 0}")
            
    finally:
        await driver.close()

if __name__ == "__main__":
    asyncio.run(import_data())

