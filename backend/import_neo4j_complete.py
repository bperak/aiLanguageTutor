#!/usr/bin/env python3
"""
Complete Neo4j import with proper transaction handling.
Uses environment variables from .env
"""
import asyncio
import os
import re
from neo4j import AsyncGraphDatabase

async def import_data():
    """Import Neo4j dump with proper UTF-8 and transaction handling."""
    # Read from environment (set by docker-compose)
    uri = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
    username = os.getenv("NEO4J_USERNAME", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "testpassword123")
    
    print(f"Connecting to {uri}...")
    driver = AsyncGraphDatabase.driver(uri, auth=(username, password))
    
    try:
        async with driver.session() as session:
            # Clear database
            print("Clearing database...")
            await session.run("MATCH (n) DETACH DELETE n")
            
            # Read dump - check /app first since that's where we copied it
            dump_path = "/app/neo4j_backup.cypher"
            if not os.path.exists(dump_path):
                dump_path = "/root/aiLanguageTutor/neo4j_backup.cypher"
            if not os.path.exists(dump_path):
                dump_path = "../neo4j_backup.cypher"
            
            if not os.path.exists(dump_path):
                raise FileNotFoundError(f"Backup file not found. Tried: /app/neo4j_backup.cypher, /root/aiLanguageTutor/neo4j_backup.cypher, ../neo4j_backup.cypher")
            
            print(f"Reading {dump_path}...")
            with open(dump_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            # Split into transactions
            # Pattern: :begin ... :commit
            transactions = []
            parts = content.split(":begin")
            
            for i, part in enumerate(parts):
                if i == 0:  # Skip header
                    continue
                
                if ":commit" not in part:
                    continue
                
                trans_content = part.split(":commit")[0].strip()
                if not trans_content:
                    continue
                
                # Skip index/constraint creation
                if "CREATE INDEX" in trans_content or "CREATE CONSTRAINT" in trans_content:
                    print(f"Skipping transaction {i} (index/constraint creation)")
                    continue
                
                transactions.append((i, trans_content))
            
            print(f"Found {len(transactions)} transactions to import")
            
            imported = 0
            errors = 0
            total_statements = 0
            
            # Process each transaction
            for trans_num, trans_content in transactions:
                try:
                    # Split into individual Cypher statements
                    # Each statement ends with a semicolon (but be careful with multiline)
                    # Better approach: split by UNWIND (each UNWIND starts a new statement)
                    statements = []
                    
                    # Split by UNWIND pattern
                    unwind_pattern = r'(UNWIND\s+\[)'
                    parts = re.split(unwind_pattern, trans_content)
                    
                    current_stmt = ""
                    for i, part in enumerate(parts):
                        if part.strip().startswith("UNWIND"):
                            if current_stmt.strip():
                                statements.append(current_stmt.strip())
                            current_stmt = part
                        else:
                            current_stmt += part
                            # Check if statement is complete (ends with semicolon or CREATE)
                            if current_stmt.strip().endswith(";") or "CREATE" in current_stmt:
                                # Check if it's a complete statement
                                if current_stmt.count("UNWIND") == current_stmt.count("CREATE"):
                                    statements.append(current_stmt.strip())
                                    current_stmt = ""
                    
                    if current_stmt.strip():
                        statements.append(current_stmt.strip())
                    
                    # Alternative: simpler approach - split by semicolon and reconstruct
                    # But UNWIND statements can span multiple lines
                    # Let's use a simpler approach: split by "UNWIND" and reconstruct
                    statements = []
                    lines = trans_content.split("\n")
                    current = []
                    
                    for line in lines:
                        line = line.strip()
                        if not line:
                            continue
                        
                        current.append(line)
                        
                        # If line starts with UNWIND and we have previous content, save it
                        if line.startswith("UNWIND") and len(current) > 1:
                            prev_stmt = "\n".join(current[:-1])
                            if prev_stmt.strip():
                                statements.append(prev_stmt.strip())
                            current = [line]
                        
                        # If line ends with semicolon and contains CREATE, it's a complete statement
                        if line.endswith(";") and "CREATE" in "\n".join(current):
                            stmt = "\n".join(current)
                            if stmt.strip() and "UNWIND" in stmt:
                                statements.append(stmt.strip())
                                current = []
                    
                    # Add remaining
                    if current:
                        stmt = "\n".join(current)
                        if stmt.strip() and "UNWIND" in stmt:
                            statements.append(stmt.strip())
                    
                    # Execute statements directly (Neo4j auto-commits each statement)
                    for stmt in statements:
                        stmt = stmt.strip()
                        if not stmt:
                            continue
                        if stmt.startswith("CALL db.awaitIndexes"):
                            continue
                        
                        # Ensure statement ends with semicolon
                        if not stmt.endswith(";"):
                            stmt += ";"
                        
                        try:
                            result = await session.run(stmt)
                            await result.consume()
                            total_statements += 1
                        except Exception as e:
                            error_str = str(e)
                            if "already exists" not in error_str.lower() and "equivalent" not in error_str.lower() and "constraint" not in error_str.lower():
                                if errors < 10:  # Only show first 10 errors
                                    print(f"  Statement error in transaction {trans_num}: {error_str[:100]}")
                                errors += 1
                    
                    imported += 1
                    if imported % 5 == 0:
                        print(f"Imported {imported}/{len(transactions)} transactions ({total_statements} statements)...")
                        
                except Exception as e:
                    error_str = str(e)
                    print(f"Transaction {trans_num} error: {error_str[:200]}")
                    errors += 1
            
            print(f"\n✅ Done: {imported} transactions imported, {total_statements} statements executed, {errors} errors")
            
            # Verify import
            result = await session.run("MATCH (n:Word) RETURN count(n) as c")
            count = (await result.single())["c"]
            print(f"Total Word nodes: {count}")
            
            result = await session.run("MATCH (n) RETURN labels(n)[0] as label, count(*) as count ORDER BY count DESC LIMIT 10")
            print("\nNode counts by label:")
            async for record in result:
                print(f"  {record['label']}: {record['count']}")
            
            # Test encoding
            result = await session.run(
                "MATCH (w:Word) WHERE w.translation = 'show' "
                "RETURN w.standard_orthography AS kanji, w.reading_hiragana AS hiragana LIMIT 1"
            )
            rec = await result.single()
            if rec:
                k = rec.get("kanji", "")
                h = rec.get("hiragana", "")
                print(f"\nEncoding test: kanji='{k}', hiragana='{h}'")
                if "?" not in k and "?" not in h and k and h:
                    print("✅ Encoding OK!")
                else:
                    print("❌ Encoding issue!")
    finally:
        await driver.close()

if __name__ == "__main__":
    asyncio.run(import_data())

