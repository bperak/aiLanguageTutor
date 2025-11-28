#!/usr/bin/env python3
"""
VDRJ Dictionary Import Script

This script imports the VDRJ (Vocabulary Database for Reading Japanese) dictionary
and maps comprehensive vocabulary data to existing Word nodes in Neo4j.

Features:
- Maps difficulty levels (International Student, General Learner, JLPT, Academic Tiers)
- Adds frequency and usage data
- Includes domain-specific difficulty classifications
- Preserves existing Word node data while adding VDRJ properties

Matching Strategy:
- Primary match: VDRJ Lexeme (見出し語彙素) against Word.lemma
- Fallback matches: Standard Orthography, Standard Reading
"""

import os
import sys
import csv
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
        logging.FileHandler('vdrj_import.log'),
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

# VDRJ Column Mapping (Latin keys -> Japanese column names)
# Based on actual TSV file structure analysis
VDRJ_MAPPING = {
    # Core Word Information (using actual column indices)
    'vdrj_lexeme': 13,  # 見出し語彙素 Lexeme
    'vdrj_standard_orthography': 14,  # 標準的（新聞）表記 Standard (Newspaper) Orthography
    'vdrj_standard_reading': 15,  # 標準的読み方（カタカナ） Standard Reading (Katakana)
    'vdrj_pos': 16,  # 品詞 Part of Speech
    'vdrj_word_origin': 17,  # 語種 Word Origin Type
    
    # Difficulty/Level Classifications (using actual column indices)
    'vdrj_international_student_level': 0,  # 留学生用 語彙レベル Word Level for International Students
    'vdrj_international_student_rank': 1,  # 留学生用語彙ランク Word Ranking for International Students
    'vdrj_general_learner_level': 2,  # 一般語彙レベル Word Level for General Learners
    'vdrj_general_learner_rank': 3,  # 一般語彙ランク Word Ranking for General Learners
    'vdrj_written_japanese_level': 4,  # 書きことば語彙レベル Word Level for Written Japanese
    'vdrj_written_japanese_rank': 5,  # 書きことば重要度ランク（想定既知語彙を除く）
    'vdrj_old_jlpt_level': 6,  # 旧日本語能力試験出題基準レベル Old JLPT Level
    'vdrj_academic_tier': 12,  # 語彙階層ラベル Word Tier Label
    'vdrj_humanities_specificity': 7,  # 人文・芸術領域特徴度レベル
    'vdrj_social_sciences_specificity': 8,  # 社会科学領域特徴度レベル
    'vdrj_tech_sciences_specificity': 9,  # 自然科学（理学・工学系）領域特徴度レベル
    'vdrj_bio_medical_specificity': 10,  # 自然科学（生物・医学系）領域特徴度レベル
    'vdrj_literary_keyword': 11,  # 文芸特徴語候補 Possible Literary Keywords
    
    # Frequency & Usage Data (using actual column indices)
    'vdrj_frequency': 19,  # 使用度数 Frequency
    'vdrj_corrected_frequency': 20,  # 修正済み使用度数（総延べ語数32656221語中）
    'vdrj_standardized_frequency': 22,  # 10分野100万語あたり使用頻度(Fw)
    'vdrj_dispersion': 30,  # 分散度 D
    'vdrj_usage_coefficient': 31,  # 書きことば使用度係数(Uw)
    'vdrj_usage_range': 34,  # 使用範囲 Range
    'vdrj_frequency_ranking': 36,  # 使用頻度順位 Freq Ranking
    'vdrj_dispersion_ranking': 37,  # 分散度順位 D Ranking
}

