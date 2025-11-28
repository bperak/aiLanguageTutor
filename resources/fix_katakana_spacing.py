#!/usr/bin/env python3
"""
Fix katakana spacing issues in romaji

The problem: Cutlet adds spaces between katakana characters
Solution: Post-process katakana-derived romaji to remove unwanted spaces
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

def fix_katakana_spacing(romaji_text):
    """Fix spacing issues in katakana-derived romaji"""
    if not romaji_text:
        return romaji_text
    
    # Common patterns where spaces should be removed
    # These are typically single words that got split by cutlet's katakana processing
    
    # Pattern 1: Single character + space + single character (like "I ie" -> "Iie")
    pattern1 = re.compile(r'\b([A-Za-z])\s+([A-Za-z])\b')
    
    # Pattern 2: Common Japanese word patterns that shouldn't have spaces
    japanese_patterns = [
        # Common endings
        (r'\b([A-Za-z]+)\s+desu\b', r'\1desu'),  # "word desu" -> "worddesu"
        (r'\b([A-Za-z]+)\s+masu\b', r'\1masu'),  # "word masu" -> "wordmasu"
        (r'\b([A-Za-z]+)\s+ta\b', r'\1ta'),      # "word ta" -> "wordta"
        (r'\b([A-Za-z]+)\s+te\b', r'\1te'),      # "word te" -> "wordte"
        (r'\b([A-Za-z]+)\s+ru\b', r'\1ru'),      # "word ru" -> "wordru"
        
        # Common beginnings
        (r'\bwa\s+([A-Za-z]+)\b', r'wa\1'),      # "wa word" -> "waword"
        (r'\bga\s+([A-Za-z]+)\b', r'ga\1'),      # "ga word" -> "gaword"
        (r'\bwo\s+([A-Za-z]+)\b', r'wo\1'),      # "wo word" -> "woword"
        (r'\bni\s+([A-Za-z]+)\b', r'ni\1'),      # "ni word" -> "niword"
        
        # Double vowels (common in Japanese)
        (r'\b([A-Za-z])\s+([A-Za-z])\b', r'\1\2'),  # "a a" -> "aa", "i i" -> "ii", etc.
    ]
    
    result = romaji_text
    
    # Apply pattern 1 first (most general case)
    result = pattern1.sub(r'\1\2', result)
    
    # Apply specific Japanese patterns
    for pattern, replacement in japanese_patterns:
        result = re.sub(pattern, replacement, result)
    
    return result

def find_katakana_spacing_issues(driver):
    """Find words with potential katakana spacing issues"""
    
    with driver.session() as session:
        # Look for romaji that contains spaces and has VDRJ katakana data
        result = session.run("""
            MATCH (w:Word)
            WHERE w.romaji CONTAINS ' ' 
            AND w.vdrj_standard_reading IS NOT NULL
            AND w.vdrj_standard_reading <> ''
            RETURN w.lemma, w.kanji, w.hiragana, w.romaji, w.vdrj_standard_reading
            LIMIT 20
        """)
        
        logger.info("Words with potential katakana spacing issues:")
        issues = []
        for record in result:
            lemma = record['w.lemma']
            kanji = record['w.kanji']
            hiragana = record['w.hiragana']
            romaji = record['w.romaji']
            katakana = record['w.vdrj_standard_reading']
            
            # Check if this looks like a spacing issue
            if len(romaji.split()) <= 3:  # Short words with spaces are likely issues
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
    logger.info("FIXING KATAKANA SPACING ISSUES")
    logger.info("=" * 60)
    
    driver = load_environment()
    if not driver:
        logger.error("Cannot connect to database")
        return
    
    try:
        # Find potential issues
        issues = find_katakana_spacing_issues(driver)
        
        if not issues:
            logger.info("No katakana spacing issues found!")
            return
        
        logger.info(f"\nFound {len(issues)} potential issues to fix")
        
        # Fix each issue
        fixed_count = 0
        for issue in issues:
            old_romaji = issue['romaji']
            new_romaji = fix_katakana_spacing(old_romaji)
            
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
        logger.info("KATAKANA SPACING FIX COMPLETED")
        logger.info("=" * 60)
        logger.info(f"Total issues found: {len(issues)}")
        logger.info(f"Successfully fixed: {fixed_count}")
        
    finally:
        driver.close()

if __name__ == "__main__":
    main()


