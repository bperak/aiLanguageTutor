#!/usr/bin/env python3
"""
Verify that all words in the database are from the Lee李 classification vocabulary list
and that all attributes are correctly imported
"""

import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv
from neo4j import GraphDatabase
import csv

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def load_environment():
    """Load environment variables and setup Neo4j connection"""
    env_path = Path(__file__).parent.parent / '.env'
    load_dotenv(env_path)
    
    URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    USER = os.getenv("NEO4J_USERNAME", "neo4j")
    PASSWORD = "testpassword123"
    
    if URI.startswith("neo4j://"):
        URI = URI.replace("neo4j://", "bolt://localhost:")
    
    try:
        driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))
        with driver.session() as session:
            result = session.run("RETURN 'Connection successful' as status")
            status = result.single()['status']
            logger.info(f"✅ {status}")
        return driver
    except Exception as e:
        logger.error(f"❌ Connection failed: {e}")
        return None

def load_lee_vocabulary():
    """Load the Lee李 vocabulary list"""
    lee_file = Path(__file__).parent / "Lee李  分類語彙表学習者用goi.xlsx - Sheet1.tsv"
    
    lee_words = {}
    lee_attributes = {}
    
    logger.info(f"Loading Lee李 vocabulary from: {lee_file}")
    
    with open(lee_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter='\t')
        
        for row in reader:
            # Get the key fields
            no = row.get('No', '').strip()
            kanji = row.get('Standard orthography (kanji or other) 標準的な表記', '').strip()
            katakana = row.get('Katakana reading 読み', '').strip()
            level = row.get('Level 語彙の難易度', '').strip()
            pos1 = row.get('品詞1', '').strip()
            pos2 = row.get('品詞2(詳細)', '').strip()
            word_type = row.get('語種', '').strip()
            
            if kanji and katakana:
                # Store word data
                lee_words[kanji] = {
                    'no': no,
                    'kanji': kanji,
                    'katakana': katakana,
                    'level': level,
                    'pos1': pos1,
                    'pos2': pos2,
                    'word_type': word_type
                }
                
                # Also store by katakana for lookup
                lee_words[katakana] = lee_words[kanji]
    
    logger.info(f"Loaded {len(lee_words)} unique words from Lee李 vocabulary")
    return lee_words

