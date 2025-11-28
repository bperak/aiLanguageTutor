#!/usr/bin/env python
"""
Migration script to generate embeddings for all existing CanDoDescriptor nodes.

This script:
1. Fetches all CanDoDescriptor nodes from Neo4j
2. Generates embeddings for their descriptions (descriptionEn + descriptionJa)
3. Stores embeddings in the descriptionEmbedding property
4. Processes in batches with progress tracking and error handling

Usage (PowerShell on Windows):
  # Ensure venv and environment
  python -m venv .venv ; .\.venv\Scripts\Activate.ps1
  pip install neo4j python-dotenv openai google-genai
  
  # Configure API keys in .env (OPENAI_API_KEY or GEMINI_API_KEY)
  python resources/generate_cando_embeddings.py --batch-size 50 --provider openai

Options:
  --batch-size: Number of nodes to process at once (default: 50)
  --provider: AI provider for embeddings (openai or gemini, default: openai)
  --skip-existing: Skip nodes that already have embeddings (default: True)
  --dry-run: Only report counts without generating embeddings
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
from app.core.config import settings


def _normalize_uri(uri: str) -> str:
    """Normalize docker-style neo4j scheme to bolt for local dev."""
    if uri.startswith("neo4j://neo4j:"):
        return uri.replace("neo4j://neo4j:", "bolt://localhost:")
    if uri.startswith("neo4j://"):
        return uri.replace("neo4j://", "bolt://")
    return uri


async def main() -> None:
    """Main migration function."""
    parser = argparse.ArgumentParser(
        description="Generate embeddings for CanDoDescriptor nodes"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=50,
        help="Number of nodes to process at once (default: 50)"
    )
    parser.add_argument(
        "--provider",
        type=str,
        default="openai",
        choices=["openai", "gemini"],
        help="AI provider for embeddings (default: openai)"
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        default=True,
        help="Skip nodes that already have embeddings (default: True)"
    )
    parser.add_argument(
        "--no-skip-existing",
        dest="skip_existing",
        action="store_false",
        help="Regenerate embeddings for all nodes"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only report counts without generating embeddings"
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
            
            if args.skip_existing:
                result = await session.run(
                    """
                    MATCH (c:CanDoDescriptor)
                    WHERE (c.descriptionEn IS NOT NULL OR c.descriptionJa IS NOT NULL)
                      AND c.descriptionEmbedding IS NOT NULL
                    RETURN count(c) AS with_embedding
                    """
                )
                with_embedding_record = await result.single()
                with_embedding = with_embedding_record.get("with_embedding", 0) if with_embedding_record else 0
                to_process = total - with_embedding
                
                print(f"\nCanDoDescriptor Statistics:")
                print(f"  Total: {total:,}")
                print(f"  With embeddings: {with_embedding:,}")
                print(f"  To process: {to_process:,}")
            else:
                print(f"\nCanDoDescriptor Statistics:")
                print(f"  Total: {total:,}")
                print(f"  To process: {total:,} (regenerating all)")
            
            if args.dry_run:
                print("\nDry run mode - no embeddings will be generated")
                return
            
            if total == 0:
                print("\nNo CanDoDescriptors found to process")
                return
            
            # Generate embeddings
            print(f"\nStarting embedding generation...")
            print(f"  Batch size: {args.batch_size}")
            print(f"  Provider: {args.provider}")
            print(f"  Skip existing: {args.skip_existing}")
            
            stats = await service.batch_generate_cando_embeddings(
                session,
                batch_size=args.batch_size,
                provider=args.provider,
                skip_existing=args.skip_existing
            )
            
            print(f"\nEmbedding Generation Completed:")
            print(f"  Processed: {stats['processed']:,}")
            print(f"  Generated: {stats['generated']:,}")
            print(f"  Skipped: {stats['skipped']:,}")
            print(f"  Errors: {stats['errors']:,}")
            
    except Exception as e:
        print(f"\nError: {e}")
        raise
    finally:
        await driver.close()


if __name__ == "__main__":
    asyncio.run(main())

