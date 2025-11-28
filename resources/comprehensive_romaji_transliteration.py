#!/usr/bin/env python3
"""
Comprehensive Romaji Transliteration with All Fixes

This script addresses all discovered issues:
1. use_foreign_spelling = False (prevents "amateur" issues)
2. use_wa = True (proper "は" particle handling)
3. Katakana spacing fixes
4. Prioritize hiragana over katakana
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

def install_cutlet():
    """Install and configure cutlet with optimal settings"""
    try:
        import cutlet
        logger.info("✅ Cutlet already installed")
    except ImportError:
        logger.info("Installing cutlet...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "cutlet"])
        import cutlet
        logger.info("✅ Cutlet installed successfully")
    
    # Configure cutlet with optimal settings
    katsu = cutlet.Cutlet()
    katsu.use_foreign_spelling = False  # Prevent "amateur" issues
    katsu.use_wa = True  # Proper "は" particle handling
    
    logger.info("✅ Cutlet configured with:")
    logger.info("  - use_foreign_spelling = False")
    logger.info("  - use_wa = True")
    
    return katsu

def fix_katakana_spacing(romaji_text):
    """Fix spacing issues in katakana-derived romaji"""
    if not romaji_text:
        return romaji_text
    
    # Simple pattern: single character + space + single character
    # This handles cases like "I ie" -> "Iie", "A a" -> "Aa", etc.
    pattern = re.compile(r'\b([A-Za-z])\s+([A-Za-z])\b')
    result = pattern.sub(r'\1\2', romaji_text)
    
    return result

def get_best_input_text(word_data):
    """Get the best input text for transliteration, prioritizing hiragana over katakana"""
    lemma = word_data.get('lemma')
    kanji = word_data.get('kanji')
    hiragana = word_data.get('hiragana')
    katakana = word_data.get('vdrj_standard_reading')
    
    # Priority order: hiragana > katakana > kanji > lemma
    if hiragana and hiragana.strip():
        return hiragana.strip(), 'hiragana'
    elif katakana and katakana.strip():
        return katakana.strip(), 'katakana'
    elif kanji and kanji.strip():
        return kanji.strip(), 'kanji'
    elif lemma and lemma.strip():
        return lemma.strip(), 'lemma'
    else:
        return None, None

def transliterate_word(cutlet_instance, word_data):
    """Transliterate a single word using the best available input"""
    input_text, input_type = get_best_input_text(word_data)
    
    if not input_text:
        return None, None, "No input text available"
    
    try:
        # Transliterate using cutlet
        romaji = cutlet_instance.romaji(input_text)
        
        # Post-process katakana results to fix spacing
        if input_type == 'katakana':
            original_romaji = romaji
            romaji = fix_katakana_spacing(romaji)
            if romaji != original_romaji:
                logger.debug(f"Fixed katakana spacing: '{original_romaji}' -> '{romaji}'")
        
        return romaji, input_type, "Success"
        
    except Exception as e:
        return None, input_type, f"Transliteration error: {e}"

def update_word_romaji(driver, word_id, new_romaji):
    """Update a word's romaji in the database"""
    try:
        with driver.session() as session:
            session.run("""
                MATCH (w:Word)
                WHERE id(w) = $word_id
                SET w.romaji = $new_romaji
            """, {'word_id': word_id, 'new_romaji': new_romaji})
            return True
    except Exception as e:
        logger.error(f"Error updating word {word_id}: {e}")
        return False

def process_words_batch(driver, cutlet_instance, batch_size=1000):
    """Process words in batches for transliteration"""
    
    with driver.session() as session:
        # Get total count
        result = session.run("MATCH (w:Word) RETURN count(w) as total")
        total_words = result.single()['total']
        logger.info(f"Total words to process: {total_words}")
        
        processed = 0
        updated = 0
        errors = 0
        
        # Process in batches
        offset = 0
        while offset < total_words:
            # Get batch of words
            result = session.run("""
                MATCH (w:Word)
                RETURN id(w) as word_id, w.lemma, w.kanji, w.hiragana, w.romaji, w.vdrj_standard_reading
                SKIP $offset
                LIMIT $batch_size
            """, {'offset': offset, 'batch_size': batch_size})
            
            batch_words = list(result)
            if not batch_words:
                break
            
            logger.info(f"Processing batch {offset//batch_size + 1}: words {offset+1}-{offset+len(batch_words)}")
            
            for record in batch_words:
                word_id = record['word_id']
                word_data = {
                    'lemma': record['w.lemma'],
                    'kanji': record['w.kanji'],
                    'hiragana': record['w.hiragana'],
                    'vdrj_standard_reading': record['w.vdrj_standard_reading']
                }
                current_romaji = record['w.romaji']
                
                # Transliterate the word
                new_romaji, input_type, status = transliterate_word(cutlet_instance, word_data)
                
                if new_romaji and new_romaji != current_romaji:
                    # Update the word
                    if update_word_romaji(driver, word_id, new_romaji):
                        updated += 1
                        logger.debug(f"Updated: {word_data['lemma']} ({word_data['kanji']}) - '{current_romaji}' -> '{new_romaji}' ({input_type})")
                    else:
                        errors += 1
                elif new_romaji == current_romaji:
                    logger.debug(f"No change needed: {word_data['lemma']} ({word_data['kanji']}) - '{current_romaji}'")
                else:
                    errors += 1
                    logger.warning(f"Failed to transliterate: {word_data['lemma']} ({word_data['kanji']}) - {status}")
                
                processed += 1
                
                # Progress update
                if processed % 1000 == 0:
                    logger.info(f"Progress: {processed}/{total_words} words processed, {updated} updated, {errors} errors")
            
            offset += batch_size
        
        return processed, updated, errors

def main():
    """Main function"""
    logger.info("=" * 80)
    logger.info("COMPREHENSIVE ROMAJI TRANSLITERATION")
    logger.info("=" * 80)
    logger.info("Features:")
    logger.info("  - use_foreign_spelling = False (prevents 'amateur' issues)")
    logger.info("  - use_wa = True (proper 'は' particle handling)")
    logger.info("  - Katakana spacing fixes")
    logger.info("  - Prioritize hiragana over katakana")
    logger.info("=" * 80)
    
    # Load environment and connect to database
    driver = load_environment()
    if not driver:
        logger.error("Cannot connect to database")
        return
    
    try:
        # Install and configure cutlet
        cutlet_instance = install_cutlet()
        
        # Test cutlet with known cases
        logger.info("\nTesting cutlet configuration:")
        test_cases = [
            ('いいえ', 'hiragana'),
            ('イイエ', 'katakana'),
            ('こんにちは', 'hiragana'),
            ('数多', 'kanji')
        ]
        
        for test_text, test_type in test_cases:
            result = cutlet_instance.romaji(test_text)
            logger.info(f"  {test_text} ({test_type}) -> {result}")
        
        # Process all words
        logger.info("\nStarting comprehensive transliteration...")
        processed, updated, errors = process_words_batch(driver, cutlet_instance)
        
        # Final summary
        logger.info("=" * 80)
        logger.info("COMPREHENSIVE TRANSLITERATION COMPLETED")
        logger.info("=" * 80)
        logger.info(f"Total words processed: {processed}")
        logger.info(f"Words updated: {updated}")
        logger.info(f"Errors: {errors}")
        logger.info(f"Success rate: {((processed - errors) / processed * 100):.1f}%")
        logger.info("=" * 80)
        
    finally:
        driver.close()

if __name__ == "__main__":
    main()