def parse_vdrj_file(file_path: str) -> List[Dict]:
    """Parse the VDRJ TSV file and return structured data"""
    logger.info(f"Parsing VDRJ file: {file_path}")
    
    if not os.path.exists(file_path):
        logger.error(f"VDRJ file not found: {file_path}")
        return []
    
    entries = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            # Read the header row
            header_line = file.readline().strip()
            headers = header_line.split('\t')
            
            logger.info(f"Found {len(headers)} columns in VDRJ file")
            logger.info(f"First few headers: {headers[:5]}")
            
            # Use direct column indices (already mapped)
            column_indices = VDRJ_MAPPING.copy()
            logger.info(f"Using {len(column_indices)} VDRJ columns for mapping")
            
            # Read data rows
            reader = csv.reader(file, delimiter='\t')
            for row_num, row in enumerate(reader, start=2):
                if len(row) < len(headers):
                    # Pad row with empty strings if it's shorter
                    row.extend([''] * (len(headers) - len(row)))
                
                # Extract mapped data
                entry = {}
                for latin_key, col_index in column_indices.items():
                    if col_index < len(row):
                        value = row[col_index].strip()
                        # Convert numeric values
                        if latin_key.endswith('_rank') or latin_key.endswith('_frequency') or latin_key.endswith('_dispersion') or latin_key.endswith('_coefficient') or latin_key.endswith('_range'):
                            try:
                                if value and value != '':
                                    entry[latin_key] = float(value) if '.' in value else int(value)
                                else:
                                    entry[latin_key] = None
                            except (ValueError, TypeError):
                                entry[latin_key] = None
                        else:
                            entry[latin_key] = value if value else None
                    else:
                        entry[latin_key] = None
                
                entries.append(entry)
                
                if row_num % 10000 == 0:
                    logger.info(f"Processed {row_num-1} entries...")
    
    except Exception as e:
        logger.error(f"Error parsing VDRJ file: {e}")
        return []
    
    logger.info(f"Successfully parsed {len(entries)} VDRJ entries")
    return entries

def find_matching_words(driver, vdrj_entry: Dict) -> List[int]:
    """Find Word nodes that match the VDRJ entry"""
    matches = []
    
    with driver.session() as session:
        # Primary match: VDRJ Lexeme against Word.lemma
        if vdrj_entry.get('vdrj_lexeme'):
            result = session.run("""
                MATCH (w:Word)
                WHERE w.lemma = $lexeme
                RETURN id(w) as word_id
            """, {'lexeme': vdrj_entry['vdrj_lexeme']})
            
            for record in result:
                matches.append(record['word_id'])
        
        # Fallback match 1: Standard Orthography against Word.standard_orthography (or legacy kanji)
        if not matches and vdrj_entry.get('vdrj_standard_orthography'):
            result = session.run("""
                MATCH (w:Word)
                WHERE coalesce(w.standard_orthography, w.kanji) = $orthography
                RETURN id(w) as word_id
            """, {'orthography': vdrj_entry['vdrj_standard_orthography']})
            
            for record in result:
                matches.append(record['word_id'])
        
        # Fallback match 2: Standard Reading against Word.hiragana / reading_hiragana
        if not matches and vdrj_entry.get('vdrj_standard_reading'):
            result = session.run("""
                MATCH (w:Word)
                WHERE w.hiragana = $reading OR w.reading_hiragana = $reading
                RETURN id(w) as word_id
            """, {'reading': vdrj_entry['vdrj_standard_reading']})
            
            for record in result:
                matches.append(record['word_id'])
    
    return matches

def update_word_with_vdrj_data(driver, word_id: int, vdrj_entry: Dict) -> bool:
    """Update a Word node with VDRJ data"""
    try:
        with driver.session() as session:
            # Prepare properties for update
            properties = {}
            for key, value in vdrj_entry.items():
                if value is not None and value != '':
                    properties[key] = value
            
            if not properties:
                return False
            
            # Update the Word node
            session.run("""
                MATCH (w:Word)
                WHERE id(w) = $word_id
                SET w += $properties
            """, {'word_id': word_id, 'properties': properties})
            
            return True
            
    except Exception as e:
        logger.error(f"Error updating word {word_id}: {e}")
        return False

