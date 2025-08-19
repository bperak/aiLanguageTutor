#!/usr/bin/env python
"""Ensure all Word nodes have kanji, hiragana, katakana, translation, romaji"""
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

# Initialize pykakasi for conversions
kks = pykakasi.kakasi()

def analyze_missing_attributes(session):
    """Analyze which attributes are missing from Word nodes"""
    print("=" * 80)
    print("ANALYZING MISSING ATTRIBUTES")
    print("=" * 80)
    
    # Check availability of each required attribute
    required_attrs = ['kanji', 'hiragana', 'katakana', 'translation', 'romaji']
    
    for attr in required_attrs:
        result = session.run(f"""
            MATCH (w:Word)
            RETURN 
                count(w) as total,
                sum(CASE WHEN w.{attr} IS NOT NULL AND w.{attr} <> '' THEN 1 ELSE 0 END) as has_attr,
                sum(CASE WHEN w.{attr} IS NULL OR w.{attr} = '' THEN 1 ELSE 0 END) as missing_attr
        """)
        
        stats = result.single()
        coverage = stats['has_attr'] / stats['total'] * 100 if stats['total'] > 0 else 0
        
        print(f"{attr:<12}: {stats['has_attr']:>8,}/{stats['total']:,} ({coverage:5.1f}%) | Missing: {stats['missing_attr']:,}")
    
    # Check nodes missing multiple attributes
    print(f"\nNodes missing multiple attributes:")
    result = session.run("""
        MATCH (w:Word)
        WITH w,
             CASE WHEN w.kanji IS NULL OR w.kanji = '' THEN 1 ELSE 0 END as no_kanji,
             CASE WHEN w.hiragana IS NULL OR w.hiragana = '' THEN 1 ELSE 0 END as no_hiragana,
             CASE WHEN w.katakana IS NULL OR w.katakana = '' THEN 1 ELSE 0 END as no_katakana,
             CASE WHEN w.translation IS NULL OR w.translation = '' THEN 1 ELSE 0 END as no_translation,
             CASE WHEN w.romaji IS NULL OR w.romaji = '' THEN 1 ELSE 0 END as no_romaji
        WITH w, no_kanji + no_hiragana + no_katakana + no_translation + no_romaji as missing_count
        WHERE missing_count > 0
        RETURN missing_count, count(w) as node_count
        ORDER BY missing_count DESC
    """)
    
    for record in result:
        print(f"  Missing {record['missing_count']} attributes: {record['node_count']:,} nodes")

def get_available_source_fields(session):
    """Check what source fields are available for filling missing data"""
    print(f"\nAvailable source fields:")
    
    # Get all property names from a sample of nodes
    result = session.run("""
        MATCH (w:Word)
        WITH w LIMIT 1000
        UNWIND keys(w) as key
        RETURN DISTINCT key
        ORDER BY key
    """)
    
    all_props = [record['key'] for record in result]
    
    # Potential source fields for each target attribute
    source_mapping = {
        'kanji': ['lemma', 'Standard_orthography', 'kanji'],
        'hiragana': ['hiragana', 'reading', 'reading_hiragana'],
        'katakana': ['katakana', 'Katakana_reading', 'reading_katakana'],
        'translation': ['translation'],
        'romaji': ['romaji']
    }
    
    available_sources = {}
    for target, potential_sources in source_mapping.items():
        available = [prop for prop in potential_sources if prop in all_props]
        available_sources[target] = available
        print(f"  {target:<12}: {available}")
    
    return available_sources

def convert_text(text, target_type):
    """Convert text to target type using pykakasi"""
    if not text:
        return None
    
    try:
        result = kks.convert(str(text))
        
        if target_type == 'hiragana':
            return ''.join([item['hiragana'] for item in result])
        elif target_type == 'katakana':
            return ''.join([item['katakana'] for item in result])
        elif target_type == 'romaji':
            return ' '.join([item['hepburn'] if 'hepburn' in item else item['orig'] for item in result]).strip()
        else:
            return str(text)  # For kanji, keep original
            
    except Exception as e:
        print(f"Error converting '{text}' to {target_type}: {e}")
        return None

