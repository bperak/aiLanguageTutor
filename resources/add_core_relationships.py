#!/usr/bin/env python3
"""
Add Core Relationships to Marugoto Grammar Graph
===============================================

This script adds the essential missing relationships:
1. HAS_CLASSIFICATION - Already done ✅
2. USES_WORD - Connect to existing :Word nodes
3. SIMILAR_TO - Connect similar patterns
4. PREREQUISITE_FOR - Learning progression

Usage:
    python add_core_relationships.py
"""

import os
import sys
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('add_core_relationships.log'),
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
    logger.warning("⚠️ python-dotenv not installed")

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

class CoreRelationshipAdder:
    """Add core relationships to grammar patterns"""
    
    def __init__(self, neo4j_uri: str, neo4j_user: str, neo4j_password: str):
        self.driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
        
        try:
            with self.driver.session() as session:
                result = session.run("RETURN 1 as test")
                result.single()
            logger.info("✅ Neo4j connection established")
        except Exception as e:
            logger.error(f"❌ Neo4j connection failed: {e}")
            raise
    
    def __del__(self):
        if hasattr(self, 'driver'):
            self.driver.close()
    
    def connect_to_word_nodes(self):
        """Connect grammar patterns to existing :Word nodes"""
        
        logger.info("🔗 Connecting grammar patterns to existing :Word nodes...")
        
        with self.driver.session() as session:
            # Simple approach: Connect common words found in examples
            common_connections = [
                ('私', 'watashi'),
                ('です', 'desu'),
                ('は', 'wa'),
                ('が', 'ga'),
                ('を', 'wo'),
                ('に', 'ni'),
                ('で', 'de'),
                ('と', 'to'),
                ('も', 'mo'),
                ('から', 'kara'),
                ('まで', 'made'),
                ('時', 'toki'),
                ('家', 'ie'),
                ('人', 'hito'),
                ('日本語', 'nihongo'),
                ('食べる', 'taberu'),
                ('飲む', 'nomu'),
                ('行く', 'iku'),
                ('来る', 'kuru'),
                ('する', 'suru'),
                ('ある', 'aru'),
                ('いる', 'iru'),
                ('好き', 'suki'),
                ('時間', 'jikan'),
                ('朝', 'asa'),
                ('夜', 'yoru'),
                ('今', 'ima'),
                ('昨日', 'kinou'),
                ('明日', 'ashita')
            ]
            
            total_connected = 0
            
            for word, reading in common_connections:
                # Find grammar patterns containing this word
                result = session.run("""
                    MATCH (g:GrammarPattern)
                    WHERE g.example_sentence CONTAINS $word OR g.pattern CONTAINS $word
                    MATCH (w:Word)
                    WHERE w.kanji = $word OR w.hiragana = $reading
                    MERGE (g)-[:USES_WORD]->(w)
                    RETURN count(*) as connected
                """, word=word, reading=reading)
                
                connected = result.single()['connected']
                total_connected += connected
                
                if connected > 0:
                    logger.info(f"   Connected '{word}' to {connected} patterns")
            
            logger.info(f"✅ Created {total_connected} USES_WORD relationships")
    
    def create_similar_relationships(self):
        """Create SIMILAR_TO relationships"""
        
        logger.info("🔄 Creating SIMILAR_TO relationships...")
        
        with self.driver.session() as session:
            # Similar patterns by classification
            result = session.run("""
                MATCH (g1:GrammarPattern), (g2:GrammarPattern)
                WHERE g1.classification = g2.classification 
                AND g1.id < g2.id  
                MERGE (g1)-[:SIMILAR_TO {reason: 'same_classification'}]->(g2)
                MERGE (g2)-[:SIMILAR_TO {reason: 'same_classification'}]->(g1)
                RETURN count(*) as created
            """)
            
            created1 = result.single()['created']
            logger.info(f"   Same classification: {created1} relationships")
            
            # Similar particle patterns
            particle_patterns = [
                ('～は～', 'wa_pattern'),
                ('～が～', 'ga_pattern'),
                ('～を～', 'wo_pattern'),
                ('～に～', 'ni_pattern'),
                ('～で～', 'de_pattern'),
                ('～と～', 'to_pattern'),
                ('～から～', 'kara_pattern'),
                ('～まで～', 'made_pattern')
            ]
            
            total_created2 = 0
            for pattern, pattern_type in particle_patterns:
                result = session.run("""
                    MATCH (g1:GrammarPattern), (g2:GrammarPattern)
                    WHERE g1.pattern CONTAINS $pattern 
                    AND g2.pattern CONTAINS $pattern
                    AND g1.id < g2.id
                    AND g1.classification <> g2.classification
                    MERGE (g1)-[:SIMILAR_TO {reason: $reason}]->(g2)
                    MERGE (g2)-[:SIMILAR_TO {reason: $reason}]->(g1)
                    RETURN count(*) as created
                """, pattern=pattern, reason=f'similar_{pattern_type}')
                
                created = result.single()['created']
                total_created2 += created
                
                if created > 0:
                    logger.info(f"   {pattern}: {created} relationships")
            
            logger.info(f"✅ Created {created1 + total_created2} SIMILAR_TO relationships")
    
    def create_prerequisite_relationships(self):
        """Create PREREQUISITE_FOR relationships based on textbook progression"""
        
        logger.info("📚 Creating PREREQUISITE_FOR relationships...")
        
        with self.driver.session() as session:
            # Textbook level progression
            level_progression = [
                ('入門(りかい)', '初級1(りかい)'),
                ('初級1(りかい)', '初級2(りかい)'),
                ('初級2(りかい)', '初中級'),
                ('初中級', '中級1'),
                ('中級1', '中級2')
            ]
            
            total_created = 0
            
            for basic_level, advanced_level in level_progression:
                # Connect patterns of same classification across levels
                result = session.run("""
                    MATCH (basic:GrammarPattern {textbook: $basic_level})
                    MATCH (advanced:GrammarPattern {textbook: $advanced_level})
                    WHERE basic.classification = advanced.classification
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
            
            # Basic prerequisite patterns (foundational grammar)
            foundational_patterns = [
                '～は～です',
                '～を～ます',
                '～が好き',
                '～に～がある'
            ]
            
            for foundation in foundational_patterns:
                result = session.run("""
                    MATCH (foundation:GrammarPattern)
                    WHERE foundation.pattern = $foundation_pattern
                    MATCH (other:GrammarPattern)
                    WHERE other.pattern <> $foundation_pattern
                    AND other.textbook IN ['初級1(りかい)', '初級2(りかい)', '初中級', '中級1', '中級2']
                    AND foundation.sequence_number < other.sequence_number
                    MERGE (foundation)-[:PREREQUISITE_FOR {
                        reason: 'foundational_grammar'
                    }]->(other)
                    RETURN count(*) as created
                """, foundation_pattern=foundation)
                
                created = result.single()['created']
                if created > 0:
                    total_created += created
                    logger.info(f"   Foundation '{foundation}': {created} relationships")
            
            logger.info(f"✅ Created {total_created} PREREQUISITE_FOR relationships")
    
    def create_jfs_category_relationships(self):
        """Create JFSCategory nodes and relationships"""
        
        logger.info("🏷️ Creating JFSCategory relationships...")
        
        with self.driver.session() as session:
            # Get unique JFS categories
            result = session.run("""
                MATCH (g:GrammarPattern)
                RETURN DISTINCT g.jfs_category as category
            """)
            
            categories = [record['category'] for record in result]
            
            # Create JFSCategory nodes
            for category in categories:
                session.run("""
                    MERGE (jfs:JFSCategory {id: $id})
                    SET jfs.name = $name,
                        jfs.created_at = datetime(),
                        jfs.source = 'marugoto_grammar_list'
                """, 
                    id=category.replace(' ', '_').replace('（', '_').replace('）', '_'),
                    name=category
                )
            
            # Create CATEGORIZED_AS relationships
            result = session.run("""
                MATCH (g:GrammarPattern)
                MATCH (jfs:JFSCategory {name: g.jfs_category})
                MERGE (g)-[:CATEGORIZED_AS]->(jfs)
                RETURN count(*) as created
            """)
            
            created = result.single()['created']
            logger.info(f"✅ Created {len(categories)} JFSCategory nodes and {created} relationships")
    
    def run_enhancement(self):
        """Run all core relationship enhancements"""
        
        logger.info("🚀 Adding core relationships to grammar graph...")
        
        try:
            # Step 1: Connect to existing Word nodes
            self.connect_to_word_nodes()
            
            # Step 2: Create similarity relationships
            self.create_similar_relationships()
            
            # Step 3: Create prerequisite relationships
            self.create_prerequisite_relationships()
            
            # Step 4: Create JFS category relationships
            self.create_jfs_category_relationships()
            
            logger.info("🎉 Core relationship enhancement completed!")
            
            # Generate summary
            self.generate_summary()
            
        except Exception as e:
            logger.error(f"❌ Enhancement failed: {e}")
            raise
    
    def generate_summary(self):
        """Generate a summary of all relationships"""
        
        logger.info("📊 Generating relationship summary...")
        
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
📋 GRAMMAR GRAPH RELATIONSHIP SUMMARY
====================================

📊 Node Types:
"""
            for node in nodes:
                labels = ', '.join(node['node_labels'])
                report += f"- {labels}: {node['count']} nodes\n"
            
            report += f"\n🔗 Relationship Types:\n"
            for rel in relationships:
                report += f"- {rel['relationship_type']}: {rel['count']} relationships\n"
            
            logger.info(report)
            
            # Save report
            with open('core_relationships_summary.txt', 'w', encoding='utf-8') as f:
                f.write(report)
            
            logger.info("📄 Summary saved to: core_relationships_summary.txt")

def main():
    """Main function"""
    
    try:
        adder = CoreRelationshipAdder(
            settings.NEO4J_URI, 
            settings.NEO4J_USER, 
            settings.NEO4J_PASSWORD
        )
        adder.run_enhancement()
        
    except Exception as e:
        logger.error(f"❌ Enhancement failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
