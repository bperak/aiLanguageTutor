#!/usr/bin/env python
"""Batch translate remaining words without translations"""

from neo4j import GraphDatabase
import os
from dotenv import load_dotenv
from pathlib import Path
import time

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

def batch_translate_priority_words(session, batch_size=50):
    """Translate priority words (Level 1-3) in batches"""
    print("=" * 80)
    print("BATCH TRANSLATING PRIORITY WORDS")
    print("=" * 80)
    
    # Check if AI is available
    try:
        from ai_synonym_enhancer import AISynonymEnhancer
        
        gemini_key = os.getenv('GEMINI_API_KEY')
        openai_key = os.getenv('OPENAI_API_KEY')
        provider = os.getenv('AI_PROVIDER', 'gemini')
        
        if not (gemini_key or openai_key):
            print("⚠️ No AI API keys available")
            return 0
        
        enhancer = AISynonymEnhancer(provider)
        print(f"Using {provider.upper()} for translation")
        
    except Exception as e:
        print(f"⚠️ AI not available: {e}")
        return 0
    
    # Get priority words (Level 1-3) missing translations
    result = session.run("""
        MATCH (w:Word)
        WHERE w.source = 'LeeGoi'
        AND (w.translation IS NULL OR w.translation = '')
        AND w.level_int <= 3
        RETURN w.lemma as word, w.reading as reading, w.pos as pos, 
               w.level_int as level, w.lee_id as lee_id
        ORDER BY w.level_int ASC, w.lemma
        LIMIT $batch_size
    """, batch_size=batch_size)
    
    words_to_translate = [dict(record) for record in result]
    
    if not words_to_translate:
        print("✅ No priority words need translation!")
        return 0
    
    print(f"Translating {len(words_to_translate)} priority words (Level 1-3)...")
    
    translated = 0
    for i, word_data in enumerate(words_to_translate):
        word = word_data['word']
        reading = word_data['reading']
        pos = word_data['pos']
        level = word_data['level']
        lee_id = word_data['lee_id']
        
        print(f"[{i+1}/{len(words_to_translate)}] {word} ({reading}) [Level {level}]")
        
        # Create translation prompt
        prompt = f"""Translate this Japanese word to English. Provide a concise, accurate translation:

Japanese: {word}
Reading: {reading}
Part of Speech: {pos}
Level: {level}

Examples:
- 例の → "that, the aforementioned"
- あさって → "day after tomorrow"  
- 連体詞 → "adnominal"

Provide ONLY the English translation (1-4 words maximum):"""
        
        try:
            if provider == "gemini":
                response = enhancer.model.generate_content(prompt)
                translation = response.text.strip()
            elif provider == "openai":
                response = enhancer.client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.1,
                    max_tokens=30
                )
                translation = response.choices[0].message.content.strip()
            
            # Clean up translation
            translation = translation.replace('"', '').replace("'", "").strip()
            if ':' in translation:
                translation = translation.split(':')[-1].strip()
            
            # Update in database
            session.run("""
                MATCH (w:Word {source: 'LeeGoi', lee_id: $lee_id})
                SET w.translation = $translation,
                    w.updated_at = datetime(),
                    w.ai_translated = true
            """, lee_id=lee_id, translation=translation)
            
            translated += 1
            print(f"  → {translation}")
            
            # Rate limiting to be nice to the API
            time.sleep(0.5)
            
        except Exception as e:
            print(f"  ✗ Error: {e}")
    
    print(f"\n✓ Successfully translated {translated}/{len(words_to_translate)} words")
    return translated

def main():
    """Run batch translation for remaining words"""
    driver = GraphDatabase.driver(URI, auth=AUTH)
    
    try:
        with driver.session() as session:
            # Check current status
            result = session.run("""
                MATCH (w:Word)
                WHERE w.source = 'LeeGoi'
                AND (w.translation IS NULL OR w.translation = '')
                AND w.level_int <= 3
                RETURN count(w) as priority_missing
            """)
            
            priority_missing = result.single()['priority_missing']
            print(f"Priority words (Level 1-3) missing translations: {priority_missing:,}")
            
            if priority_missing == 0:
                print("✅ All priority words have translations!")
                return
            
            # Translate in batches
            total_translated = 0
            batch_size = 50
            
            while True:
                translated = batch_translate_priority_words(session, batch_size)
                total_translated += translated
                
                if translated == 0:
                    break
                
                print(f"\nBatch complete. Total translated so far: {total_translated}")
                
                # Check if we should continue
                if translated < batch_size:
                    break
                
                # Short break between batches
                print("Pausing 5 seconds before next batch...")
                time.sleep(5)
            
            print(f"\n✅ BATCH TRANSLATION COMPLETE!")
            print(f"Total words translated: {total_translated}")
            
            # Final status check
            result = session.run("""
                MATCH (w:Word)
                WHERE w.source = 'LeeGoi'
                RETURN count(w) as total,
                       sum(CASE WHEN w.translation IS NOT NULL AND w.translation <> '' THEN 1 ELSE 0 END) as with_translation
            """)
            
            stats = result.single()
            total = stats['total']
            with_translation = stats['with_translation']
            
            print(f"\nFinal status:")
            print(f"  LeeGoi words with translations: {with_translation:,} / {total:,} ({with_translation/total*100:.1f}%)")
            
    except Exception as e:
        print(f"\n❌ Error during batch translation: {e}")
        import traceback
        traceback.print_exc()
    finally:
        driver.close()

if __name__ == "__main__":
    main()
