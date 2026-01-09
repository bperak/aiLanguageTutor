#!/usr/bin/env python3
"""
Simple Neo4j import with UTF-8 encoding.
Uses environment variables from .env
"""
import asyncio
import os
from neo4j import AsyncGraphDatabase

async def import_data():
    """Import Neo4j dump with proper UTF-8."""
    # Read from environment (set by docker-compose)
    uri = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
    username = os.getenv("NEO4J_USERNAME", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "testpassword123")
    
    print(f"Connecting to {uri}...")
    driver = AsyncGraphDatabase.driver(uri, auth=(username, password))
    
    try:
        async with driver.session() as session:
            # Clear
            print("Clearing database...")
            await session.run("MATCH (n) DETACH DELETE n")
            
            # Read dump
            dump_path = "/root/neo4j_backup.cypher"
            if not os.path.exists(dump_path):
                dump_path = "../neo4j_backup.cypher"
            
            print(f"Reading {dump_path}...")
            with open(dump_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            # Process transactions - each :begin ... :commit is one transaction
            # Skip the first transaction (index/constraint creation)
            parts = content.split(":begin")
            imported = skipped = errors = 0
            
            for i, part in enumerate(parts):
                if i == 0:  # Skip first part (before first :begin)
                    continue
                
                # Extract transaction (everything before :commit)
                if ":commit" not in part:
                    continue
                
                trans = part.split(":commit")[0].strip()
                if not trans:
                    continue
                
                # Skip index/constraint creation (first real transaction)
                if i == 1 and ("CREATE INDEX" in trans or "CREATE CONSTRAINT" in trans):
                    skipped += 1
                    continue
                
                try:
                    # Split transaction into individual statements
                    # Each UNWIND...CREATE is a separate statement
                    # Better approach: split by "UNWIND" pattern more carefully
                    statements = []
                    lines = trans.split("\n")
                    current_stmt = []
                    
                    for line in lines:
                        line_stripped = line.strip()
                        if not line_stripped:
                            if current_stmt:
                                current_stmt.append("")
                            continue
                        
                        # If we see a new UNWIND and we have content, save previous statement
                        if line_stripped.startswith("UNWIND") and current_stmt:
                            prev_stmt = "\n".join(current_stmt).strip()
                            if prev_stmt and "UNWIND" in prev_stmt:
                                statements.append(prev_stmt)
                            current_stmt = [line]
                        else:
                            current_stmt.append(line)
                    
                    # Add final statement
                    if current_stmt:
                        final_stmt = "\n".join(current_stmt).strip()
                        if final_stmt and "UNWIND" in final_stmt:
                            statements.append(final_stmt)
                    
                    # Execute each statement (run individually, not in explicit transaction)
                    for stmt in statements:
                        stmt = stmt.strip()
                        if not stmt or stmt.startswith("CALL db.awaitIndexes"):
                            continue
                        
                        # Ensure statement ends with semicolon
                        if not stmt.rstrip().endswith(";"):
                            stmt = stmt.rstrip() + ";"
                        
                        try:
                            result = await session.run(stmt)
                            await result.consume()
                        except Exception as e:
                            error_str = str(e)
                            if "already exists" not in error_str and "equivalent" not in error_str:
                                # Don't fail the whole transaction, just log
                                if errors < 10:
                                    print(f"  Statement error in transaction {i}: {error_str[:100]}")
                                errors += 1
                    
                    imported += 1
                    if imported % 5 == 0:
                        print(f"Imported {imported}/{len(parts)-1} transactions...")
                except Exception as e:
                    error_str = str(e)
                    if "already exists" not in error_str and "equivalent" not in error_str:
                        errors += 1
                        if errors <= 10:
                            print(f"Transaction {i} error: {error_str[:150]}")
            
            print(f"\nDone: {imported} imported, {skipped} skipped, {errors} errors")
            
            # Test encoding
            result = await session.run(
                "MATCH (w:Word) WHERE w.translation = 'show' "
                "RETURN w.standard_orthography AS kanji, w.reading_hiragana AS hiragana LIMIT 1"
            )
            rec = await result.single()
            if rec:
                k = rec.get("kanji", "")
                h = rec.get("hiragana", "")
                print(f"\nTest: kanji='{k}', hiragana='{h}'")
                if "?" not in k and "?" not in h and k and h:
                    print("✅ Encoding OK!")
                else:
                    print("❌ Encoding issue!")
            
            result = await session.run("MATCH (n:Word) RETURN count(n) as c")
            count = (await result.single())["c"]
            print(f"Total words: {count}")
    finally:
        await driver.close()

if __name__ == "__main__":
    asyncio.run(import_data())

