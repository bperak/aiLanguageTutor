#!/usr/bin/env python3
"""
Neo4j Database Explorer

This script provides a comprehensive exploration of the current state of your Neo4j graph database 
for the AI Language Tutor project.

What This Script Does:
1. Database Overview: Connection status, basic statistics
2. Node Analysis: All node labels, counts, and property schemas
3. Relationship Analysis: All relationship types, counts, and properties
4. Data Quality Checks: Missing properties, data consistency
5. Graph Pattern Analysis: Connectivity and common patterns
6. Performance Metrics: Database size, index status

Prerequisites:
- Neo4j database running (via Docker or local)
- Environment variables set in .env file
- Required Python packages: neo4j, python-dotenv, pandas, matplotlib, seaborn
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from neo4j import GraphDatabase
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from collections import defaultdict, Counter
import json
from datetime import datetime

# Set up plotting
plt.style.use('default')
sns.set_palette("husl")

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
    passwords_to_try = [PASSWORD, "testpassword123"]
    
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

def get_database_overview(driver):
    """Get basic database statistics and overview"""
    if not driver:
        return None
    
    with driver.session() as session:
        # Get database info
        result = session.run("CALL dbms.components() YIELD name, versions, edition")
        db_info = result.single()
        
        # Get node and relationship counts
        result = session.run("MATCH (n) RETURN count(n) as node_count")
        node_count = result.single()['node_count']
        
        result = session.run("MATCH ()-[r]->() RETURN count(r) as rel_count")
        rel_count = result.single()['rel_count']
        
        return {
            'version': db_info['versions'][0] if db_info else 'Unknown',
            'edition': db_info['edition'] if db_info else 'Unknown',
            'node_count': node_count,
            'relationship_count': rel_count,
            'total_elements': node_count + rel_count
        }

def analyze_node_labels(driver):
    """Analyze all node labels and their properties"""
    if not driver:
        return None
    
    with driver.session() as session:
        # Get all labels with counts
        result = session.run("""
            CALL db.labels() YIELD label
            CALL {
                WITH label
                MATCH (n)
                WHERE label IN labels(n)
                RETURN count(n) as count
            }
            RETURN label, count
            ORDER BY count DESC
        """)
        
        labels_data = []
        for record in result:
            labels_data.append({
                'label': record['label'],
                'count': record['count']
            })
        
        # Create DataFrame for visualization
        df_labels = pd.DataFrame(labels_data)
        
        # Plot node label distribution
        plt.figure(figsize=(12, 6))
        plt.subplot(1, 2, 1)
        plt.pie(df_labels['count'], labels=df_labels['label'], autopct='%1.1f%%')
        plt.title('Node Distribution by Label')
        
        plt.subplot(1, 2, 2)
        plt.bar(df_labels['label'], df_labels['count'])
        plt.title('Node Count by Label')
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig('node_labels_analysis.png', dpi=300, bbox_inches='tight')
        plt.show()
        
        return df_labels

def analyze_node_properties(driver):
    """Analyze properties for each node label"""
    if not driver:
        return None
    
    with driver.session() as session:
        # Get all labels
        result = session.run("CALL db.labels() YIELD label")
        labels = [record['label'] for record in result]
        
        all_properties = {}
        
        for label in labels:
            # Get properties for this label
            result = session.run(f"""
                MATCH (n:{label})
                WITH n LIMIT 1000
                UNWIND keys(n) as key
                WITH key, count(key) as freq
                RETURN key, freq
                ORDER BY freq DESC
            """)
            
            properties = {}
            for record in result:
                properties[record['key']] = record['freq']
            
            all_properties[label] = properties
        
        # Create a comprehensive properties table
        all_keys = set()
        for props in all_properties.values():
            all_keys.update(props.keys())
        
        properties_matrix = []
        for label in labels:
            row = {'label': label}
            for key in sorted(all_keys):
                row[key] = all_properties[label].get(key, 0)
            properties_matrix.append(row)
        
        df_properties = pd.DataFrame(properties_matrix)
        df_properties = df_properties.set_index('label')
        
        # Show properties heatmap
        plt.figure(figsize=(16, 8))
        sns.heatmap(df_properties, annot=True, fmt='d', cmap='YlOrRd')
        plt.title('Node Properties Distribution by Label')
        plt.xlabel('Property Names')
        plt.ylabel('Node Labels')
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig('node_properties_heatmap.png', dpi=300, bbox_inches='tight')
        plt.show()
        
        return df_properties

def analyze_relationships(driver):
    """Analyze all relationship types and their properties"""
    if not driver:
        return None
    
    with driver.session() as session:
        # Get all relationship types with counts
        result = session.run("""
            CALL db.relationshipTypes() YIELD relationshipType
            CALL {
                WITH relationshipType
                MATCH ()-[r]->()
                WHERE type(r) = relationshipType
                RETURN count(r) as count
            }
            RETURN relationshipType, count
            ORDER BY count DESC
        """)
        
        rel_data = []
        for record in result:
            rel_data.append({
                'type': record['relationshipType'],
                'count': record['count']
            })
        
        df_relationships = pd.DataFrame(rel_data)
        
        # Plot relationship distribution
        plt.figure(figsize=(14, 6))
        plt.subplot(1, 2, 1)
        plt.pie(df_relationships['count'], labels=df_relationships['type'], autopct='%1.1f%%')
        plt.title('Relationship Distribution by Type')
        
        plt.subplot(1, 2, 2)
        plt.bar(df_relationships['type'], df_relationships['count'])
        plt.title('Relationship Count by Type')
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig('relationship_analysis.png', dpi=300, bbox_inches='tight')
        plt.show()
        
        return df_relationships

def analyze_relationship_properties(driver):
    """Analyze properties for each relationship type"""
    if not driver:
        return None
    
    with driver.session() as session:
        # Get all relationship types
        result = session.run("CALL db.relationshipTypes() YIELD relationshipType")
        rel_types = [record['relationshipType'] for record in result]
        
        all_rel_properties = {}
        
        for rel_type in rel_types:
            # Get properties for this relationship type
            result = session.run(f"""
                MATCH ()-[r:{rel_type}]->()
                WITH r LIMIT 1000
                UNWIND keys(r) as key
                WITH key, count(key) as freq
                RETURN key, freq
                ORDER BY freq DESC
            """)
            
            properties = {}
            for record in result:
                properties[record['key']] = record['freq']
            
            all_rel_properties[rel_type] = properties
        
        # Create properties matrix
        all_keys = set()
        for props in all_rel_properties.values():
            all_keys.update(props.keys())
        
        rel_properties_matrix = []
        for rel_type in rel_types:
            row = {'type': rel_type}
            for key in sorted(all_keys):
                row[key] = all_rel_properties[rel_type].get(key, 0)
            rel_properties_matrix.append(row)
        
        df_rel_properties = pd.DataFrame(rel_properties_matrix)
        df_rel_properties = df_rel_properties.set_index('type')
        
        # Show properties heatmap
        plt.figure(figsize=(16, 8))
        sns.heatmap(df_rel_properties, annot=True, fmt='d', cmap='Blues')
        plt.title('Relationship Properties Distribution by Type')
        plt.xlabel('Property Names')
        plt.ylabel('Relationship Types')
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig('relationship_properties_heatmap.png', dpi=300, bbox_inches='tight')
        plt.show()
        
        return df_rel_properties

def analyze_data_quality(driver):
    """Analyze data quality and consistency issues"""
    if not driver:
        return None
    
    with driver.session() as session:
        print("=" * 60)
        print("DATA QUALITY ANALYSIS")
        print("=" * 60)
        
        # Check for nodes without labels
        result = session.run("""
            MATCH (n)
            WHERE labels(n) = []
            RETURN count(n) as unlabeled_count
        """)
        unlabeled = result.single()['unlabeled_count']
        print(f"\nUnlabeled nodes: {unlabeled}")
        
        # Check for isolated nodes
        result = session.run("""
            MATCH (n)
            WHERE NOT (n)--()
            RETURN count(n) as isolated_count
        """)
        isolated = result.single()['isolated_count']
        print(f"Isolated nodes: {isolated}")
        
        # Check for duplicate lemmas in Word nodes
        result = session.run("""
            MATCH (w:Word)
            WHERE w.lemma IS NOT NULL
            WITH w.lemma as lemma, count(w) as count
            WHERE count > 1
            RETURN count(lemma) as duplicate_lemmas
        """)
        duplicates = result.single()['duplicate_lemmas']
        print(f"Duplicate lemmas: {duplicates}")
        
        # Check for missing critical properties
        result = session.run("""
            MATCH (w:Word)
            RETURN 
                count(w) as total_words,
                count(w.lemma) as with_lemma,
                count(w.romaji) as with_romaji
        """)
        word_stats = result.single()
        
        print(f"\nWord Node Property Completeness:")
        print(f"  Total words: {word_stats['total_words']}")
        print(f"  With lemma: {word_stats['with_lemma']} ({word_stats['with_lemma']/word_stats['total_words']*100:.1f}%)")
        print(f"  With romaji: {word_stats['with_romaji']} ({word_stats['with_romaji']/word_stats['total_words']*100:.1f}%)")
        
        return {
            'unlabeled_nodes': unlabeled,
            'isolated_nodes': isolated,
            'duplicate_lemmas': duplicates,
            'word_stats': word_stats
        }

def explore_sample_data(driver):
    """Explore sample data from different node types"""
    if not driver:
        return None
    
    with driver.session() as session:
        print("=" * 60)
        print("SAMPLE DATA EXPLORATION")
        print("=" * 60)
        
        # Sample Word nodes
        print("\n📚 Sample Word Nodes:")
        result = session.run("""
            MATCH (w:Word)
            RETURN w.lemma as lemma, w.romaji as romaji
            LIMIT 5
        """)
        
        for i, record in enumerate(result, 1):
            print(f"  {i}. {record['lemma']} | {record['romaji']}")
        
        # Sample relationships
        print("\n🔗 Sample Relationships:")
        result = session.run("""
            MATCH (a)-[r]->(b)
            RETURN labels(a)[0] as from_label, a.lemma as from_lemma, 
                   type(r) as rel_type, labels(b)[0] as to_label, b.lemma as to_lemma
            LIMIT 5
        """)
        
        for i, record in enumerate(result, 1):
            print(f"  {i}. ({record['from_label']}) {record['from_lemma']} -[{record['rel_type']}]-> ({record['to_label']}) {record['to_lemma']}")

def analyze_graph_patterns(driver):
    """Analyze common graph patterns and connectivity"""
    if not driver:
        return None
    
    with driver.session() as session:
        print("=" * 60)
        print("GRAPH PATTERN ANALYSIS")
        print("=" * 60)
        
        # Most connected nodes
        print("\n🔗 Most Connected Nodes:")
        result = session.run("""
            MATCH (n)
            WITH n, COUNT{(n)--()} as degree
            ORDER BY degree DESC
            LIMIT 10
            RETURN labels(n)[0] as label, n.lemma as lemma, degree
        """)
        
        for record in result:
            print(f"  {record['label']}: {record['lemma']} (degree: {record['degree']})")
        
        # Common relationship patterns
        print("\n📊 Common Relationship Patterns:")
        result = session.run("""
            MATCH (a)-[r]->(b)
            WITH labels(a)[0] as from_label, type(r) as rel_type, labels(b)[0] as to_label, count(r) as count
            ORDER BY count DESC
            LIMIT 10
            RETURN from_label, rel_type, to_label, count
        """)
        
        for record in result:
            print(f"  ({record['from_label']}) -[{record['rel_type']}]-> ({record['to_label']}) : {record['count']}")

def check_database_performance(driver):
    """Check database performance metrics and indexes"""
    if not driver:
        return None
    
    with driver.session() as session:
        print("=" * 60)
        print("DATABASE PERFORMANCE & INDEXES")
        print("=" * 60)
        
        # Check indexes
        print("\n📋 Database Indexes:")
        result = session.run("SHOW INDEXES")
        
        indexes = []
        for record in result:
            indexes.append({
                'name': record.get('name', 'N/A'),
                'type': record.get('type', 'N/A'),
                'labelsOrTypes': record.get('labelsOrTypes', []),
                'properties': record.get('properties', []),
                'state': record.get('state', 'N/A')
            })
        
        for idx in indexes:
            print(f"  {idx['name']} ({idx['type']}) on {idx['labelsOrTypes']}.{idx['properties']} - {idx['state']}")
        
        # Check constraints
        print("\n🔒 Database Constraints:")
        result = session.run("SHOW CONSTRAINTS")
        
        constraints = []
        for record in result:
            constraints.append({
                'name': record.get('name', 'N/A'),
                'type': record.get('type', 'N/A'),
                'labelsOrTypes': record.get('labelsOrTypes', []),
                'properties': record.get('properties', [])
            })
        
        for constraint in constraints:
            print(f"  {constraint['name']} ({constraint['type']}) on {constraint['labelsOrTypes']}.{constraint['properties']}")
        
        return {
            'indexes': indexes,
            'constraints': constraints
        }

def generate_summary_report(overview, labels_df, relationships_df, properties_df, rel_properties_df, quality_data, performance_data):
    """Generate a comprehensive summary report"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    report = {
        'timestamp': timestamp,
        'database_overview': overview,
        'node_labels': labels_df.to_dict('records') if labels_df is not None else None,
        'relationship_types': relationships_df.to_dict('records') if relationships_df is not None else None,
        'node_properties': properties_df.to_dict() if properties_df is not None else None,
        'relationship_properties': rel_properties_df.to_dict() if rel_properties_df is not None else None,
        'data_quality': quality_data,
        'performance': performance_data
    }
    
    # Save report to file
    report_file = f"neo4j_exploration_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2, default=str)
    
    print(f"\n📄 Summary report saved to: {report_file}")
    
    return report

