"""
Run UniDic Enrichment Until Complete

Continuously runs enrichment until all words have canonical POS or no more can be enriched.
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


async def get_missing_count(session):
    """Get count of words missing POS that can be enriched."""
    query = """
    MATCH (w:Word)
    WHERE w.unidic_lemma IS NULL AND w.pos1 IS NULL
    RETURN count(*) AS count
    """
    result = await session.run(query)
    record = await result.single()
    return record["count"] if record else 0


async def run_until_complete(batch_size: int = 5000):
    """Run enrichment until all words are processed."""
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "password")
    
    driver = AsyncGraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
    
    try:
        async with driver.session() as session:
            service = UnidicEnrichmentService()
            
            if not service.is_available:
                logger.error("UniDic not available")
                return False
            
            total_enriched = 0
            batch_num = 0
            
            while True:
                batch_num += 1
                missing_before = await get_missing_count(session)
                
                if missing_before == 0:
                    logger.info("All words have been processed!")
                    break
                
                logger.info(
                    f"Starting batch {batch_num}",
                    words_remaining=missing_before,
                    total_enriched_so_far=total_enriched
                )
                
                stats = await service.batch_enrich(session, limit=batch_size)
                enriched = stats.get("enriched", 0)
                total_enriched += enriched
                
                logger.info(
                    f"Batch {batch_num} complete",
                    enriched_this_batch=enriched,
                    skipped=stats.get("skipped", 0),
                    errors=stats.get("errors", 0),
                    total_enriched=total_enriched
                )
                
                # Check progress
                missing_after = await get_missing_count(session)
                progress = ((missing_before - missing_after) / missing_before * 100) if missing_before > 0 else 0
                
                print(f"\nBatch {batch_num} Results:")
                print(f"  Enriched: {enriched:,}")
                print(f"  Remaining: {missing_after:,} ({missing_after/missing_before*100:.1f}% of batch start)")
                print(f"  Total enriched so far: {total_enriched:,}")
                print()
                
                # If no words were enriched, we're done
                if enriched == 0:
                    logger.info("No more words can be enriched")
                    break
                
                # Small delay between batches to avoid overwhelming the system
                await asyncio.sleep(1)
            
            # Final status
            final_missing = await get_missing_count(session)
            print("\n" + "=" * 70)
            print("ENRICHMENT COMPLETE")
            print("=" * 70)
            print(f"Total batches: {batch_num}")
            print(f"Total words enriched: {total_enriched:,}")
            print(f"Words still missing POS: {final_missing:,}")
            print("=" * 70)
            
            return True
    
    finally:
        await driver.close()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Run UniDic enrichment until complete")
    parser.add_argument("--batch-size", type=int, default=5000, help="Batch size per run")
    
    args = parser.parse_args()
    
    success = asyncio.run(run_until_complete(batch_size=args.batch_size))
    sys.exit(0 if success else 1)
