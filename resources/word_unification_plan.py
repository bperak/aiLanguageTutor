#!/usr/bin/env python3
"""
Word Unification and Deduplication Plan
=======================================

This script analyzes the current state and creates a plan to:
1. Remove duplicates based on kanji + hiragana combinations
2. Unify word properties across different sources
3. Merge relationships and consolidate data
4. Create a clean, unified word database

Based on the analysis, we have:
- 69,063 nodes with lemma
- 68,350 unique lemma values (99% unique)
- 607 duplicate lemmas identified
- Multiple data sources (LeeGoi, NetworkX, AI_Generated)
- Inconsistent property coverage
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from neo4j import GraphDatabase
import pandas as pd
from collections import defaultdict, Counter
import json
from datetime import datetime

def load_environment():
    """Load environment variables and setup Neo4j connection"""
    env_path = Path(__file__).parent.parent / '.env'
    load_dotenv(env_path)
    
    URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    USER = os.getenv("NEO4J_USERNAME", "neo4j")
    
    # Try environment password first, then fallback to Docker default
    env_password = os.getenv("NEO4J_PASSWORD")
    PASSWORD = env_password if env_password else "testpassword123"
    
    # Handle Docker container URIs
    if URI.startswith("neo4j://neo4j:"):
        URI = URI.replace("neo4j://neo4j:", "bolt://localhost:")
    elif URI.startswith("neo4j://"):
        URI = URI.replace("neo4j://", "bolt://localhost:")
    
    # Test connection with multiple password attempts
    passwords_to_try = [PASSWORD, "testpassword123"]
    
    for i, password in enumerate(passwords_to_try, 1):
        try:
            driver = GraphDatabase.driver(URI, auth=(USER, password))
            with driver.session() as session:
                result = session.run("RETURN 'Connection successful' as status")
                status = result.single()['status']
                print(f"✅ {status}")
            return driver
        except Exception as e:
            if i == len(passwords_to_try):
                print(f"❌ All connection attempts failed: {e}")
                return None
            continue
    
    return None

def analyze_duplicates(driver):
    """Analyze duplicate patterns in the database"""
    if not driver:
        return None
    
    with driver.session() as session:
        print("=" * 80)
        print("DUPLICATE ANALYSIS")
        print("=" * 80)
        
        # 1. Analyze duplicates by kanji + hiragana combination
        print("\n1. DUPLICATES BY KANJI + HIRAGANA COMBINATION:")
        print("-" * 60)
        
        result = session.run("""
            MATCH (w:Word)
            WHERE w.kanji IS NOT NULL AND w.hiragana IS NOT NULL
            WITH w.kanji + '|' + w.hiragana as combo, collect(w) as nodes
            WHERE size(nodes) > 1
            WITH combo, nodes, size(nodes) as count
            ORDER BY count DESC
            LIMIT 20
            RETURN combo, count, 
                   [n in nodes | {id: id(n), lemma: n.lemma, source: n.source, 
                                 kanji: n.kanji, hiragana: n.hiragana, 
                                 translation: n.translation}] as duplicates
        """)
        
        kanji_hiragana_duplicates = []
        for record in result:
            combo = record['combo']
            count = record['count']
            duplicates = record['duplicates']
            kanji_hiragana_duplicates.append({
                'combo': combo,
                'count': count,
                'duplicates': duplicates
            })
            print(f"  {combo} - {count} duplicates")
            for dup in duplicates[:3]:  # Show first 3
                print(f"    ID: {dup['id']}, Lemma: {dup['lemma']}, Source: {dup['source']}")
            if len(duplicates) > 3:
                print(f"    ... and {len(duplicates) - 3} more")
        
        # 2. Analyze duplicates by lemma
        print(f"\n2. DUPLICATES BY LEMMA:")
        print("-" * 60)
        
        result = session.run("""
            MATCH (w:Word)
            WHERE w.lemma IS NOT NULL
            WITH w.lemma as lemma, collect(w) as nodes
            WHERE size(nodes) > 1
            WITH lemma, nodes, size(nodes) as count
            ORDER BY count DESC
            LIMIT 20
            RETURN lemma, count,
                   [n in nodes | {id: id(n), source: n.source, kanji: n.kanji, 
                                 hiragana: n.hiragana, translation: n.translation}] as duplicates
        """)
        
        lemma_duplicates = []
        for record in result:
            lemma = record['lemma']
            count = record['count']
            duplicates = record['duplicates']
            lemma_duplicates.append({
                'lemma': lemma,
                'count': count,
                'duplicates': duplicates
            })
            print(f"  {lemma} - {count} duplicates")
            for dup in duplicates[:3]:  # Show first 3
                print(f"    ID: {dup['id']}, Source: {dup['source']}, Kanji: {dup['kanji']}")
            if len(duplicates) > 3:
                print(f"    ... and {len(duplicates) - 3} more")
        
        # 3. Analyze source distribution
        print(f"\n3. SOURCE DISTRIBUTION:")
        print("-" * 60)
        
        result = session.run("""
            MATCH (w:Word)
            WHERE w.lemma IS NOT NULL
            RETURN w.source as source, count(w) as count
            ORDER BY count DESC
        """)
        
        source_distribution = {}
        for record in result:
            source = record['source']
            count = record['count']
            source_distribution[source] = count
            print(f"  {source}: {count:,} nodes")
        
        # 4. Analyze property completeness by source
        print(f"\n4. PROPERTY COMPLETENESS BY SOURCE:")
        print("-" * 60)
        
        properties_to_check = ['kanji', 'hiragana', 'romaji', 'translation', 'pos', 'level']
        
        for source in source_distribution.keys():
            print(f"\n  Source: {source}")
            for prop in properties_to_check:
                result = session.run(f"""
                    MATCH (w:Word)
                    WHERE w.source = '{source}' AND w.lemma IS NOT NULL
                    RETURN count(w) as total, count(w.{prop}) as with_prop
                """)
                stats = result.single()
                total = stats['total']
                with_prop = stats['with_prop']
                percentage = (with_prop / total * 100) if total > 0 else 0
                print(f"    {prop}: {with_prop:,}/{total:,} ({percentage:.1f}%)")
        
        return {
            'kanji_hiragana_duplicates': kanji_hiragana_duplicates,
            'lemma_duplicates': lemma_duplicates,
            'source_distribution': source_distribution
        }

def create_unification_plan(analysis_data):
    """Create a detailed unification plan"""
    print("\n" + "=" * 80)
    print("WORD UNIFICATION PLAN")
    print("=" * 80)
    
    plan = {
        'timestamp': datetime.now().isoformat(),
        'phases': []
    }
    
    # Phase 1: Analysis and Preparation
    phase1 = {
        'name': 'Phase 1: Analysis and Preparation',
        'description': 'Analyze current state and prepare for unification',
        'steps': [
            {
                'step': 1,
                'action': 'Backup current database',
                'description': 'Create a full backup before making changes',
                'estimated_time': '30 minutes'
            },
            {
                'step': 2,
                'action': 'Create temporary indexes',
                'description': 'Add indexes for kanji+hiragana and lemma for faster processing',
                'estimated_time': '10 minutes'
            },
            {
                'step': 3,
                'action': 'Export duplicate analysis',
                'description': 'Export detailed duplicate analysis for review',
                'estimated_time': '15 minutes'
            }
        ]
    }
    
    # Phase 2: Duplicate Resolution
    phase2 = {
        'name': 'Phase 2: Duplicate Resolution',
        'description': 'Remove duplicates based on kanji+hiragana combination',
        'steps': [
            {
                'step': 1,
                'action': 'Identify master nodes',
                'description': 'For each kanji+hiragana combination, identify the best node to keep',
                'criteria': [
                    'Prefer nodes with more complete properties',
                    'Prefer LeeGoi source over AI_Generated',
                    'Prefer nodes with translations',
                    'Prefer nodes with more relationships'
                ],
                'estimated_time': '45 minutes'
            },
            {
                'step': 2,
                'action': 'Merge properties',
                'description': 'Merge properties from duplicate nodes into master nodes',
                'estimated_time': '60 minutes'
            },
            {
                'step': 3,
                'action': 'Transfer relationships',
                'description': 'Transfer all relationships from duplicate nodes to master nodes',
                'estimated_time': '90 minutes'
            },
            {
                'step': 4,
                'action': 'Delete duplicate nodes',
                'description': 'Remove duplicate nodes after merging',
                'estimated_time': '30 minutes'
            }
        ]
    }
    
    # Phase 3: Property Unification
    phase3 = {
        'name': 'Phase 3: Property Unification',
        'description': 'Standardize and unify properties across all nodes',
        'steps': [
            {
                'step': 1,
                'action': 'Standardize property names',
                'description': 'Ensure consistent property naming across all sources',
                'estimated_time': '30 minutes'
            },
            {
                'step': 2,
                'action': 'Fill missing properties',
                'description': 'Use AI or cross-reference to fill missing translations and other properties',
                'estimated_time': '120 minutes'
            },
            {
                'step': 3,
                'action': 'Validate data quality',
                'description': 'Run validation checks to ensure data integrity',
                'estimated_time': '30 minutes'
            }
        ]
    }
    
    # Phase 4: Optimization
    phase4 = {
        'name': 'Phase 4: Optimization and Cleanup',
        'description': 'Optimize the unified database',
        'steps': [
            {
                'step': 1,
                'action': 'Update indexes',
                'description': 'Update and optimize indexes for the unified schema',
                'estimated_time': '20 minutes'
            },
            {
                'step': 2,
                'action': 'Run performance tests',
                'description': 'Test query performance on the unified database',
                'estimated_time': '30 minutes'
            },
            {
                'step': 3,
                'action': 'Generate final report',
                'description': 'Generate comprehensive report of the unification process',
                'estimated_time': '15 minutes'
            }
        ]
    }
    
    plan['phases'] = [phase1, phase2, phase3, phase4]
    
    # Calculate total estimated time
    total_time = 0
    for phase in plan['phases']:
        for step in phase['steps']:
            time_str = step['estimated_time']
            minutes = int(time_str.split()[0])
            total_time += minutes
    
    plan['total_estimated_time'] = f"{total_time} minutes ({total_time/60:.1f} hours)"
    
    # Print the plan
    print(f"\n📋 UNIFICATION PLAN OVERVIEW:")
    print(f"Total estimated time: {plan['total_estimated_time']}")
    print(f"Number of phases: {len(plan['phases'])}")
    
    for i, phase in enumerate(plan['phases'], 1):
        print(f"\n{i}. {phase['name']}")
        print(f"   {phase['description']}")
        for step in phase['steps']:
            print(f"   {step['step']}. {step['action']} ({step['estimated_time']})")
            if 'criteria' in step:
                for criterion in step['criteria']:
                    print(f"      - {criterion}")
    
    # Save plan to file
    plan_file = f"word_unification_plan_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(plan_file, 'w', encoding='utf-8') as f:
        json.dump(plan, f, indent=2, ensure_ascii=False)
    
    print(f"\n📄 Detailed plan saved to: {plan_file}")
    
    return plan

def generate_unification_script_template():
    """Generate a template script for the unification process"""
    script_content = '''#!/usr/bin/env python3
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
'''
    
    script_file = "word_unification_script.py"
    with open(script_file, 'w', encoding='utf-8') as f:
        f.write(script_content)
    
    print(f"\n📝 Unification script template saved to: {script_file}")
    return script_file

def main():
    """Main function"""
    print("=" * 80)
    print("WORD UNIFICATION PLANNER")
    print("=" * 80)
    
    driver = load_environment()
    if not driver:
        print("❌ Cannot proceed without database connection")
        return
    
    try:
        # Analyze current state
        analysis_data = analyze_duplicates(driver)
        
        if analysis_data:
            # Create unification plan
            plan = create_unification_plan(analysis_data)
            
            # Generate script template
            script_file = generate_unification_script_template()
            
            print("\n" + "=" * 80)
            print("PLANNING COMPLETE!")
            print("=" * 80)
            print("✅ Duplicate analysis completed")
            print("✅ Unification plan created")
            print("✅ Script template generated")
            print("\nNext steps:")
            print("1. Review the analysis and plan")
            print("2. Test the unification script in a development environment")
            print("3. Run the unification process")
            print("4. Validate the results")
        
    except Exception as e:
        print(f"❌ Error during planning: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        if driver:
            driver.close()
            print("\n🔌 Database connection closed")

if __name__ == "__main__":
    main()
