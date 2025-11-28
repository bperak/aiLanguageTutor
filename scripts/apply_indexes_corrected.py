#!/usr/bin/env python3
"""
Apply Neo4j performance indexes for AI Language Tutor (Corrected Docker version).

This script connects to the Neo4j container and applies all performance indexes
with correct syntax for Neo4j 5.x.
"""

import asyncio
import time
from neo4j import AsyncGraphDatabase


async def apply_indexes():
    """Apply all performance indexes to Neo4j."""
    
    # Neo4j connection details (from docker-compose)
    NEO4J_URI = "bolt://localhost:7687"
    NEO4J_USERNAME = "neo4j"
    NEO4J_PASSWORD = "testpassword123"
    
    print("🔧 Neo4j Performance Index Application (Corrected)")
    print("=" * 60)
    
    try:
        # Connect to Neo4j
        print("🚀 Connecting to Neo4j...")
        driver = AsyncGraphDatabase.driver(
            NEO4J_URI,
            auth=(NEO4J_USERNAME, NEO4J_PASSWORD)
        )
        
        # Verify connectivity
        await driver.verify_connectivity()
        print("✅ Connected to Neo4j successfully!")
        
        # Index creation queries (corrected syntax for Neo4j 5.x)
        indexes = [
            # Primary lookup indexes for Word nodes
            "CREATE INDEX word_kanji_lookup_v2 IF NOT EXISTS FOR (w:Word) ON (w.kanji)",
            "CREATE INDEX word_hiragana_lookup_v2 IF NOT EXISTS FOR (w:Word) ON (w.hiragana)",
            "CREATE INDEX word_lemma_lookup_v2 IF NOT EXISTS FOR (w:Word) ON (w.lemma)",
            
            # Composite indexes for common query patterns
            "CREATE INDEX word_kanji_difficulty_v2 IF NOT EXISTS FOR (w:Word) ON (w.kanji, w.difficulty_numeric)",
            "CREATE INDEX word_kanji_pos_v2 IF NOT EXISTS FOR (w:Word) ON (w.kanji, w.pos_primary)",
            "CREATE INDEX word_kanji_etymology_v2 IF NOT EXISTS FOR (w:Word) ON (w.kanji, w.etymology)",
            
            # Performance indexes for classification queries
            "CREATE INDEX word_difficulty_numeric_perf_v2 IF NOT EXISTS FOR (w:Word) ON (w.difficulty_numeric)",
            "CREATE INDEX word_pos_primary_perf_v2 IF NOT EXISTS FOR (w:Word) ON (w.pos_primary)",
            "CREATE INDEX word_etymology_perf_v2 IF NOT EXISTS FOR (w:Word) ON (w.etymology)",
            "CREATE INDEX word_jlpt_level_perf_v2 IF NOT EXISTS FOR (w:Word) ON (w.jlpt_level)",
            
            # Index for SYNONYM_OF relationships with weights (corrected syntax)
            "CREATE INDEX synonym_weight_index_v2 IF NOT EXISTS FOR ()-[r:SYNONYM_OF]-() ON (r.synonym_strength)",
            "CREATE INDEX synonym_relation_type_index_v2 IF NOT EXISTS FOR ()-[r:SYNOMYM_OF]-() ON (r.relation_type)",
            
            # Index for classification relationships (corrected syntax)
            "CREATE INDEX has_difficulty_index_v2 IF NOT EXISTS FOR ()-[r:HAS_DIFFICULTY]-() ON (r.synonym_strength)",
            "CREATE INDEX has_pos_index_v2 IF NOT EXISTS FOR ()-[r:HAS_POS]-() ON (r.synonym_strength)",
            "CREATE INDEX has_etymology_index_v2 IF NOT EXISTS FOR ()-[r:HAS_ETYMOLOGY]-() ON (r.synonym_strength)",
            "CREATE INDEX belongs_to_domain_index_v2 IF NOT EXISTS FOR ()-[r:BELONGS_TO_DOMAIN]-() ON (r.synonym_strength)",
        ]
        
        print(f"📊 Applying {len(indexes)} corrected performance indexes...")
        
        async with driver.session() as session:
            # Apply each index
            for i, query in enumerate(indexes, 1):
                print(f"  [{i:2d}/{len(indexes)}] Creating index...")
                try:
                    result = await session.run(query)
                    await result.consume()
                    print(f"  ✅ Index {i} created successfully")
                except Exception as e:
                    print(f"  ⚠️  Index {i} creation warning: {e}")
                    # Continue with other indexes
            
            # Show current indexes
            print("\n📋 Current indexes:")
            try:
                result = await session.run("SHOW INDEXES")
                async for record in result:
                    print(f"  - {record['name']}: {record['state']} ({record['populationPercent']}% populated)")
            except Exception as e:
                print(f"  ⚠️  Could not show indexes: {e}")
        
        print("\n🎉 Corrected index application completed!")
        
    except Exception as e:
        print(f"❌ Error applying indexes: {e}")
        raise
    finally:
        if 'driver' in locals():
            await driver.close()


