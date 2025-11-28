#!/usr/bin/env python3
"""
Verify the results of the comprehensive transliteration
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

def test_cutlet_configuration():
    """Test cutlet configuration"""
    import cutlet
    
    logger.info("Testing cutlet configuration:")
    logger.info("=" * 50)
    
    katsu = cutlet.Cutlet()
    katsu.use_foreign_spelling = False
    katsu.use_wa = True
    
    test_cases = [
        ('いいえ', 'hiragana'),
        ('イイエ', 'katakana'),
        ('こんにちは', 'hiragana'),
        ('数多', 'kanji'),
        ('は', 'particle'),
        ('こんばんは', 'hiragana')
    ]
    
    for test_text, test_type in test_cases:
        result = katsu.romaji(test_text)
        logger.info(f"  {test_text} ({test_type}) -> {result}")

def check_specific_words(driver):
    """Check specific words in the database"""
    
    test_words = [
        ('いいえ', 'Iie'),
        ('こんにちは', 'Konnichiwa'),
        ('こんばんは', 'Konbanwa'),
        ('数多', 'Amata'),
        ('は', 'wa')
    ]
    
    with driver.session() as session:
        logger.info("\nChecking specific words in database:")
        logger.info("=" * 50)
        
        for word, expected in test_words:
            result = session.run("""
                MATCH (w:Word)
                WHERE w.lemma = $word OR w.kanji = $word OR w.hiragana = $word
                RETURN w.lemma, w.kanji, w.hiragana, w.romaji, w.vdrj_standard_reading
                LIMIT 3
            """, {'word': word})
            
            logger.info(f"\nWord: {word} (expected: {expected})")
            found = False
            for record in result:
                found = True
                lemma = record['w.lemma']
                kanji = record['w.kanji']
                hiragana = record['w.hiragana']
                romaji = record['w.romaji']
                katakana = record['w.vdrj_standard_reading']
                
                status = "✅" if romaji == expected else "❌"
                logger.info(f"  {status} {lemma} ({kanji}) - {hiragana} -> {romaji} (VDRJ: {katakana})")
            
            if not found:
                logger.info(f"  ❌ Word '{word}' not found in database")

def check_spacing_issues(driver):
    """Check for remaining spacing issues"""
    
    with driver.session() as session:
        logger.info("\nChecking for remaining spacing issues:")
        logger.info("=" * 50)
        
        # Look for romaji with spaces
        result = session.run("""
            MATCH (w:Word)
            WHERE w.romaji CONTAINS ' '
            RETURN w.lemma, w.kanji, w.hiragana, w.romaji, w.vdrj_standard_reading
            LIMIT 10
        """)
        
        count = 0
        for record in result:
            count += 1
            lemma = record['w.lemma']
            kanji = record['w.kanji']
            hiragana = record['w.hiragana']
            romaji = record['w.romaji']
            katakana = record['w.vdrj_standard_reading']
            
            logger.info(f"  {lemma} ({kanji}) - {hiragana} -> {romaji} (VDRJ: {katakana})")
        
        if count == 0:
            logger.info("  ✅ No spacing issues found!")
        else:
            logger.info(f"  Found {count} words with spaces in romaji")

def main():
    """Main function"""
    logger.info("=" * 80)
    logger.info("VERIFYING TRANSLITERATION RESULTS")
    logger.info("=" * 80)
    
    # Test cutlet configuration
    test_cutlet_configuration()
    
    # Connect to database
    driver = load_environment()
    if not driver:
        logger.error("Cannot connect to database")
        return
    
    try:
        # Check specific words
        check_specific_words(driver)
        
        # Check for spacing issues
        check_spacing_issues(driver)
        
    finally:
        driver.close()

if __name__ == "__main__":
    main()


