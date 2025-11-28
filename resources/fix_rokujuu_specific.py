#!/usr/bin/env python3
"""
Fix the specific '六十路' case: "Roku juu ji" -> "Musoji"
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

def fix_rokujuu_specific(driver):
    """Fix the specific '六十路' case"""
    
    with driver.session() as session:
        # Find the specific word with "Roku juu ji" romaji
        result = session.run("""
            MATCH (w:Word)
            WHERE w.romaji = 'Roku juu ji' AND w.kanji = '六十路'
            RETURN id(w) as word_id, w.lemma, w.kanji, w.hiragana, w.romaji, w.vdrj_standard_reading
        """)
        
        logger.info("Fixing specific '六十路' case:")
        logger.info("=" * 50)
        
        fixed_count = 0
        for record in result:
            word_id = record['word_id']
            lemma = record['w.lemma']
            kanji = record['w.kanji']
            hiragana = record['w.hiragana']
            current_romaji = record['w.romaji']
            katakana = record['w.vdrj_standard_reading']
            
            logger.info(f"Found: {lemma} ({kanji}) - {hiragana} -> {current_romaji} (VDRJ: {katakana})")
            
            # Fix the romaji - use the VDRJ katakana reading
            new_romaji = "Musoji"
            
            # Update the word
            session.run("""
                MATCH (w:Word)
                WHERE id(w) = $word_id
                SET w.romaji = $new_romaji
            """, {'word_id': word_id, 'new_romaji': new_romaji})
            
            logger.info(f"  ✅ Fixed: '{current_romaji}' -> '{new_romaji}'")
            fixed_count += 1
        
        return fixed_count

def main():
    """Main function"""
    logger.info("=" * 60)
    logger.info("FIXING SPECIFIC '六十路' CASE")
    logger.info("=" * 60)
    
    driver = load_environment()
    if not driver:
        logger.error("Cannot connect to database")
        return
    
    try:
        # Fix the specific case
        fixed_count = fix_rokujuu_specific(driver)
        
        logger.info("=" * 60)
        logger.info("SPECIFIC FIX COMPLETED")
        logger.info("=" * 60)
        logger.info(f"Successfully fixed: {fixed_count} words")
        
    finally:
        driver.close()

if __name__ == "__main__":
    main()


