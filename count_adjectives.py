#!/usr/bin/env python3
"""
Count i-adjectives and na-adjectives in Neo4j database.
"""
import asyncio
import os
from neo4j import AsyncGraphDatabase
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def count_adjectives():
    """Count adjectives by type in Neo4j database."""
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    username = os.getenv("NEO4J_USERNAME", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "")
    
    print(f"Connecting to Neo4j at {uri}...")
    driver = AsyncGraphDatabase.driver(uri, auth=(username, password))
    
    try:
        async with driver.session() as session:
            # Count i-adjectives (形容詞)
            result = await session.run("""
                MATCH (w:Word)
                WHERE w.pos1 = '形容詞' OR w.pos_primary_norm = '形容詞'
                RETURN count(w) as count
            """)
            record = await result.single()
            i_adj_count = record["count"] if record else 0
            
            # Count na-adjectives (形状詞)
            result = await session.run("""
                MATCH (w:Word)
                WHERE w.pos1 = '形状詞' OR w.pos_primary_norm = '形状詞'
                RETURN count(w) as count
            """)
            record = await result.single()
            na_adj_count = record["count"] if record else 0
            
            # Total adjectives
            total_adjectives = i_adj_count + na_adj_count
            
            print(f"\n=== Adjective Counts ===")
            print(f"i-adjectives (形容詞):  {i_adj_count}")
            print(f"na-adjectives (形状詞): {na_adj_count}")
            print(f"Total adjectives:       {total_adjectives}")
            
            # Count relations between adjectives
            result = await session.run("""
                MATCH (w1:Word)-[r:LEXICAL_RELATION]->(w2:Word)
                WHERE (w1.pos1 IN ['形容詞', '形状詞'] OR w1.pos_primary_norm IN ['形容詞', '形状詞'])
                  AND (w2.pos1 IN ['形容詞', '形状詞'] OR w2.pos_primary_norm IN ['形容詞', '形状詞'])
                RETURN count(r) as count
            """)
            record = await result.single()
            adj_relations = record["count"] if record else 0
            
            # Count relations by type
            result = await session.run("""
                MATCH (w1:Word)-[r:LEXICAL_RELATION]->(w2:Word)
                WHERE (w1.pos1 IN ['形容詞', '形状詞'] OR w1.pos_primary_norm IN ['形容詞', '形状詞'])
                  AND (w2.pos1 IN ['形容詞', '形状詞'] OR w2.pos_primary_norm IN ['形容詞', '形状詞'])
                RETURN r.relation_type as relation_type, count(r) as count
                ORDER BY count DESC
            """)
            records = await result.values()
            
            print(f"\n=== Adjective Relations ===")
            print(f"Total adjective-adjective relations: {adj_relations}")
            if records:
                print("\nBy relation type:")
                for rec in records:
                    print(f"  {rec[0]}: {rec[1]}")
            
            # Sample i-adjectives
            result = await session.run("""
                MATCH (w:Word)
                WHERE w.pos1 = '形容詞' OR w.pos_primary_norm = '形容詞'
                RETURN w.standard_orthography as word, w.reading_hiragana as reading, w.translation as translation
                LIMIT 10
            """)
            records = await result.values()
            print(f"\n=== Sample i-adjectives (first 10) ===")
            for rec in records:
                print(f"  {rec[0]} ({rec[1]}): {rec[2]}")
            
            # Sample na-adjectives
            result = await session.run("""
                MATCH (w:Word)
                WHERE w.pos1 = '形状詞' OR w.pos_primary_norm = '形状詞'
                RETURN w.standard_orthography as word, w.reading_hiragana as reading, w.translation as translation
                LIMIT 10
            """)
            records = await result.values()
            print(f"\n=== Sample na-adjectives (first 10) ===")
            for rec in records:
                print(f"  {rec[0]} ({rec[1]}): {rec[2]}")
                
    finally:
        await driver.close()

if __name__ == "__main__":
    asyncio.run(count_adjectives())
