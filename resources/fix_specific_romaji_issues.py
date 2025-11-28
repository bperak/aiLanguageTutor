#!/usr/bin/env python3
"""
Fix specific romaji issues that weren't resolved by the comprehensive transliteration
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

def fix_specific_words(driver):
    """Fix specific words with known issues"""
    
    # Define specific fixes
    fixes = [
        # (search_pattern, new_romaji, description)
        ("いいえ", "Iie", "Fix いいえ spacing"),
        ("こんにちは", "Konnichiwa", "Fix こんにちは wa particle"),
        ("こんばんは", "Konbanwa", "Fix こんばんは wa particle"),
        ("数多", "Amata", "Fix 数多 spacing"),
    ]
    
    with driver.session() as session:
        logger.info("Fixing specific romaji issues:")
        logger.info("=" * 50)
        
        total_fixed = 0
        
        for search_pattern, new_romaji, description in fixes:
            logger.info(f"\n{description}:")
            
            # Find words matching the pattern
            result = session.run("""
                MATCH (w:Word)
                WHERE w.lemma = $pattern OR w.kanji = $pattern OR w.hiragana = $pattern
                RETURN id(w) as word_id, w.lemma, w.kanji, w.hiragana, w.romaji, w.vdrj_standard_reading
            """, {'pattern': search_pattern})
            
            fixed_count = 0
            for record in result:
                word_id = record['word_id']
                lemma = record['w.lemma']
                kanji = record['w.kanji']
                hiragana = record['w.hiragana']
                current_romaji = record['w.romaji']
                katakana = record['w.vdrj_standard_reading']
                
                if current_romaji != new_romaji:
                    # Update the word
                    session.run("""
                        MATCH (w:Word)
                        WHERE id(w) = $word_id
                        SET w.romaji = $new_romaji
                    """, {'word_id': word_id, 'new_romaji': new_romaji})
                    
                    logger.info(f"  ✅ Fixed: {lemma} ({kanji}) - '{current_romaji}' -> '{new_romaji}'")
                    fixed_count += 1
                else:
                    logger.info(f"  ✅ Already correct: {lemma} ({kanji}) - '{current_romaji}'")
            
            total_fixed += fixed_count
            logger.info(f"  Fixed {fixed_count} words for '{search_pattern}'")
        
        return total_fixed

def fix_spacing_issues(driver):
    """Fix remaining spacing issues"""
    
    with driver.session() as session:
        logger.info("\nFixing remaining spacing issues:")
        logger.info("=" * 50)
        
        # Find words with spaces in romaji
        result = session.run("""
            MATCH (w:Word)
            WHERE w.romaji CONTAINS ' '
            RETURN id(w) as word_id, w.lemma, w.kanji, w.hiragana, w.romaji, w.vdrj_standard_reading
            LIMIT 50
        """)
        
        fixed_count = 0
        for record in result:
            word_id = record['word_id']
            lemma = record['w.lemma']
            kanji = record['w.kanji']
            hiragana = record['w.hiragana']
            current_romaji = record['w.romaji']
            katakana = record['w.vdrj_standard_reading']
            
            # Simple spacing fix: remove spaces between single characters
            import re
            new_romaji = re.sub(r'\b([A-Za-z])\s+([A-Za-z])\b', r'\1\2', current_romaji)
            
            if new_romaji != current_romaji:
                # Update the word
                session.run("""
                    MATCH (w:Word)
                    WHERE id(w) = $word_id
                    SET w.romaji = $new_romaji
                """, {'word_id': word_id, 'new_romaji': new_romaji})
                
                logger.info(f"  ✅ Fixed spacing: {lemma} ({kanji}) - '{current_romaji}' -> '{new_romaji}'")
                fixed_count += 1
        
        return fixed_count

def main():
    """Main function"""
    logger.info("=" * 80)
    logger.info("FIXING SPECIFIC ROMAJI ISSUES")
    logger.info("=" * 80)
    
    driver = load_environment()
    if not driver:
        logger.error("Cannot connect to database")
        return
    
    try:
        # Fix specific words
        specific_fixed = fix_specific_words(driver)
        
        # Fix spacing issues
        spacing_fixed = fix_spacing_issues(driver)
        
        # Final summary
        logger.info("=" * 80)
        logger.info("SPECIFIC FIXES COMPLETED")
        logger.info("=" * 80)
        logger.info(f"Specific words fixed: {specific_fixed}")
        logger.info(f"Spacing issues fixed: {spacing_fixed}")
        logger.info(f"Total fixes: {specific_fixed + spacing_fixed}")
        logger.info("=" * 80)
        
    finally:
        driver.close()

if __name__ == "__main__":
    main()


