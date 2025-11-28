#!/usr/bin/env python
"""
Apply Neo4j vector index migration for CanDoDescriptor embeddings.

This script reads the Cypher migration file and applies it to Neo4j.

Usage (PowerShell on Windows):
  python -m venv .venv ; .\.venv\Scripts\Activate.ps1
  pip install neo4j python-dotenv
  python scripts\apply_cando_vector_index.py
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv
from neo4j import AsyncGraphDatabase


def _normalize_uri(uri: str) -> str:
    """Normalize docker-style neo4j scheme to bolt for local dev."""
    if uri.startswith("neo4j://neo4j:"):
        return uri.replace("neo4j://neo4j:", "bolt://localhost:")
    if uri.startswith("neo4j://"):
        return uri.replace("neo4j://", "bolt://")
    return uri


async def main() -> None:
    """Apply vector index migration."""
    # Load environment
    project_root = Path(__file__).parent.parent
    env_path = project_root / ".env"
    load_dotenv(env_path)
    
    # Get Neo4j connection
    neo4j_uri = _normalize_uri(os.getenv("NEO4J_URI", "bolt://localhost:7687"))
    neo4j_user = os.getenv("NEO4J_USER", os.getenv("NEO4J_USERNAME", "neo4j"))
    neo4j_password = os.getenv("NEO4J_PASSWORD")
    
    if not neo4j_password:
        raise RuntimeError("NEO4J_PASSWORD is not set. Please define it in your .env file.")
    
    # Read migration file
    migration_file = project_root / "backend" / "migrations" / "create_cando_vector_index.cypher"
    if not migration_file.exists():
        raise FileNotFoundError(f"Migration file not found: {migration_file}")
    
    with open(migration_file, "r", encoding="utf-8") as f:
        cypher_script = f.read()
    
    # Connect to Neo4j
    driver = AsyncGraphDatabase.driver(
        neo4j_uri,
        auth=(neo4j_user, neo4j_password)
    )
    
    try:
        async with driver.session() as session:
            # Check connectivity
            await driver.verify_connectivity()
            print(f"Connected to Neo4j at {neo4j_uri}")
            
            # Split script into individual statements
            # Remove comment lines and split by semicolon
            lines = [line.strip() for line in cypher_script.split("\n") if line.strip() and not line.strip().startswith("//")]
            script_without_comments = "\n".join(lines)
            statements = [s.strip() for s in script_without_comments.split(";") if s.strip()]
            
            print(f"\nApplying {len(statements)} Cypher statements...")
            
            for i, statement in enumerate(statements, 1):
                if not statement:
                    continue
                
                try:
                    print(f"\n[{i}/{len(statements)}] Executing statement...")
                    result = await session.run(statement)
                    
                    # Try to get results if it's a query
                    if "SHOW" in statement.upper() or "RETURN" in statement.upper():
                        records = [record async for record in result]
                        if records:
                            print(f"  Result: {len(records)} record(s)")
                            for record in records[:3]:  # Show first 3
                                print(f"    {dict(record)}")
                    else:
                        # For CREATE/DROP statements, just await
                        await result.consume()
                        print(f"  ✓ Statement executed successfully")
                    
                except Exception as e:
                    # Some statements might fail if index already exists, which is okay
                    if "already exists" in str(e).lower() or "does not exist" in str(e).lower():
                        print(f"  ⚠ {str(e)}")
                    else:
                        print(f"  ✗ Error: {e}")
                        raise
            
            print("\n✓ Vector index migration completed!")
            
            # Verify index was created
            print("\nVerifying index creation...")
            result = await session.run(
                """
                SHOW INDEXES YIELD name, type, state, populationPercent
                WHERE name = 'cando_descriptor_embeddings'
                RETURN name, type, state, populationPercent
                """
            )
            
            records = [record async for record in result]
            if records:
                for record in records:
                    print(f"  Index: {record.get('name')}")
                    print(f"  Type: {record.get('type')}")
                    print(f"  State: {record.get('state')}")
                    print(f"  Population: {record.get('populationPercent', 0)}%")
            else:
                print("  ⚠ Index not found - it may need time to populate")
            
    except Exception as e:
        print(f"\n✗ Error: {e}")
        raise
    finally:
        await driver.close()


if __name__ == "__main__":
    asyncio.run(main())

