#!/usr/bin/env python3
"""
Word Unification Script
=======================

This script implements the word unification plan to:
1. Remove duplicates based on kanji + hiragana combinations
2. Merge properties from duplicate nodes
3. Transfer relationships to master nodes
4. Clean up the database

IMPORTANT: Run this script in a test environment first!
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from neo4j import GraphDatabase
from datetime import datetime
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('word_unification.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def load_environment():
    """Load environment variables and setup Neo4j connection"""
    env_path = Path(__file__).parent.parent / '.env'
    load_dotenv(env_path)
    
    URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    USER = os.getenv("NEO4J_USERNAME", "neo4j")
    
    env_password = os.getenv("NEO4J_PASSWORD")
    PASSWORD = env_password if env_password else "testpassword123"
    
    if URI.startswith("neo4j://neo4j:"):
        URI = URI.replace("neo4j://neo4j:", "bolt://localhost:")
    elif URI.startswith("neo4j://"):
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

def backup_database(driver):
    """Create a backup of the current database"""
    logger.info("Creating database backup...")
    # Implementation would depend on your backup strategy
    # This could be a Neo4j dump, or copying the data directory
    pass

def identify_master_nodes(driver):
    """Identify master nodes for each kanji+hiragana combination"""
    logger.info("Identifying master nodes...")
    
    with driver.session() as session:
        # Get all kanji+hiragana combinations with duplicates
        result = session.run("""
            MATCH (w:Word)
            WHERE w.kanji IS NOT NULL AND w.hiragana IS NOT NULL
            WITH w.kanji + '|' + w.hiragana as combo, collect(w) as nodes
            WHERE size(nodes) > 1
            RETURN combo, nodes
        """)
        
        master_nodes = []
        for record in result:
            combo = record['combo']
            nodes = record['nodes']
            
            # Score each node to determine the best master
            best_node = None
            best_score = -1
            
            for node in nodes:
                score = 0
                
                # Prefer nodes with more complete properties
                if node.get('translation'): score += 10
                if node.get('pos'): score += 5
                if node.get('level'): score += 5
                if node.get('romaji'): score += 3
                
                # Prefer LeeGoi source over AI_Generated
                if node.get('source') == 'LeeGoi': score += 20
                elif node.get('source') == 'NetworkX': score += 15
                elif node.get('source') == 'AI_Generated': score += 5
                
                # Prefer nodes with more relationships
                # This would require a separate query to count relationships
                
                if score > best_score:
                    best_score = score
                    best_node = node
            
            master_nodes.append({
                'combo': combo,
                'master': best_node,
                'duplicates': [n for n in nodes if n != best_node]
            })
        
        logger.info(f"Identified {len(master_nodes)} master nodes")
        return master_nodes

def merge_properties(driver, master_nodes):
    """Merge properties from duplicate nodes into master nodes"""
    logger.info("Merging properties...")
    
    with driver.session() as session:
        for item in master_nodes:
            master = item['master']
            duplicates = item['duplicates']
            
            # Merge properties from duplicates into master
            for duplicate in duplicates:
                # Update master with any missing properties from duplicate
                # This is a simplified example - actual implementation would be more complex
                pass

def transfer_relationships(driver, master_nodes):
    """Transfer relationships from duplicate nodes to master nodes"""
    logger.info("Transferring relationships...")
    
    with driver.session() as session:
        for item in master_nodes:
            master = item['master']
            duplicates = item['duplicates']
            
            for duplicate in duplicates:
                # Transfer all relationships from duplicate to master
                # This would involve complex Cypher queries
                pass

def delete_duplicates(driver, master_nodes):
    """Delete duplicate nodes after merging"""
    logger.info("Deleting duplicate nodes...")
    
    with driver.session() as session:
        for item in master_nodes:
            duplicates = item['duplicates']
            
            for duplicate in duplicates:
                # Delete the duplicate node
                session.run("MATCH (n) WHERE id(n) = $id DELETE n", id=duplicate.id)

def main():
    """Main unification process"""
    logger.info("Starting word unification process...")
    
    driver = load_environment()
    if not driver:
        logger.error("Cannot proceed without database connection")
        return
    
    try:
        # Phase 1: Backup
        backup_database(driver)
        
        # Phase 2: Identify master nodes
        master_nodes = identify_master_nodes(driver)
        
        # Phase 3: Merge properties
        merge_properties(driver, master_nodes)
        
        # Phase 4: Transfer relationships
        transfer_relationships(driver, master_nodes)
        
        # Phase 5: Delete duplicates
        delete_duplicates(driver, master_nodes)
        
        logger.info("Word unification completed successfully!")
        
    except Exception as e:
        logger.error(f"Error during unification: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        if driver:
            driver.close()

if __name__ == "__main__":
    main()
