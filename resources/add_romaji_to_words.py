#!/usr/bin/env python
"""Add romaji transcription to all Word nodes in Neo4j"""
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
if not PASSWORD:
    raise RuntimeError("NEO4J_PASSWORD not set in .env")

driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))

# Initialize pykakasi for romanization
kks = pykakasi.kakasi()

def to_romaji(text):
    """Convert Japanese text to romaji using Hepburn romanization"""
    if not text:
        return None
    try:
        result = kks.convert(str(text))
        # Join all parts with spaces for multi-character words
        romaji_parts = []
        for item in result:
            if 'hepburn' in item:
                romaji_parts.append(item['hepburn'])
            elif 'orig' in item:
                # Keep original for non-Japanese characters
                romaji_parts.append(item['orig'])
        return ' '.join(romaji_parts).strip()
    except Exception as e:
        print(f"Error converting '{text}': {e}")
        return None

def add_romaji_to_words(session, batch_size=1000):
    """Add romaji transcription to all Word nodes"""
    
    # Get total count
    result = session.run("MATCH (w:Word) RETURN count(w) as total")
    total = result.single()['total']
    print(f"Total Word nodes to process: {total:,}")
    
    processed = 0
    updated = 0
    
    # Process in batches
    skip = 0
    while skip < total:
        # Fetch batch of words
        result = session.run("""
            MATCH (w:Word)
            RETURN id(w) as id, w.lemma as lemma, w.reading as reading, 
                   w.reading_hiragana as hiragana, w.reading_katakana as katakana
            SKIP $skip LIMIT $limit
        """, skip=skip, limit=batch_size)
        
        batch_updates = []
        for record in result:
            # Priority: Use lemma first, then reading, then hiragana, then katakana
            text_to_convert = (record['lemma'] or 
                             record['reading'] or 
                             record['hiragana'] or 
                             record['katakana'])
            
            if text_to_convert:
                romaji = to_romaji(text_to_convert)
                if romaji:
                    batch_updates.append({
                        'id': record['id'],
                        'romaji': romaji
                    })
        
        # Update batch in Neo4j
        if batch_updates:
            session.run("""
                UNWIND $updates as update
                MATCH (w:Word)
                WHERE id(w) = update.id
                SET w.romaji = update.romaji
            """, updates=batch_updates)
            updated += len(batch_updates)
        
        processed += batch_size
        skip += batch_size
        
        if processed % 5000 == 0 or processed >= total:
            print(f"Processed {min(processed, total):,}/{total:,} words, updated {updated:,} with romaji")
    
    print(f"\n✓ Complete! Added romaji to {updated:,} Word nodes")

def verify_romaji(session):
    """Verify romaji was added correctly"""
    print("\n" + "=" * 60)
    print("VERIFICATION - Sample words with romaji:")
    print("=" * 60)
    
    result = session.run("""
        MATCH (w:Word)
        WHERE w.romaji IS NOT NULL
        RETURN w.lemma as lemma, w.reading as reading, w.romaji as romaji
        LIMIT 20
    """)
    
    for record in result:
        lemma = record['lemma'] or 'N/A'
        reading = record['reading'] or 'N/A'
        romaji = record['romaji']
        print(f"  {lemma:<15} ({reading:<15}) → {romaji}")
    
    # Count statistics
    result = session.run("""
        MATCH (w:Word)
        RETURN count(w) as total,
               sum(CASE WHEN w.romaji IS NOT NULL THEN 1 ELSE 0 END) as with_romaji
    """)
    stats = result.single()
    
    print(f"\nStatistics:")
    print(f"  Total Word nodes: {stats['total']:,}")
    print(f"  Words with romaji: {stats['with_romaji']:,}")
    print(f"  Coverage: {stats['with_romaji']/stats['total']*100:.1f}%")

def main():
    """Run the romaji addition process"""
    print("=" * 60)
    print("ADDING ROMAJI TRANSCRIPTION TO WORD NODES")
    print("=" * 60)
    
    with driver.session() as session:
        add_romaji_to_words(session)
        verify_romaji(session)
    
    driver.close()

if __name__ == "__main__":
    # First install pykakasi if not already installed
    try:
        import pykakasi
    except ImportError:
        print("Installing pykakasi...")
        import subprocess
        subprocess.check_call(["pip", "install", "pykakasi"])
        print("pykakasi installed successfully!")
        import pykakasi
    
    main()
