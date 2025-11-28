#!/usr/bin/env python3
"""
Fix specific romaji issues where cutlet misinterprets katakana
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from neo4j import GraphDatabase
import logging

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

def katakana_to_romaji_manual(katakana_text):
    """Manual katakana to romaji conversion for problematic cases"""
    if not katakana_text:
        return ''
    
    # Simple katakana to romaji mapping for common cases
    katakana_map = {
        'ア': 'a', 'イ': 'i', 'ウ': 'u', 'エ': 'e', 'オ': 'o',
        'カ': 'ka', 'キ': 'ki', 'ク': 'ku', 'ケ': 'ke', 'コ': 'ko',
        'サ': 'sa', 'シ': 'shi', 'ス': 'su', 'セ': 'se', 'ソ': 'so',
        'タ': 'ta', 'チ': 'chi', 'ツ': 'tsu', 'テ': 'te', 'ト': 'to',
        'ナ': 'na', 'ニ': 'ni', 'ヌ': 'nu', 'ネ': 'ne', 'ノ': 'no',
        'ハ': 'ha', 'ヒ': 'hi', 'フ': 'fu', 'ヘ': 'he', 'ホ': 'ho',
        'マ': 'ma', 'ミ': 'mi', 'ム': 'mu', 'メ': 'me', 'モ': 'mo',
        'ヤ': 'ya', 'ユ': 'yu', 'ヨ': 'yo',
        'ラ': 'ra', 'リ': 'ri', 'ル': 'ru', 'レ': 're', 'ロ': 'ro',
        'ワ': 'wa', 'ヲ': 'wo', 'ン': 'n',
        'ガ': 'ga', 'ギ': 'gi', 'グ': 'gu', 'ゲ': 'ge', 'ゴ': 'go',
        'ザ': 'za', 'ジ': 'ji', 'ズ': 'zu', 'ゼ': 'ze', 'ゾ': 'zo',
        'ダ': 'da', 'ヂ': 'ji', 'ヅ': 'zu', 'デ': 'de', 'ド': 'do',
        'バ': 'ba', 'ビ': 'bi', 'ブ': 'bu', 'ベ': 'be', 'ボ': 'bo',
        'パ': 'pa', 'ピ': 'pi', 'プ': 'pu', 'ペ': 'pe', 'ポ': 'po',
        'ッ': '',  # Small tsu (handled separately)
        'ー': '',  # Long vowel mark (handled separately)
    }
    
    result = ''
    i = 0
    while i < len(katakana_text):
        char = katakana_text[i]
        
        # Handle small tsu (gemination)
        if char == 'ッ' and i + 1 < len(katakana_text):
            next_char = katakana_text[i + 1]
            if next_char in katakana_map:
                # Double the consonant
                romaji = katakana_map[next_char]
                if len(romaji) > 0:
                    result += romaji[0]  # Double the first consonant
                i += 1
                continue
        
        # Handle long vowel mark
        if char == 'ー' and len(result) > 0:
            # Extend the last vowel
            last_char = result[-1]
            if last_char in 'aeiou':
                result += last_char
            i += 1
            continue
        
        # Regular character
        if char in katakana_map:
            result += katakana_map[char]
        else:
            result += char  # Keep unknown characters as-is
        
        i += 1
    
    return result

def fix_specific_romaji_issues(driver):
    """Fix specific known romaji issues"""
    
    # Known problematic cases
    fixes = [
        {
            'hiragana': 'あまた',
            'katakana': 'アマタ',
            'correct_romaji': 'amata',
            'description': '数多 - many, numerous'
        }
    ]
    
    with driver.session() as session:
        for fix in fixes:
            hiragana = fix['hiragana']
            katakana = fix['katakana']
            correct_romaji = fix['correct_romaji']
            description = fix['description']
            
            # Find words with this hiragana or katakana
            result = session.run("""
                MATCH (w:Word)
                WHERE w.hiragana = $hiragana OR w.vdrj_standard_reading = $katakana
                RETURN id(w) as word_id, w.lemma, w.kanji, w.hiragana, w.romaji, w.vdrj_standard_reading
            """, {'hiragana': hiragana, 'katakana': katakana})
            
            for record in result:
                word_id = record['word_id']
                lemma = record['w.lemma']
                kanji = record['w.kanji']
                current_romaji = record['w.romaji']
                
                logger.info(f"Fixing: {lemma} ({kanji}) - {description}")
                logger.info(f"  Current romaji: {current_romaji}")
                logger.info(f"  Correct romaji: {correct_romaji}")
                
                # Update the romaji
                session.run("""
                    MATCH (w:Word)
                    WHERE id(w) = $word_id
                    SET w.romaji = $correct_romaji
                """, {'word_id': word_id, 'correct_romaji': correct_romaji})
                
                logger.info(f"  ✅ Updated successfully")

def find_problematic_romaji(driver):
    """Find words with potentially problematic romaji"""
    
    with driver.session() as session:
        # Look for romaji that contains "amateur" or similar issues
        result = session.run("""
            MATCH (w:Word)
            WHERE w.romaji CONTAINS 'amateur' OR w.romaji CONTAINS 'Amateur'
            RETURN w.lemma, w.kanji, w.hiragana, w.romaji, w.vdrj_standard_reading
            LIMIT 20
        """)
        
        logger.info("Words with 'amateur' in romaji:")
        for record in result:
            logger.info(f"  {record['w.lemma']} ({record['w.kanji']}) - {record['w.hiragana']} -> {record['w.romaji']}")
        
        # Look for other potential issues
        result2 = session.run("""
            MATCH (w:Word)
            WHERE w.romaji CONTAINS 'ta' AND w.vdrj_standard_reading IS NOT NULL
            AND w.romaji <> w.vdrj_standard_reading
            RETURN w.lemma, w.kanji, w.hiragana, w.romaji, w.vdrj_standard_reading
            LIMIT 10
        """)
        
        logger.info("\nWords ending with 'ta' that might have issues:")
        for record in result2:
            logger.info(f"  {record['w.lemma']} ({record['w.kanji']}) - {record['w.hiragana']} -> {record['w.romaji']} (VDRJ: {record['w.vdrj_standard_reading']})")

def main():
    """Main function"""
    logger.info("=" * 60)
    logger.info("FIXING ROMAJI ISSUES")
    logger.info("=" * 60)
    
    driver = load_environment()
    if not driver:
        logger.error("Cannot connect to database")
        return
    
    try:
        # First, find problematic cases
        find_problematic_romaji(driver)
        
        # Fix specific known issues
        fix_specific_romaji_issues(driver)
        
        logger.info("=" * 60)
        logger.info("ROMAJI FIXES COMPLETED")
        logger.info("=" * 60)
        
    finally:
        driver.close()

if __name__ == "__main__":
    main()


