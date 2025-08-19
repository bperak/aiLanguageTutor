#!/usr/bin/env python3
"""
Test script to validate the Marugoto Grammar Graph import
"""

import os
from neo4j import GraphDatabase
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_marugoto_graph():
    """Test the imported Marugoto grammar patterns"""
    
    # Connect to Neo4j
    uri = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
    user = os.getenv('NEO4J_USERNAME', 'neo4j')
    password = os.getenv('NEO4J_PASSWORD')
    
    driver = GraphDatabase.driver(uri, auth=(user, password))
    
    with driver.session() as session:
        
        print("🧪 Testing Marugoto Grammar Graph Import")
        print("=" * 50)
        
        # Test 1: Count total grammar patterns
        result = session.run("MATCH (g:GrammarPattern) RETURN count(g) as total")
        total = result.single()['total']
        print(f"✅ Total GrammarPattern nodes: {total}")
        
        # Test 2: Sample grammar patterns with romaji
        print(f"\n📋 Sample Grammar Patterns:")
        result = session.run("""
            MATCH (g:GrammarPattern) 
            RETURN g.pattern, g.pattern_romaji, g.example_sentence, g.example_romaji
            ORDER BY g.sequence_number 
            LIMIT 5
        """)
        
        for record in result:
            print(f"   Pattern: {record['g.pattern']} → {record['g.pattern_romaji']}")
            print(f"   Example: {record['g.example_sentence']} → {record['g.example_romaji']}")
            print()
        
        # Test 3: TextbookLevel relationships
        print(f"📚 Grammar Patterns by Textbook Level:")
        result = session.run("""
            MATCH (g:GrammarPattern)-[:BELONGS_TO_LEVEL]->(t:TextbookLevel)
            RETURN t.name, t.level_order, count(g) as pattern_count
            ORDER BY t.level_order
        """)
        
        for record in result:
            print(f"   {record['t.name']}: {record['pattern_count']} patterns")
        
        # Test 4: Classification breakdown
        print(f"\n🏷️ Top Classifications:")
        result = session.run("""
            MATCH (g:GrammarPattern)
            RETURN g.classification, count(g) as count
            ORDER BY count DESC
            LIMIT 10
        """)
        
        for record in result:
            print(f"   {record['g.classification']}: {record['count']} patterns")
        
        # Test 5: Find patterns with specific words
        print(f"\n🔍 Patterns containing 'です':")
        result = session.run("""
            MATCH (g:GrammarPattern)
            WHERE g.pattern CONTAINS 'です'
            RETURN g.pattern, g.pattern_romaji, g.textbook
            ORDER BY g.sequence_number
            LIMIT 5
        """)
        
        for record in result:
            print(f"   {record['g.pattern']} → {record['g.pattern_romaji']} ({record['g.textbook']})")
        
        # Test 6: Graph schema overview
        print(f"\n📊 Graph Schema Overview:")
        result = session.run("""
            CALL db.schema.visualization()
        """)
        
        # Alternative schema query
        result = session.run("""
            MATCH (n)
            RETURN DISTINCT labels(n) as node_labels, count(n) as count
            ORDER BY count DESC
        """)
        
        for record in result:
            labels = ', '.join(record['node_labels'])
            print(f"   {labels}: {record['count']} nodes")
        
        print(f"\n🎉 Graph validation completed successfully!")
    
    driver.close()

if __name__ == "__main__":
    test_marugoto_graph()
