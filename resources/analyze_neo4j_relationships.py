#!/usr/bin/env python
"""Detailed analysis of all relationship types in Neo4j"""

from neo4j import GraphDatabase
import os
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

# Neo4j connection
URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
if URI.startswith("neo4j://neo4j:"):
    URI = URI.replace("neo4j://neo4j:", "bolt://localhost:")
elif URI.startswith("neo4j://"):
    URI = URI.replace("neo4j://", "bolt://")

USER = os.getenv("NEO4J_USER", "neo4j")
PASSWORD = os.getenv("NEO4J_PASSWORD")
AUTH = (USER, PASSWORD)

print(f"Connecting to Neo4j at: {URI}")

def analyze_relationships(session):
    """Detailed analysis of all relationships"""
    
    print("=" * 80)
    print("ALL RELATIONSHIP TYPES IN NEO4J")
    print("=" * 80)
    
    # Get all relationship types with counts
    result = session.run("""
        MATCH ()-[r]->()
        RETURN type(r) as type, count(r) as count
        ORDER BY count DESC
    """)
    
    rel_types = []
    print("\nRelationship types and counts:")
    print("-" * 40)
    for record in result:
        rel_types.append(record['type'])
        print(f"  {record['type']:<25} {record['count']:>10,} relationships")
    
    # Analyze each relationship type
    for rel_type in rel_types:
        print("\n" + "=" * 80)
        print(f"ANALYZING: {rel_type}")
        print("=" * 80)
        
        # Get sample properties
        result = session.run(f"""
            MATCH ()-[r:{rel_type}]->()
            WITH r LIMIT 100
            UNWIND keys(r) as key
            WITH key, count(key) as freq
            RETURN key, freq
            ORDER BY freq DESC
        """)
        
        print(f"\nProperties found in {rel_type}:")
        props = []
        for record in result:
            props.append(record['key'])
            print(f"  - {record['key']:<40} (in {record['freq']} samples)")
        
        # Get sample relationships with data
        result = session.run(f"""
            MATCH (a)-[r:{rel_type}]->(b)
            RETURN a.lemma as from, b.lemma as to, r
            LIMIT 3
        """)
        
        print(f"\nSample {rel_type} relationships:")
        for i, record in enumerate(result, 1):
            from_word = record['from'] or 'N/A'
            to_word = record['to'] or 'N/A'
            print(f"\n  Example {i}: '{from_word}' -> '{to_word}'")
            
            # Show key properties
            rel_props = dict(record['r'])
            
            # Group properties by category
            important_props = ['weight', 'strength', 'synonym_strength', 'antonym_strength', 
                             'subtype', 'relation_type', 'type', 'source']
            semantic_props = ['mutual_sense', 'mutual_sense_translation', 
                            'synonymy_domain', 'synonymy_domain_translation',
                            'synonymy_explanation', 'antonym_explanation']
            
            shown_props = []
            
            # Show important properties first
            for prop in important_props:
                if prop in rel_props and rel_props[prop] is not None:
                    value = rel_props[prop]
                    if isinstance(value, float):
                        print(f"    {prop}: {value:.2f}")
                    else:
                        print(f"    {prop}: {value}")
                    shown_props.append(prop)
            
            # Show semantic properties
            for prop in semantic_props:
                if prop in rel_props and rel_props[prop] is not None:
                    value = str(rel_props[prop])[:60] + "..." if len(str(rel_props[prop])) > 60 else rel_props[prop]
                    print(f"    {prop}: {value}")
                    shown_props.append(prop)
            
            # Show any other properties
            other_props = [p for p in rel_props.keys() if p not in shown_props and p != 'edge_id']
            if other_props:
                print(f"    Other properties: {', '.join(other_props[:5])}")

def analyze_specific_relationships(session):
    """Analyze the three main relationship types we created"""
    
    print("\n" + "=" * 80)
    print("DETAILED ANALYSIS OF MAIN RELATIONSHIP TYPES")
    print("=" * 80)
    
    # SYNONYM_OF analysis
    print("\n1. SYNONYM_OF Relationships")
    print("-" * 40)
    result = session.run("""
        MATCH ()-[r:SYNONYM_OF]->()
        WITH r.relation_type as rel_type, count(r) as count
        WHERE rel_type IS NOT NULL
        RETURN rel_type, count
        ORDER BY count DESC
        LIMIT 10
    """)
    
    print("  Subtypes by relation_type:")
    for record in result:
        print(f"    {record['rel_type']:<30} {record['count']:>8,}")
    
    result = session.run("""
        MATCH ()-[r:SYNONYM_OF]->()
        WHERE r.weight IS NOT NULL
        RETURN min(r.weight) as min_weight, max(r.weight) as max_weight, 
               avg(r.weight) as avg_weight, count(r) as count
    """)
    
    stats = result.single()
    if stats and stats['count'] > 0:
        print(f"\n  Weight statistics:")
        print(f"    Min: {stats['min_weight']:.2f}, Max: {stats['max_weight']:.2f}, Avg: {stats['avg_weight']:.2f}")
        print(f"    Relationships with weights: {stats['count']:,}")
    
    # ANTONYM_OF analysis
    print("\n2. ANTONYM_OF Relationships")
    print("-" * 40)
    result = session.run("""
        MATCH ()-[r:ANTONYM_OF]->()
        WHERE r.antonym_antonym_strength IS NOT NULL
        RETURN min(r.antonym_antonym_strength) as min_str, 
               max(r.antonym_antonym_strength) as max_str,
               avg(r.antonym_antonym_strength) as avg_str,
               count(r) as count
    """)
    
    stats = result.single()
    if stats and stats['count'] > 0:
        print(f"  Antonym strength statistics:")
        print(f"    Min: {stats['min_str']:.2f}, Max: {stats['max_str']:.2f}, Avg: {stats['avg_str']:.2f}")
        print(f"    Relationships with strength: {stats['count']:,}")
    
    # DOMAIN_OF analysis
    print("\n3. DOMAIN_OF Relationships")
    print("-" * 40)
    result = session.run("""
        MATCH ()-[r:DOMAIN_OF]->()
        RETURN r.subtype as subtype, count(r) as count
        ORDER BY count DESC
    """)
    
    print("  Hierarchical subtypes:")
    for record in result:
        subtype = record['subtype'] or 'unspecified'
        print(f"    {subtype:<20} {record['count']:>8,}")
    
    # Other relationship types
    print("\n4. Other Relationship Types (from previous imports)")
    print("-" * 40)
    result = session.run("""
        MATCH ()-[r]->()
        WHERE NOT type(r) IN ['SYNONYM_OF', 'ANTONYM_OF', 'DOMAIN_OF']
        RETURN type(r) as type, count(r) as count
        ORDER BY count DESC
    """)
    
    for record in result:
        print(f"    {record['type']:<30} {record['count']:>8,}")

def main():
    driver = GraphDatabase.driver(URI, auth=AUTH)
    
    try:
        with driver.session() as session:
            analyze_relationships(session)
            analyze_specific_relationships(session)
            
            print("\n" + "=" * 80)
            print("✅ RELATIONSHIP ANALYSIS COMPLETE")
            print("=" * 80)
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        driver.close()

if __name__ == "__main__":
    main()
