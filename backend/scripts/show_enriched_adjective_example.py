"""
Show Example of Enriched Adjective

Shows a detailed example of an adjective that has been enriched with UniDic POS data.
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from neo4j import AsyncGraphDatabase
from dotenv import load_dotenv
import os

load_dotenv()


async def show_example():
    """Show example of enriched adjective."""
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "password")
    
    driver = AsyncGraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
    
    try:
        async with driver.session() as session:
            # First, try to find an adjective from UniDic with full hierarchy
            query = """
            MATCH (w:Word)
            WHERE w.pos1 IS NOT NULL
            AND w.pos_source = 'unidic'
            AND w.pos2 IS NOT NULL
            AND (w.pos1 = '形容詞' OR w.pos1 = '形状詞')
            RETURN w.standard_orthography AS word,
                   w.reading_hiragana AS reading,
                   w.pos1, w.pos2, w.pos3, w.pos4,
                   w.pos_primary_norm,
                   w.pos_source,
                   w.pos_confidence,
                   w.unidic_lemma,
                   w.unidic_pos1,
                   w.unidic_pos2,
                   w.translation
            LIMIT 3
            """
            result = await session.run(query)
            records = await result.data()
            
            if not records:
                # Fallback: any word with UniDic and canonical POS
                query2 = """
                MATCH (w:Word)
                WHERE w.pos1 IS NOT NULL
                AND w.pos_source = 'unidic'
                AND w.pos2 IS NOT NULL
                RETURN w.standard_orthography AS word,
                       w.reading_hiragana AS reading,
                       w.pos1, w.pos2, w.pos3, w.pos4,
                       w.pos_primary_norm,
                       w.unidic_lemma,
                       w.unidic_pos1,
                       w.unidic_pos2,
                       w.translation
                LIMIT 3
                """
                result = await session.run(query2)
                records = await result.data()
            
            if records:
                print("\n" + "=" * 70)
                print("ENRICHED ADJECTIVE EXAMPLE")
                print("=" * 70)
                
                for i, r in enumerate(records, 1):
                    print(f"\nExample {i}:")
                    print(f"  Word: {r.get('word')}")
                    if r.get('reading'):
                        print(f"  Reading: {r.get('reading')}")
                    if r.get('translation'):
                        print(f"  Translation: {r.get('translation')}")
                    
                    print(f"\n  Canonical POS (UniDic normalized):")
                    print(f"    pos1 (Primary):        {r.get('pos1')}")
                    print(f"    pos2 (Secondary):      {r.get('pos2')}")
                    if r.get('pos3'):
                        print(f"    pos3 (Tertiary):       {r.get('pos3')}")
                    if r.get('pos4'):
                        print(f"    pos4 (Quaternary):     {r.get('pos4')}")
                    print(f"    pos_primary_norm:      {r.get('pos_primary_norm')}")
                    
                    print(f"\n  Source Information:")
                    print(f"    pos_source:            {r.get('pos_source')}")
                    if r.get('pos_confidence'):
                        print(f"    pos_confidence:        {r.get('pos_confidence')}")
                    
                    if r.get('unidic_lemma'):
                        print(f"\n  UniDic Morphological Data:")
                        print(f"    unidic_lemma:         {r.get('unidic_lemma')}")
                        print(f"    unidic_pos1:          {r.get('unidic_pos1')}")
                        if r.get('unidic_pos2'):
                            print(f"    unidic_pos2:          {r.get('unidic_pos2')}")
                    
                    print()
            else:
                print("\nNo enriched adjectives found with full POS hierarchy.")
                print("Checking what we have...")
                
                query3 = """
                MATCH (w:Word)
                WHERE w.pos1 IS NOT NULL
                AND w.pos_source = 'unidic'
                RETURN w.standard_orthography AS word,
                       w.pos1, w.pos2
                LIMIT 5
                """
                result3 = await session.run(query3)
                records3 = await result3.data()
                
                if records3:
                    print("\nWords with UniDic canonical POS:")
                    for r in records3:
                        print(f"  {r.get('word')}: pos1={r.get('pos1')}, pos2={r.get('pos2')}")
                else:
                    print("No words found with UniDic canonical POS.")
            
            print("=" * 70)
    
    finally:
        await driver.close()


if __name__ == "__main__":
    asyncio.run(show_example())
