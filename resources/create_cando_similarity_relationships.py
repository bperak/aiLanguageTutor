#!/usr/bin/env python
"""
Script to compute similarity scores and create SEMANTICALLY_SIMILAR relationships.

This script:
1. Finds all CanDoDescriptor pairs with embeddings
2. Computes semantic similarity scores using vector embeddings
3. Creates SEMANTICALLY_SIMILAR relationships with rich metadata:
   - similarity_score: cosine similarity value
   - source_level, target_level: CEFR levels
   - source_topic, target_topic: primary topics
   - source_skillDomain, target_skillDomain: skill domains
   - cross_domain: boolean flag indicating if domains differ
   - created_at: timestamp

Usage (PowerShell on Windows):
  # Ensure venv and environment
  python -m venv .venv ; .\.venv\Scripts\Activate.ps1
  pip install neo4j python-dotenv
  
  # Configure Neo4j connection via .env
  python resources\create_cando_similarity_relationships.py --threshold 0.65 --batch-size 100

Options:
  --threshold: Minimum similarity score to create relationships (default: 0.65)
  --batch-size: Number of relationships to create per batch (default: 100)
  --dry-run: Only report statistics without creating relationships
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

from app.services.cando_embedding_service import CanDoEmbeddingService


def _normalize_uri(uri: str) -> str:
    """Normalize docker-style neo4j scheme to bolt for local dev."""
    if uri.startswith("neo4j://neo4j:"):
        return uri.replace("neo4j://neo4j:", "bolt://localhost:")
    if uri.startswith("neo4j://"):
        return uri.replace("neo4j://", "bolt://")
    return uri


async def main() -> None:
    """Main function to create similarity relationships."""
    parser = argparse.ArgumentParser(
        description="Create SEMANTICALLY_SIMILAR relationships between CanDoDescriptors"
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.65,
        help="Minimum similarity score to create relationships (default: 0.65)"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Number of relationships to create per batch (default: 100)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only report statistics without creating relationships"
    )
    
    args = parser.parse_args()
    
    # Load environment (already set PROJECT_ROOT above)
    env_path = PROJECT_ROOT / ".env"
    load_dotenv(env_path)
    
    # Get Neo4j connection
    neo4j_uri = _normalize_uri(os.getenv("NEO4J_URI", "bolt://localhost:7687"))
    neo4j_user = os.getenv("NEO4J_USER", os.getenv("NEO4J_USERNAME", "neo4j"))
    neo4j_password = os.getenv("NEO4J_PASSWORD")
    
    if not neo4j_password:
        raise RuntimeError("NEO4J_PASSWORD is not set. Please define it in your .env file.")
    
    # Initialize service
    service = CanDoEmbeddingService()
    
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
            
            # Count CanDoDescriptors with embeddings
            result = await session.run(
                """
                MATCH (c:CanDoDescriptor)
                WHERE c.descriptionEmbedding IS NOT NULL
                RETURN count(c) AS total
                """
            )
            total_record = await result.single()
            total = total_record.get("total", 0) if total_record else 0
            
            # Count existing relationships
            result = await session.run(
                """
                MATCH ()-[r:SEMANTICALLY_SIMILAR]->()
                RETURN count(r) AS existing
                """
            )
            existing_record = await result.single()
            existing = existing_record.get("existing", 0) if existing_record else 0
            
            print(f"\nCanDoDescriptor Statistics:")
            print(f"  Total with embeddings: {total:,}")
            print(f"  Existing relationships: {existing:,}")
            print(f"  Similarity threshold: {args.threshold}")
            
            if total == 0:
                print("\nNo CanDoDescriptors with embeddings found.")
                print("Please run generate_cando_embeddings.py first.")
                return
            
            if args.dry_run:
                print("\nDry run mode - no relationships will be created")
                print(f"Estimated relationships to create: ~{total * (total - 1) // 2:,} (all pairs)")
                print("Note: Actual count will be filtered by similarity threshold")
                return
            
            # Create relationships
            print(f"\nStarting similarity relationship creation...")
            print(f"  Threshold: {args.threshold}")
            print(f"  Batch size: {args.batch_size}")
            print("  This may take a while for large datasets...")
            
            stats = await service.create_similarity_relationships(
                session,
                similarity_threshold=args.threshold,
                batch_size=args.batch_size
            )
            
            print(f"\nSimilarity Relationship Creation Completed:")
            print(f"  Created: {stats['created']:,}")
            print(f"  Updated: {stats['updated']:,}")
            print(f"  Errors: {stats['errors']:,}")
            
            # Verify final count
            result = await session.run(
                """
                MATCH ()-[r:SEMANTICALLY_SIMILAR]->()
                RETURN count(r) AS total
                """
            )
            final_record = await result.single()
            final = final_record.get("total", 0) if final_record else 0
            
            print(f"\nFinal relationship count: {final:,}")
            
    except Exception as e:
        print(f"\nError: {e}")
        raise
    finally:
        await driver.close()


if __name__ == "__main__":
    asyncio.run(main())

