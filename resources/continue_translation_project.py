#!/usr/bin/env python
"""Master script to continue the translation project with different strategies"""

from neo4j import GraphDatabase
import os
from dotenv import load_dotenv
from pathlib import Path
import subprocess
import sys

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

def show_menu():
    """Show the main menu"""
    print("=" * 80)
    print("TRANSLATION PROJECT CONTINUATION MENU")
    print("=" * 80)
    print("1. Check current translation status")
    print("2. Continue batch translation (Level 1-3 priority)")
    print("3. Fix specific words")
    print("4. Translate by part of speech")
    print("5. Use original Lee TSV file (if available)")
    print("6. Exit")
    print("-" * 80)

def check_api_availability():
    """Check if AI APIs are available"""
    gemini_key = os.getenv('GEMINI_API_KEY')
    openai_key = os.getenv('OPENAI_API_KEY')
    
    if gemini_key:
        return True, "gemini"
    elif openai_key:
        return True, "openai"
    else:
        return False, None

def run_script(script_name):
    """Run another Python script"""
    try:
        result = subprocess.run([sys.executable, script_name], 
                              capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print("Errors:", result.stderr)
        return result.returncode == 0
    except Exception as e:
        print(f"Error running {script_name}: {e}")
        return False

def translate_by_pos(session, pos_filter, limit=100):
    """Translate words by part of speech"""
    print(f"=" * 80)
    print(f"TRANSLATING WORDS BY PART OF SPEECH: {pos_filter}")
    print(f"=" * 80)
    
    # Check if AI is available
    api_available, provider = check_api_availability()
    if not api_available:
        print("⚠️ No AI API keys available")
        return 0
    
    try:
        from ai_synonym_enhancer import AISynonymEnhancer
        enhancer = AISynonymEnhancer(provider)
        print(f"Using {provider.upper()} for translation")
        
    except Exception as e:
        print(f"⚠️ AI not available: {e}")
        return 0
    
    # Get words of specific POS missing translations
    result = session.run("""
        MATCH (w:Word)
        WHERE w.source = 'LeeGoi'
          AND (w.translation IS NULL OR w.translation = '')
          AND coalesce(w.pos, w.pos_primary) CONTAINS $pos_filter
        RETURN coalesce(w.standard_orthography, w.lemma) AS word,
               coalesce(w.reading_hiragana, '') AS reading,
               coalesce(w.pos, w.pos_primary) AS pos,
               w.level_int AS level,
               w.lee_id AS lee_id
        ORDER BY w.level_int ASC, word
        LIMIT $limit
    """, pos_filter=pos_filter, limit=limit)
    
    words = [dict(record) for record in result]
    
    if not words:
        print(f"✅ No {pos_filter} words need translation!")
        return 0
    
    print(f"Translating {len(words)} {pos_filter} words...")
    
    translated = 0
    for word_data in words:
        word = word_data['word']
        reading = word_data['reading']
        pos = word_data['pos']
        level = word_data['level']
        lee_id = word_data['lee_id']
        
        print(f"{word} ({reading}) [{pos}] Level {level}")
        
        # Create translation prompt
        prompt = f"""Translate this Japanese {pos_filter}:

Japanese: {word}
Reading: {reading}
Part of Speech: {pos}

Provide ONLY the English translation:"""
        
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
            
            import time
            time.sleep(0.5)
            
        except Exception as e:
            print(f"  ✗ Error: {e}")
    
    print(f"\n✓ Translated {translated}/{len(words)} {pos_filter} words")
    return translated

def main():
    """Main menu loop"""
    driver = GraphDatabase.driver(URI, auth=AUTH)
    
    try:
        while True:
            show_menu()
            choice = input("Enter your choice (1-6): ").strip()
            
            if choice == '1':
                print("\n" + "="*80)
                run_script("check_translation_status.py")
                
            elif choice == '2':
                print("\n" + "="*80)
                run_script("batch_translate_remaining.py")
                
            elif choice == '3':
                print("\n" + "="*80)
                run_script("fix_specific_translations.py")
                
            elif choice == '4':
                print("\n" + "="*80)
                print("Available parts of speech to focus on:")
                print("1. 名詞 (nouns)")
                print("2. 動詞 (verbs)")
                print("3. 形容詞 (adjectives)")
                print("4. 副詞 (adverbs)")
                print("5. Custom POS")
                
                pos_choice = input("Choose POS (1-5): ").strip()
                pos_map = {
                    '1': '名詞',
                    '2': '動詞', 
                    '3': '形容詞',
                    '4': '副詞'
                }
                
                if pos_choice in pos_map:
                    pos_filter = pos_map[pos_choice]
                elif pos_choice == '5':
                    pos_filter = input("Enter custom POS to filter: ").strip()
                else:
                    print("Invalid choice")
                    continue
                
                limit = int(input("How many words to translate (default 50): ") or "50")
                
                with driver.session() as session:
                    translate_by_pos(session, pos_filter, limit)
                
            elif choice == '5':
                print("\n" + "="*80)
                print("Checking Lee TSV file for translations...")
                
                # Check if TSV has translation columns
                try:
                    import pandas as pd
                    df = pd.read_csv('Lee李  分類語彙表学習者用goi.xlsx - Sheet1.tsv', sep='\t')
                    translation_cols = [col for col in df.columns if 'translation' in col.lower() or 'english' in col.lower()]
                    
                    if translation_cols:
                        print(f"Found translation columns: {translation_cols}")
                        print("This feature needs to be implemented based on your TSV structure")
                    else:
                        print("No translation columns found in TSV file")
                        print("Available columns:", list(df.columns)[:10])
                        
                except Exception as e:
                    print(f"Error reading TSV: {e}")
                
            elif choice == '6':
                print("Exiting...")
                break
                
            else:
                print("Invalid choice. Please try again.")
            
            input("\nPress Enter to continue...")
            
    except KeyboardInterrupt:
        print("\n\nExiting...")
    finally:
        driver.close()

if __name__ == "__main__":
    main()
