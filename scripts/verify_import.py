"""
Quick verification script to check the imported Neo4j data.
"""

import os
import asyncio
from dotenv import load_dotenv
from neo4j import AsyncGraphDatabase

# Load environment variables
load_dotenv()

async def verify_import():
    """Verify the imported data in Neo4j."""
    
    # Configuration
    NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687").replace("neo4j://neo4j:7687", "bolt://localhost:7687")
    NEO4J_USER = os.getenv("NEO4J_USERNAME", "neo4j")
    NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")
    
    driver = AsyncGraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    
    try:
        async with driver.session() as session:
            print("🔍 ENHANCED LEXICAL IMPORT VERIFICATION")
            print("=" * 50)
            
            # Node counts
            result = await session.run("""
                MATCH (n) 
                RETURN labels(n) as NodeType, count(n) as Count 
                ORDER BY Count DESC
            """)
            
            print("\n📊 NODE COUNTS:")
            async for record in result:
                node_type = record['NodeType'][0] if record['NodeType'] else 'Unknown'
                count = record['Count']
                print(f"  {node_type:15} {count:,}")
            
            # Relationship counts
            result = await session.run("""
                MATCH ()-[r]->() 
                RETURN type(r) as RelType, count(r) as Count 
                ORDER BY Count DESC
            """)
            
            print("\n🔗 RELATIONSHIP COUNTS:")
            async for record in result:
                rel_type = record['RelType']
                count = record['Count']
                print(f"  {rel_type:20} {count:,}")
            
            # Sample vocabulary with proper encoding
            result = await session.run("""
                MATCH (w:Word)
                WHERE w.translation IS NOT NULL 
                AND w.kanji IS NOT NULL
                RETURN w.kanji, w.katakana, w.translation, w.etymology
                LIMIT 10
            """)
            
            print("\n📚 SAMPLE VOCABULARY:")
            async for record in result:
                kanji = record['w.kanji']
                katakana = record['w.katakana']
                translation = record['w.translation']
                etymology = record['w.etymology']
                print(f"  {kanji} ({katakana}) → {translation} [{etymology}]")
            
            # Semantic domains
            result = await session.run("""
                MATCH (d:SemanticDomain)
                WHERE d.translation IS NOT NULL
                RETURN d.name, d.translation, d.word_count
                ORDER BY d.word_count DESC
                LIMIT 10
            """)
            
            print("\n🌐 TOP SEMANTIC DOMAINS:")
            async for record in result:
                name = record['d.name']
                translation = record['d.translation']
                word_count = record['d.word_count'] or 0
                print(f"  {name} ({translation}) - {word_count} words")
            
            # Strong synonym relationships
            result = await session.run("""
                MATCH (w1:Word)-[r:SYNONYM_OF]->(w2:Word)
                WHERE r.synonym_strength > 0.8 
                AND w1.translation IS NOT NULL 
                AND w2.translation IS NOT NULL
                RETURN w1.kanji, w1.translation, w2.kanji, w2.translation, r.synonym_strength
                ORDER BY r.synonym_strength DESC
                LIMIT 5
            """)
            
            print("\n🔄 STRONG SYNONYM PAIRS:")
            async for record in result:
                w1_kanji = record['w1.kanji']
                w1_trans = record['w1.translation']
                w2_kanji = record['w2.kanji']
                w2_trans = record['w2.translation']
                strength = record['r.synonym_strength']
                print(f"  {w1_kanji} ({w1_trans}) ↔ {w2_kanji} ({w2_trans}) [{strength:.2f}]")
            
            print("\n" + "=" * 50)
            print("✅ VERIFICATION COMPLETE!")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await driver.close()

if __name__ == "__main__":
    asyncio.run(verify_import())
