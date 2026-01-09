"""
Comprehensive POS Resolution Script

Runs migration + enrichment in sequence to resolve all missing canonical POS.
Strategy:
1. First, migrate existing POS data (UniDic, Lee, Matsushita, AI) to canonical format
2. Then, run UniDic enrichment for words still missing POS

Usage:
    python backend/scripts/resolve_all_pos.py [--migration-batch-size N] [--enrichment-limit N] [--dry-run]
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

from app.services.lexical_network.unidic_enrichment_service import UnidicEnrichmentService
from app.services.lexical_network.pos_mapper import (
    map_lee_pos_to_unidic,
    map_matsushita_pos_to_unidic,
    parse_unidic_pos,
    should_update_canonical_pos,
)

logger = structlog.get_logger()

load_dotenv()


async def get_pos_coverage(session):
    """Get current POS coverage statistics."""
    query = """
    MATCH (w:Word)
    RETURN 
        count(*) AS total_words,
        sum(CASE WHEN w.pos1 IS NOT NULL THEN 1 ELSE 0 END) AS has_canonical_pos,
        sum(CASE WHEN w.pos1 IS NULL THEN 1 ELSE 0 END) AS missing_canonical_pos,
        sum(CASE WHEN w.unidic_pos1 IS NOT NULL AND w.pos1 IS NULL THEN 1 ELSE 0 END) AS has_unidic_but_no_canonical,
        sum(CASE WHEN w.pos_primary IS NOT NULL AND w.pos1 IS NULL THEN 1 ELSE 0 END) AS has_old_pos_but_no_canonical,
        sum(CASE WHEN w.unidic_lemma IS NULL AND w.pos1 IS NULL THEN 1 ELSE 0 END) AS can_enrich_with_unidic
    """
    result = await session.run(query)
    return await result.single()


async def run_migration(session, batch_size: int = 1000, dry_run: bool = False):
    """Run POS migration from existing data."""
    from app.services.lexical_network.pos_mapper import (
        map_lee_pos_to_unidic,
        map_matsushita_pos_to_unidic,
        parse_unidic_pos,
    )
    
    stats = {
        "processed": 0,
        "updated": 0,
        "skipped": 0,
        "errors": 0,
        "by_source": {"unidic": 0, "matsushita": 0, "lee": 0, "ai": 0},
    }
    
    # Find words that need POS migration
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
    
    batch_num = 0
    while True:
        result = await session.run(query, batch_size=batch_size)
        records = await result.data()
        
        if not records:
            break
        
        batch_num += 1
        logger.info("Migration batch", batch_num=batch_num, count=len(records), dry_run=dry_run)
        
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
                    confidence = 0.8
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
        
        # Progress logging
        if batch_num % 10 == 0:
            logger.info("Migration progress", stats=stats)
    
    return stats


async def run_enrichment(session, limit: int = 1000, dry_run: bool = False):
    """Run UniDic enrichment for words missing POS."""
    service = UnidicEnrichmentService()
    
    if not service.is_available:
        logger.error("UniDic not available")
        return {"enriched": 0, "skipped": 0, "errors": 0, "reason": "unidic_not_available"}
    
    if dry_run:
        # Just count how many words could be enriched
        query = """
        MATCH (w:Word)
        WHERE w.unidic_lemma IS NULL AND w.pos1 IS NULL
        RETURN count(*) AS count
        """
        result = await session.run(query)
        record = await result.single()
        return {"enriched": 0, "skipped": 0, "errors": 0, "could_enrich": record["count"]}
    
    return await service.batch_enrich(session, limit=limit)


async def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Resolve all missing canonical POS")
    parser.add_argument("--migration-batch-size", type=int, default=1000, help="Migration batch size")
    parser.add_argument("--enrichment-limit", type=int, default=5000, help="UniDic enrichment limit per run")
    parser.add_argument("--dry-run", action="store_true", help="Don't write changes")
    parser.add_argument("--skip-migration", action="store_true", help="Skip migration step")
    parser.add_argument("--skip-enrichment", action="store_true", help="Skip enrichment step")
    
    args = parser.parse_args()
    
    # Get Neo4j connection
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "password")
    
    driver = AsyncGraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
    
    try:
        async with driver.session() as session:
            # Initial status
            print("\n" + "=" * 60)
            print("POS RESOLUTION - INITIAL STATUS")
            print("=" * 60)
            initial = await get_pos_coverage(session)
            print(f"Total words: {initial['total_words']:,}")
            print(f"Words with canonical POS: {initial['has_canonical_pos']:,} ({initial['has_canonical_pos']/initial['total_words']*100:.1f}%)")
            print(f"Words missing canonical POS: {initial['missing_canonical_pos']:,} ({initial['missing_canonical_pos']/initial['total_words']*100:.1f}%)")
            print(f"  - Has UniDic data but no canonical: {initial['has_unidic_but_no_canonical']:,}")
            print(f"  - Has old pos_primary but no canonical: {initial['has_old_pos_but_no_canonical']:,}")
            print(f"  - Can enrich with UniDic: {initial['can_enrich_with_unidic']:,}")
            print()
            
            # Step 1: Migration
            if not args.skip_migration:
                print("=" * 60)
                print("STEP 1: MIGRATING EXISTING POS DATA")
                print("=" * 60)
                migration_stats = await run_migration(
                    session, 
                    batch_size=args.migration_batch_size,
                    dry_run=args.dry_run
                )
                print(f"\nMigration complete:")
                print(f"  Processed: {migration_stats['processed']:,}")
                print(f"  Updated: {migration_stats['updated']:,}")
                print(f"  Skipped: {migration_stats['skipped']:,}")
                print(f"  Errors: {migration_stats['errors']:,}")
                print(f"\nBy source:")
                for source, count in migration_stats["by_source"].items():
                    if count > 0:
                        print(f"    {source}: {count:,}")
                print()
            else:
                print("Skipping migration step\n")
            
            # Status after migration
            after_migration = await get_pos_coverage(session)
            print("=" * 60)
            print("STATUS AFTER MIGRATION")
            print("=" * 60)
            print(f"Words with canonical POS: {after_migration['has_canonical_pos']:,} ({after_migration['has_canonical_pos']/after_migration['total_words']*100:.1f}%)")
            print(f"Words missing canonical POS: {after_migration['missing_canonical_pos']:,} ({after_migration['missing_canonical_pos']/after_migration['total_words']*100:.1f}%)")
            print()
            
            # Step 2: Enrichment
            if not args.skip_enrichment:
                print("=" * 60)
                print("STEP 2: UNIDIC ENRICHMENT")
                print("=" * 60)
                enrichment_stats = await run_enrichment(
                    session,
                    limit=args.enrichment_limit,
                    dry_run=args.dry_run
                )
                print(f"\nEnrichment complete:")
                for key, value in enrichment_stats.items():
                    if isinstance(value, int):
                        print(f"  {key}: {value:,}")
                    else:
                        print(f"  {key}: {value}")
                print()
            else:
                print("Skipping enrichment step\n")
            
            # Final status
            final = await get_pos_coverage(session)
            print("=" * 60)
            print("FINAL STATUS")
            print("=" * 60)
            print(f"Total words: {final['total_words']:,}")
            print(f"Words with canonical POS: {final['has_canonical_pos']:,} ({final['has_canonical_pos']/final['total_words']*100:.1f}%)")
            print(f"Words missing canonical POS: {final['missing_canonical_pos']:,} ({final['missing_canonical_pos']/final['total_words']*100:.1f}%)")
            print()
            print(f"Improvement: +{final['has_canonical_pos'] - initial['has_canonical_pos']:,} words ({((final['has_canonical_pos'] - initial['has_canonical_pos']) / initial['total_words'] * 100):.1f}%)")
            print("=" * 60)
    
    finally:
        await driver.close()


if __name__ == "__main__":
    asyncio.run(main())
