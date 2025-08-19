"""
Enhanced Lee's 分類語彙表 Vocabulary Importer
Imports structured Japanese vocabulary data into Neo4j knowledge graph.
"""

import asyncio
import csv
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import structlog
from neo4j import AsyncGraphDatabase
import pandas as pd
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = structlog.get_logger()


class LeeVocabularyImporter:
    """Import Lee's 分類語彙表 vocabulary data into Neo4j."""
    
    def __init__(self, neo4j_uri: str, neo4j_user: str, neo4j_password: str):
        self.driver = AsyncGraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
        self.imported_count = 0
        self.skipped_count = 0
        self.error_count = 0
    
    async def close(self):
        """Close Neo4j connection."""
        await self.driver.close()
    
    def parse_difficulty_level(self, level_str: str) -> Tuple[int, str, str]:
        """
        Parse difficulty level string into components.
        
        Args:
            level_str: e.g., "1.Beg1 1.初級前半" or "2.初級後半"
            
        Returns:
            Tuple of (numeric_level, stage, substage)
        """
        # Clean up the level string
        level_clean = level_str.strip()
        
        # Extract numeric level (1-6)
        numeric_match = re.match(r'^(\d+)', level_clean)
        if not numeric_match:
            logger.warning("Could not parse numeric level", level=level_clean)
            return (0, "unknown", "unknown")
        
        numeric_level = int(numeric_match.group(1))
        
        # Extract stage and substage
        if "初級前半" in level_clean:
            return (numeric_level, "初級", "前半")
        elif "初級後半" in level_clean:
            return (numeric_level, "初級", "後半")
        elif "中級前半" in level_clean:
            return (numeric_level, "中級", "前半")
        elif "中級後半" in level_clean:
            return (numeric_level, "中級", "後半")
        elif "上級前半" in level_clean:
            return (numeric_level, "上級", "前半")
        elif "上級後半" in level_clean:
            return (numeric_level, "上級", "後半")
        else:
            logger.warning("Could not parse stage/substage", level=level_clean)
            return (numeric_level, "unknown", "unknown")
    
    def parse_pos_tags(self, pos1: str, pos2: str) -> Tuple[str, str, str]:
        """
        Parse POS tags into hierarchical components.
        
        Args:
            pos1: Primary POS (e.g., "名詞")
            pos2: Detailed POS (e.g., "名詞-普通名詞-一般")
            
        Returns:
            Tuple of (primary, secondary, tertiary)
        """
        # Use pos2 as the main source since it's more detailed
        pos_parts = pos2.split('-') if pos2 else [pos1] if pos1 else ["unknown"]
        
        primary = pos_parts[0] if len(pos_parts) > 0 else pos1
        secondary = pos_parts[1] if len(pos_parts) > 1 else ""
        tertiary = pos_parts[2] if len(pos_parts) > 2 else ""
        
        return (primary.strip(), secondary.strip(), tertiary.strip())
    
    async def create_difficulty_levels(self, session):
        """Create all difficulty level nodes."""
        levels = [
            {"level": "1.初級前半", "numeric": 1, "stage": "初級", "substage": "前半"},
            {"level": "2.初級後半", "numeric": 2, "stage": "初級", "substage": "後半"},
            {"level": "3.中級前半", "numeric": 3, "stage": "中級", "substage": "前半"},
            {"level": "4.中級後半", "numeric": 4, "stage": "中級", "substage": "後半"},
            {"level": "5.上級前半", "numeric": 5, "stage": "上級", "substage": "前半"},
            {"level": "6.上級後半", "numeric": 6, "stage": "上級", "substage": "後半"},
        ]
        
        for level_data in levels:
            await session.run("""
                MERGE (d:DifficultyLevel {level: $level})
                SET d.numeric_level = $numeric,
                    d.stage = $stage,
                    d.substage = $substage,
                    d.description = $stage + $substage,
                    d.created_at = datetime()
            """, **level_data)
        
        logger.info("Created difficulty level nodes")
    
    async def create_etymology_nodes(self, session):
        """Create etymology classification nodes."""
        etymologies = [
            {
                "type": "和語", 
                "name_en": "Native Japanese",
                "description": "Words of native Japanese origin (Yamato-kotoba)"
            },
            {
                "type": "漢語", 
                "name_en": "Sino-Japanese",
                "description": "Words derived from Chinese (Kango)"
            },
            {
                "type": "外来語", 
                "name_en": "Foreign loanwords",
                "description": "Words borrowed from foreign languages (mainly Western)"
            },
            {
                "type": "混種語", 
                "name_en": "Hybrid words",
                "description": "Words combining different etymological sources"
            }
        ]
        
        for etym in etymologies:
            await session.run("""
                MERGE (e:Etymology {type: $type})
                SET e.name_en = $name_en,
                    e.description = $description,
                    e.created_at = datetime()
            """, **etym)
        
        logger.info("Created etymology nodes")
    
    async def import_vocabulary_batch(self, session, words_batch: List[Dict]) -> int:
        """Import a batch of vocabulary words."""
        imported = 0
        
        for word_data in words_batch:
            try:
                # Parse difficulty level
                numeric_level, stage, substage = self.parse_difficulty_level(word_data['difficulty'])
                
                # Parse POS tags
                pos_primary, pos_secondary, pos_tertiary = self.parse_pos_tags(
                    word_data['pos1'], word_data['pos2']
                )
                
                # Create word node
                result = await session.run("""
                    MERGE (w:Word {lee_id: $lee_id})
                    SET w.kanji = $kanji,
                        w.katakana = $katakana,
                        w.difficulty_level = $difficulty_level,
                        w.difficulty_numeric = $difficulty_numeric,
                        w.pos_primary = $pos_primary,
                        w.pos_detailed = $pos_detailed,
                        w.etymology = $etymology,
                        w.source = 'lee_vocab',
                        w.created_at = datetime(),
                        w.updated_at = datetime()
                    
                    // Create relationships
                    WITH w
                    MERGE (d:DifficultyLevel {level: $difficulty_level})
                    MERGE (w)-[:HAS_DIFFICULTY]->(d)
                    
                    WITH w
                    MERGE (p:POSTag {tag: $pos_detailed})
                    SET p.primary_pos = $pos_primary,
                        p.secondary_pos = $pos_secondary,
                        p.tertiary_pos = $pos_tertiary,
                        p.created_at = coalesce(p.created_at, datetime())
                    MERGE (w)-[:HAS_POS]->(p)
                    
                    WITH w
                    MERGE (e:Etymology {type: $etymology})
                    MERGE (w)-[:HAS_ETYMOLOGY]->(e)
                    
                    RETURN w.lee_id as imported_id
                """, {
                    'lee_id': word_data['lee_id'],
                    'kanji': word_data['kanji'],
                    'katakana': word_data['katakana'],
                    'difficulty_level': word_data['difficulty'],
                    'difficulty_numeric': numeric_level,
                    'pos_primary': pos_primary,
                    'pos_detailed': word_data['pos2'],
                    'pos_secondary': pos_secondary,
                    'pos_tertiary': pos_tertiary,
                    'etymology': word_data['etymology']
                })
                
                if await result.single():
                    imported += 1
                    
            except Exception as e:
                logger.error("Error importing word", 
                           word_id=word_data.get('lee_id'),
                           kanji=word_data.get('kanji'),
                           error=str(e))
                self.error_count += 1
        
        return imported
    
    async def load_and_import_vocabulary(self, file_path: Path) -> Dict[str, int]:
        """
        Load Lee's vocabulary file and import into Neo4j.
        
        Args:
            file_path: Path to the TSV file
            
        Returns:
            Dict with import statistics
        """
        logger.info("Starting Lee vocabulary import", file=str(file_path))
        
        # Read TSV file
        try:
            df = pd.read_csv(file_path, sep='\t', encoding='utf-8')
            logger.info("Loaded vocabulary file", rows=len(df))
        except Exception as e:
            logger.error("Failed to load vocabulary file", error=str(e))
            raise
        
        # Prepare data
        words_data = []
        for _, row in df.iterrows():
            word_data = {
                'lee_id': int(row['No']) if pd.notna(row['No']) else None,
                'kanji': str(row['Standard orthography (kanji or other) 標準的な表記']).strip(),
                'katakana': str(row['Katakana reading 読み']).strip(),
                'difficulty': str(row['Level 語彙の難易度']).strip(),
                'pos1': str(row['品詞1']).strip() if pd.notna(row['品詞1']) else '',
                'pos2': str(row['品詞2(詳細)']).strip() if pd.notna(row['品詞2(詳細)']) else '',
                'etymology': str(row['語種']).strip() if pd.notna(row['語種']) else ''
            }
            
            # Skip invalid entries
            if not word_data['kanji'] or word_data['kanji'] == 'nan':
                self.skipped_count += 1
                continue
                
            words_data.append(word_data)
        
        # Import in batches
        async with self.driver.session() as session:
            # Create supporting nodes first
            await self.create_difficulty_levels(session)
            await self.create_etymology_nodes(session)
            
            # Import words in batches of 1000
            batch_size = 1000
            total_imported = 0
            
            for i in range(0, len(words_data), batch_size):
                batch = words_data[i:i + batch_size]
                batch_imported = await self.import_vocabulary_batch(session, batch)
                total_imported += batch_imported
                
                logger.info("Imported batch", 
                          batch_num=i // batch_size + 1,
                          batch_size=len(batch),
                          batch_imported=batch_imported,
                          total_imported=total_imported)
        
        self.imported_count = total_imported
        
        return {
            'imported': self.imported_count,
            'skipped': self.skipped_count,
            'errors': self.error_count,
            'total_processed': len(words_data)
        }


async def main():
    """Main import function."""
    import os
    from pathlib import Path
    
    # Configuration
    NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687").replace("neo4j://neo4j:7687", "bolt://localhost:7687")
    NEO4J_USER = os.getenv("NEO4J_USERNAME", "neo4j")
    NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")
    
    # File path
    vocab_file = Path("resources/Lee李  分類語彙表学習者用goi.xlsx - Sheet1.tsv")
    
    if not vocab_file.exists():
        logger.error("Vocabulary file not found", path=str(vocab_file))
        return
    
    # Import vocabulary
    importer = LeeVocabularyImporter(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    
    try:
        stats = await importer.load_and_import_vocabulary(vocab_file)
        logger.info("Import completed", **stats)
    except Exception as e:
        logger.error("Import failed", error=str(e))
    finally:
        await importer.close()


if __name__ == "__main__":
    asyncio.run(main())
