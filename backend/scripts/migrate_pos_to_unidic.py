"""
Migration Script: Backfill Canonical POS from Existing Data

Migrates existing Word nodes to use canonical UniDic POS format.
Priority: UniDic > Matsushita > Lee > AI

Usage:
    python backend/scripts/migrate_pos_to_unidic.py [--batch-size N] [--dry-run]
"""

import asyncio
import argparse
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from neo4j import AsyncGraphDatabase
from dotenv import load_dotenv
import os
import structlog

from app.services.lexical_network.pos_mapper import (
    map_lee_pos_to_unidic,
    map_matsushita_pos_to_unidic,
    parse_unidic_pos,
    get_pos_priority,
    should_update_canonical_pos,
)

logger = structlog.get_logger()

load_dotenv()


async def migrate_pos_batch(
    session,
    batch_size: int = 1000,
    dry_run: bool = False,
) -> dict:
    """
    Migrate POS for a batch of words.
    
    Args:
        session: Neo4j async session
        batch_size: Number of words to process per batch
        dry_run: If True, don't write changes
        
    Returns:
        Statistics dictionary
    """
    stats = {
        "processed": 0,
        "updated": 0,
        "skipped": 0,
        "errors": 0,
        "by_source": {"unidic": 0, "matsushita": 0, "lee": 0, "ai": 0},
    }
    
    # Find words that need POS migration
    # More comprehensive: find all words where pos1 IS NULL and they have some POS data
    query = """
    MATCH (w:Word)
    WHERE w.standard_orthography IS NOT NULL
    AND w.pos1 IS NULL
    AND (w.unidic_pos1 IS NOT NULL 
         OR w.pos_primary IS NOT NULL 
         OR w.sources IS NOT NULL)
    RETURN w.standard_orthography AS word,
           w.pos_primary AS pos_primary,
           w.pos_detailed AS pos_detailed,
           w.unidic_pos1 AS unidic_pos1,
           w.unidic_pos2 AS unidic_pos2,
           w.unidic_pos3 AS unidic_pos3,
           w.unidic_pos4 AS unidic_pos4,
           w.pos_source AS pos_source,
           w.sources AS sources
    LIMIT $batch_size
    """
    
    result = await session.run(query, batch_size=batch_size)
    records = await result.data()
    
    if not records:
        return stats
    
    logger.info("Processing batch", count=len(records), dry_run=dry_run)
    
    for record in records:
        try:
            word = record["word"]
            pos_primary = record.get("pos_primary")
            pos_detailed = record.get("pos_detailed")
            unidic_pos1 = record.get("unidic_pos1")
            unidic_pos2 = record.get("unidic_pos2")
            unidic_pos3 = record.get("unidic_pos3")
            unidic_pos4 = record.get("unidic_pos4")
            existing_pos_source = record.get("pos_source")
            sources = record.get("sources") or []
            
            stats["processed"] += 1
            
            # Determine best POS source (priority: unidic > matsushita > lee > ai)
            canonical_pos = None
            new_pos_source = None
            confidence = 1.0
            
            # Priority 1: UniDic (if unidic_pos1 exists)
            if unidic_pos1:
                canonical_pos = {
                    "pos1": unidic_pos1,
                    "pos2": unidic_pos2,
                    "pos3": unidic_pos3,
                    "pos4": unidic_pos4,
                    "pos_primary_norm": unidic_pos1,
                }
                new_pos_source = "unidic"
                stats["by_source"]["unidic"] += 1
            
            # Priority 2: Matsushita (if sources contains matsushita and pos_primary is UniDic-style)
            elif "matsushita" in sources and pos_primary and "-" in pos_primary:
                canonical_pos = map_matsushita_pos_to_unidic(pos_primary)
                new_pos_source = "matsushita"
                stats["by_source"]["matsushita"] += 1
            
            # Priority 3: Lee (if sources contains lee)
            elif "lee" in sources and pos_primary:
                canonical_pos = map_lee_pos_to_unidic(pos_primary, pos_detailed)
                new_pos_source = "lee"
                stats["by_source"]["lee"] += 1
            
            # Priority 4: AI (if pos_source is ai and we have pos_primary)
            elif existing_pos_source == "ai" and pos_primary:
                if "-" in pos_primary:
                    canonical_pos = parse_unidic_pos(pos_primary)
                else:
                    canonical_pos = {
                        "pos1": pos_primary,
                        "pos2": None,
                        "pos3": None,
                        "pos4": None,
                        "pos_primary_norm": pos_primary,
                    }
                new_pos_source = "ai"
                confidence = 0.8  # AI has lower confidence
                stats["by_source"]["ai"] += 1
            
            # Skip if no canonical POS could be determined
            if not canonical_pos or not new_pos_source:
                stats["skipped"] += 1
                continue
            
            # Check if we should update (new source has higher priority)
            if not should_update_canonical_pos(existing_pos_source, new_pos_source):
                stats["skipped"] += 1
                continue
            
            # Update word with canonical POS
            if not dry_run:
                update_query = """
                MATCH (w:Word {standard_orthography: $word})
                SET w.pos1 = $pos1,
                    w.pos2 = $pos2,
                    w.pos3 = $pos3,
                    w.pos4 = $pos4,
                    w.pos_primary_norm = $pos_primary_norm,
                    w.pos_source = $pos_source,
                    w.pos_confidence = $pos_confidence,
                    w.updated_at = datetime()
                """
                await session.run(
                    update_query,
                    word=word,
                    pos1=canonical_pos.get("pos1"),
                    pos2=canonical_pos.get("pos2"),
                    pos3=canonical_pos.get("pos3"),
                    pos4=canonical_pos.get("pos4"),
                    pos_primary_norm=canonical_pos.get("pos_primary_norm"),
                    pos_source=new_pos_source,
                    pos_confidence=confidence,
                )
            
            stats["updated"] += 1
            
        except Exception as e:
            logger.error("Migration error", word=record.get("word"), error=str(e))
            stats["errors"] += 1
    
    return stats


