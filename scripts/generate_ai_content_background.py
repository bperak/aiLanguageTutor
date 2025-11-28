#!/usr/bin/env python3
"""
Background AI Content Generation Script

Generates AI-enhanced content for words in the lexical graph.
Can be run as a background process to populate content for words that need it.

Usage:
    python scripts/generate_ai_content_background.py --help
    python scripts/generate_ai_content_background.py --difficulty 1-3 --limit 100
    python scripts/generate_ai_content_background.py --word "水" --force
"""

import asyncio
import argparse
import logging
import sys
import os
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
from dotenv import load_dotenv

# Set UTF-8 encoding for Windows console
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.detach())

# Load environment variables from root .env file
project_root = Path(__file__).parent.parent
load_dotenv(project_root / ".env")

# Add the backend directory to the Python path
backend_dir = project_root / "backend"
sys.path.insert(0, str(backend_dir))

from app.db import get_neo4j_session, init_neo4j
from app.services.ai_word_content_service import ai_word_content_service

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ai_content_generation.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class AIContentGenerator:
    """Background AI content generator"""
    
    def __init__(self):
        self.session = None
        self.stats = {
            'processed': 0,
            'successful': 0,
            'failed': 0,
            'skipped': 0,
            'start_time': None,
            'end_time': None
        }
    
    async def initialize(self):
        """Initialize database session"""
        # Initialize Neo4j connection only
        await init_neo4j()
        # Use the same pattern as FastAPI endpoints
        async for session in get_neo4j_session():
            self.session = session
            break
        self.stats['start_time'] = datetime.now()
        logger.info("AI Content Generator initialized")
    
    async def cleanup(self):
        """Cleanup resources"""
        if self.session:
            await self.session.close()
        self.stats['end_time'] = datetime.now()
        logger.info("AI Content Generator cleanup completed")
    
    async def get_words_needing_content(
        self, 
        difficulty_min: int = 1, 
        difficulty_max: int = 6, 
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get words that need AI content generation"""
        
        query = """
        MATCH (w:Word)
        WHERE w.ai_generated_at IS NULL
        AND w.difficulty_numeric >= $difficulty_min
        AND w.difficulty_numeric <= $difficulty_max
        AND w.kanji IS NOT NULL
        AND w.kanji <> ''
        RETURN w.kanji, w.hiragana, w.translation, w.difficulty_numeric, w.pos_primary
        ORDER BY w.difficulty_numeric ASC, w.kanji ASC
        LIMIT $limit
        """
        
        result = await self.session.run(query, 
            difficulty_min=difficulty_min,
            difficulty_max=difficulty_max,
            limit=limit
        )
        
        words = []
        async for record in result:
            words.append({
                'kanji': record['w.kanji'],
                'hiragana': record['w.hiragana'],
                'translation': record['w.translation'],
                'difficulty_level': record['w.difficulty_numeric'],
                'pos': record['w.pos_primary']
            })
        
        return words
    
    async def generate_content_for_word(self, word_kanji: str, force: bool = False) -> bool:
        """Generate AI content for a single word"""
        try:
            logger.info(f"Generating content for: {word_kanji}")
            
            content = await ai_word_content_service.generate_word_content(
                word_kanji=word_kanji,
                session=self.session,
                force_regenerate=force
            )
            
            if content:
                logger.info(f"✅ Successfully generated content for {word_kanji} (confidence: {content.confidence_score:.2f})")
                self.stats['successful'] += 1
                return True
            else:
                logger.warning(f"⚠️ Failed to generate content for {word_kanji}")
                self.stats['failed'] += 1
                return False
                
        except Exception as e:
            logger.error(f"❌ Error generating content for {word_kanji}: {e}")
            self.stats['failed'] += 1
            return False
    
    async def generate_content_batch(
        self, 
        words: List[Dict[str, Any]], 
        force: bool = False,
        delay_between_words: float = 1.0
    ):
        """Generate content for a batch of words"""
        
        logger.info(f"Starting batch generation for {len(words)} words")
        
        for i, word in enumerate(words, 1):
            word_kanji = word['kanji']
            logger.info(f"Processing word {i}/{len(words)}: {word_kanji}")
            
            # Check if content already exists (unless forcing)
            if not force:
                existing_query = """
                MATCH (w:Word {kanji: $kanji})
                WHERE w.ai_generated_at IS NOT NULL
                RETURN w.kanji
                """
                result = await self.session.run(existing_query, kanji=word_kanji)
                if await result.single():
                    logger.info(f"⏭️ Skipping {word_kanji} - content already exists")
                    self.stats['skipped'] += 1
                    continue
            
            # Generate content
            success = await self.generate_content_for_word(word_kanji, force)
            self.stats['processed'] += 1
            
            # Add delay between requests to avoid rate limiting
            if i < len(words) and delay_between_words > 0:
                await asyncio.sleep(delay_between_words)
            
            # Log progress every 10 words
            if i % 10 == 0:
                self.log_progress()
    
    def log_progress(self):
        """Log current progress statistics"""
        elapsed = datetime.now() - self.stats['start_time'] if self.stats['start_time'] else None
        logger.info(f"Progress: {self.stats['processed']} processed, "
                   f"{self.stats['successful']} successful, "
                   f"{self.stats['failed']} failed, "
                   f"{self.stats['skipped']} skipped"
                   f"{f', elapsed: {elapsed}' if elapsed else ''}")
    
    def log_final_stats(self):
        """Log final statistics"""
        total_time = self.stats['end_time'] - self.stats['start_time'] if self.stats['start_time'] and self.stats['end_time'] else None
        
        logger.info("=" * 60)
        logger.info("AI CONTENT GENERATION COMPLETED")
        logger.info("=" * 60)
        logger.info(f"Total processed: {self.stats['processed']}")
        logger.info(f"Successful: {self.stats['successful']}")
        logger.info(f"Failed: {self.stats['failed']}")
        logger.info(f"Skipped: {self.stats['skipped']}")
        if total_time:
            logger.info(f"Total time: {total_time}")
            if self.stats['processed'] > 0:
                avg_time = total_time.total_seconds() / self.stats['processed']
                logger.info(f"Average time per word: {avg_time:.2f} seconds")
        logger.info("=" * 60)

async def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Generate AI content for words in the lexical graph")
    parser.add_argument("--word", type=str, help="Generate content for a specific word")
    parser.add_argument("--difficulty", type=str, default="1-6", help="Difficulty range (e.g., '1-3' or '4-6')")
    parser.add_argument("--limit", type=int, default=50, help="Maximum number of words to process")
    parser.add_argument("--force", action="store_true", help="Force regenerate existing content")
    parser.add_argument("--delay", type=float, default=1.0, help="Delay between requests in seconds")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be processed without actually generating")
    
    args = parser.parse_args()
    
    # Parse difficulty range
    try:
        difficulty_parts = args.difficulty.split('-')
        difficulty_min = int(difficulty_parts[0])
        difficulty_max = int(difficulty_parts[1]) if len(difficulty_parts) > 1 else difficulty_min
    except (ValueError, IndexError):
        logger.error("Invalid difficulty range format. Use format like '1-3' or '4'")
        return
    
    generator = AIContentGenerator()
    
    try:
        await generator.initialize()
        
        if args.word:
            # Generate content for a specific word
            logger.info(f"Generating content for specific word: {args.word}")
            success = await generator.generate_content_for_word(args.word, args.force)
            if success:
                logger.info(f"✅ Successfully generated content for {args.word}")
            else:
                logger.error(f"❌ Failed to generate content for {args.word}")
        else:
            # Generate content for a batch of words
            words = await generator.get_words_needing_content(
                difficulty_min=difficulty_min,
                difficulty_max=difficulty_max,
                limit=args.limit
            )
            
            if not words:
                logger.info("No words found that need AI content generation")
                return
            
            logger.info(f"Found {len(words)} words needing content generation")
            logger.info(f"Difficulty range: {difficulty_min}-{difficulty_max}")
            logger.info(f"Force regenerate: {args.force}")
            
            if args.dry_run:
                logger.info("DRY RUN - Words that would be processed:")
                for i, word in enumerate(words, 1):
                    logger.info(f"{i:3d}. {word['kanji']} ({word['hiragana']}) - {word['translation']} [Level {word['difficulty_level']}]")
                return
            
            await generator.generate_content_batch(
                words=words,
                force=args.force,
                delay_between_words=args.delay
            )
        
    except KeyboardInterrupt:
        logger.info("Generation interrupted by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
    finally:
        await generator.cleanup()
        generator.log_final_stats()

if __name__ == "__main__":
    asyncio.run(main())