def create_vdrj_indexes(driver):
    """Create indexes for VDRJ properties"""
    logger.info("Creating indexes for VDRJ properties...")
    
    indexes = [
        "CREATE INDEX vdrj_international_student_level IF NOT EXISTS FOR (w:Word) ON (w.vdrj_international_student_level)",
        "CREATE INDEX vdrj_old_jlpt_level IF NOT EXISTS FOR (w:Word) ON (w.vdrj_old_jlpt_level)",
        "CREATE INDEX vdrj_academic_tier IF NOT EXISTS FOR (w:Word) ON (w.vdrj_academic_tier)",
        "CREATE INDEX vdrj_frequency IF NOT EXISTS FOR (w:Word) ON (w.vdrj_frequency)",
        "CREATE INDEX vdrj_standardized_frequency IF NOT EXISTS FOR (w:Word) ON (w.vdrj_standardized_frequency)",
    ]
    
    with driver.session() as session:
        for index_query in indexes:
            try:
                session.run(index_query)
                logger.info(f"✅ Created index: {index_query.split('FOR')[1].split('ON')[0].strip()}")
            except Exception as e:
                logger.warning(f"Index creation failed: {e}")

def main():
    """Main function to run VDRJ import"""
    logger.info("=" * 80)
    logger.info("VDRJ DICTIONARY IMPORT")
    logger.info("=" * 80)
    
    # Load environment and connect to database
    driver = load_environment()
    if not driver:
        logger.error("Cannot proceed without database connection")
        return
    
    try:
        # Parse VDRJ file
        vdrj_file = "networkx_objects/VDRJ_Ver1_1_Research_Top60894.xlsx - 重要度順語彙リスト60894語.tsv"
        vdrj_entries = parse_vdrj_file(vdrj_file)
        
        if not vdrj_entries:
            logger.error("No VDRJ entries found. Exiting.")
            return
        
        logger.info(f"Starting import of {len(vdrj_entries)} VDRJ entries...")
        
        # Statistics
        stats = {
            'total_entries': len(vdrj_entries),
            'matched_words': 0,
            'updated_words': 0,
            'no_matches': 0,
            'errors': 0
        }
        
        # Process each VDRJ entry
        for i, entry in enumerate(vdrj_entries, 1):
            try:
                # Find matching Word nodes
                word_ids = find_matching_words(driver, entry)
                
                if word_ids:
                    stats['matched_words'] += len(word_ids)
                    
                    # Update each matching word
                    for word_id in word_ids:
                        if update_word_with_vdrj_data(driver, word_id, entry):
                            stats['updated_words'] += 1
                        else:
                            stats['errors'] += 1
                else:
                    stats['no_matches'] += 1
                
                # Progress reporting
                if i % 1000 == 0:
                    logger.info(f"Processed {i}/{len(vdrj_entries)} entries...")
                    logger.info(f"  Matched: {stats['matched_words']}, Updated: {stats['updated_words']}, No matches: {stats['no_matches']}")
            
            except Exception as e:
                logger.error(f"Error processing entry {i}: {e}")
                stats['errors'] += 1
                continue
        
        # Create indexes
        create_vdrj_indexes(driver)
        
        # Final statistics
        logger.info("=" * 80)
        logger.info("VDRJ IMPORT COMPLETED")
        logger.info("=" * 80)
        logger.info(f"Total VDRJ entries processed: {stats['total_entries']}")
        logger.info(f"Words matched: {stats['matched_words']}")
        logger.info(f"Words updated: {stats['updated_words']}")
        logger.info(f"No matches found: {stats['no_matches']}")
        logger.info(f"Errors: {stats['errors']}")
        logger.info(f"Success rate: {stats['updated_words']/stats['total_entries']*100:.1f}%")
        
    except Exception as e:
        logger.error(f"Error during VDRJ import: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        if driver:
            driver.close()
            logger.info("Database connection closed")

if __name__ == "__main__":
    main()
