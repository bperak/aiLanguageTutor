#!/usr/bin/env python
"""Debug why some Word nodes don't have romaji"""
import os
from pathlib import Path
from neo4j import GraphDatabase  # type: ignore
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

# Neo4j connection setup
URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
if URI.startswith("neo4j://neo4j:"):
    URI = URI.replace("neo4j://neo4j:", "bolt://localhost:")
elif URI.startswith("neo4j://"):
    URI = URI.replace("neo4j://", "bolt://")
USER = os.getenv("NEO4J_USER", "neo4j")
PASSWORD = os.getenv("NEO4J_PASSWORD")
AUTH = (USER, PASSWORD)

driver = GraphDatabase.driver(URI, auth=AUTH)

def debug_missing_romaji(session):
    """Find out why some nodes don't have romaji"""
    
    print("=" * 60)
    print("DEBUGGING MISSING ROMAJI")
    print("=" * 60)
    
    # Check nodes without romaji
    result = session.run("""
        MATCH (w:Word)
        WHERE w.romaji IS NULL
        RETURN w.lemma as lemma, w.reading as reading, 
               w.reading_hiragana as hiragana, w.reading_katakana as katakana,
               w.source as source, w.source_id as source_id
        LIMIT 10
    """)
    
    print("\nSample nodes WITHOUT romaji:")
    print("-" * 60)
    for record in result:
        lemma = record['lemma'] or 'NULL'
        reading = record['reading'] or 'NULL'
        hiragana = record['hiragana'] or 'NULL'
        katakana = record['katakana'] or 'NULL'
        source = record['source'] or 'NULL'
        source_id = record['source_id'] or 'NULL'
        
        print(f"Source: {source} | ID: {source_id}")
        print(f"  lemma: {lemma}")
        print(f"  reading: {reading}")
        print(f"  hiragana: {hiragana}")
        print(f"  katakana: {katakana}")
        print()
    
    # Count by source
    result = session.run("""
        MATCH (w:Word)
        WHERE w.romaji IS NULL
        RETURN w.source as source, count(w) as missing_count
        ORDER BY missing_count DESC
    """)
    
    print("Missing romaji by source:")
    print("-" * 30)
    for record in result:
        print(f"  {record['source']}: {record['missing_count']:,}")
    
    # Check what fields are null
    result = session.run("""
        MATCH (w:Word)
        WHERE w.romaji IS NULL
        RETURN 
            sum(CASE WHEN w.lemma IS NULL THEN 1 ELSE 0 END) as null_lemma,
            sum(CASE WHEN w.reading IS NULL THEN 1 ELSE 0 END) as null_reading,
            sum(CASE WHEN w.reading_hiragana IS NULL THEN 1 ELSE 0 END) as null_hiragana,
            sum(CASE WHEN w.reading_katakana IS NULL THEN 1 ELSE 0 END) as null_katakana,
            count(w) as total_missing
    """)
    
    stats = result.single()
    print(f"\nField availability in nodes missing romaji:")
    print(f"  Total missing romaji: {stats['total_missing']:,}")
    print(f"  NULL lemma: {stats['null_lemma']:,}")
    print(f"  NULL reading: {stats['null_reading']:,}")
    print(f"  NULL hiragana: {stats['null_hiragana']:,}")
    print(f"  NULL katakana: {stats['null_katakana']:,}")
    
    # Check if all fields are null
    result = session.run("""
        MATCH (w:Word)
        WHERE w.romaji IS NULL
        AND w.lemma IS NULL 
        AND w.reading IS NULL 
        AND w.reading_hiragana IS NULL 
        AND w.reading_katakana IS NULL
        RETURN count(w) as all_null_count
    """)
    
    all_null = result.single()['all_null_count']
    print(f"  Nodes with ALL text fields NULL: {all_null:,}")

def main():
    with driver.session() as session:
        debug_missing_romaji(session)
    driver.close()

if __name__ == "__main__":
    main()