def main():
    """Main function to run the complete database exploration"""
    print("=" * 80)
    print("NEO4J DATABASE EXPLORER")
    print("=" * 80)
    
    # Load environment and connect to database
    driver = load_environment()
    if not driver:
        print("❌ Cannot proceed without database connection")
        return
    
    try:
        # 1. Database Overview
        print("\n" + "=" * 60)
        print("1. DATABASE OVERVIEW")
        print("=" * 60)
        overview = get_database_overview(driver)
        if overview:
            for key, value in overview.items():
                print(f"{key.replace('_', ' ').title()}: {value}")
        
        # 2. Node Analysis
        print("\n" + "=" * 60)
        print("2. NODE LABELS AND PROPERTIES ANALYSIS")
        print("=" * 60)
        labels_df = analyze_node_labels(driver)
        if labels_df is not None:
            print("\nNode Labels Summary:")
            print(labels_df.to_string(index=False))
        
        properties_df = analyze_node_properties(driver)
        
        # 3. Relationship Analysis
        print("\n" + "=" * 60)
        print("3. RELATIONSHIP TYPES AND PROPERTIES ANALYSIS")
        print("=" * 60)
        relationships_df = analyze_relationships(driver)
        if relationships_df is not None:
            print("\nRelationship Types Summary:")
            print(relationships_df.to_string(index=False))
        
        rel_properties_df = analyze_relationship_properties(driver)
        
        # 4. Data Quality Analysis
        print("\n" + "=" * 60)
        print("4. DATA QUALITY AND CONSISTENCY ANALYSIS")
        print("=" * 60)
        quality_data = analyze_data_quality(driver)
        
        # 5. Sample Data Exploration
        print("\n" + "=" * 60)
        print("5. SAMPLE DATA EXPLORATION")
        print("=" * 60)
        explore_sample_data(driver)
        
        # 6. Graph Pattern Analysis
        print("\n" + "=" * 60)
        print("6. GRAPH PATTERN ANALYSIS")
        print("=" * 60)
        analyze_graph_patterns(driver)
        
        # 7. Performance Analysis
        print("\n" + "=" * 60)
        print("7. DATABASE PERFORMANCE AND INDEXES")
        print("=" * 60)
        performance_data = check_database_performance(driver)
        
        # 8. Generate Summary Report
        print("\n" + "=" * 60)
        print("8. EXPORT SUMMARY REPORT")
        print("=" * 60)
        summary_report = generate_summary_report(
            overview, labels_df, relationships_df, properties_df, 
            rel_properties_df, quality_data, performance_data
        )
        
        print("\n" + "=" * 80)
        print("EXPLORATION COMPLETE!")
        print("=" * 80)
        print("✅ Database Overview: Connection status, version, and basic statistics")
        print("✅ Node Analysis: All labels, counts, and property schemas")
        print("✅ Relationship Analysis: All types, counts, and properties")
        print("✅ Data Quality: Consistency checks and missing data analysis")
        print("✅ Performance: Index and constraint information")
        print("✅ Visualization: Charts and graphs saved as PNG files")
        print("✅ Report: Comprehensive JSON report generated")
        
        print("\nNext Steps:")
        print("1. Review the generated charts and JSON report")
        print("2. Identify data issues and optimization opportunities")
        print("3. Fix missing properties, duplicate entries")
        print("4. Add missing indexes for better performance")
        print("5. Standardize property names and types")
        
    except Exception as e:
        print(f"❌ Error during exploration: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        if driver:
            driver.close()
            print("\n🔌 Database connection closed")

if __name__ == "__main__":
    main()
