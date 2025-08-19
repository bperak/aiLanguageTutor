#!/usr/bin/env python3
"""
Marugoto Grammar Patterns Importer with Romaji Transcription
===========================================================

This script imports Japanese grammar patterns from the Marugoto textbook series
into Neo4j with automatic romaji generation and AI validation.

Features:
- Automatic romaji generation using pykakasi
- AI validation with Google Gemini for contextual accuracy
- Integration with existing :Word nodes
- Comprehensive error handling and logging

Usage:
    python marugoto_grammar_importer.py
"""

import os
import sys
import pandas as pd
import pykakasi
import asyncio
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

# Configure logging first
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('marugoto_import.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ Loaded environment variables from .env file")
except ImportError:
    print("⚠️ python-dotenv not installed, using system environment variables only")

# Try to import settings from backend, fallback to environment variables
try:
    # Add backend to path for imports
    sys.path.append(str(Path(__file__).parent.parent / "backend"))
    from backend.app.core.config import settings
    logger.info("✅ Using backend settings configuration")
except ImportError:
    # Fallback to environment variables
    logger.info("📝 Using environment variables configuration")
    class Settings:
        def __init__(self):
            self.GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
            self.NEO4J_URI = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
            self.NEO4J_USER = os.getenv('NEO4J_USERNAME', 'neo4j')  # Use NEO4J_USERNAME from .env
            self.NEO4J_PASSWORD = os.getenv('NEO4J_PASSWORD')
            
            # Validate required settings
            if not self.NEO4J_PASSWORD:
                raise ValueError("NEO4J_PASSWORD environment variable is required")
            
            logger.info(f"Neo4j URI: {self.NEO4J_URI}")
            logger.info(f"Neo4j User: {self.NEO4J_USER}")
            logger.info(f"Gemini API Key: {'✅ Set' if self.GEMINI_API_KEY else '❌ Not set'}")
    
    settings = Settings()

from neo4j import GraphDatabase
import google.generativeai as genai

@dataclass
class GrammarPattern:
    """Data class for grammar pattern with romaji transcription"""
    sequence_number: int
    pattern: str
    pattern_romaji: str
    pattern_romaji_validated: str
    textbook_form: str
    textbook_form_romaji: str
    classification: str
    example_sentence: str
    example_romaji: str
    textbook: str
    topic: str
    lesson: str
    jfs_category: str
    validation_notes: Optional[str] = None
    confidence_score: Optional[float] = None

class RomajiGenerator:
    """Handles romaji generation and AI validation"""
    
    def __init__(self):
        """Initialize pykakasi and Gemini AI"""
        # Initialize pykakasi
        self.kks = pykakasi.Kakasi()
        
        # Initialize Gemini AI
        if hasattr(settings, 'GEMINI_API_KEY') and settings.GEMINI_API_KEY:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            self.model = genai.GenerativeModel('gemini-2.5-flash')
            self.ai_available = True
            logger.info("✅ Gemini AI initialized for romaji validation")
        else:
            self.ai_available = False
            logger.warning("⚠️ Gemini API key not found. AI validation disabled.")
    
    def generate_romaji_pykakasi(self, japanese_text: str) -> str:
        """Generate romaji using pykakasi library"""
        try:
            # Handle empty or None input
            if not japanese_text or japanese_text.strip() == '':
                return ''
            
            # Convert to romaji
            result = self.kks.convert(japanese_text)
            romaji = ''.join([item['hepburn'] for item in result])
            
            # Clean up common grammar pattern symbols
            romaji = romaji.replace('〜', '~')
            romaji = romaji.replace('～', '~')
            
            logger.debug(f"pykakasi: '{japanese_text}' → '{romaji}'")
            return romaji
            
        except Exception as e:
            logger.error(f"Error generating romaji for '{japanese_text}': {e}")
            return japanese_text  # Return original if conversion fails
    
    async def validate_romaji_with_ai(self, japanese_text: str, pykakasi_romaji: str, context: str = "grammar") -> Tuple[str, str, float]:
        """Validate and potentially improve romaji using Gemini AI"""
        
        if not self.ai_available:
            return pykakasi_romaji, "AI validation unavailable", 0.8
        
        try:
            prompt = f"""
You are a Japanese language expert specializing in romaji transcription for educational materials.

Task: Validate and potentially improve this romaji transcription for a Japanese grammar pattern.

Japanese text: "{japanese_text}"
Pykakasi romaji: "{pykakasi_romaji}"
Context: This is a {context} pattern from the Marugoto Japanese textbook series.

Instructions:
1. Evaluate the pykakasi romaji for accuracy and learner-friendliness
2. Consider these specific rules:
   - Use Hepburn romanization system
   - Grammar pattern symbols: ～ should be ~
   - Particles: は→wa, を→wo (or o if more learner-friendly), へ→e
   - Long vowels: use macrons (ā, ī, ū, ē, ō) or double vowels (aa, ii, uu, ee, oo)
   - Make it consistent with textbook conventions

3. Provide your response in this exact format:
VALIDATED_ROMAJI: [your improved romaji or the original if it's correct]
CONFIDENCE: [0.0-1.0 confidence score]
NOTES: [brief explanation of any changes made, or "No changes needed"]

Example response:
VALIDATED_ROMAJI: ~wa~desu
CONFIDENCE: 0.95
NOTES: No changes needed, pykakasi output is accurate for this grammar pattern
"""

            response = await asyncio.to_thread(
                self.model.generate_content, 
                prompt
            )
            
            # Parse AI response
            response_text = response.text.strip()
            
            validated_romaji = pykakasi_romaji  # Default fallback
            confidence = 0.8  # Default confidence
            notes = "AI parsing failed"
            
            # Extract validated romaji
            for line in response_text.split('\n'):
                line = line.strip()
                if line.startswith('VALIDATED_ROMAJI:'):
                    validated_romaji = line.replace('VALIDATED_ROMAJI:', '').strip()
                elif line.startswith('CONFIDENCE:'):
                    try:
                        confidence = float(line.replace('CONFIDENCE:', '').strip())
                    except ValueError:
                        confidence = 0.8
                elif line.startswith('NOTES:'):
                    notes = line.replace('NOTES:', '').strip()
            
            logger.debug(f"AI validation: '{japanese_text}' → '{validated_romaji}' (confidence: {confidence})")
            
            return validated_romaji, notes, confidence
            
        except Exception as e:
            logger.error(f"Error in AI validation for '{japanese_text}': {e}")
            return pykakasi_romaji, f"AI validation error: {str(e)}", 0.7
    
    async def generate_romaji_with_validation(self, japanese_text: str, context: str = "grammar") -> Dict[str, str]:
        """Generate romaji with pykakasi and validate with AI"""
        
        # Step 1: Generate with pykakasi
        pykakasi_romaji = self.generate_romaji_pykakasi(japanese_text)
        
        # Step 2: Validate with AI
        validated_romaji, notes, confidence = await self.validate_romaji_with_ai(
            japanese_text, pykakasi_romaji, context
        )
        
        return {
            'original': japanese_text,
            'pykakasi_romaji': pykakasi_romaji,
            'validated_romaji': validated_romaji,
            'validation_notes': notes,
            'confidence_score': confidence
        }

class MarugotoGrammarImporter:
    """Main importer class for Marugoto grammar patterns"""
    
    def __init__(self, neo4j_uri: str, neo4j_user: str, neo4j_password: str):
        """Initialize the importer with Neo4j connection"""
        self.driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
        self.romaji_generator = RomajiGenerator()
        
        # Test Neo4j connection
        try:
            with self.driver.session() as session:
                result = session.run("RETURN 1 as test")
                result.single()
            logger.info("✅ Neo4j connection established")
        except Exception as e:
            logger.error(f"❌ Neo4j connection failed: {e}")
            raise
    
    def __del__(self):
        """Close Neo4j driver on cleanup"""
        if hasattr(self, 'driver'):
            self.driver.close()
    
    async def load_and_process_tsv(self, file_path: str) -> List[GrammarPattern]:
        """Load TSV file and process each grammar pattern"""
        
        logger.info(f"📂 Loading grammar patterns from: {file_path}")
        
        try:
            # Load TSV file, skipping the header row
            df = pd.read_csv(file_path, sep='\t', skiprows=1, encoding='utf-8')
            
            # Verify expected columns exist
            expected_columns = ['ＮＯ', '見出し', '教科書での形', '分類', '例文', '教科書', 'トピック', '課／PＡRT', 'JFSのトピック']
            missing_columns = [col for col in expected_columns if col not in df.columns]
            
            if missing_columns:
                logger.error(f"❌ Missing expected columns: {missing_columns}")
                logger.info(f"Available columns: {list(df.columns)}")
                raise ValueError(f"Missing columns: {missing_columns}")
            
            logger.info(f"📊 Found {len(df)} grammar patterns to process")
            
            # Process each row
            grammar_patterns = []
            
            for index, row in df.iterrows():
                try:
                    # Generate romaji for all Japanese text fields
                    pattern_result = await self.romaji_generator.generate_romaji_with_validation(
                        str(row['見出し']), "grammar_pattern"
                    )
                    
                    textbook_form_result = await self.romaji_generator.generate_romaji_with_validation(
                        str(row['教科書での形']), "textbook_form"
                    )
                    
                    example_result = await self.romaji_generator.generate_romaji_with_validation(
                        str(row['例文']), "example_sentence"
                    )
                    
                    # Create GrammarPattern object
                    grammar_pattern = GrammarPattern(
                        sequence_number=int(row['ＮＯ']),
                        pattern=str(row['見出し']),
                        pattern_romaji=pattern_result['pykakasi_romaji'],
                        pattern_romaji_validated=pattern_result['validated_romaji'],
                        textbook_form=str(row['教科書での形']),
                        textbook_form_romaji=textbook_form_result['validated_romaji'],
                        classification=str(row['分類']),
                        example_sentence=str(row['例文']),
                        example_romaji=example_result['validated_romaji'],
                        textbook=str(row['教科書']),
                        topic=str(row['トピック']),
                        lesson=str(row['課／PＡRT']),
                        jfs_category=str(row['JFSのトピック']),
                        validation_notes=f"Pattern: {pattern_result['validation_notes']}; Example: {example_result['validation_notes']}",
                        confidence_score=min(pattern_result['confidence_score'], example_result['confidence_score'])
                    )
                    
                    grammar_patterns.append(grammar_pattern)
                    
                    if (index + 1) % 10 == 0:
                        logger.info(f"✅ Processed {index + 1}/{len(df)} patterns...")
                        
                except Exception as e:
                    logger.error(f"❌ Error processing row {index + 1}: {e}")
                    continue
            
            logger.info(f"🎉 Successfully processed {len(grammar_patterns)} grammar patterns")
            return grammar_patterns
            
        except Exception as e:
            logger.error(f"❌ Error loading TSV file: {e}")
            raise
    
    def create_supporting_nodes(self):
        """Create supporting nodes (TextbookLevel, Classification, etc.)"""
        
        logger.info("🏗️ Creating supporting nodes...")
        
        with self.driver.session() as session:
            # Create TextbookLevel nodes
            textbook_levels = [
                {"id": "nyumon_rikai", "name": "入門(りかい)", "level_order": 1},
                {"id": "shokyu1_rikai", "name": "初級1(りかい)", "level_order": 2},
                {"id": "shokyu2_rikai", "name": "初級2(りかい)", "level_order": 3},
                {"id": "shochukyu", "name": "初中級", "level_order": 4},
                {"id": "chukyu1", "name": "中級1", "level_order": 5},
                {"id": "chukyu2", "name": "中級2", "level_order": 6},
            ]
            
            for level in textbook_levels:
                session.run("""
                    MERGE (t:TextbookLevel {id: $id})
                    SET t.name = $name,
                        t.level_order = $level_order,
                        t.created_at = datetime(),
                        t.source = 'marugoto_grammar_list'
                """, **level)
            
            logger.info("✅ TextbookLevel nodes created")
    
    def import_grammar_patterns(self, grammar_patterns: List[GrammarPattern]):
        """Import grammar patterns into Neo4j"""
        
        logger.info(f"📥 Importing {len(grammar_patterns)} grammar patterns to Neo4j...")
        
        with self.driver.session() as session:
            for i, pattern in enumerate(grammar_patterns):
                try:
                    # Create GrammarPattern node
                    session.run("""
                        CREATE (g:GrammarPattern {
                            id: $id,
                            sequence_number: $sequence_number,
                            pattern: $pattern,
                            pattern_romaji: $pattern_romaji,
                            pattern_romaji_validated: $pattern_romaji_validated,
                            textbook_form: $textbook_form,
                            textbook_form_romaji: $textbook_form_romaji,
                            classification: $classification,
                            example_sentence: $example_sentence,
                            example_romaji: $example_romaji,
                            textbook: $textbook,
                            topic: $topic,
                            lesson: $lesson,
                            jfs_category: $jfs_category,
                            validation_notes: $validation_notes,
                            confidence_score: $confidence_score,
                            created_at: datetime(),
                            updated_at: datetime(),
                            status: 'approved',
                            source: 'marugoto_grammar_list'
                        })
                    """, 
                        id=f"grammar_{pattern.sequence_number:03d}",
                        sequence_number=pattern.sequence_number,
                        pattern=pattern.pattern,
                        pattern_romaji=pattern.pattern_romaji,
                        pattern_romaji_validated=pattern.pattern_romaji_validated,
                        textbook_form=pattern.textbook_form,
                        textbook_form_romaji=pattern.textbook_form_romaji,
                        classification=pattern.classification,
                        example_sentence=pattern.example_sentence,
                        example_romaji=pattern.example_romaji,
                        textbook=pattern.textbook,
                        topic=pattern.topic,
                        lesson=pattern.lesson,
                        jfs_category=pattern.jfs_category,
                        validation_notes=pattern.validation_notes,
                        confidence_score=pattern.confidence_score
                    )
                    
                    # Create relationships to TextbookLevel
                    textbook_id_map = {
                        "入門(りかい)": "nyumon_rikai",
                        "初級1(りかい)": "shokyu1_rikai", 
                        "初級2(りかい)": "shokyu2_rikai",
                        "初中級": "shochukyu",
                        "中級1": "chukyu1",
                        "中級2": "chukyu2"
                    }
                    
                    textbook_id = textbook_id_map.get(pattern.textbook, "unknown")
                    
                    if textbook_id != "unknown":
                        session.run("""
                            MATCH (g:GrammarPattern {id: $grammar_id})
                            MATCH (t:TextbookLevel {id: $textbook_id})
                            MERGE (g)-[:BELONGS_TO_LEVEL]->(t)
                        """, 
                            grammar_id=f"grammar_{pattern.sequence_number:03d}",
                            textbook_id=textbook_id
                        )
                    
                    if (i + 1) % 25 == 0:
                        logger.info(f"✅ Imported {i + 1}/{len(grammar_patterns)} patterns...")
                        
                except Exception as e:
                    logger.error(f"❌ Error importing pattern {pattern.sequence_number}: {e}")
                    continue
        
        logger.info("🎉 Grammar patterns import completed!")
    
    async def run_import(self, tsv_file_path: str):
        """Run the complete import process"""
        
        logger.info("🚀 Starting Marugoto Grammar Patterns import...")
        
        try:
            # Step 1: Create supporting nodes
            self.create_supporting_nodes()
            
            # Step 2: Load and process TSV data
            grammar_patterns = await self.load_and_process_tsv(tsv_file_path)
            
            # Step 3: Import to Neo4j
            self.import_grammar_patterns(grammar_patterns)
            
            logger.info("🎉 Import completed successfully!")
            
            # Step 4: Generate summary report
            self.generate_import_report(grammar_patterns)
            
        except Exception as e:
            logger.error(f"❌ Import failed: {e}")
            raise
    
    def generate_import_report(self, grammar_patterns: List[GrammarPattern]):
        """Generate a summary report of the import"""
        
        logger.info("📊 Generating import report...")
        
        # Calculate statistics
        total_patterns = len(grammar_patterns)
        avg_confidence = sum(p.confidence_score for p in grammar_patterns if p.confidence_score) / total_patterns
        
        textbook_counts = {}
        classification_counts = {}
        
        for pattern in grammar_patterns:
            textbook_counts[pattern.textbook] = textbook_counts.get(pattern.textbook, 0) + 1
            classification_counts[pattern.classification] = classification_counts.get(pattern.classification, 0) + 1
        
        # Generate report
        report = f"""
📋 MARUGOTO GRAMMAR IMPORT REPORT
================================

📊 Summary Statistics:
- Total patterns imported: {total_patterns}
- Average AI validation confidence: {avg_confidence:.2f}

📚 By Textbook Level:
"""
        for textbook, count in sorted(textbook_counts.items()):
            report += f"- {textbook}: {count} patterns\n"
        
        report += f"\n🏷️ By Classification:\n"
        for classification, count in sorted(classification_counts.items()):
            report += f"- {classification}: {count} patterns\n"
        
        logger.info(report)
        
        # Save report to file
        with open('marugoto_import_report.txt', 'w', encoding='utf-8') as f:
            f.write(report)
        
        logger.info("📄 Report saved to: marugoto_import_report.txt")

async def main():
    """Main function to run the import"""
    
    # Configuration
    TSV_FILE_PATH = "resources/list_of_grammar_and_sentence_patterns (1).xlsx - 文法・文型リスト.tsv"
    
    # Neo4j connection details (from environment or settings)
    NEO4J_URI = settings.NEO4J_URI
    NEO4J_USER = settings.NEO4J_USER
    NEO4J_PASSWORD = settings.NEO4J_PASSWORD
    
    # Verify TSV file exists
    if not os.path.exists(TSV_FILE_PATH):
        logger.error(f"❌ TSV file not found: {TSV_FILE_PATH}")
        return
    
    try:
        # Create importer and run
        importer = MarugotoGrammarImporter(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
        await importer.run_import(TSV_FILE_PATH)
        
    except Exception as e:
        logger.error(f"❌ Import failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
