#!/usr/bin/env python
"""Fix specific words or groups of words that need translations"""

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

def fix_specific_words(session, word_list):
    """Fix translations for specific words provided as a list"""
    print("=" * 80)
    print("FIXING SPECIFIC WORD TRANSLATIONS")
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
    
    translated = 0
    for word in word_list:
        print(f"\nProcessing word: {word}")
        
        # Get word details
        result = session.run("""
            MATCH (w:Word {lemma: $word, source: 'LeeGoi'})
            RETURN w.lemma as word, w.reading as reading, w.pos as pos, 
                   w.level_int as level, w.lee_id as lee_id,
                   w.translation as current_translation
        """, word=word)
        
        word_data = result.single()
        if not word_data:
            print(f"  ⚠️ Word '{word}' not found in LeeGoi")
            continue
        
        current_translation = word_data['current_translation']
        if current_translation and current_translation.strip():
            print(f"  ℹ️ Word already has translation: {current_translation}")
            continue
        
        reading = word_data['reading']
        pos = word_data['pos']
        level = word_data['level']
        lee_id = word_data['lee_id']
        
        print(f"  Details: {reading} [{pos}] Level {level}")
        
        # Create translation prompt
        prompt = f"""Translate this Japanese word to English. Provide a concise, accurate translation:

Japanese: {word}
Reading: {reading}
Part of Speech: {pos}
Level: {level}

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
            print(f"  ✓ Translated: {word} → {translation}")
            
            # Rate limiting
            time.sleep(0.5)
            
        except Exception as e:
            print(f"  ✗ Error translating '{word}': {e}")
    
    return translated

def fix_manual_translations(session, manual_translations):
    """Fix translations using manual dictionary"""
    print("=" * 80)
    print("APPLYING MANUAL TRANSLATIONS")
    print("=" * 80)
    
    updated = 0
    for word, translation in manual_translations.items():
        result = session.run("""
            MATCH (w:Word {lemma: $word, source: 'LeeGoi'})
            SET w.translation = $translation,
                w.updated_at = datetime(),
                w.manually_translated = true
            RETURN w.lemma as word
        """, word=word, translation=translation)
        
        if result.single():
            print(f"  ✓ {word} → {translation}")
            updated += 1
        else:
            print(f"  ⚠️ Word '{word}' not found")
    
    return updated

def main():
    """Fix specific translations"""
    driver = GraphDatabase.driver(URI, auth=AUTH)
    
    try:
        with driver.session() as session:
            print("Choose translation method:")
            print("1. AI translate specific words")
            print("2. Apply manual translations")
            print("3. Both")
            
            # Example usage - you can modify these lists
            specific_words_to_fix = [
                "例の",  # The word you mentioned
                "連体詞", # Part of speech terms
                "混種語", # Word type terms
                "和語",   # More word type terms
            ]
            
            # Manual translations for technical terms
            manual_translations = {
                "連体詞": "adnominal",
                "混種語": "hybrid word", 
                "和語": "native Japanese word",
                "漢語": "Chinese-origin word",
                "外来語": "loanword",
                "名詞": "noun",
                "動詞": "verb",
                "形容詞": "adjective",
                "副詞": "adverb",
            }
            
            # Method 1: AI translate specific words
            if specific_words_to_fix:
                ai_translated = fix_specific_words(session, specific_words_to_fix)
                print(f"\nAI translated: {ai_translated} words")
            
            # Method 2: Apply manual translations
            if manual_translations:
                manual_updated = fix_manual_translations(session, manual_translations)
                print(f"\nManual translations applied: {manual_updated} words")
            
            print(f"\n✅ SPECIFIC TRANSLATION FIX COMPLETE!")
            
    except Exception as e:
        print(f"\n❌ Error during specific translation fix: {e}")
        import traceback
        traceback.print_exc()
    finally:
        driver.close()

if __name__ == "__main__":
    main()
