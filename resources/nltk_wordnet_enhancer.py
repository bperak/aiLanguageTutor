#!/usr/bin/env python
"""Enhance Japanese synonyms using NLTK WordNet and multilingual mappings"""
import os
from pathlib import Path
from neo4j import GraphDatabase  # type: ignore
from dotenv import load_dotenv
import nltk
from nltk.corpus import wordnet as wn
import requests
import time

# Load environment variables
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

# Neo4j connection
URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
if URI.startswith("neo4j://neo4j:"):
    URI = URI.replace("neo4j://neo4j:", "bolt://localhost:")
elif URI.startswith("neo4j://"):
    URI = URI.replace("neo4j://", "bolt://")
USER = os.getenv("NEO4J_USER", "neo4j")
PASSWORD = os.getenv("NEO4J_PASSWORD")
AUTH = (USER, PASSWORD)

driver = GraphDatabase.driver(URI, auth=AUTH)

def ensure_nltk_data():
    """Download required NLTK data"""
    try:
        nltk.data.find('corpora/wordnet')
        nltk.data.find('corpora/omw-1.4')  # Open Multilingual WordNet
    except LookupError:
        print("Downloading NLTK WordNet data...")
        nltk.download('wordnet')
        nltk.download('omw-1.4')  # Multilingual WordNet including Japanese
        print("NLTK data downloaded successfully!")

class WordNetSynonymExtractor:
    def __init__(self):
        ensure_nltk_data()
    
    def get_english_synonyms(self, english_word, pos_filter=None):
        """Get English synonyms from WordNet"""
        synonyms = set()
        
        # Get synsets for the word
        synsets = wn.synsets(english_word, pos=pos_filter)
        
        for synset in synsets:
            # Get all lemmas in the synset (these are synonyms)
            for lemma in synset.lemmas():
                synonym = lemma.name().replace('_', ' ')
                if synonym.lower() != english_word.lower():
                    synonyms.add(synonym)
        
        return list(synonyms)
    
    def get_multilingual_synonyms(self, english_word, target_lang='jpn'):
        """Get synonyms in target language using WordNet multilingual mappings"""
        synonyms = set()
        
        synsets = wn.synsets(english_word)
        
        for synset in synsets:
            # Get lemmas in target language
            target_lemmas = synset.lemmas(lang=target_lang)
            for lemma in target_lemmas:
                synonym = lemma.name().replace('_', ' ')
                synonyms.add(synonym)
        
        return list(synonyms)

def translate_via_api(text, target_lang='ja'):
    """Simple translation using a free API (example with MyMemory)"""
    try:
        url = "https://api.mymemory.translated.net/get"
        params = {
            'q': text,
            'langpair': f'en|{target_lang}'
        }
        
        response = requests.get(url, params=params, timeout=5)
        data = response.json()
        
        if data.get('responseStatus') == 200:
            return data.get('responseData', {}).get('translatedText')
    except Exception as e:
        print(f"Translation error for '{text}': {e}")
    
    return None

