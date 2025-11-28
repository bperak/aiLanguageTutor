#!/usr/bin/env python3
"""
Romaji Transliteration Script using Cutlet

This script uses the cutlet library to generate high-quality romaji
for all Word nodes in the Neo4j database.

Strategy:
1. Use VDRJ katakana data when available (best quality)
2. Use existing hiragana data as fallback
3. Use cutlet for intelligent transliteration with proper spacing
4. Handle missing romaji cases
"""

import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv
from neo4j import GraphDatabase
from typing import Dict, List, Optional, Tuple
import time

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('romaji_transliteration.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def load_environment():
    """Load environment variables and setup Neo4j connection"""
    # Load environment variables from root directory
    env_path = Path(__file__).parent.parent / '.env'
    load_dotenv(env_path)
    
    # Also try loading from current directory as fallback
    if not env_path.exists():
        load_dotenv()
    
    print(f"Environment loaded from: {env_path}")
    print(f"Current working directory: {Path.cwd()}")
    print(f"Environment file exists: {env_path.exists()}")
    
    # Neo4j connection configuration
    URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    USER = os.getenv("NEO4J_USERNAME", "neo4j")
    
    # Try environment password first, then fallback to Docker default
    env_password = os.getenv("NEO4J_PASSWORD")
    PASSWORD = env_password if env_password else "testpassword123"
    
    # Debug environment variables
    print(f"Environment variables loaded:")
    print(f"  NEO4J_URI: {URI}")
    print(f"  NEO4J_USERNAME: {USER}")
    print(f"  NEO4J_PASSWORD: {'***' if PASSWORD else 'NOT SET'}")
    print(f"  NEO4J_PASSWORD length: {len(PASSWORD) if PASSWORD else 0}")
    
    # Handle Docker container URIs
    if URI.startswith("neo4j://neo4j:"):
        URI = URI.replace("neo4j://neo4j:", "bolt://localhost:")
    elif URI.startswith("neo4j://"):
        URI = URI.replace("neo4j://", "bolt://localhost:")
    
    print(f"Connecting to Neo4j at: {URI}")
    print(f"User: {USER}")
    print(f"Password set: {'Yes' if PASSWORD else 'No'}")
    
    # Test connection with multiple password attempts
    # Skip environment password due to rate limiting, use only working password
    passwords_to_try = ["testpassword123"]
    
    for i, password in enumerate(passwords_to_try, 1):
        if password == PASSWORD and env_password:
            print(f"Trying environment password (attempt {i})")
        else:
            print(f"Trying fallback password (attempt {i})")
            
        try:
            driver = GraphDatabase.driver(URI, auth=(USER, password))
            with driver.session() as session:
                result = session.run("RETURN 'Connection successful' as status")
                status = result.single()['status']
                print(f"✅ {status}")
            return driver
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            if driver:
                driver.close()
            continue
    
    print("❌ All connection attempts failed")
    return None

def install_cutlet():
    """Install cutlet if not available"""
    try:
        import cutlet
        logger.info("✅ Cutlet is already installed")
        # Create a cutlet instance
        katsu = cutlet.Cutlet()
        return katsu
    except ImportError:
        logger.info("Installing cutlet...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "cutlet"])
        import cutlet
        logger.info("✅ Cutlet installed successfully")
        # Create a cutlet instance
        katsu = cutlet.Cutlet()
        return katsu

def get_words_needing_romaji(driver) -> List[Dict]:
    """Get all Word nodes that need romaji transliteration"""
    words = []
    
    with driver.session() as session:
        # Get words with VDRJ katakana data (best quality)
        result = session.run("""
            MATCH (w:Word)
            WHERE w.vdrj_standard_reading IS NOT NULL 
            AND w.vdrj_standard_reading <> ''
            RETURN id(w) as word_id, w.lemma, w.kanji, w.hiragana, w.romaji, w.vdrj_standard_reading
        """)
        
        for record in result:
            words.append({
                'word_id': record['word_id'],
                'lemma': record['w.lemma'],
                'kanji': record['w.kanji'],
                'hiragana': record['w.hiragana'],
                'current_romaji': record['w.romaji'],
                'vdrj_katakana': record['w.vdrj_standard_reading'],
                'source': 'vdrj_katakana'
            })
        
        # Get words with hiragana but no VDRJ data
        result = session.run("""
            MATCH (w:Word)
            WHERE w.hiragana IS NOT NULL 
            AND w.hiragana <> ''
            AND (w.vdrj_standard_reading IS NULL OR w.vdrj_standard_reading = '')
            RETURN id(w) as word_id, w.lemma, w.kanji, w.hiragana, w.romaji
        """)
        
        for record in result:
            words.append({
                'word_id': record['word_id'],
                'lemma': record['w.lemma'],
                'kanji': record['w.kanji'],
                'hiragana': record['w.hiragana'],
                'current_romaji': record['w.romaji'],
                'vdrj_katakana': None,
                'source': 'hiragana'
            })
        
        # Get words with missing romaji (no hiragana or VDRJ data)
        result = session.run("""
            MATCH (w:Word)
            WHERE (w.romaji IS NULL OR w.romaji = '')
            AND (w.hiragana IS NULL OR w.hiragana = '')
            AND (w.vdrj_standard_reading IS NULL OR w.vdrj_standard_reading = '')
            RETURN id(w) as word_id, w.lemma, w.kanji, w.hiragana, w.romaji
        """)
        
        for record in result:
            words.append({
                'word_id': record['word_id'],
                'lemma': record['w.lemma'],
                'kanji': record['w.kanji'],
                'hiragana': record['w.hiragana'],
                'current_romaji': record['w.romaji'],
                'vdrj_katakana': None,
                'source': 'missing'
            })
    
    return words

def transliterate_with_cutlet(cutlet_instance, text: str, source_type: str) -> str:
    """Transliterate Japanese text using cutlet"""
    if not text or text.strip() == '':
        return ''
    
    try:
        # Clean the text
        text = text.strip()
        
        # Use cutlet for transliteration
        romaji = cutlet_instance.romaji(text)
        
        # Clean up the result
        romaji = romaji.strip()
        
        # Handle common issues
        if source_type == 'vdrj_katakana':
            # VDRJ katakana might need special handling
            pass
        
        return romaji
        
    except Exception as e:
        logger.warning(f"Cutlet transliteration failed for '{text}': {e}")
        return ''

def update_word_romaji(driver, word_id: int, new_romaji: str) -> bool:
    """Update a Word node with new romaji"""
    try:
        with driver.session() as session:
            session.run("""
                MATCH (w:Word)
                WHERE id(w) = $word_id
                SET w.romaji = $romaji
            """, {'word_id': word_id, 'romaji': new_romaji})
            return True
    except Exception as e:
        logger.error(f"Error updating word {word_id}: {e}")
        return False

def main():
    """Main function to run romaji transliteration"""
    logger.info("=" * 80)
    logger.info("ROMAJI TRANSLITERATION WITH CUTLET")
    logger.info("=" * 80)
    
    # Install and import cutlet
    cutlet = install_cutlet()
    
    # Load environment and connect to database
    driver = load_environment()
    if not driver:
        logger.error("Cannot proceed without database connection")
        return
    
    try:
        # Get all words needing romaji
        logger.info("Fetching words needing romaji transliteration...")
        words = get_words_needing_romaji(driver)
        
        logger.info(f"Found {len(words)} words to process")
        
        # Statistics
        stats = {
            'total_words': len(words),
            'vdrj_katakana': 0,
            'hiragana_fallback': 0,
            'missing_data': 0,
            'updated': 0,
            'errors': 0,
            'skipped': 0
        }
        
        # Count by source type
        for word in words:
            if word['source'] == 'vdrj_katakana':
                stats['vdrj_katakana'] += 1
            elif word['source'] == 'hiragana':
                stats['hiragana_fallback'] += 1
            else:
                stats['missing_data'] += 1
        
        logger.info(f"Source breakdown:")
        logger.info(f"  VDRJ katakana: {stats['vdrj_katakana']}")
        logger.info(f"  Hiragana fallback: {stats['hiragana_fallback']}")
        logger.info(f"  Missing data: {stats['missing_data']}")
        
        # Process each word
        for i, word in enumerate(words, 1):
            try:
                word_id = word['word_id']
                lemma = word['lemma']
                kanji = word['kanji']
                hiragana = word['hiragana']
                current_romaji = word['current_romaji']
                vdrj_katakana = word['vdrj_katakana']
                source = word['source']
                
                # Determine input text for transliteration
                input_text = None
                if source == 'vdrj_katakana' and vdrj_katakana:
                    input_text = vdrj_katakana
                elif source == 'hiragana' and hiragana:
                    input_text = hiragana
                elif source == 'missing':
                    # Try to use standard_orthography, kanji, or lemma as fallback
                    # We fetch standard_orthography on demand to avoid changing earlier result shape
                    std = None
                    try:
                        rec = driver.session().run(
                            "MATCH (w:Word) WHERE id(w) = $id RETURN w.standard_orthography AS s",
                            id=word_id
                        ).single()
                        std = rec and rec['s']
                    except Exception:
                        std = None
                    input_text = std or kanji or lemma
                
                if not input_text:
                    stats['skipped'] += 1
                    continue
                
                # Generate new romaji
                new_romaji = transliterate_with_cutlet(cutlet, input_text, source)
                
                if new_romaji and new_romaji != current_romaji:
                    # Update the word
                    if update_word_romaji(driver, word_id, new_romaji):
                        stats['updated'] += 1
                        logger.debug(f"Updated {lemma}: '{current_romaji}' → '{new_romaji}'")
                    else:
                        stats['errors'] += 1
                else:
                    stats['skipped'] += 1
                
                # Progress reporting
                if i % 1000 == 0:
                    logger.info(f"Processed {i}/{len(words)} words...")
                    logger.info(f"  Updated: {stats['updated']}, Errors: {stats['errors']}, Skipped: {stats['skipped']}")
            
            except Exception as e:
                logger.error(f"Error processing word {i}: {e}")
                stats['errors'] += 1
                continue
        
        # Final statistics
        logger.info("=" * 80)
        logger.info("ROMAJI TRANSLITERATION COMPLETED")
        logger.info("=" * 80)
        logger.info(f"Total words processed: {stats['total_words']}")
        logger.info(f"Words updated: {stats['updated']}")
        logger.info(f"Words skipped: {stats['skipped']}")
        logger.info(f"Errors: {stats['errors']}")
        logger.info(f"Success rate: {stats['updated']/stats['total_words']*100:.1f}%")
        
        # Show source breakdown
        logger.info(f"\nSource breakdown:")
        logger.info(f"  VDRJ katakana: {stats['vdrj_katakana']}")
        logger.info(f"  Hiragana fallback: {stats['hiragana_fallback']}")
        logger.info(f"  Missing data: {stats['missing_data']}")
        
    except Exception as e:
        logger.error(f"Error during romaji transliteration: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        if driver:
            driver.close()
            logger.info("Database connection closed")

if __name__ == "__main__":
    main()
