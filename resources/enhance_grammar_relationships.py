#!/usr/bin/env python3
"""
Enhance Marugoto Grammar Graph with Additional Relationships
===========================================================

This script adds the missing relationship types to make the grammar graph
more useful for AI-powered learning:

1. USES_WORD - Connect patterns to existing :Word nodes
2. SIMILAR_TO - Connect similar grammar patterns
3. PREREQUISITE_FOR - Learning progression relationships
4. HAS_CLASSIFICATION - Connect to classification nodes

Usage:
    python enhance_grammar_relationships.py
"""

import os
import sys
import asyncio
import logging
from typing import List, Dict, Set
from pathlib import Path
import re

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('enhance_grammar_relationships.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
    logger.info("✅ Loaded environment variables from .env file")
except ImportError:
    logger.warning("⚠️ python-dotenv not installed, using system environment variables only")

# Settings
class Settings:
    def __init__(self):
        self.NEO4J_URI = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
        self.NEO4J_USER = os.getenv('NEO4J_USERNAME', 'neo4j')
        self.NEO4J_PASSWORD = os.getenv('NEO4J_PASSWORD')
        
        if not self.NEO4J_PASSWORD:
            raise ValueError("NEO4J_PASSWORD environment variable is required")

settings = Settings()

from neo4j import GraphDatabase

class GrammarRelationshipEnhancer:
    """Enhance grammar patterns with additional relationships"""
    
    def __init__(self, neo4j_uri: str, neo4j_user: str, neo4j_password: str):
        """Initialize with Neo4j connection"""
        self.driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
        
        # Test connection
        try:
            with self.driver.session() as session:
                result = session.run("RETURN 1 as test")
                result.single()
            logger.info("✅ Neo4j connection established")
        except Exception as e:
            logger.error(f"❌ Neo4j connection failed: {e}")
            raise
    
    def __del__(self):
        """Close Neo4j driver"""
        if hasattr(self, 'driver'):
            self.driver.close()
    
    def create_classification_nodes(self):
        """Create GrammarClassification nodes"""
        
        logger.info("🏷️ Creating GrammarClassification nodes...")
        
        with self.driver.session() as session:
            # Get all unique classifications
            result = session.run("""
                MATCH (g:GrammarPattern)
                RETURN DISTINCT g.classification as classification
            """)
            
            classifications = [record['classification'] for record in result]
            logger.info(f"Found {len(classifications)} unique classifications")
            
            # Create classification nodes
            for classification in classifications:
                session.run("""
                    MERGE (gc:GrammarClassification {id: $id})
                    SET gc.name = $name,
                        gc.created_at = datetime(),
                        gc.source = 'marugoto_grammar_list'
                """, 
                    id=classification.replace(' ', '_').replace('・', '_').replace('（', '_').replace('）', '_'),
                    name=classification
                )
            
            logger.info(f"✅ Created {len(classifications)} GrammarClassification nodes")
    
    def create_has_classification_relationships(self):
        """Create HAS_CLASSIFICATION relationships"""
        
        logger.info("🔗 Creating HAS_CLASSIFICATION relationships...")
        
        with self.driver.session() as session:
            result = session.run("""
                MATCH (g:GrammarPattern)
                MATCH (gc:GrammarClassification {name: g.classification})
                MERGE (g)-[:HAS_CLASSIFICATION]->(gc)
                RETURN count(*) as created
            """)
            
            created = result.single()['created']
            logger.info(f"✅ Created {created} HAS_CLASSIFICATION relationships")
    
    def extract_words_from_examples(self):
        """Extract Japanese words from example sentences and connect to existing :Word nodes"""
        
        logger.info("📝 Connecting grammar patterns to existing :Word nodes...")
        
        with self.driver.session() as session:
            # Get all grammar patterns
            result = session.run("""
                MATCH (g:GrammarPattern)
                RETURN g.id, g.example_sentence, g.pattern
                ORDER BY g.sequence_number
            """)
            
            patterns = list(result)
            connected_count = 0
            
            for pattern in patterns:
                grammar_id = pattern['g.id']
                example = pattern['g.example_sentence']
                pattern_text = pattern['g.pattern']
                
                # Extract potential words (basic approach - could be enhanced)
                # Remove punctuation and split by common separators
                words_in_example = self._extract_japanese_words(example)
                words_in_pattern = self._extract_japanese_words(pattern_text)
                
                all_words = set(words_in_example + words_in_pattern)
                
                # Try to match with existing :Word nodes
                for word in all_words:
                    if len(word) > 0:  # Skip empty strings
                        # Try to find matching Word node by kanji or hiragana
                        match_result = session.run("""
                            MATCH (w:Word)
                            WHERE coalesce(w.standard_orthography, w.kanji) = $word
                               OR w.hiragana = $word OR w.reading_hiragana = $word
                            MATCH (g:GrammarPattern {id: $grammar_id})
                            MERGE (g)-[:USES_WORD]->(w)
                            RETURN count(*) as matched
                        """, word=word, grammar_id=grammar_id)
                        
                        matched = match_result.single()['matched']
                        connected_count += matched
                
                if (patterns.index(pattern) + 1) % 50 == 0:
                    logger.info(f"✅ Processed {patterns.index(pattern) + 1}/{len(patterns)} patterns...")
            
            logger.info(f"✅ Created {connected_count} USES_WORD relationships")
    
    def _extract_japanese_words(self, text: str) -> List[str]:
        """Extract Japanese words from text (basic implementation)"""
        if not text:
            return []
        
        # Remove grammar pattern symbols and punctuation
        text = text.replace('～', '').replace('〜', '').replace('。', '').replace('、', '')
        text = text.replace('（', '').replace('）', '').replace('/', '').replace('　', ' ')
        
        # Split by spaces and common separators
        words = []
        current_word = ""
        
        for char in text:
            # Japanese characters (hiragana, katakana, kanji)
            if '\u3040' <= char <= '\u309F' or '\u30A0' <= char <= '\u30FF' or '\u4E00' <= char <= '\u9FAF':
                current_word += char
            else:
                if current_word:
                    words.append(current_word)
                    current_word = ""
        
        if current_word:
            words.append(current_word)
        
        # Filter out single characters and very short words (except particles)
        particles = ['は', 'が', 'を', 'に', 'で', 'と', 'も', 'か', 'の', 'や', 'へ', 'から', 'まで']
        filtered_words = []
        
        for word in words:
            if len(word) >= 2 or word in particles:
                filtered_words.append(word)
        
        return filtered_words
    
    def create_similar_relationships(self):
        """Create SIMILAR_TO relationships based on classification and pattern structure"""
        
        logger.info("🔄 Creating SIMILAR_TO relationships...")
        
        with self.driver.session() as session:
            # Find patterns with same classification
            result = session.run("""
                MATCH (g1:GrammarPattern), (g2:GrammarPattern)
                WHERE g1.classification = g2.classification 
                AND g1.id < g2.id  // Avoid duplicates
                AND g1.textbook = g2.textbook  // Same textbook level
                MERGE (g1)-[:SIMILAR_TO {reason: 'same_classification_and_level'}]->(g2)
                MERGE (g2)-[:SIMILAR_TO {reason: 'same_classification_and_level'}]->(g1)
                RETURN count(*) as created
            """)
            
            created = result.single()['created']
            logger.info(f"✅ Created {created} SIMILAR_TO relationships (same classification)")
            
            # Find patterns with similar structure (basic pattern matching)
            result = session.run("""
                MATCH (g1:GrammarPattern), (g2:GrammarPattern)
                WHERE g1.id < g2.id
                AND (
                    (g1.pattern CONTAINS '～は～' AND g2.pattern CONTAINS '～は～') OR
                    (g1.pattern CONTAINS '～を～' AND g2.pattern CONTAINS '～を～') OR
                    (g1.pattern CONTAINS '～が～' AND g2.pattern CONTAINS '～が～') OR
                    (g1.pattern CONTAINS '～に～' AND g2.pattern CONTAINS '～に～') OR
                    (g1.pattern CONTAINS '～で～' AND g2.pattern CONTAINS '～で～')
                )
                AND g1.classification <> g2.classification  // Different classification
                MERGE (g1)-[:SIMILAR_TO {reason: 'similar_particle_pattern'}]->(g2)
                MERGE (g2)-[:SIMILAR_TO {reason: 'similar_particle_pattern'}]->(g1)
                RETURN count(*) as created
            """)
            
            created2 = result.single()['created']
            logger.info(f"✅ Created {created2} SIMILAR_TO relationships (similar patterns)")
    
    def create_prerequisite_relationships(self):
        """Create PREREQUISITE_FOR relationships based on textbook progression"""
        
        logger.info("📚 Creating PREREQUISITE_FOR relationships...")
        
        with self.driver.session() as session:
            # Create prerequisites based on textbook level progression
            # Basic patterns in earlier levels are prerequisites for advanced patterns
            
            prerequisite_pairs = [
                ('入門(りかい)', '初級1(りかい)'),
                ('初級1(りかい)', '初級2(りかい)'),
                ('初級2(りかい)', '初中級'),
                ('初中級', '中級1'),
                ('中級1', '中級2')
            ]
            
            total_created = 0
            
            for basic_level, advanced_level in prerequisite_pairs:
                # Connect basic patterns of same classification to advanced ones
                result = session.run("""
                    MATCH (basic:GrammarPattern {textbook: $basic_level})
                    MATCH (advanced:GrammarPattern {textbook: $advanced_level})
                    WHERE basic.classification = advanced.classification
                    AND basic.sequence_number < advanced.sequence_number
                    MERGE (basic)-[:PREREQUISITE_FOR {
                        reason: 'textbook_progression',
                        from_level: $basic_level,
                        to_level: $advanced_level
                    }]->(advanced)
                    RETURN count(*) as created
                """, basic_level=basic_level, advanced_level=advanced_level)
                
                created = result.single()['created']
                total_created += created
                logger.info(f"   {basic_level} → {advanced_level}: {created} relationships")
            
            logger.info(f"✅ Created {total_created} PREREQUISITE_FOR relationships")
    
    def create_topic_and_lesson_nodes(self):
        """Create MarugotoTopic and MarugotoLesson nodes"""
        
        logger.info("📖 Creating MarugotoTopic and MarugotoLesson nodes...")
        
        with self.driver.session() as session:
            # Create Topic nodes
            result = session.run("""
                MATCH (g:GrammarPattern)
                RETURN DISTINCT g.topic as topic, g.textbook as textbook
            """)
            
            topics = list(result)
            for topic_record in topics:
                topic = topic_record['topic']
                textbook = topic_record['textbook']
                
                session.run("""
                    MERGE (mt:MarugotoTopic {id: $id})
                    SET mt.name = $name,
                        mt.textbook = $textbook,
                        mt.created_at = datetime(),
                        mt.source = 'marugoto_grammar_list'
                """, 
                    id=f"{textbook}_{topic}".replace(' ', '_').replace('(', '').replace(')', ''),
                    name=topic,
                    textbook=textbook
                )
            
            logger.info(f"✅ Created {len(topics)} MarugotoTopic nodes")
            
            # Create Lesson nodes
            result = session.run("""
                MATCH (g:GrammarPattern)
                RETURN DISTINCT g.lesson as lesson, g.topic as topic, g.textbook as textbook
            """)
            
            lessons = list(result)
            for lesson_record in lessons:
                lesson = lesson_record['lesson']
                topic = lesson_record['topic']
                textbook = lesson_record['textbook']
                
                session.run("""
                    MERGE (ml:MarugotoLesson {id: $id})
                    SET ml.name = $name,
                        ml.topic = $topic,
                        ml.textbook = $textbook,
                        ml.created_at = datetime(),
                        ml.source = 'marugoto_grammar_list'
                """, 
                    id=f"{textbook}_{topic}_{lesson}".replace(' ', '_').replace('(', '').replace(')', '').replace('/', '_'),
                    name=lesson
                )
            
            logger.info(f"✅ Created {len(lessons)} MarugotoLesson nodes")
    
    def create_topic_lesson_relationships(self):
        """Create relationships between patterns, topics, and lessons"""
        
        logger.info("🔗 Creating topic and lesson relationships...")
        
        with self.driver.session() as session:
            # Connect patterns to topics
            result = session.run("""
                MATCH (g:GrammarPattern)
                MATCH (mt:MarugotoTopic)
                WHERE mt.name = g.topic AND mt.textbook = g.textbook
                MERGE (g)-[:COVERED_IN_TOPIC]->(mt)
                RETURN count(*) as created
            """)
            created1 = result.single()['created']
            
            # Connect patterns to lessons
            result = session.run("""
                MATCH (g:GrammarPattern)
                MATCH (ml:MarugotoLesson)
                WHERE ml.name = g.lesson AND ml.topic = g.topic AND ml.textbook = g.textbook
                MERGE (g)-[:TAUGHT_IN_LESSON]->(ml)
                RETURN count(*) as created
            """)
            created2 = result.single()['created']
            
            # Connect lessons to topics
            result = session.run("""
                MATCH (ml:MarugotoLesson)
                MATCH (mt:MarugotoTopic)
                WHERE mt.name = ml.topic AND mt.textbook = ml.textbook
                MERGE (ml)-[:PART_OF]->(mt)
                RETURN count(*) as created
            """)
            created3 = result.single()['created']
            
            # Connect topics to textbook levels
            result = session.run("""
                MATCH (mt:MarugotoTopic)
                MATCH (tl:TextbookLevel)
                WHERE tl.name = mt.textbook
                MERGE (mt)-[:PART_OF]->(tl)
                RETURN count(*) as created
            """)
            created4 = result.single()['created']
            
            logger.info(f"✅ Created topic/lesson relationships:")
            logger.info(f"   - COVERED_IN_TOPIC: {created1}")
            logger.info(f"   - TAUGHT_IN_LESSON: {created2}")
            logger.info(f"   - PART_OF (lesson→topic): {created3}")
            logger.info(f"   - PART_OF (topic→level): {created4}")
    
    def run_enhancement(self):
        """Run all relationship enhancements"""
        
        logger.info("🚀 Starting Grammar Relationship Enhancement...")
        
        try:
            # Step 1: Create classification nodes and relationships
            self.create_classification_nodes()
            self.create_has_classification_relationships()
            
            # Step 2: Create topic and lesson structure
            self.create_topic_and_lesson_nodes()
            self.create_topic_lesson_relationships()
            
            # Step 3: Connect to existing Word nodes
            self.extract_words_from_examples()
            
            # Step 4: Create learning relationships
            self.create_similar_relationships()
            self.create_prerequisite_relationships()
            
            logger.info("🎉 Grammar relationship enhancement completed!")
            
            # Generate summary
            self.generate_enhancement_report()
            
        except Exception as e:
            logger.error(f"❌ Enhancement failed: {e}")
            raise
    
    def generate_enhancement_report(self):
        """Generate a report of the enhanced relationships"""
        
        logger.info("📊 Generating enhancement report...")
        
        with self.driver.session() as session:
            # Count all relationship types
            result = session.run("""
                MATCH ()-[r]->()
                RETURN type(r) as relationship_type, count(r) as count
                ORDER BY count DESC
            """)
            
            relationships = list(result)
            
            # Count node types
            result = session.run("""
                MATCH (n)
                RETURN DISTINCT labels(n) as node_labels, count(n) as count
                ORDER BY count DESC
            """)
            
            nodes = list(result)
            
            report = f"""
📋 GRAMMAR RELATIONSHIP ENHANCEMENT REPORT
=========================================

📊 Node Statistics:
"""
            for node in nodes:
                labels = ', '.join(node['node_labels'])
                report += f"- {labels}: {node['count']} nodes\n"
            
            report += f"\n🔗 Relationship Statistics:\n"
            for rel in relationships:
                report += f"- {rel['relationship_type']}: {rel['count']} relationships\n"
            
            logger.info(report)
            
            # Save report
            with open('grammar_enhancement_report.txt', 'w', encoding='utf-8') as f:
                f.write(report)
            
            logger.info("📄 Report saved to: grammar_enhancement_report.txt")

def main():
    """Main function"""
    
    try:
        enhancer = GrammarRelationshipEnhancer(
            settings.NEO4J_URI, 
            settings.NEO4J_USER, 
            settings.NEO4J_PASSWORD
        )
        enhancer.run_enhancement()
        
    except Exception as e:
        logger.error(f"❌ Enhancement failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
