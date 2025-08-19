#!/usr/bin/env python
"""Check current translation status"""

from neo4j import GraphDatabase
import os
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables from parent directory
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

# Neo4j connection - parse URI to handle neo4j:// format
URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")

# Convert neo4j://neo4j:7687 to bolt://localhost:7687 if needed
if URI.startswith("neo4j://neo4j:"):
    URI = URI.replace("neo4j://neo4j:", "bolt://localhost:")
elif URI.startswith("neo4j://"):
    URI = URI.replace("neo4j://", "bolt://")

USER = os.getenv("NEO4J_USER", "neo4j")
PASSWORD = os.getenv("NEO4J_PASSWORD")
AUTH = (USER, PASSWORD)

def check_status():
    """Check translation status"""
    driver = GraphDatabase.driver(URI, auth=AUTH)
    
    try:
        with driver.session() as session:
            print("=" * 80)
            print("TRANSLATION STATUS REPORT")
            print("=" * 80)
            
            # Overall LeeGoi translation status
            result = session.run("""
                MATCH (w:Word)
                WHERE w.source = 'LeeGoi'
                WITH count(w) as total,
                     sum(CASE WHEN w.translation IS NOT NULL AND w.translation <> '' THEN 1 ELSE 0 END) as with_translation,
                     sum(CASE WHEN w.ai_translated = true THEN 1 ELSE 0 END) as ai_generated
                RETURN total, with_translation, ai_generated,
                       (total - with_translation) as missing
            """)
            
            stats = result.single()
            total = stats['total']
            with_translation = stats['with_translation']
            missing = stats['missing']
            ai_generated = stats['ai_generated']
            
            print(f"LeeGoi Translation Status:")
            print(f"  Total words: {total:,}")
            print(f"  With translations: {with_translation:,} ({with_translation/total*100:.1f}%)")
            print(f"  Missing translations: {missing:,} ({missing/total*100:.1f}%)")
            print(f"  AI-generated translations: {ai_generated:,}")
            
            # Breakdown by level
            result = session.run("""
                MATCH (w:Word)
                WHERE w.source = 'LeeGoi'
                WITH w.level_int as level,
                     count(w) as total,
                     sum(CASE WHEN w.translation IS NOT NULL AND w.translation <> '' THEN 1 ELSE 0 END) as with_translation
                WHERE level IS NOT NULL
                RETURN level, total, with_translation,
                       (total - with_translation) as missing
                ORDER BY level
            """)
            
            print(f"\nTranslation status by level:")
            print(f"{'Level':<8} {'Total':<8} {'Translated':<12} {'Missing':<8} {'Coverage':<10}")
            print("-" * 50)
            
            for record in result:
                level = record['level']
                total = record['total']
                translated = record['with_translation']
                missing = record['missing']
                coverage = translated/total*100 if total > 0 else 0
                
                marker = " ← Priority" if level <= 3 else ""
                print(f"{level:<8} {total:<8} {translated:<12} {missing:<8} {coverage:<10.1f}%{marker}")
            
            # Sample missing words by level (prioritize easier levels)
            print(f"\nSample missing translations (by priority level):")
            result = session.run("""
                MATCH (w:Word)
                WHERE w.source = 'LeeGoi'
                AND (w.translation IS NULL OR w.translation = '')
                AND w.level_int <= 4
                RETURN w.lemma as word, w.reading as reading, 
                       w.pos as pos, w.level_int as level
                ORDER BY w.level_int ASC, w.lemma
                LIMIT 15
            """)
            
            for record in result:
                print(f"  {record['word']} ({record['reading']}) [{record['pos']}] Level {record['level']}")
            
            # Recent AI translations
            result = session.run("""
                MATCH (w:Word)
                WHERE w.ai_translated = true
                RETURN w.lemma as word, w.translation as translation
                ORDER BY w.updated_at DESC
                LIMIT 10
            """)
            
            recent_translations = [dict(record) for record in result]
            if recent_translations:
                print(f"\nRecent AI translations:")
                for record in recent_translations:
                    print(f"  {record['word']} → {record['translation']}")
                    
    except Exception as e:
        print(f"Error checking status: {e}")
        import traceback
        traceback.print_exc()
    finally:
        driver.close()

if __name__ == "__main__":
    check_status()