async def main():
    """Main migration function."""
    parser = argparse.ArgumentParser(description="Migrate POS to UniDic canonical format")
    parser.add_argument("--batch-size", type=int, default=1000, help="Batch size for processing")
    parser.add_argument("--dry-run", action="store_true", help="Don't write changes")
    parser.add_argument("--max-batches", type=int, default=None, help="Maximum number of batches")
    
    args = parser.parse_args()
    
    # Get Neo4j connection
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "password")
    
    driver = AsyncGraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
    
    try:
        async with driver.session() as session:
            total_stats = {
                "processed": 0,
                "updated": 0,
                "skipped": 0,
                "errors": 0,
                "by_source": {"unidic": 0, "matsushita": 0, "lee": 0, "ai": 0},
            }
            
            batch_num = 0
            while True:
                if args.max_batches and batch_num >= args.max_batches:
                    break
                
                batch_stats = await migrate_pos_batch(
                    session, batch_size=args.batch_size, dry_run=args.dry_run
                )
                
                # Merge stats
                for key in ["processed", "updated", "skipped", "errors"]:
                    total_stats[key] += batch_stats[key]
                for source in total_stats["by_source"]:
                    total_stats["by_source"][source] += batch_stats["by_source"][source]
                
                batch_num += 1
                logger.info(
                    f"Batch {batch_num} complete",
                    batch_stats=batch_stats,
                    total_stats=total_stats,
                )
                
                # Stop if no more words to process
                if batch_stats["processed"] == 0:
                    break
            
            logger.info("Migration complete", total_stats=total_stats, dry_run=args.dry_run)
            
            if args.dry_run:
                print("\n=== DRY RUN - No changes were made ===")
            print(f"\nTotal processed: {total_stats['processed']}")
            print(f"Total updated: {total_stats['updated']}")
            print(f"Total skipped: {total_stats['skipped']}")
            print(f"Total errors: {total_stats['errors']}")
            print(f"\nBy source:")
            for source, count in total_stats["by_source"].items():
                print(f"  {source}: {count}")
    
    finally:
        await driver.close()


if __name__ == "__main__":
    asyncio.run(main())