def fill_missing_attributes(session, available_sources):
    """Fill missing attributes using available source fields and conversions"""
    print(f"\n" + "=" * 80)
    print("FILLING MISSING ATTRIBUTES")
    print("=" * 80)
    
    # Get nodes with missing attributes
    result = session.run("""
        MATCH (w:Word)
        WHERE w.kanji IS NULL OR w.kanji = '' OR
              w.hiragana IS NULL OR w.hiragana = '' OR
              w.katakana IS NULL OR w.katakana = '' OR
              w.translation IS NULL OR w.translation = '' OR
              w.romaji IS NULL OR w.romaji = ''
        RETURN elementId(w) as id, w.lemma as lemma, w.reading as reading, 
               w.kanji as kanji, w.hiragana as hiragana, w.katakana as katakana,
               w.translation as translation, w.romaji as romaji,
               w.source as source
    """)
    
    updates = []
    processed = 0
    
    for record in result:
        node_id = record['id']
        
        # Determine primary text source (priority: lemma -> reading -> kanji -> hiragana -> katakana)
        primary_text = (record['lemma'] or record['reading'] or record['kanji'] or 
                       record['hiragana'] or record['katakana'])
        
        if not primary_text:
            continue
        
        update = {'id': node_id}
        
        # Fill kanji (use lemma if available, otherwise keep existing)
        if not record['kanji']:
            update['kanji'] = record['lemma'] or primary_text
        
        # Fill hiragana (convert from primary text if missing)
        if not record['hiragana']:
            converted = convert_text(primary_text, 'hiragana')
            if converted:
                update['hiragana'] = converted
        
        # Fill katakana (convert from primary text if missing)
        if not record['katakana']:
            converted = convert_text(primary_text, 'katakana')
            if converted:
                update['katakana'] = converted
        
        # Fill romaji (convert from primary text if missing)
        if not record['romaji']:
            converted = convert_text(primary_text, 'romaji')
            if converted:
                update['romaji'] = converted
        
        # Keep existing translation (we'll handle this separately if needed)
        
        if len(update) > 1:  # More than just 'id'
            updates.append(update)
        
        processed += 1
        if processed % 10000 == 0:
            print(f"Processed {processed:,} nodes, prepared {len(updates):,} updates")
    
    print(f"Total processed: {processed:,}, will update: {len(updates):,}")
    
    # Apply updates in batches
    batch_size = 1000
    updated = 0
    
    for i in range(0, len(updates), batch_size):
        batch = updates[i:i+batch_size]
        
        session.run("""
            UNWIND $updates as update
            MATCH (w:Word)
            WHERE elementId(w) = update.id
            SET w.kanji = COALESCE(update.kanji, w.kanji),
                w.hiragana = COALESCE(update.hiragana, w.hiragana),
                w.katakana = COALESCE(update.katakana, w.katakana),
                w.romaji = COALESCE(update.romaji, w.romaji)
        """, updates=batch)
        
        updated += len(batch)
        
        if updated % 5000 == 0:
            print(f"Updated {updated:,}/{len(updates):,} nodes")
    
    print(f"✓ Updated {updated:,} nodes with missing attributes")

def final_verification(session):
    """Verify all nodes now have the required attributes"""
    print(f"\n" + "=" * 80)
    print("FINAL VERIFICATION")
    print("=" * 80)
    
    required_attrs = ['kanji', 'hiragana', 'katakana', 'translation', 'romaji']
    
    for attr in required_attrs:
        result = session.run(f"""
            MATCH (w:Word)
            RETURN 
                count(w) as total,
                sum(CASE WHEN w.{attr} IS NOT NULL AND w.{attr} <> '' THEN 1 ELSE 0 END) as has_attr
        """)
        
        stats = result.single()
        coverage = stats['has_attr'] / stats['total'] * 100 if stats['total'] > 0 else 0
        
        print(f"{attr:<12}: {stats['has_attr']:>8,}/{stats['total']:,} ({coverage:5.1f}%)")
    
    # Show sample of complete nodes
    print(f"\nSample complete nodes:")
    result = session.run("""
        MATCH (w:Word)
        WHERE w.kanji IS NOT NULL AND w.kanji <> ''
        AND w.hiragana IS NOT NULL AND w.hiragana <> ''
        AND w.katakana IS NOT NULL AND w.katakana <> ''
        AND w.romaji IS NOT NULL AND w.romaji <> ''
        RETURN w.kanji as kanji, w.hiragana as hiragana, 
               w.katakana as katakana, w.romaji as romaji, w.translation as translation
        LIMIT 5
    """)
    
    print(f"{'Kanji':<10} {'Hiragana':<12} {'Katakana':<12} {'Romaji':<15} {'Translation':<20}")
    print("-" * 80)
    for record in result:
        kanji = record['kanji'][:8] if record['kanji'] else 'N/A'
        hiragana = record['hiragana'][:10] if record['hiragana'] else 'N/A'
        katakana = record['katakana'][:10] if record['katakana'] else 'N/A'
        romaji = record['romaji'][:13] if record['romaji'] else 'N/A'
        translation = record['translation'][:18] if record['translation'] else 'N/A'
        
        print(f"{kanji:<10} {hiragana:<12} {katakana:<12} {romaji:<15} {translation:<20}")

def main():
    print("=" * 80)
    print("UNIFYING ALL WORD ATTRIBUTES")
    print("=" * 80)
    
    with driver.session() as session:
        analyze_missing_attributes(session)
        available_sources = get_available_source_fields(session)
        fill_missing_attributes(session, available_sources)
        final_verification(session)
    
    driver.close()

if __name__ == "__main__":
    main()
