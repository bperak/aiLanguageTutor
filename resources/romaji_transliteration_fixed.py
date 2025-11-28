#!/usr/bin/env python3
"""
Romaji Transliteration Script with Fixed Cutlet Settings

This script re-runs romaji transliteration with use_foreign_spelling = False
to fix the "amateur" issue and other similar problems.
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
        logging.FileHandler('romaji_transliteration_fixed.log'),
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
        # Create a cutlet instance with foreign spelling disabled
        katsu = cutlet.Cutlet()
        katsu.use_foreign_spelling = False  # This fixes the "amateur" issue!
        logger.info("✅ Cutlet configured with use_foreign_spelling = False")
        return katsu
    except ImportError:
        logger.info("Installing cutlet...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "cutlet"])
        import cutlet
        logger.info("✅ Cutlet installed successfully")
        # Create a cutlet instance with foreign spelling disabled
        katsu = cutlet.Cutlet()
        katsu.use_foreign_spelling = False  # This fixes the "amateur" issue!
        logger.info("✅ Cutlet configured with use_foreign_spelling = False")
        return katsu

def get_words_with_problematic_romaji(driver) -> List[Dict]:
    """Get words that have problematic romaji (containing 'amateur' or similar issues)"""
    words = []
    
    with driver.session() as session:
        # Get words with "amateur" in romaji
        result = session.run("""
            MATCH (w:Word)
            WHERE w.romaji CONTAINS 'amateur' OR w.romaji CONTAINS 'Amateur'
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
                'source': 'vdrj_katakana' if record['w.vdrj_standard_reading'] else 'hiragana'
            })
    
    return words

def transliterate_with_fixed_cutlet(cutlet_instance, text: str, source_type: str) -> str:
    """Transliterate Japanese text using cutlet with foreign spelling disabled"""
    if not text or text.strip() == '':
        return ''
    
    try:
        # Clean the text
        text = text.strip()
        
        # Use cutlet for transliteration (with foreign spelling disabled)
        romaji = cutlet_instance.romaji(text)
        
        # Clean up the result
        romaji = romaji.strip()
        
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
    """Main function to fix romaji issues"""
    logger.info("=" * 80)
    logger.info("ROMAJI TRANSLITERATION FIX - DISABLING FOREIGN SPELLING")
    logger.info("=" * 80)
    
    # Install and import cutlet with fixed settings
    cutlet = install_cutlet()
    
    # Load environment and connect to database
    driver = load_environment()
    if not driver:
        logger.error("Cannot proceed without database connection")
        return
    
    try:
        # Get words with problematic romaji
        logger.info("Finding words with problematic romaji...")
        words = get_words_with_problematic_romaji(driver)
        
        logger.info(f"Found {len(words)} words with problematic romaji")
        
        if len(words) == 0:
            logger.info("No problematic words found!")
            return
        
        # Statistics
        stats = {
            'total_words': len(words),
            'updated': 0,
            'errors': 0,
            'skipped': 0
        }
        
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
                
                if not input_text:
                    stats['skipped'] += 1
                    continue
                
                # Generate new romaji with fixed cutlet
                new_romaji = transliterate_with_fixed_cutlet(cutlet, input_text, source)
                
                if new_romaji and new_romaji != current_romaji:
                    # Update the word
                    if update_word_romaji(driver, word_id, new_romaji):
                        stats['updated'] += 1
                        logger.info(f"Fixed {lemma}: '{current_romaji}' → '{new_romaji}'")
                    else:
                        stats['errors'] += 1
                else:
                    stats['skipped'] += 1
                
                # Progress reporting
                if i % 10 == 0:
                    logger.info(f"Processed {i}/{len(words)} words...")
            
            except Exception as e:
                logger.error(f"Error processing word {i}: {e}")
                stats['errors'] += 1
                continue
        
        # Final statistics
        logger.info("=" * 80)
        logger.info("ROMAJI FIX COMPLETED")
        logger.info("=" * 80)
        logger.info(f"Total words processed: {stats['total_words']}")
        logger.info(f"Words updated: {stats['updated']}")
        logger.info(f"Words skipped: {stats['skipped']}")
        logger.info(f"Errors: {stats['errors']}")
        logger.info(f"Success rate: {stats['updated']/stats['total_words']*100:.1f}%")
        
    except Exception as e:
        logger.error(f"Error during romaji fix: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        if driver:
            driver.close()
            logger.info("Database connection closed")

if __name__ == "__main__":
    main()


