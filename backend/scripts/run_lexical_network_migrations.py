#!/usr/bin/env python3
"""
Run Neo4j migrations for Lexical Network Builder.

Applies schema and index migrations to Neo4j database.
"""

import asyncio
import sys
from pathlib import Path

from neo4j import AsyncGraphDatabase

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from app.core.config import settings


async def run_migrations():
    """Run lexical network migrations."""
    print("=" * 60)
    print("Lexical Network Builder - Neo4j Migrations")
    print("=" * 60)
    
    # Connect to Neo4j
    driver = AsyncGraphDatabase.driver(
        settings.NEO4J_URI,
        auth=(settings.NEO4J_USERNAME, settings.NEO4J_PASSWORD),
    )
    
    try:
        await driver.verify_connectivity()
        print("✓ Connected to Neo4j")
        
        async with driver.session() as session:
            # Read schema file
            schema_path = backend_path / "migrations" / "lexical_relations_schema.cypher"
            if schema_path.exists():
                print(f"\nReading schema: {schema_path.name}")
                with open(schema_path, "r", encoding="utf-8") as f:
                    schema_content = f.read()
                print("✓ Schema file loaded")
            else:
                print(f"⚠ Schema file not found: {schema_path}")
                schema_content = None
            
            # Read indexes file
            indexes_path = backend_path / "migrations" / "lexical_indexes.cypher"
            if indexes_path.exists():
                print(f"\nReading indexes: {indexes_path.name}")
                with open(indexes_path, "r", encoding="utf-8") as f:
                    indexes_content = f.read()
                print("✓ Indexes file loaded")
            else:
                print(f"⚠ Indexes file not found: {indexes_path}")
                indexes_content = None
            
            # Execute index creation (these are idempotent with IF NOT EXISTS)
            if indexes_content:
                print("\n" + "=" * 60)
                print("Creating indexes...")
                print("=" * 60)
                
                # Split by CREATE statements
                statements = []
                current_statement = []
                
                for line in indexes_content.split("\n"):
                    line = line.strip()
                    if not line or line.startswith("//"):
                        continue
                    
                    current_statement.append(line)
                    
                    if line.endswith(";") or "CREATE" in line and "IF NOT EXISTS" in line:
                        stmt = " ".join(current_statement)
                        if stmt:
                            statements.append(stmt)
                        current_statement = []
                
                # Add any remaining statement
                if current_statement:
                    stmt = " ".join(current_statement)
                    if stmt:
                        statements.append(stmt)
                
                executed = 0
                errors = 0
                
                for stmt in statements:
                    try:
                        await session.run(stmt)
                        executed += 1
                        print(f"✓ Executed: {stmt[:60]}...")
                    except Exception as e:
                        error_msg = str(e)
                        if "already exists" in error_msg.lower() or "equivalent" in error_msg.lower():
                            print(f"⊘ Skipped (already exists): {stmt[:60]}...")
                        else:
                            print(f"✗ Error: {error_msg[:100]}")
                            errors += 1
                
                print(f"\nIndexes: {executed} executed, {errors} errors")
            
            # Verify indexes
            print("\n" + "=" * 60)
            print("Verifying indexes...")
            print("=" * 60)
            
            result = await session.run("SHOW INDEXES")
            indexes = await result.data()
            
            lexical_indexes = [
                idx for idx in indexes
                if "lexical" in str(idx.get("name", "")).lower()
                or "word_embedding" in str(idx.get("name", "")).lower()
            ]
            
            if lexical_indexes:
                print(f"✓ Found {len(lexical_indexes)} lexical-related indexes:")
                for idx in lexical_indexes:
                    print(f"  - {idx.get('name', 'unknown')}")
            else:
                print("⚠ No lexical indexes found (may need to create)")
            
            # Check for LEXICAL_RELATION relationships
            print("\n" + "=" * 60)
            print("Checking existing data...")
            print("=" * 60)
            
            result = await session.run(
                "MATCH ()-[r:LEXICAL_RELATION]->() RETURN count(r) AS count"
            )
            rel_count = (await result.single())["count"]
            print(f"✓ Existing LEXICAL_RELATION edges: {rel_count}")
            
            result = await session.run("MATCH (w:Word) RETURN count(w) AS count")
            word_count = (await result.single())["count"]
            print(f"✓ Total Word nodes: {word_count}")
            
            print("\n" + "=" * 60)
            print("✓ Migrations completed successfully!")
            print("=" * 60)
            print("\nNext steps:")
            print("1. Test the API endpoints: GET /api/v1/lexical-network/stats")
            print("2. Create a test job: POST /api/v1/lexical-network/jobs")
            print("3. Build relations for a word: POST /api/v1/lexical-network/build-relations?word=美しい")
            
    except Exception as e:
        print(f"\n✗ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        await driver.close()
    
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(run_migrations()))
