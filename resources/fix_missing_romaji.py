#!/usr/bin/env python
"""Fix missing romaji by using actual property names and filling gaps"""
import os
from pathlib import Path
from neo4j import GraphDatabase  # type: ignore
from dotenv import load_dotenv
import pykakasi  # type: ignore

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

# Initialize pykakasi for romanization
kks = pykakasi.kakasi()

def to_romaji(text):
    """Convert Japanese text to romaji using Hepburn romanization"""
    if not text:
        return None
    try:
        result = kks.convert(str(text))
        romaji_parts = []
        for item in result:
            if 'hepburn' in item:
                romaji_parts.append(item['hepburn'])
            elif 'orig' in item:
                romaji_parts.append(item['orig'])
        return ' '.join(romaji_parts).strip()
    except Exception as e:
        print(f"Error converting '{text}': {e}")
        return None

def get_available_properties(session):
    """Find what properties actually exist"""
    result = session.run("""
        MATCH (w:Word)
        WHERE w.romaji IS NULL
        WITH w LIMIT 100
        UNWIND keys(w) as key
        RETURN DISTINCT key
        ORDER BY key
    """)
    
    props = [record['key'] for record in result]
    print(f"Available properties in nodes missing romaji: {props}")
    return props

def fix_missing_romaji(session):
    """Fix nodes missing romaji using available properties"""
    
    # Get available properties
    available_props = get_available_properties(session)
    
    # Define priority order for text fields (use what's actually available)
    text_fields = []
    for field in ['lemma', 'kanji', 'hiragana', 'katakana', 'reading', 'source_id']:
        if field in available_props:
            text_fields.append(field)
    
    print(f"Will try to use these fields for romaji: {text_fields}")
    
    # Build dynamic query based on available fields
    field_cases = []
    field_selects = []
    
    for field in text_fields:
        field_cases.append(f"w.{field}")
        field_selects.append(f"w.{field} as {field}")
    
    if not field_cases:
        print("No text fields available - cannot generate romaji")
        return
    
    # Query to get nodes without romaji
    query = f"""
        MATCH (w:Word)
        WHERE w.romaji IS NULL
        RETURN id(w) as id, {', '.join(field_selects)}
    """
    
    print("Processing nodes without romaji...")
    result = session.run(query)
    
    updates = []
    processed = 0
    
    for record in result:
        # Try each field in priority order
        text_to_convert = None
        for field in text_fields:
            value = record.get(field)
            if value and str(value).strip():
                text_to_convert = str(value).strip()
                break
        
        if text_to_convert:
            romaji = to_romaji(text_to_convert)
            if romaji:
                updates.append({
                    'id': record['id'],
                    'romaji': romaji
                })
        
        processed += 1
        if processed % 10000 == 0:
            print(f"Processed {processed:,} nodes, found {len(updates):,} to update")
    
    print(f"Total processed: {processed:,}, will update: {len(updates):,}")
    
    # Apply updates in batches
    batch_size = 1000
    updated = 0
    
    for i in range(0, len(updates), batch_size):
        batch = updates[i:i+batch_size]
        session.run("""
            UNWIND $updates as update
            MATCH (w:Word)
            WHERE id(w) = update.id
            SET w.romaji = update.romaji
        """, updates=batch)
        updated += len(batch)
        
        if updated % 5000 == 0:
            print(f"Updated {updated:,}/{len(updates):,} nodes with romaji")
    
    print(f"✓ Added romaji to {updated:,} additional nodes")

def clean_empty_nodes(session):
    """Remove or fix completely empty Word nodes"""
    print("\nChecking for completely empty Word nodes...")
    
    # Find nodes with no useful properties
    result = session.run("""
        MATCH (w:Word)
        WHERE w.lemma IS NULL 
        AND w.reading IS NULL 
        AND w.source_id IS NULL
        AND w.romaji IS NULL
        RETURN count(w) as empty_count
    """)
    
    empty_count = result.single()['empty_count']
    print(f"Found {empty_count:,} completely empty Word nodes")
    
    if empty_count > 0:
        response = input(f"Delete these {empty_count:,} empty nodes? (y/n): ")
        if response.lower() == 'y':
            session.run("""
                MATCH (w:Word)
                WHERE w.lemma IS NULL 
                AND w.reading IS NULL 
                AND w.source_id IS NULL
                AND w.romaji IS NULL
                DETACH DELETE w
            """)
            print(f"✓ Deleted {empty_count:,} empty Word nodes")

def final_stats(session):
    """Show final statistics"""
    result = session.run("""
        MATCH (w:Word)
        RETURN count(w) as total,
               sum(CASE WHEN w.romaji IS NOT NULL THEN 1 ELSE 0 END) as with_romaji
    """)
    
    stats = result.single()
    coverage = stats['with_romaji'] / stats['total'] * 100 if stats['total'] > 0 else 0
    
    print(f"\nFinal Statistics:")
    print(f"  Total Word nodes: {stats['total']:,}")
    print(f"  Words with romaji: {stats['with_romaji']:,}")
    print(f"  Coverage: {coverage:.1f}%")

def main():
    print("=" * 60)
    print("FIXING MISSING ROMAJI")
    print("=" * 60)
    
    with driver.session() as session:
        fix_missing_romaji(session)
        clean_empty_nodes(session)
        final_stats(session)
    
    driver.close()

if __name__ == "__main__":
    main()
