#!/usr/bin/env python
"""
Validation script for CanDo embeddings implementation.

This script verifies that:
1. Vector index exists and is populated
2. Embeddings are generated for CanDoDescriptors
3. Similarity relationships are created
4. API endpoint is accessible

Usage (PowerShell on Windows):
  python scripts\validate_cando_embeddings.py
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
from typing import Dict, Any

from dotenv import load_dotenv
from neo4j import AsyncGraphDatabase


def _normalize_uri(uri: str) -> str:
    """Normalize docker-style neo4j scheme to bolt for local dev."""
    if uri.startswith("neo4j://neo4j:"):
        return uri.replace("neo4j://neo4j:", "bolt://localhost:")
    if uri.startswith("neo4j://"):
        return uri.replace("neo4j://", "bolt://")
    return uri


async def check_vector_index(session) -> Dict[str, Any]:
    """Check if vector index exists and is populated."""
    result = {
        "exists": False,
        "state": None,
        "population": None,
        "error": None
    }
    
    try:
        query_result = await session.run(
            """
            SHOW INDEXES YIELD name, type, state, populationPercent
            WHERE name = 'cando_descriptor_embeddings'
            RETURN name, type, state, populationPercent
            """
        )
        
        record = await query_result.single()
        if record:
            result["exists"] = True
            result["state"] = record.get("state")
            result["population"] = record.get("populationPercent", 0)
        else:
            result["error"] = "Index not found"
    except Exception as e:
        result["error"] = str(e)
    
    return result


async def check_embeddings(session) -> Dict[str, Any]:
    """Check embedding generation status."""
    result = {
        "total_candos": 0,
        "with_embeddings": 0,
        "without_embeddings": 0,
        "percentage": 0.0
    }
    
    try:
        # Total CanDoDescriptors
        total_result = await session.run(
            """
            MATCH (c:CanDoDescriptor)
            WHERE c.descriptionEn IS NOT NULL OR c.descriptionJa IS NOT NULL
            RETURN count(c) AS total
            """
        )
        total_record = await total_result.single()
        result["total_candos"] = total_record.get("total", 0) if total_record else 0
        
        # With embeddings
        with_emb_result = await session.run(
            """
            MATCH (c:CanDoDescriptor)
            WHERE c.descriptionEmbedding IS NOT NULL
            RETURN count(c) AS with_emb
            """
        )
        with_emb_record = await with_emb_result.single()
        result["with_embeddings"] = with_emb_record.get("with_emb", 0) if with_emb_record else 0
        
        result["without_embeddings"] = result["total_candos"] - result["with_embeddings"]
        
        if result["total_candos"] > 0:
            result["percentage"] = (result["with_embeddings"] / result["total_candos"]) * 100.0
    except Exception as e:
        result["error"] = str(e)
    
    return result


async def check_relationships(session) -> Dict[str, Any]:
    """Check similarity relationships status."""
    result = {
        "total_relationships": 0,
        "avg_similarity": 0.0,
        "min_similarity": 0.0,
        "max_similarity": 0.0,
        "cross_domain_count": 0
    }
    
    try:
        rel_result = await session.run(
            """
            MATCH ()-[r:SEMANTICALLY_SIMILAR]->()
            RETURN count(r) AS total,
                   avg(r.similarity_score) AS avg_sim,
                   min(r.similarity_score) AS min_sim,
                   max(r.similarity_score) AS max_sim
            """
        )
        rel_record = await rel_result.single()
        if rel_record:
            result["total_relationships"] = rel_record.get("total", 0)
            result["avg_similarity"] = rel_record.get("avg_sim", 0.0) or 0.0
            result["min_similarity"] = rel_record.get("min_sim", 0.0) or 0.0
            result["max_similarity"] = rel_record.get("max_sim", 0.0) or 0.0
        
        # Cross-domain relationships
        cross_result = await session.run(
            """
            MATCH ()-[r:SEMANTICALLY_SIMILAR]->()
            WHERE r.cross_domain = true
            RETURN count(r) AS cross_count
            """
        )
        cross_record = await cross_result.single()
        if cross_record:
            result["cross_domain_count"] = cross_record.get("cross_count", 0)
    except Exception as e:
        result["error"] = str(e)
    
    return result


async def test_similarity_search(session) -> Dict[str, Any]:
    """Test similarity search functionality."""
    result = {
        "success": False,
        "found_similar": 0,
        "error": None
    }
    
    try:
        # Find a CanDoDescriptor with embedding
        test_result = await session.run(
            """
            MATCH (c:CanDoDescriptor)
            WHERE c.descriptionEmbedding IS NOT NULL
            RETURN c.uid AS uid
            LIMIT 1
            """
        )
        test_record = await test_result.single()
        
        if not test_record:
            result["error"] = "No CanDoDescriptors with embeddings found"
            return result
        
        test_uid = test_record.get("uid")
        
        # Try to find similar (using relationships as proxy)
        similar_result = await session.run(
            """
            MATCH (source:CanDoDescriptor {uid: $uid})-[r:SEMANTICALLY_SIMILAR]->(target:CanDoDescriptor)
            RETURN count(target) AS similar_count
            """,
            {"uid": test_uid}
        )
        similar_record = await similar_result.single()
        if similar_record:
            result["found_similar"] = similar_record.get("similar_count", 0)
            result["success"] = True
    except Exception as e:
        result["error"] = str(e)
    
    return result


async def main() -> None:
    """Main validation function."""
    # Load environment
    project_root = Path(__file__).parent.parent
    env_path = project_root / ".env"
    load_dotenv(env_path)
    
    # Get Neo4j connection
    neo4j_uri = _normalize_uri(os.getenv("NEO4J_URI", "bolt://localhost:7687"))
    neo4j_user = os.getenv("NEO4J_USER", os.getenv("NEO4J_USERNAME", "neo4j"))
    neo4j_password = os.getenv("NEO4J_PASSWORD")
    
    if not neo4j_password:
        print("❌ NEO4J_PASSWORD is not set. Please define it in your .env file.")
        sys.exit(1)
    
    # Connect to Neo4j
    driver = AsyncGraphDatabase.driver(
        neo4j_uri,
        auth=(neo4j_user, neo4j_password)
    )
    
    print("=" * 60)
    print("CanDo Embeddings Validation")
    print("=" * 60)
    print()
    
    try:
        async with driver.session() as session:
            # Check connectivity
            await driver.verify_connectivity()
            print(f"✓ Connected to Neo4j at {neo4j_uri}")
            print()
            
            # 1. Check Vector Index
            print("1. Checking Vector Index...")
            index_status = await check_vector_index(session)
            if index_status["exists"]:
                print(f"   ✓ Index exists")
                print(f"   State: {index_status['state']}")
                print(f"   Population: {index_status.get('population', 0)}%")
            else:
                print(f"   ❌ Index not found: {index_status.get('error', 'Unknown error')}")
                print(f"   → Run: python scripts\\apply_cando_vector_index.py")
            print()
            
            # 2. Check Embeddings
            print("2. Checking Embeddings...")
            emb_status = await check_embeddings(session)
            print(f"   Total CanDoDescriptors: {emb_status['total_candos']:,}")
            print(f"   With embeddings: {emb_status['with_embeddings']:,}")
            print(f"   Without embeddings: {emb_status['without_embeddings']:,}")
            print(f"   Coverage: {emb_status['percentage']:.1f}%")
            
            if emb_status['percentage'] < 100:
                print(f"   ⚠ Some CanDoDescriptors are missing embeddings")
                print(f"   → Run: python resources\\generate_cando_embeddings.py")
            else:
                print(f"   ✓ All CanDoDescriptors have embeddings")
            print()
            
            # 3. Check Relationships
            print("3. Checking Similarity Relationships...")
            rel_status = await check_relationships(session)
            print(f"   Total relationships: {rel_status['total_relationships']:,}")
            
            if rel_status['total_relationships'] > 0:
                print(f"   ✓ Relationships exist")
                print(f"   Average similarity: {rel_status['avg_similarity']:.3f}")
                print(f"   Min similarity: {rel_status['min_similarity']:.3f}")
                print(f"   Max similarity: {rel_status['max_similarity']:.3f}")
                print(f"   Cross-domain: {rel_status['cross_domain_count']:,}")
            else:
                print(f"   ❌ No relationships found")
                print(f"   → Run: python resources\\create_cando_similarity_relationships.py")
            print()
            
            # 4. Test Similarity Search
            print("4. Testing Similarity Search...")
            test_status = await test_similarity_search(session)
            if test_status["success"]:
                print(f"   ✓ Similarity search working")
                print(f"   Found {test_status['found_similar']} similar CanDoDescriptors")
            else:
                print(f"   ⚠ {test_status.get('error', 'Unknown error')}")
            print()
            
            # Summary
            print("=" * 60)
            print("Summary")
            print("=" * 60)
            
            all_ok = (
                index_status["exists"] and
                emb_status["percentage"] == 100.0 and
                rel_status["total_relationships"] > 0 and
                test_status["success"]
            )
            
            if all_ok:
                print("✅ All checks passed! CanDo embeddings are fully configured.")
            else:
                print("⚠ Some checks failed. Please review the output above.")
                print()
                print("Next steps:")
                if not index_status["exists"]:
                    print("  1. Create vector index: python scripts\\apply_cando_vector_index.py")
                if emb_status["percentage"] < 100:
                    print("  2. Generate embeddings: python resources\\generate_cando_embeddings.py")
                if rel_status["total_relationships"] == 0:
                    print("  3. Create relationships: python resources\\create_cando_similarity_relationships.py")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
    finally:
        await driver.close()


if __name__ == "__main__":
    asyncio.run(main())