def enhance_via_wordnet(session):
    """Enhance synonyms using WordNet and translation"""
    print("=" * 60)
    print("WORDNET SYNONYM ENHANCEMENT")
    print("=" * 60)
    
    extractor = WordNetSynonymExtractor()
    
    # Get words with English translations but few synonyms
    result = session.run("""
        MATCH (w:Word)
        WHERE w.translation IS NOT NULL 
        AND w.source = 'LeeGoi'
        WITH w, size((w)-[:SYNONYM_OF]-()) as syn_count
        WHERE syn_count < 5
        RETURN w.kanji as word, w.translation as translation,
               w.hiragana as reading, w.pos as pos, syn_count
        ORDER BY syn_count ASC
        LIMIT 50
    """)
    
    words_to_enhance = [dict(record) for record in result]
    print(f"Found {len(words_to_enhance)} words to enhance via WordNet")
    
    total_created = 0
    
    for word_data in words_to_enhance:
        word = word_data['word']
        translation = word_data['translation']
        
        if not translation:
            continue
        
        print(f"Processing: {word} → {translation}")
        
        # Get English synonyms
        english_synonyms = extractor.get_english_synonyms(translation.lower())
        
        if english_synonyms:
            print(f"  Found {len(english_synonyms)} English synonyms: {english_synonyms[:3]}...")
            
            # Try to find Japanese equivalents in our database
            for eng_syn in english_synonyms[:5]:  # Limit to top 5
                # Look for Japanese words with this English translation
                result = session.run("""
                    MATCH (w:Word)
                    WHERE toLower(w.translation) = toLower($eng_translation)
                    AND w.kanji <> $original_word
                    RETURN w.kanji as synonym, w.hiragana as reading
                    LIMIT 3
                """, eng_translation=eng_syn, original_word=word)
                
                for record in result:
                    synonym = record['synonym']
                    
                    # Create synonym relationship
                    create_result = session.run("""
                        MATCH (w1:Word {kanji: $word})
                        MATCH (w2:Word {kanji: $synonym})
                        WHERE w1 <> w2
                        MERGE (w1)-[r:SYNONYM_OF {source: 'WordNet_Translation'}]->(w2)
                        SET r.english_bridge = $english_word,
                        r.method = 'translation_bridge',
                        r.strength = 0.7,
                        r.created_at = datetime()
                        RETURN count(r) as created_count
                    """, word=word, synonym=synonym, english_word=eng_syn)
                    
                    stats = create_result.single()
                    if stats and stats['created_count'] > 0:
                        total_created += stats['created_count']
                        print(f"    → {word} ↔ {synonym} (via {eng_syn})")
        
        # Rate limiting
        time.sleep(0.5)
    
    print(f"\n✓ WordNet enhancement complete: {total_created} new synonym relationships")
    return total_created

def verify_wordnet_synonyms(session):
    """Verify WordNet-derived synonyms"""
    print("\n" + "=" * 60)
    print("WORDNET SYNONYM VERIFICATION")
    print("=" * 60)
    
    result = session.run("""
        MATCH ()-[r:SYNONYM_OF {source: 'WordNet_Translation'}]->()
        RETURN count(r) as count
    """)
    
    count = result.single()['count']
    print(f"WordNet-derived synonyms: {count}")
    
    if count > 0:
        result = session.run("""
            MATCH (w1)-[r:SYNONYM_OF {source: 'WordNet_Translation'}]->(w2)
            RETURN w1.kanji as word1, w2.kanji as word2,
                   r.english_bridge as bridge, r.strength as strength
            LIMIT 10
        """)
        
        print("\nSample WordNet-derived synonyms:")
        for record in result:
            print(f"  {record['word1']} ↔ {record['word2']} (via '{record['bridge']}')")

def main():
    """Main function to enhance synonyms using multiple methods"""
    
    print("=" * 60)
    print("SYNONYM NETWORK ENHANCEMENT")
    print("=" * 60)
    print(f"Available methods:")
    print(f"  1. WordNet + Translation Bridge")
    if GEMINI_API_KEY:
        print(f"  2. Gemini AI Generation")
    if OPENAI_API_KEY:
        print(f"  3. OpenAI AI Generation")
    
    with driver.session() as session:
        # Method 1: WordNet enhancement
        wordnet_created = enhance_via_wordnet(session)
        verify_wordnet_synonyms(session)
        
        # Method 2: AI enhancement (if API keys available)
        if GEMINI_API_KEY or OPENAI_API_KEY:
            try:
                from ai_synonym_enhancer import AISynonymEnhancer, enhance_synonyms_with_ai, verify_ai_synonyms
                
                enhancer = AISynonymEnhancer(AI_PROVIDER)
                ai_created = enhance_synonyms_with_ai(session, enhancer, batch_size=10)
                verify_ai_synonyms(session)
                
                print(f"\n✅ Total enhancement complete!")
                print(f"  WordNet method: {wordnet_created} synonyms")
                print(f"  AI method: {ai_created} synonyms")
                
            except Exception as e:
                print(f"AI enhancement skipped: {e}")
                print(f"Only WordNet enhancement completed: {wordnet_created} synonyms")
        else:
            print(f"\n✅ WordNet enhancement complete: {wordnet_created} synonyms")
            print("Add GEMINI_API_KEY or OPENAI_API_KEY to .env for AI enhancement")
    
    driver.close()

if __name__ == "__main__":
    main()
