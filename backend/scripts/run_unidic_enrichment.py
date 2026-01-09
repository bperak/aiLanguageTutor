"""
Run UniDic Enrichment

Enriches Word nodes with UniDic morphological data and sets canonical POS.
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

from app.services.lexical_network.unidic_enrichment_service import UnidicEnrichmentService

logger = structlog.get_logger()

load_dotenv()


async def run_enrichment(limit: int = 1000, pos_filter: str = None):
    """Run UniDic enrichment."""
    # Get Neo4j connection
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.getenv("NEO4J_USERNAME", os.getenv("NEO4J_USER", "neo4j"))
    neo4j_password = os.getenv("NEO4J_PASSWORD", "password")
    
    # If URI contains 'neo4j:' (Docker network), use that; otherwise try localhost
    if "neo4j:" in neo4j_uri:
        # Running in Docker, use internal network
        pass
    else:
        # Running from host, try localhost
        neo4j_uri = "bolt://localhost:7687"
    
    driver = AsyncGraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
    
    try:
        async with driver.session() as session:
            service = UnidicEnrichmentService()
            
            if not service.is_available:
                logger.error("UniDic not available - fugashi not installed or UniDic dictionary not downloaded")
                return False
            
            logger.info("Starting UniDic enrichment", limit=limit, pos_filter=pos_filter)
            stats = await service.batch_enrich(session, limit=limit, pos_filter=pos_filter)
            
            logger.info("UniDic enrichment complete", stats=stats)
            print("\n=== UniDic Enrichment Complete ===")
            print(f"Enriched: {stats.get('enriched', 0)}")
            print(f"Skipped: {stats.get('skipped', 0)}")
            print(f"Errors: {stats.get('errors', 0)}")
            
            return True
    
    finally:
        await driver.close()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Run UniDic enrichment")
    parser.add_argument("--limit", type=int, default=1000, help="Maximum words to process")
    parser.add_argument("--pos-filter", type=str, default=None, help="Optional POS filter")
    
    args = parser.parse_args()
    
    success = asyncio.run(run_enrichment(limit=args.limit, pos_filter=args.pos_filter))
    sys.exit(0 if success else 1)
