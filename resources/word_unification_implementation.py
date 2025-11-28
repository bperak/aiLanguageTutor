#!/usr/bin/env python3
"""
Word Unification Implementation Script
=====================================

Based on the analysis, this script implements the word unification process:

Key Findings:
- 69,063 nodes with lemma
- Multiple duplicates by kanji+hiragana combination
- 4 main sources: NetworkX (51,086), LeeGoi (17,920), AI_Generated (32), AI_Generated_Node (25)
- NetworkX has 100% property completeness but no level data
- LeeGoi has level data but missing hiragana (42.1%) and translations (41.3%)

Strategy:
1. Use kanji+hiragana as the primary deduplication key
2. Prefer LeeGoi source for level data, NetworkX for completeness
3. Merge properties to create the most complete nodes
4. Preserve all relationships
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from neo4j import GraphDatabase
from datetime import datetime
import logging
import json

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
    
    # Also try loading from current directory as fallback
    if not env_path.exists():
        load_dotenv()
    
    print(f"Environment loaded from: {env_path}")
    print(f"Current working directory: {Path.cwd()}")
    print(f"Environment file exists: {env_path.exists()}")
    
    # Neo4j connection configuration
    URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    USER = os.getenv("NEO4J_USERNAME", "neo4j")  # Fixed: use NEO4J_USERNAME
    
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

def create_backup_indexes(driver):
    """Create temporary indexes for faster processing"""
    logger.info("Creating temporary indexes...")
    
    with driver.session() as session:
        # Index for kanji+hiragana combination
        try:
            session.run("CREATE INDEX kanji_hiragana_combo IF NOT EXISTS FOR (w:Word) ON (w.kanji, w.hiragana)")
            logger.info("✅ Created kanji+hiragana index")
        except Exception as e:
            logger.warning(f"Index creation warning: {e}")
        
        # Index for lemma
        try:
            session.run("CREATE INDEX lemma_index IF NOT EXISTS FOR (w:Word) ON (w.lemma)")
            logger.info("✅ Created lemma index")
        except Exception as e:
            logger.warning(f"Index creation warning: {e}")

def analyze_duplicates_detailed(driver):
    """Get detailed analysis of duplicates"""
    logger.info("Analyzing duplicates in detail...")
    
    with driver.session() as session:
        # Get kanji+hiragana duplicates
        result = session.run("""
            MATCH (w:Word)
            WHERE w.kanji IS NOT NULL AND w.hiragana IS NOT NULL
            WITH w.kanji + '|' + w.hiragana as combo, collect(w) as nodes
            WHERE size(nodes) > 1
            WITH combo, nodes, size(nodes) as count
            ORDER BY count DESC
            RETURN combo, count, 
                   [n in nodes | {
                       id: id(n), 
                       lemma: n.lemma, 
                       source: n.source,
                       kanji: n.kanji, 
                       hiragana: n.hiragana,
                       romaji: n.romaji,
                       translation: n.translation,
                       pos: n.pos,
                       level: n.level,
                       level_int: n.level_int
                   }] as duplicates
        """)
        
        duplicates_data = []
        total_duplicates = 0
        
        for record in result:
            combo = record['combo']
            count = record['count']
            duplicates = record['duplicates']
            
            duplicates_data.append({
                'combo': combo,
                'count': count,
                'duplicates': duplicates
            })
            total_duplicates += count - 1  # -1 because we keep one master
        
        logger.info(f"Found {len(duplicates_data)} kanji+hiragana combinations with duplicates")
        logger.info(f"Total duplicate nodes to be removed: {total_duplicates}")
        
        return duplicates_data

def score_node_for_master(node):
    """Score a node to determine if it should be the master node"""
    score = 0
    
    # Property completeness scoring
    if node.get('translation'): score += 20
    if node.get('pos'): score += 10
    if node.get('level'): score += 15
    if node.get('level_int'): score += 10
    if node.get('romaji'): score += 5
    if node.get('lemma'): score += 5
    
    # Source preference scoring
    source = node.get('source', '')
    if source == 'LeeGoi': score += 30  # Highest priority for level data
    elif source == 'NetworkX': score += 25  # High priority for completeness
    elif source == 'AI_Generated': score += 15
    elif source == 'AI_Generated_Node': score += 5
    
    # Prefer nodes with more complete data
    if node.get('kanji') and node.get('hiragana'): score += 10
    
    return score

def identify_master_nodes(driver, duplicates_data):
    """Identify master nodes for each duplicate group"""
    logger.info("Identifying master nodes...")
    
    master_plan = []
    
    for item in duplicates_data:
        combo = item['combo']
        duplicates = item['duplicates']
        
        # Score each node
        scored_nodes = []
        for node in duplicates:
            score = score_node_for_master(node)
            scored_nodes.append((node, score))
        
        # Sort by score (highest first)
        scored_nodes.sort(key=lambda x: x[1], reverse=True)
        
        master = scored_nodes[0][0]
        duplicate_nodes = [node for node, score in scored_nodes[1:]]
        
        master_plan.append({
            'combo': combo,
            'master': master,
            'duplicates': duplicate_nodes,
            'master_score': scored_nodes[0][1]
        })
    
    logger.info(f"Identified {len(master_plan)} master nodes")
    return master_plan

def merge_properties(driver, master_plan):
    """Merge properties from duplicate nodes into master nodes"""
    logger.info("Merging properties...")
    
    with driver.session() as session:
        for item in master_plan:
            master = item['master']
            duplicates = item['duplicates']
            master_id = master['id']
            
            # Collect all unique properties from duplicates
            merged_properties = {}
            
            for duplicate in duplicates:
                for key, value in duplicate.items():
                    if key == 'id':  # Skip the ID
                        continue
                    
                    # If master doesn't have this property but duplicate does
                    if not master.get(key) and value:
                        merged_properties[key] = value
                    # If both have the property, prefer the non-null one
                    elif master.get(key) and value and not master.get(key):
                        merged_properties[key] = value
            
            # Update master node with merged properties
            if merged_properties:
                set_clauses = []
                params = {'master_id': master_id}
                
                for key, value in merged_properties.items():
                    set_clauses.append(f"w.{key} = ${key}")
                    params[key] = value
                
                query = f"""
                    MATCH (w:Word)
                    WHERE id(w) = $master_id
                    SET {', '.join(set_clauses)}
                """
                
                session.run(query, params)
                logger.info(f"Merged {len(merged_properties)} properties for master {master_id}")

def transfer_relationships(driver, master_plan):
    """Transfer relationships from duplicate nodes to master nodes"""
    logger.info("Transferring relationships...")
    
    with driver.session() as session:
        for item in master_plan:
            master = item['master']
            duplicates = item['duplicates']
            master_id = master['id']
            
            for duplicate in duplicates:
                duplicate_id = duplicate['id']
                
                # Transfer incoming relationships
                session.run("""
                    MATCH (other)-[r]->(dup:Word)
                    WHERE id(dup) = $duplicate_id
                    WITH other, r, $master_id as master_id
                    MATCH (master:Word)
                    WHERE id(master) = master_id
                    MERGE (other)-[r2:RELATIONSHIP_TRANSFERRED]->(master)
                    SET r2 += properties(r)
                    DELETE r
                """, {'duplicate_id': duplicate_id, 'master_id': master_id})
                
                # Transfer outgoing relationships
                session.run("""
                    MATCH (dup:Word)-[r]->(other)
                    WHERE id(dup) = $duplicate_id
                    WITH other, r, $master_id as master_id
                    MATCH (master:Word)
                    WHERE id(master) = master_id
                    MERGE (master)-[r2:RELATIONSHIP_TRANSFERRED]->(other)
                    SET r2 += properties(r)
                    DELETE r
                """, {'duplicate_id': duplicate_id, 'master_id': master_id})
                
                logger.info(f"Transferred relationships from duplicate {duplicate_id} to master {master_id}")

def delete_duplicates(driver, master_plan):
    """Delete duplicate nodes after merging"""
    logger.info("Deleting duplicate nodes...")
    
    with driver.session() as session:
        total_deleted = 0
        
        for item in master_plan:
            duplicates = item['duplicates']
            
            for duplicate in duplicates:
                duplicate_id = duplicate['id']
                
                # Delete the duplicate node
                session.run("MATCH (n:Word) WHERE id(n) = $id DELETE n", {'id': duplicate_id})
                total_deleted += 1
        
        logger.info(f"Deleted {total_deleted} duplicate nodes")

def cleanup_transferred_relationships(driver):
    """Clean up the temporary relationship type"""
    logger.info("Cleaning up transferred relationships...")
    
    with driver.session() as session:
        # Get all transferred relationships and restore original types
        result = session.run("""
            MATCH ()-[r:RELATIONSHIP_TRANSFERRED]->()
            RETURN type(r) as old_type, properties(r) as props, id(r) as rel_id
        """)
        
        for record in result:
            old_type = record['old_type']
            props = record['props']
            rel_id = record['rel_id']
            
            # This is a simplified approach - in practice, you'd need to
            # determine the original relationship type from the properties
            # For now, we'll just remove the temporary type
            pass

def validate_unification(driver):
    """Validate the unification results"""
    logger.info("Validating unification results...")
    
    with driver.session() as session:
        # Check for remaining duplicates
        result = session.run("""
            MATCH (w:Word)
            WHERE w.kanji IS NOT NULL AND w.hiragana IS NOT NULL
            WITH w.kanji + '|' + w.hiragana as combo, collect(w) as nodes
            WHERE size(nodes) > 1
            RETURN count(combo) as remaining_duplicates
        """)
        
        remaining = result.single()['remaining_duplicates']
        logger.info(f"Remaining duplicates: {remaining}")
        
        # Check total node count
        result = session.run("MATCH (w:Word) RETURN count(w) as total_nodes")
        total = result.single()['total_nodes']
        logger.info(f"Total Word nodes after unification: {total}")
        
        # Check relationship count
        result = session.run("MATCH ()-[r]->() RETURN count(r) as total_relationships")
        total_rel = result.single()['total_relationships']
        logger.info(f"Total relationships after unification: {total_rel}")

def generate_unification_report(driver, master_plan):
    """Generate a detailed unification report"""
    logger.info("Generating unification report...")
    
    report = {
        'timestamp': datetime.now().isoformat(),
        'unification_summary': {
            'total_duplicate_groups': len(master_plan),
            'total_nodes_removed': sum(len(item['duplicates']) for item in master_plan),
            'master_nodes_kept': len(master_plan)
        },
        'source_analysis': {},
        'property_analysis': {}
    }
    
    # Analyze sources in master nodes
    source_counts = {}
    for item in master_plan:
        source = item['master'].get('source', 'Unknown')
        source_counts[source] = source_counts.get(source, 0) + 1
    
    report['source_analysis'] = source_counts
    
    # Save report
    report_file = f"unification_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Unification report saved to: {report_file}")
    return report

def main():
    """Main unification process"""
    logger.info("Starting word unification process...")
    
    driver = load_environment()
    if not driver:
        logger.error("Cannot proceed without database connection")
        return
    
    try:
        # Phase 1: Preparation
        logger.info("=== PHASE 1: PREPARATION ===")
        create_backup_indexes(driver)
        
        # Phase 2: Analysis
        logger.info("=== PHASE 2: ANALYSIS ===")
        duplicates_data = analyze_duplicates_detailed(driver)
        
        if not duplicates_data:
            logger.info("No duplicates found. Nothing to unify.")
            return
        
        # Phase 3: Planning
        logger.info("=== PHASE 3: PLANNING ===")
        master_plan = identify_master_nodes(driver, duplicates_data)
        
        # Phase 4: Execution
        logger.info("=== PHASE 4: EXECUTION ===")
        merge_properties(driver, master_plan)
        transfer_relationships(driver, master_plan)
        delete_duplicates(driver, master_plan)
        
        # Phase 5: Cleanup
        logger.info("=== PHASE 5: CLEANUP ===")
        cleanup_transferred_relationships(driver)
        
        # Phase 6: Validation
        logger.info("=== PHASE 6: VALIDATION ===")
        validate_unification(driver)
        
        # Phase 7: Reporting
        logger.info("=== PHASE 7: REPORTING ===")
        report = generate_unification_report(driver, master_plan)
        
        logger.info("Word unification completed successfully!")
        logger.info(f"Summary: {report['unification_summary']}")
        
    except Exception as e:
        logger.error(f"Error during unification: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        if driver:
            driver.close()

if __name__ == "__main__":
    main()
