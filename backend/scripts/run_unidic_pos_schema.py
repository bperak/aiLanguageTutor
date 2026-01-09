"""
Run UniDic POS Schema Migration

Applies the Cypher migration file to create indexes for canonical POS fields.
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from neo4j import AsyncGraphDatabase
from dotenv import load_dotenv
import os
import structlog

logger = structlog.get_logger()

load_dotenv()


async def run_schema_migration():
    """Run the Cypher schema migration."""
    # Read the migration file
    migration_file = backend_path / "migrations" / "unidic_pos_schema.cypher"
    if not migration_file.exists():
        logger.error("Migration file not found", path=str(migration_file))
        return False
    
    with open(migration_file, "r", encoding="utf-8") as f:
        cypher_script = f.read()
    
    # Get Neo4j connection
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.getenv("NEO4J_USERNAME", os.getenv("NEO4J_USER", "neo4j"))
    neo4j_password = os.getenv("NEO4J_PASSWORD", "password")
    
    driver = AsyncGraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
    
    try:
        async with driver.session() as session:
            # Split by statements (semicolon followed by newline or end)
            statements = [
                s.strip()
                for s in cypher_script.split(";")
                if s.strip() and not s.strip().startswith("//")
            ]
            
            logger.info("Running schema migration", statement_count=len(statements))
            
            for i, statement in enumerate(statements, 1):
                if not statement or statement.startswith("//"):
                    continue
                
                try:
                    result = await session.run(statement)
                    # Consume result
                    await result.consume()
                    logger.info(f"Executed statement {i}/{len(statements)}")
                except Exception as e:
                    # Some statements might fail if indexes already exist (IF NOT EXISTS)
                    if "already exists" in str(e).lower() or "equivalent index" in str(e).lower():
                        logger.info(f"Statement {i} skipped (already exists)", statement=statement[:50])
                    else:
                        logger.error(f"Statement {i} failed", error=str(e), statement=statement[:100])
                        raise
            
            # Run verification queries
            logger.info("Running verification queries")
            verify_query = """
            MATCH (w:Word)
            RETURN 
                count(*) AS total_words,
                sum(CASE WHEN w.pos1 IS NOT NULL THEN 1 ELSE 0 END) AS has_pos1,
                sum(CASE WHEN w.pos_primary_norm IS NOT NULL THEN 1 ELSE 0 END) AS has_pos_primary_norm,
                sum(CASE WHEN w.pos_source IS NOT NULL THEN 1 ELSE 0 END) AS has_pos_source
            """
            result = await session.run(verify_query)
            record = await result.single()
            
            if record:
                logger.info("Schema migration complete", stats=dict(record))
                print("\n=== Schema Migration Complete ===")
                print(f"Total words: {record['total_words']}")
                print(f"Words with pos1: {record['has_pos1']}")
                print(f"Words with pos_primary_norm: {record['has_pos_primary_norm']}")
                print(f"Words with pos_source: {record['has_pos_source']}")
            
            return True
    
    finally:
        await driver.close()


if __name__ == "__main__":
    success = asyncio.run(run_schema_migration())
    sys.exit(0 if success else 1)