async def wait_for_indexes():
    """Wait for indexes to finish populating."""
    
    print("\n⏳ Waiting for indexes to finish populating...")
    
    NEO4J_URI = "bolt://localhost:7687"
    NEO4J_USERNAME = "neo4j"
    NEO4J_PASSWORD = "testpassword123"
    
    try:
        driver = AsyncGraphDatabase.driver(
            NEO4J_URI,
            auth=(NEO4J_USERNAME, NEO4J_PASSWORD)
        )
        
        max_wait_time = 300  # 5 minutes max
        wait_interval = 10   # Check every 10 seconds
        elapsed_time = 0
        
        while elapsed_time < max_wait_time:
            async with driver.session() as session:
                result = await session.run("SHOW INDEXES")
                all_populated = True
                
                async for record in result:
                    if record['state'] == 'POPULATING':
                        all_populated = False
                        break
                
                if all_populated:
                    print("✅ All indexes are fully populated!")
                    break
                
                print(f"⏳ Still waiting... ({elapsed_time}s elapsed)")
                await asyncio.sleep(wait_interval)
                elapsed_time += wait_interval
        
        if elapsed_time >= max_wait_time:
            print("⚠️  Timeout waiting for indexes to populate")
        
    except Exception as e:
        print(f"⚠️  Error checking index status: {e}")
    finally:
        if 'driver' in locals():
            await driver.close()


async def test_performance():
    """Test query performance after applying indexes."""
    
    print("\n🧪 Testing query performance...")
    
    # Neo4j connection details
    NEO4J_URI = "bolt://localhost:7687"
    NEO4J_USERNAME = "neo4j"
    NEO4J_PASSWORD = "testpassword123"
    
    try:
        driver = AsyncGraphDatabase.driver(
            NEO4J_URI,
            auth=(NEO4J_USERNAME, NEO4J_PASSWORD)
        )
        
        async with driver.session() as session:
            # Test Depth 1 query
            print("  📊 Testing Depth 1 query...")
            start_time = time.time()
            
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
            
            depth1_time = (time.time() - start_time) * 1000
            print(f"  ✅ Depth 1: {neighbor_count} neighbors in {depth1_time:.1f}ms")
            
            # Test Depth 2 query (if we have neighbors)
            if neighbor_count > 0:
                print("  📊 Testing Depth 2 query...")
                start_time = time.time()
                
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
                
                depth2_time = (time.time() - start_time) * 1000
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
    finally:
        if 'driver' in locals():
            await driver.close()


async def main():
    """Main function to apply indexes and test performance."""
    print("🔧 Neo4j Performance Index Application (Corrected)")
    print("=" * 60)
    
    try:
        # Apply corrected indexes
        await apply_indexes()
        
        # Wait for indexes to populate
        await wait_for_indexes()
        
        # Test performance
        await test_performance()
        
        print("\n🎯 Index application complete!")
        print("💡 Expected improvements:")
        print("  - Depth 1 queries: 100-500ms → 10-50ms")
        print("  - Depth 2 queries: 2-10s → 100-500ms")
        print("  - Node lookup: 50-200ms → 5-20ms")
        
        print("\n🚀 Next steps:")
        print("  1. Test the frontend: http://localhost:3000/lexical/graph")
        print("  2. Set Depth to 2 and search for 'nihon'")
        print("  3. Should load dramatically faster now!")
        
    except Exception as e:
        print(f"\n❌ Failed to apply indexes: {e}")
        print("\n💡 Troubleshooting:")
        print("  - Ensure Docker containers are running: docker-compose ps")
        print("  - Check Neo4j is accessible: http://localhost:7474")
        print("  - Verify backend is running: http://localhost:8000/health")


if __name__ == "__main__":
    asyncio.run(main())
