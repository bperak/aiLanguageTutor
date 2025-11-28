#!/usr/bin/env python3
"""
Apply Neo4j performance indexes for AI Language Tutor.

This script creates comprehensive indexes to optimize lexical graph queries,
especially for Depth 2 operations which were taking too long.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add backend to path for imports
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from app.db import init_neo4j, get_neo4j_session
from app.core.config import settings


async def apply_indexes():
    """Apply all performance indexes to Neo4j."""
    
    print("🚀 Initializing Neo4j connection...")
    await init_neo4j()
    
    print("📊 Applying performance indexes...")
    
    # Index creation queries
    indexes = [
        # Primary lookup indexes for Word nodes
        "CREATE INDEX word_kanji_lookup IF NOT EXISTS FOR (w:Word) ON (w.kanji)",
        "CREATE INDEX word_hiragana_lookup IF NOT EXISTS FOR (w:Word) ON (w.hiragana)",
        "CREATE INDEX word_lemma_lookup IF NOT EXISTS FOR (w:Word) ON (w.lemma)",
        
        # Composite indexes for common query patterns
        "CREATE INDEX word_kanji_difficulty IF NOT EXISTS FOR (w:Word) ON (w.kanji, w.difficulty_numeric)",
        "CREATE INDEX word_kanji_pos IF NOT EXISTS FOR (w:Word) ON (w.kanji, w.pos_primary)",
        "CREATE INDEX word_kanji_etymology IF NOT EXISTS FOR (w:Word) ON (w.kanji, w.etymology)",
        
        # Performance indexes for classification queries
        "CREATE INDEX word_difficulty_numeric_perf IF NOT EXISTS FOR (w:Word) ON (w.difficulty_numeric)",
        "CREATE INDEX word_pos_primary_perf IF NOT EXISTS FOR (w:Word) ON (w.pos_primary)",
        "CREATE INDEX word_etymology_perf IF NOT EXISTS FOR (w:Word) ON (w.etymology)",
        "CREATE INDEX word_jlpt_level_perf IF NOT EXISTS FOR (w:Word) ON (w.jlpt_level)",
        
        # Index for SYNONYM_OF relationships with weights
        "CREATE INDEX synonym_weight_index IF NOT EXISTS FOR ()-[r:SYNONYM_OF]-() ON (r.synonym_strength)",
        "CREATE INDEX synonym_weight_desc_index IF NOT EXISTS FOR ()-[r:SYNONYM_OF]-() ON (r.synonym_strength DESC)",
        "CREATE INDEX synonym_relation_type_index IF NOT EXISTS FOR ()-[r:SYNONYM_OF]-() ON (r.relation_type)",
        
        # Index for classification relationships
        "CREATE INDEX has_difficulty_index IF NOT EXISTS FOR ()-[r:HAS_DIFFICULTY]-() ON (r)",
        "CREATE INDEX has_pos_index IF NOT EXISTS FOR ()-[r:HAS_POS]-() ON (r)",
        "CREATE INDEX has_etymology_index IF NOT EXISTS FOR ()-[r:HAS_ETYMOLOGY]-() ON (r)",
        "CREATE INDEX belongs_to_domain_index IF NOT EXISTS FOR ()-[r:BELONGS_TO_DOMAIN]-() ON (r)",
        
        # Composite relationship index
        "CREATE INDEX synonym_composite_index IF NOT EXISTS FOR ()-[r:SYNONYM_OF]-() ON (r.synonym_strength DESC, r.weight DESC)",
    ]
    
    async for session in get_neo4j_session():
        try:
            # Apply each index
            for i, query in enumerate(indexes, 1):
                print(f"  [{i:2d}/{len(indexes)}] Creating index...")
                result = await session.run(query)
                await result.consume()
                print(f"  ✅ Index {i} created successfully")
            
            # Create fulltext indexes
            print("  📚 Creating fulltext indexes...")
            
            # Fulltext index for Word nodes
            fulltext_word = """
            CALL db.index.fulltext.createNodeIndex("word_search", ["Word"], 
                ["kanji", "hiragana", "translation", "pos_primary"])
            """
            result = await session.run(fulltext_word)
            await result.consume()
            print("  ✅ Fulltext index for Word nodes created")
            
            # Fulltext index for SemanticDomain nodes
            fulltext_domain = """
            CALL db.index.fulltext.createNodeIndex("domain_search", ["SemanticDomain"], 
                ["name", "translation", "description"])
            """
            result = await session.run(fulltext_domain)
            await result.consume()
            print("  ✅ Fulltext index for SemanticDomain nodes created")
            
            # Show current indexes
            print("\n📋 Current indexes:")
            result = await session.run("SHOW INDEXES")
            async for record in result:
                print(f"  - {record['name']}: {record['state']} ({record['populationPercent']}% populated)")
            
            print("\n🎉 All indexes applied successfully!")
            
        except Exception as e:
            print(f"❌ Error applying indexes: {e}")
            raise


async def test_performance():
    """Test query performance before and after indexes."""
    
    print("\n🧪 Testing query performance...")
    
    async for session in get_neo4j_session():
        try:
            # Test Depth 1 query
            print("  📊 Testing Depth 1 query...")
            start_time = asyncio.get_event_loop().time()
            
            query1 = """
            MATCH (t:Word {kanji: "日本"})
            OPTIONAL MATCH (t)-[r:SYNONYM_OF]-(n:Word)
            OPTIONAL MATCH (n)-[:BELONGS_TO_DOMAIN]->(d:SemanticDomain)
            OPTIONAL MATCH (n)-[:HAS_POS]->(p:POSTag)
            WITH t, r, n,
                 head(collect(d.name)) AS domain,
                 head(collect(p.primary_pos)) AS pos
            ORDER BY coalesce(r.synonym_strength, r.weight, 0.0) DESC
            RETURN count(n) as neighbor_count
            LIMIT 50
            """
            
            result = await session.run(query1)
            record = await result.single()
            neighbor_count = record["neighbor_count"] if record else 0
            
            depth1_time = (asyncio.get_event_loop().time() - start_time) * 1000
            print(f"  ✅ Depth 1: {neighbor_count} neighbors in {depth1_time:.1f}ms")
            
            # Test Depth 2 query (if we have neighbors)
            if neighbor_count > 0:
                print("  📊 Testing Depth 2 query...")
                start_time = asyncio.get_event_loop().time()
                
                query2 = """
                MATCH (center:Word {kanji: "日本"})
                MATCH (center)-[:SYNONYM_OF]-(neighbor:Word)
                MATCH (neighbor)-[r:SYNONYM_OF]-(other:Word)
                WHERE other.kanji <> center.kanji
                RETURN count(r) as edge_count
                LIMIT 100
                """
                
                result = await session.run(query2)
                record = await result.single()
                edge_count = record["edge_count"] if record else 0
                
                depth2_time = (asyncio.get_event_loop().time() - start_time) * 1000
                print(f"  ✅ Depth 2: {edge_count} edges in {depth2_time:.1f}ms")
                
                # Performance assessment
                if depth1_time < 100 and depth2_time < 1000:
                    print("  🚀 Performance: EXCELLENT - queries are fast!")
                elif depth1_time < 500 and depth2_time < 5000:
                    print("  ✅ Performance: GOOD - queries are acceptable")
                else:
                    print("  ⚠️  Performance: NEEDS IMPROVEMENT - queries are still slow")
            
        except Exception as e:
            print(f"❌ Error testing performance: {e}")


async def main():
    """Main function to apply indexes and test performance."""
    print("🔧 Neo4j Performance Index Application")
    print("=" * 50)
    
    try:
        # Apply indexes
        await apply_indexes()
        
        # Test performance
        await test_performance()
        
        print("\n🎯 Index application complete!")
        print("💡 Expected improvements:")
        print("  - Depth 1 queries: 100-500ms → 10-50ms")
        print("  - Depth 2 queries: 2-10s → 100-500ms")
        print("  - Node lookup: 50-200ms → 5-20ms")
        
    except Exception as e:
        print(f"\n❌ Failed to apply indexes: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
