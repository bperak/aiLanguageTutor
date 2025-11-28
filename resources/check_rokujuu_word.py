#!/usr/bin/env python3
"""
Check the specific word '六十路' to see what romaji was generated
"""

import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv
from neo4j import GraphDatabase

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

def check_rokujuu_word(driver):
    """Check the specific word '六十路'"""
    with driver.session() as session:
        # Check the specific word
        result = session.run("""
            MATCH (w:Word)
            WHERE w.lemma = '六十路' OR w.kanji = '六十路' OR w.hiragana = 'ろくじゅうじ'
            RETURN w.lemma, w.kanji, w.hiragana, w.romaji, w.vdrj_standard_reading
            LIMIT 5
        """)
        
        logger.info("Checking word '六十路' (ろくじゅうじ):")
        logger.info("=" * 50)
        
        found = False
        for record in result:
            found = True
            print(f"Lemma: {record['w.lemma']}")
            print(f"Kanji: {record['w.kanji']}")
            print(f"Hiragana: {record['w.hiragana']}")
            print(f"Romaji: {record['w.romaji']}")
            print(f"Romaji (repr): {repr(record['w.romaji'])}")  # Show exact characters
            print(f"VDRJ katakana: {record['w.vdrj_standard_reading']}")
            print("---")
        
        if not found:
            logger.info("Word '六十路' not found in database")
            
            # Check for similar words
            result2 = session.run("""
                MATCH (w:Word)
                WHERE w.hiragana CONTAINS 'ろく' OR w.romaji CONTAINS 'roku' OR w.romaji CONTAINS 'Roku'
                RETURN w.lemma, w.kanji, w.hiragana, w.romaji
                LIMIT 10
            """)
            
            logger.info("\nSimilar words found:")
            for record in result2:
                print(f"Lemma: {record['w.lemma']}, Kanji: {record['w.kanji']}, Hiragana: {record['w.hiragana']}, Romaji: {repr(record['w.romaji'])}")

def test_cutlet_rokujuu():
    """Test cutlet with the specific word"""
    import cutlet
    
    print("\nTesting cutlet with 'ろくじゅうじ':")
    print("=" * 50)
    
    katsu = cutlet.Cutlet()
    katsu.use_foreign_spelling = False
    katsu.use_wa = True
    test_text = 'ろくじゅうじ'
    
    result = katsu.romaji(test_text)
    print(f"Cutlet result: '{test_text}' -> '{result}'")
    print(f"Cutlet result (repr): {repr(result)}")
    
    # Test if there are any spaces
    if ' ' in result:
        print("⚠️  WARNING: Result contains spaces!")
    else:
        print("✅ No spaces in result")

def main():
    """Main function"""
    print("Checking '六十路' word in database")
    print("=" * 60)
    
    # Test cutlet first
    test_cutlet_rokujuu()
    
    # Check database
    driver = load_environment()
    if driver:
        try:
            check_rokujuu_word(driver)
        finally:
            driver.close()
    else:
        print("Cannot connect to database")

if __name__ == "__main__":
    main()


