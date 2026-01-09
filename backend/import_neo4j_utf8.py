#!/usr/bin/env python3
"""
Import Neo4j data with proper UTF-8 encoding using Python driver.
"""
import asyncio
import os
import sys

# Add app directory to path
sys.path.insert(0, os.path.dirname(__file__))

# Use backend's database connection
from app.db import init_neo4j, get_neo4j_session

async def import_with_utf8():
    """Import Neo4j dump with proper UTF-8 encoding."""
    print("Initializing Neo4j connection...")
    await init_neo4j()
    
    # Get session using backend's dependency
    async for session in get_neo4j_session():
            # Clear database
            print("Clearing database...")
            await session.run("MATCH (n) DETACH DELETE n")
            
            # Read dump file with UTF-8 encoding
            dump_path = "../neo4j_backup.cypher"
            print(f"Reading dump file: {dump_path}")
            
            with open(dump_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            # Split by transactions
            transactions = content.split(":commit")
            
            imported = 0
            skipped = 0
            errors = 0
            
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
                    error_msg = str(e)
                    # Skip duplicate index/constraint errors
                    if "already exists" in error_msg or "equivalent" in error_msg:
                        skipped += 1
                        continue
                    errors += 1
                    if errors <= 10:  # Only show first 10 errors
                        print(f"Error in transaction {i}: {error_msg[:150]}")
                    continue
            
            print(f"\nImport complete:")
            print(f"  - Imported: {imported} transactions")
            print(f"  - Skipped: {skipped} transactions")
            print(f"  - Errors: {errors} transactions")
            
            # Verify with a test query
            result = await session.run("MATCH (w:Word) WHERE w.translation = 'show' RETURN w.standard_orthography, w.reading_hiragana LIMIT 1")
            record = await result.single()
            if record:
                kanji = record.get("w.standard_orthography", "")
                hiragana = record.get("w.reading_hiragana", "")
                print(f"\nTest query result:")
                print(f"  Kanji: {kanji}")
                print(f"  Hiragana: {hiragana}")
                if "?" in kanji or "?" in hiragana:
                    print("  ⚠️  WARNING: Encoding issue detected!")
                else:
                    print("  ✅ Encoding looks correct!")
            
            # Count words
            result = await session.run("MATCH (n:Word) RETURN count(n) as count")
            record = await result.single()
            word_count = record["count"] if record else 0
            print(f"\nTotal Word nodes: {word_count}")
            
            break  # Only need one iteration

if __name__ == "__main__":
    asyncio.run(import_with_utf8())

