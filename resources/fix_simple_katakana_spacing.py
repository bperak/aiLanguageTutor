#!/usr/bin/env python3
"""
Fix simple katakana spacing issues in romaji

Target: Simple cases like "I ie" -> "Iie", "A a" -> "Aa", etc.
"""

import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv
from neo4j import GraphDatabase
import re

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

def fix_simple_katakana_spacing(romaji_text):
    """Fix simple katakana spacing issues"""
    if not romaji_text:
        return romaji_text
    
    # Simple pattern: single character + space + single character
    # This handles cases like "I ie" -> "Iie", "A a" -> "Aa", etc.
    pattern = re.compile(r'\b([A-Za-z])\s+([A-Za-z])\b')
    
    result = pattern.sub(r'\1\2', romaji_text)
    
    return result

def find_simple_spacing_issues(driver):
    """Find words with simple katakana spacing issues"""
    
    with driver.session() as session:
        # Look for romaji that matches the pattern "X Y" (single char + space + single char)
        result = session.run("""
            MATCH (w:Word)
            WHERE w.romaji =~ '^[A-Za-z] [A-Za-z]$'
            RETURN w.lemma, w.kanji, w.hiragana, w.romaji, w.vdrj_standard_reading
        """)
        
        logger.info("Words with simple katakana spacing issues:")
        issues = []
        for record in result:
            lemma = record['w.lemma']
            kanji = record['w.kanji']
            hiragana = record['w.hiragana']
            romaji = record['w.romaji']
            katakana = record['w.vdrj_standard_reading']
            
            issues.append({
                'lemma': lemma,
                'kanji': kanji,
                'hiragana': hiragana,
                'romaji': romaji,
                'katakana': katakana
            })
            logger.info(f"  {lemma} ({kanji}) - {hiragana} -> {romaji} (VDRJ: {katakana})")
        
        return issues

def fix_word_romaji(driver, word_data, new_romaji):
    """Fix a specific word's romaji"""
    try:
        with driver.session() as session:
            # Find the word by lemma and kanji
            result = session.run("""
                MATCH (w:Word)
                WHERE w.lemma = $lemma AND w.kanji = $kanji
                RETURN id(w) as word_id
            """, {'lemma': word_data['lemma'], 'kanji': word_data['kanji']})
            
            for record in result:
                word_id = record['word_id']
                session.run("""
                    MATCH (w:Word)
                    WHERE id(w) = $word_id
                    SET w.romaji = $new_romaji
                """, {'word_id': word_id, 'new_romaji': new_romaji})
                return True
        return False
    except Exception as e:
        logger.error(f"Error fixing word {word_data['lemma']}: {e}")
        return False

def main():
    """Main function"""
    logger.info("=" * 60)
    logger.info("FIXING SIMPLE KATAKANA SPACING ISSUES")
    logger.info("=" * 60)
    
    driver = load_environment()
    if not driver:
        logger.error("Cannot connect to database")
        return
    
    try:
        # Find potential issues
        issues = find_simple_spacing_issues(driver)
        
        if not issues:
            logger.info("No simple katakana spacing issues found!")
            return
        
        logger.info(f"\nFound {len(issues)} simple spacing issues to fix")
        
        # Fix each issue
        fixed_count = 0
        for issue in issues:
            old_romaji = issue['romaji']
            new_romaji = fix_simple_katakana_spacing(old_romaji)
            
            if new_romaji != old_romaji:
                logger.info(f"Fixing: {issue['lemma']} - '{old_romaji}' -> '{new_romaji}'")
                
                if fix_word_romaji(driver, issue, new_romaji):
                    fixed_count += 1
                    logger.info(f"  ✅ Fixed successfully")
                else:
                    logger.error(f"  ❌ Failed to fix")
            else:
                logger.info(f"No change needed: {issue['lemma']} - '{old_romaji}'")
        
        logger.info("=" * 60)
        logger.info("SIMPLE KATAKANA SPACING FIX COMPLETED")
        logger.info("=" * 60)
        logger.info(f"Total issues found: {len(issues)}")
        logger.info(f"Successfully fixed: {fixed_count}")
        
    finally:
        driver.close()

if __name__ == "__main__":
    main()


