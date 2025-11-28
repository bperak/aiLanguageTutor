#!/usr/bin/env python
"""
Migration script to generate titles for all existing CanDoDescriptor nodes.

This script:
1. Fetches all CanDoDescriptors without titles
2. Generates titles (titleEn and titleJa) using AI
3. Updates nodes with generated titles
4. Processes in batches with progress tracking

Usage (PowerShell on Windows):
  # From project root
  cd backend
  poetry run python ../resources/generate_cando_titles.py --batch-size 50
"""

from __future__ import annotations

import asyncio
import argparse
import os
import sys
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from neo4j import AsyncGraphDatabase

# Add backend directory to Python path
PROJECT_ROOT = Path(__file__).parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app.services.cando_title_service import CanDoTitleService


def _normalize_uri(uri: str) -> str:
    """Normalize docker-style neo4j scheme to bolt for local dev."""
    if uri.startswith("neo4j://neo4j:"):
        return uri.replace("neo4j://neo4j:", "bolt://localhost:")
    if uri.startswith("neo4j://"):
        return uri.replace("neo4j://", "bolt://")
    return uri


async def main() -> None:
    """Main migration function."""
    parser = argparse.ArgumentParser(description="Generate titles for CanDoDescriptor nodes.")
    parser.add_argument("--batch-size", type=int, default=50, help="Number of nodes to process at once")
    parser.add_argument("--dry-run", action="store_true", help="Only report counts without generating titles")
    args = parser.parse_args()
    
    # Load environment (already set PROJECT_ROOT above)
    env_path = PROJECT_ROOT / ".env"
    load_dotenv(env_path)
    
    # Get Neo4j connection
    neo4j_uri = _normalize_uri(os.getenv("NEO4J_URI", "bolt://localhost:7687"))
    neo4j_user = os.getenv("NEO4J_USER", os.getenv("NEO4J_USERNAME", "neo4j"))
    neo4j_password = os.getenv("NEO4J_PASSWORD")
    
    if not neo4j_password:
        print("❌ NEO4J_PASSWORD is not set. Please define it in your .env file.")
        return
    
    title_service = CanDoTitleService()
    
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
            
            # Count CanDoDescriptors
            result = await session.run(
                """
                MATCH (c:CanDoDescriptor)
                WHERE (c.descriptionEn IS NOT NULL OR c.descriptionJa IS NOT NULL)
                RETURN count(c) AS total
                """
            )
            total_record = await result.single()
            total = total_record.get("total", 0) if total_record else 0
            
            # Count without titles
            result = await session.run(
                """
                MATCH (c:CanDoDescriptor)
                WHERE (c.descriptionEn IS NOT NULL OR c.descriptionJa IS NOT NULL)
                  AND (c.titleEn IS NULL OR c.titleJa IS NULL)
                RETURN count(c) AS without_title
                """
            )
            without_title_record = await result.single()
            without_title = without_title_record.get("without_title", 0) if without_title_record else 0
            
            print(f"\nCanDoDescriptor Statistics:")
            print(f"  Total: {total:,}")
            print(f"  Without titles: {without_title:,}")
            print(f"  With titles: {total - without_title:,}")
            
            if args.dry_run:
                print("\nDry run mode - no titles will be generated")
                return
            
            if without_title == 0:
                print("\nAll CanDoDescriptors already have titles")
                return
            
            # Generate titles in batches
            print(f"\nStarting title generation...")
            print(f"  Batch size: {args.batch_size}")
            
            stats = {
                "processed": 0,
                "generated": 0,
                "errors": 0
            }
            
            skip = 0
            while True:
                # Fetch batch
                result = await session.run(
                    """
                    MATCH (c:CanDoDescriptor)
                    WHERE (c.descriptionEn IS NOT NULL OR c.descriptionJa IS NOT NULL)
                      AND (c.titleEn IS NULL OR c.titleJa IS NULL)
                    RETURN c.uid AS uid,
                           c.descriptionEn AS descriptionEn,
                           c.descriptionJa AS descriptionJa
                    ORDER BY c.uid
                    SKIP $skip
                    LIMIT $limit
                    """,
                    {"skip": skip, "limit": args.batch_size}
                )
                
                batch = []
                async for record in result:
                    batch.append({
                        "uid": record.get("uid"),
                        "descriptionEn": record.get("descriptionEn"),
                        "descriptionJa": record.get("descriptionJa")
                    })
                
                if not batch:
                    break
                
                # Process batch
                for item in batch:
                    try:
                        # Generate titles
                        titles = await title_service.generate_titles(
                            description_en=item["descriptionEn"],
                            description_ja=item["descriptionJa"]
                        )
                        
                        # Update node
                        await session.run(
                            """
                            MATCH (c:CanDoDescriptor {uid: $uid})
                            SET c.titleEn = $titleEn,
                                c.titleJa = $titleJa
                            RETURN c.uid AS uid
                            """,
                            {
                                "uid": item["uid"],
                                "titleEn": titles["titleEn"],
                                "titleJa": titles["titleJa"]
                            }
                        )
                        
                        stats["generated"] += 1
                        print(f"  Generated titles for {item['uid']}")
                        
                    except Exception as e:
                        stats["errors"] += 1
                        print(f"  ❌ Error processing {item.get('uid', 'unknown')}: {e}")
                
                stats["processed"] += len(batch)
                skip += len(batch)
                
                print(f"  Progress: {stats['processed']}/{without_title} processed, "
                      f"{stats['generated']} generated, {stats['errors']} errors")
            
            print(f"\nTitle Generation Completed:")
            print(f"  Processed: {stats['processed']:,}")
            print(f"  Generated: {stats['generated']:,}")
            print(f"  Errors: {stats['errors']:,}")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        await driver.close()


if __name__ == "__main__":
    asyncio.run(main())

