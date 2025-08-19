#!/usr/bin/env python
"""Extract Japanese synonyms from BabelNet API and integrate into Neo4j"""
import requests
import json
import time
from pathlib import Path
from neo4j import GraphDatabase  # type: ignore
from dotenv import load_dotenv
import os

# Load environment variables
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

# BabelNet API configuration
BABELNET_API_KEY = os.getenv("BABELNET_API_KEY")  # Add to your .env file
BASE_URL = "https://babelnet.io/v9"

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

class BabelNetSynonymExtractor:
    def __init__(self, api_key):
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({'Accept-encoding': 'gzip'})
        
    def get_synsets_for_word(self, word, lang='JA'):
        """Get BabelNet synsets for a Japanese word"""
        url = f"{BASE_URL}/getSynsetIds"
        params = {
            'lemma': word,
            'searchLang': lang,
            'key': self.api_key
        }
        
        try:
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Error fetching synsets for '{word}': {e}")
            return []
    
    def get_synset_details(self, synset_id, target_lang='JA'):
        """Get detailed information about a synset"""
        url = f"{BASE_URL}/getSynset"
        params = {
            'id': synset_id,
            'targetLang': target_lang,
            'key': self.api_key
        }
        
        try:
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Error fetching synset details for '{synset_id}': {e}")
            return None
    
    def extract_japanese_synonyms(self, word):
        """Extract Japanese synonyms for a given word"""
        print(f"Processing word: {word}")
        
        # Get synsets
        synsets = self.get_synsets_for_word(word)
        if not synsets:
            return []
        
        all_synonyms = []
        
        for synset_info in synsets:
            synset_id = synset_info.get('id')
            if not synset_id:
                continue
                
            # Get synset details
            synset_data = self.get_synset_details(synset_id)
            if not synset_data:
                continue
            
            # Extract Japanese senses (synonyms)
            senses = synset_data.get('senses', [])
            japanese_senses = [
                sense for sense in senses 
                if sense.get('language') == 'JA' and sense.get('lemma') != word
            ]
            
            for sense in japanese_senses:
                synonym_data = {
                    'word': word,
                    'synonym': sense.get('lemma'),
                    'synset_id': synset_id,
                    'pos': sense.get('pos'),
                    'source': sense.get('source'),
                    'sense_key': sense.get('senseKey'),
                    'frequency': sense.get('frequency', 0)
                }
                all_synonyms.append(synonym_data)
            
            # Rate limiting - BabelNet has API limits
            time.sleep(0.1)
        
        return all_synonyms

def get_sample_japanese_words(session, limit=100):
    """Get a sample of Japanese words from Neo4j to test BabelNet"""
    result = session.run("""
        MATCH (w:Word)
        WHERE w.kanji IS NOT NULL 
        AND w.source = 'LeeGoi'
        RETURN w.kanji as word
        ORDER BY rand()
        LIMIT $limit
    """, limit=limit)
    
    return [record['word'] for record in result]

def store_babelnet_synonyms(session, synonyms_data):
    """Store BabelNet synonyms as relationships in Neo4j"""
    if not synonyms_data:
        return 0
    
    # Create relationships in batches
    batch_size = 100
    created = 0
    
    for i in range(0, len(synonyms_data), batch_size):
        batch = synonyms_data[i:i+batch_size]
        
        result = session.run("""
            UNWIND $batch as syn
            MATCH (w1:Word {kanji: syn.word})
            MATCH (w2:Word {kanji: syn.synonym})
            WHERE w1 <> w2
            MERGE (w1)-[r:SYNONYM_OF {source: 'BabelNet'}]->(w2)
            SET r.synset_id = syn.synset_id,
                r.babelnet_pos = syn.pos,
                r.babelnet_source = syn.source,
                r.sense_key = syn.sense_key,
                r.frequency = syn.frequency,
                r.relation_type = 'BabelNet_Synonym'
            RETURN count(r) as created_count
        """, batch=batch)
        
        stats = result.single()
        created += stats['created_count'] if stats else 0
    
    return created

def main():
    """Main function to extract BabelNet synonyms"""
    if not BABELNET_API_KEY:
        print("ERROR: BABELNET_API_KEY not found in .env file")
        print("Please sign up at https://babelnet.org/ and add your API key to .env")
        return
    
    print("=" * 60)
    print("BABELNET JAPANESE SYNONYM EXTRACTION")
    print("=" * 60)
    
    extractor = BabelNetSynonymExtractor(BABELNET_API_KEY)
    
    with driver.session() as session:
        # Get sample words to test
        print("Getting sample Japanese words from Neo4j...")
        sample_words = get_sample_japanese_words(session, limit=50)  # Start small
        print(f"Found {len(sample_words)} words to process")
        
        all_synonyms = []
        processed = 0
        
        for word in sample_words:
            try:
                synonyms = extractor.extract_japanese_synonyms(word)
                all_synonyms.extend(synonyms)
                processed += 1
                
                if processed % 10 == 0:
                    print(f"Processed {processed}/{len(sample_words)} words, found {len(all_synonyms)} synonym pairs")
                
                # Rate limiting
                time.sleep(0.5)
                
            except Exception as e:
                print(f"Error processing word '{word}': {e}")
                continue
        
        print(f"\nTotal synonym pairs found: {len(all_synonyms)}")
        
        if all_synonyms:
            print("Storing synonyms in Neo4j...")
            created = store_babelnet_synonyms(session, all_synonyms)
            print(f"✓ Created {created} new BabelNet synonym relationships")
        
        # Show sample results
        print("\nSample BabelNet synonyms:")
        result = session.run("""
            MATCH (w1)-[r:SYNONYM_OF {source: 'BabelNet'}]->(w2)
            RETURN w1.kanji as word1, w2.kanji as word2, 
                   r.babelnet_pos as pos, r.babelnet_source as source
            LIMIT 10
        """)
        
        for record in result:
            print(f"  {record['word1']} ↔ {record['word2']} ({record['pos']}) [{record['source']}]")
    
    driver.close()

if __name__ == "__main__":
    main()
