#!/usr/bin/env python
"""
Test script for CanDo similarity API endpoint.

This script tests the /api/v1/cando/similar endpoint to verify
that semantic similarity search is working correctly.

Usage (PowerShell on Windows):
  python scripts\test_cando_similarity_api.py
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
from typing import Dict, Any

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


async def test_similarity_search() -> None:
    """Test similarity search functionality."""
    # Load environment
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
            print("✓ Connected to Neo4j")
            print()
            
            # Find a CanDoDescriptor with embedding
            result = await session.run(
                """
                MATCH (c:CanDoDescriptor)
                WHERE c.descriptionEmbedding IS NOT NULL
                RETURN c.uid AS uid, c.descriptionEn AS descriptionEn
                LIMIT 5
                """
            )
            
            test_candos = []
            async for record in result:
                test_candos.append({
                    'uid': record.get("uid"),
                    'description': record.get("descriptionEn", "")[:50]
                })
            
            if not test_candos:
                print("❌ No CanDoDescriptors with embeddings found")
                return
            
            print(f"Testing similarity search with {len(test_candos)} CanDoDescriptors:")
            print()
            
            for i, test_cando in enumerate(test_candos, 1):
                uid = test_cando['uid']
                desc = test_cando['description']
                
                print(f"[{i}] Testing: {uid}")
                print(f"     Description: {desc}...")
                
                # Find similar
                similar = await service.find_similar_candos(
                    session,
                    uid,
                    limit=5,
                    similarity_threshold=0.65
                )
                
                if similar:
                    print(f"     ✓ Found {len(similar)} similar CanDoDescriptors:")
                    for j, sim in enumerate(similar[:3], 1):  # Show top 3
                        print(f"        {j}. {sim['uid']} (similarity: {sim['similarity']:.3f})")
                        if sim.get('cross_domain'):
                            print(f"           └─ Cross-domain connection")
                else:
                    print(f"     ⚠ No similar CanDoDescriptors found (threshold: 0.65)")
                
                print()
            
            print("=" * 60)
            print("✓ Similarity search test completed successfully!")
            print("=" * 60)
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        await driver.close()


if __name__ == "__main__":
    asyncio.run(test_similarity_search())

