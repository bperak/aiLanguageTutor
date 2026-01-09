"""
Check POS Resolution Progress

Quick script to check current POS coverage status.
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

load_dotenv()


async def check_progress():
    """Check current POS coverage progress."""
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "password")
    
    driver = AsyncGraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
    
    try:
        async with driver.session() as session:
            query = """
            MATCH (w:Word)
            RETURN 
                count(*) AS total_words,
                sum(CASE WHEN w.pos1 IS NOT NULL THEN 1 ELSE 0 END) AS has_canonical_pos,
                sum(CASE WHEN w.pos1 IS NULL THEN 1 ELSE 0 END) AS missing_canonical_pos,
                sum(CASE WHEN w.pos_source = 'unidic' THEN 1 ELSE 0 END) AS from_unidic,
                sum(CASE WHEN w.pos_source = 'lee' THEN 1 ELSE 0 END) AS from_lee,
                sum(CASE WHEN w.pos_source = 'matsushita' THEN 1 ELSE 0 END) AS from_matsushita,
                sum(CASE WHEN w.pos_source = 'ai' THEN 1 ELSE 0 END) AS from_ai,
                sum(CASE WHEN w.unidic_lemma IS NOT NULL THEN 1 ELSE 0 END) AS has_unidic_data,
                sum(CASE WHEN w.unidic_lemma IS NULL AND w.pos1 IS NULL THEN 1 ELSE 0 END) AS can_still_enrich
            """
            result = await session.run(query)
            stats = await result.single()
            
            total = stats["total_words"]
            has_pos = stats["has_canonical_pos"]
            missing = stats["missing_canonical_pos"]
            
            print("\n" + "=" * 70)
            print("POS RESOLUTION PROGRESS")
            print("=" * 70)
            print(f"\nTotal words: {total:,}")
            print(f"Words with canonical POS: {has_pos:,} ({has_pos/total*100:.1f}%)")
            print(f"Words missing canonical POS: {missing:,} ({missing/total*100:.1f}%)")
            print()
            print("POS Source Breakdown:")
            print(f"  - From UniDic: {stats['from_unidic']:,}")
            print(f"  - From Lee: {stats['from_lee']:,}")
            print(f"  - From Matsushita: {stats['from_matsushita']:,}")
            print(f"  - From AI: {stats['from_ai']:,}")
            print()
            print("Enrichment Status:")
            print(f"  - Words with UniDic data: {stats['has_unidic_data']:,}")
            print(f"  - Words that can still be enriched: {stats['can_still_enrich']:,}")
            print()
            
            # Show recent enrichment activity
            recent_query = """
            MATCH (w:Word)
            WHERE w.last_enriched_at IS NOT NULL
            RETURN count(*) AS recently_enriched,
                   max(w.last_enriched_at) AS last_enrichment_time
            """
            recent_result = await session.run(recent_query)
            recent = await recent_result.single()
            
            if recent["recently_enriched"]:
                print("Recent Activity:")
                print(f"  - Words enriched: {recent['recently_enriched']:,}")
                if recent["last_enrichment_time"]:
                    print(f"  - Last enrichment: {recent['last_enrichment_time']}")
            print("=" * 70)
            print()
    
    finally:
        await driver.close()


if __name__ == "__main__":
    asyncio.run(check_progress())
