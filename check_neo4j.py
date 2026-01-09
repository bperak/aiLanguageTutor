#!/usr/bin/env python3
"""
Quick script to check Neo4j database contents.
"""
import asyncio
import os
from neo4j import AsyncGraphDatabase
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def check_neo4j():
    """Check Neo4j database for data."""
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    username = os.getenv("NEO4J_USERNAME", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "")
    
    print(f"Connecting to Neo4j at {uri}...")
    driver = AsyncGraphDatabase.driver(uri, auth=(username, password))
    
    try:
        async with driver.session() as session:
            # Check total node count
            result = await session.run("MATCH (n) RETURN count(n) as total")
            record = await result.single()
            total_nodes = record["total"] if record else 0
            print(f"\nTotal nodes in database: {total_nodes}")
            
            # Check Word nodes
            result = await session.run("MATCH (n:Word) RETURN count(n) as count")
            record = await result.single()
            word_count = record["count"] if record else 0
            print(f"Word nodes: {word_count}")
            
            # Check for specific word "日本"
            result = await session.run("""
                MATCH (w:Word)
                WHERE coalesce(w.standard_orthography, w.kanji) = $kanji
                   OR coalesce(w.reading_hiragana, w.hiragana) = $hiragana
                   OR w.translation CONTAINS $translation
                RETURN coalesce(w.standard_orthography, w.kanji) AS kanji,
                       coalesce(w.reading_hiragana, w.hiragana) AS hiragana,
                       w.translation AS translation
                LIMIT 5
            """, kanji="日本", hiragana="にほん", translation="Japan")
            records = await result.values()
            print(f"\nSearching for '日本' (Japan):")
            if records:
                for rec in records:
                    print(f"  Found: {rec}")
            else:
                print("  Not found")
            
            # Get sample words
            result = await session.run("""
                MATCH (w:Word)
                RETURN coalesce(w.standard_orthography, w.kanji) AS kanji,
                       coalesce(w.reading_hiragana, w.hiragana) AS hiragana,
                       w.translation AS translation
                LIMIT 10
            """)
            records = await result.values()
            print(f"\nSample words (first 10):")
            if records:
                for rec in records:
                    print(f"  {rec}")
            else:
                print("  No words found")
            
            # Check node labels
            result = await session.run("CALL db.labels()")
            labels = [record["label"] for record in await result.values()]
            print(f"\nNode labels in database: {labels}")
            
            # Check relationship types
            result = await session.run("CALL db.relationshipTypes()")
            rel_types = [record["relationshipType"] for record in await result.values()]
            print(f"\nRelationship types: {rel_types}")
            
    finally:
        await driver.close()

if __name__ == "__main__":
    asyncio.run(check_neo4j())