def check_database_words(driver, lee_words):
    """Check all words in the database against Lee李 vocabulary"""
    
    with driver.session() as session:
        # Get total count of words in database
        result = session.run("MATCH (w:Word) RETURN count(w) as total")
        total_db_words = result.single()['total']
        logger.info(f"Total words in database: {total_db_words}")
        
        # Get all words from database
        result = session.run("""
            MATCH (w:Word)
            RETURN w.lemma, w.kanji, w.hiragana, w.romaji, w.vdrj_standard_reading
            ORDER BY w.kanji
        """)
        
        db_words = list(result)
        logger.info(f"Retrieved {len(db_words)} words from database")
        
        # Check each word
        found_in_lee = 0
        not_found_in_lee = 0
        missing_attributes = 0
        
        lee_not_in_db = set(lee_words.keys())
        
        logger.info("\nChecking words against Lee李 vocabulary:")
        logger.info("=" * 60)
        
        for record in db_words:
            lemma = record['w.lemma']
            kanji = record['w.kanji']
            hiragana = record['w.hiragana']
            romaji = record['w.romaji']
            vdrj_katakana = record['w.vdrj_standard_reading']
            
            # Check if word exists in Lee李 vocabulary
            found = False
            lee_data = None
            
            # Try to find by kanji first
            if kanji and kanji in lee_words:
                found = True
                lee_data = lee_words[kanji]
                lee_not_in_db.discard(kanji)
            # Try to find by katakana
            elif vdrj_katakana and vdrj_katakana in lee_words:
                found = True
                lee_data = lee_words[vdrj_katakana]
                lee_not_in_db.discard(vdrj_katakana)
            # Try to find by hiragana
            elif hiragana and hiragana in lee_words:
                found = True
                lee_data = lee_words[hiragana]
                lee_not_in_db.discard(hiragana)
            
            if found:
                found_in_lee += 1
                # Check if attributes are properly imported
                if not lee_data:
                    missing_attributes += 1
                    logger.warning(f"  ⚠️  {kanji} - Found in Lee李 but no data")
            else:
                not_found_in_lee += 1
                logger.warning(f"  ❌ {kanji} ({hiragana}) - NOT FOUND in Lee李 vocabulary")
        
        # Summary
        logger.info("\n" + "=" * 60)
        logger.info("VERIFICATION SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Total words in database: {total_db_words}")
        logger.info(f"Words found in Lee李: {found_in_lee}")
        logger.info(f"Words NOT found in Lee李: {not_found_in_lee}")
        logger.info(f"Words with missing attributes: {missing_attributes}")
        logger.info(f"Lee李 words not in database: {len(lee_not_in_db)}")
        
        if not_found_in_lee > 0:
            logger.warning(f"⚠️  {not_found_in_lee} words in database are NOT in Lee李 vocabulary!")
        
        if len(lee_not_in_db) > 0:
            logger.info(f"\nFirst 10 Lee李 words not in database:")
            for i, word in enumerate(sorted(lee_not_in_db)[:10]):
                logger.info(f"  {i+1}. {word}")
        
        return {
            'total_db_words': total_db_words,
            'found_in_lee': found_in_lee,
            'not_found_in_lee': not_found_in_lee,
            'missing_attributes': missing_attributes,
            'lee_not_in_db': len(lee_not_in_db)
        }

def check_specific_examples(driver, lee_words):
    """Check specific examples to verify attribute import"""
    
    with driver.session() as session:
        logger.info("\nChecking specific examples:")
        logger.info("=" * 60)
        
        # Check a few specific words
        test_words = ['愛', 'アイス', '挨拶', '相手', '愛国心']
        
        for word in test_words:
            if word in lee_words:
                lee_data = lee_words[word]
                logger.info(f"\nWord: {word}")
                logger.info(f"Lee李 data: {lee_data}")
                
                # Find in database
                result = session.run("""
                    MATCH (w:Word)
                    WHERE w.kanji = $word OR w.lemma = $word
                    RETURN w.lemma, w.kanji, w.hiragana, w.romaji, w.vdrj_standard_reading
                    LIMIT 1
                """, {'word': word})
                
                for record in result:
                    logger.info(f"Database: {dict(record)}")
                    break
                else:
                    logger.warning(f"  ❌ {word} not found in database")

def main():
    """Main function"""
    logger.info("=" * 80)
    logger.info("VERIFYING LEE李 VOCABULARY IMPORT")
    logger.info("=" * 80)
    
    # Load Lee李 vocabulary
    lee_words = load_lee_vocabulary()
    
    # Connect to database
    driver = load_environment()
    if not driver:
        logger.error("Cannot connect to database")
        return
    
    try:
        # Check database words
        results = check_database_words(driver, lee_words)
        
        # Check specific examples
        check_specific_examples(driver, lee_words)
        
        # Final summary
        logger.info("\n" + "=" * 80)
        logger.info("FINAL VERIFICATION RESULTS")
        logger.info("=" * 80)
        
        if results['not_found_in_lee'] == 0:
            logger.info("✅ ALL words in database are from Lee李 vocabulary!")
        else:
            logger.warning(f"⚠️  {results['not_found_in_lee']} words in database are NOT from Lee李 vocabulary")
        
        if results['lee_not_in_db'] == 0:
            logger.info("✅ ALL Lee李 words are in database!")
        else:
            logger.info(f"ℹ️  {results['lee_not_in_db']} Lee李 words are not in database (this may be normal)")
        
        logger.info("=" * 80)
        
    finally:
        driver.close()

if __name__ == "__main__":
    main()


