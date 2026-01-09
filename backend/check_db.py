#!/usr/bin/env python3
"""
Check Neo4j database contents using backend's database connection.
"""
import asyncio
import sys
import os

# Add the app directory to the path
sys.path.insert(0, os.path.dirname(__file__))

from app.db import init_neo4j, get_neo4j_session
from neo4j import AsyncSession

async def check_database():
    """Check Neo4j database for data."""
    try:
        # Initialize Neo4j connection
        await init_neo4j()
        
        # Get a session
        async for session in get_neo4j_session():
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
                    print(f"  Found: kanji={rec[0]}, hiragana={rec[1]}, translation={rec[2]}")
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
                    print(f"  kanji={rec[0]}, hiragana={rec[1]}, translation={rec[2]}")
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
            
            break  # Only need one iteration
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(check_database())

