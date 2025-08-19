#!/usr/bin/env python3
"""
Test Enhanced Grammar Graph with Advanced Queries
================================================

This script demonstrates the power of the enhanced grammar graph
with complex learning-oriented queries.
"""

import os
from neo4j import GraphDatabase
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_enhanced_queries():
    """Test advanced queries on the enhanced grammar graph"""
    
    # Connect to Neo4j
    uri = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
    user = os.getenv('NEO4J_USERNAME', 'neo4j')
    password = os.getenv('NEO4J_PASSWORD')
    
    driver = GraphDatabase.driver(uri, auth=(user, password))
    
    with driver.session() as session:
        
        print("🔍 Testing Enhanced Grammar Graph Queries")
        print("=" * 55)
        
        # Query 1: Learning progression path
        print(f"\n📚 Learning Path: Basic → Advanced Patterns")
        result = session.run("""
            MATCH path = (basic:GrammarPattern {pattern: '～は～です'})-[:PREREQUISITE_FOR*1..3]->(advanced:GrammarPattern)
            WHERE advanced.textbook IN ['中級1', '中級2']
            RETURN advanced.pattern, advanced.textbook, advanced.classification
            ORDER BY advanced.sequence_number
            LIMIT 5
        """)
        
        for record in result:
            print(f"   {record['advanced.pattern']} ({record['advanced.textbook']}) - {record['advanced.classification']}")
        
        # Query 2: Similar patterns across levels
        print(f"\n🔄 Similar Patterns Across Levels:")
        result = session.run("""
            MATCH (g1:GrammarPattern)-[s:SIMILAR_TO]->(g2:GrammarPattern)
            WHERE g1.textbook <> g2.textbook
            RETURN g1.pattern, g1.textbook, g2.pattern, g2.textbook, s.reason
            ORDER BY g1.sequence_number
            LIMIT 5
        """)
        
        for record in result:
            print(f"   {record['g1.pattern']} ({record['g1.textbook']}) ↔ {record['g2.pattern']} ({record['g2.textbook']})")
            print(f"     Reason: {record['s.reason']}")
        
        # Query 3: Grammar patterns using common words
        print(f"\n📝 Patterns Using Common Words:")
        result = session.run("""
            MATCH (w:Word)<-[:USES_WORD]-(g:GrammarPattern)
            WHERE w.kanji IN ['私', 'です', 'は', 'が']
            WITH w, count(g) as pattern_count
            ORDER BY pattern_count DESC
            LIMIT 4
            MATCH (w)<-[:USES_WORD]-(g:GrammarPattern)
            RETURN w.kanji, w.hiragana, g.pattern, g.textbook
            ORDER BY w.kanji, g.sequence_number
            LIMIT 8
        """)
        
        current_word = None
        for record in result:
            word = record['w.kanji']
            if word != current_word:
                print(f"   Word: {word} ({record['w.hiragana']})")
                current_word = word
            print(f"     → {record['g.pattern']} ({record['g.textbook']})")
        
        # Query 4: Grammar classification analysis
        print(f"\n🏷️ Classification Relationships:")
        result = session.run("""
            MATCH (g:GrammarPattern)-[:HAS_CLASSIFICATION]->(gc:GrammarClassification)
            WITH gc, count(g) as pattern_count
            ORDER BY pattern_count DESC
            LIMIT 5
            MATCH (g:GrammarPattern)-[:HAS_CLASSIFICATION]->(gc)
            RETURN gc.name, g.pattern, g.textbook
            ORDER BY gc.name, g.sequence_number
            LIMIT 10
        """)
        
        current_classification = None
        for record in result:
            classification = record['gc.name']
            if classification != current_classification:
                print(f"   Classification: {classification}")
                current_classification = classification
            print(f"     → {record['g.pattern']} ({record['g.textbook']})")
        
        # Query 5: JFS Category learning paths
        print(f"\n🎯 JFS Category Learning Paths:")
        result = session.run("""
            MATCH (g:GrammarPattern)-[:CATEGORIZED_AS]->(jfs:JFSCategory)
            WHERE jfs.name IN ['自分と家族', '食生活', '仕事と職業']
            WITH jfs, collect(g) as patterns
            UNWIND patterns as pattern
            RETURN jfs.name, pattern.pattern, pattern.textbook
            ORDER BY jfs.name, pattern.sequence_number
            LIMIT 12
        """)
        
        current_category = None
        for record in result:
            category = record['jfs.name']
            if category != current_category:
                print(f"   Category: {category}")
                current_category = category
            print(f"     → {record['pattern.pattern']} ({record['pattern.textbook']})")
        
        # Query 6: Complex learning recommendation
        print(f"\n🎓 Learning Recommendation Engine:")
        result = session.run("""
            // Find beginner patterns that are prerequisites for many advanced patterns
            MATCH (basic:GrammarPattern)-[:PREREQUISITE_FOR]->(advanced:GrammarPattern)
            WHERE basic.textbook = '入門(りかい)'
            WITH basic, count(advanced) as prerequisite_count
            ORDER BY prerequisite_count DESC
            LIMIT 3
            MATCH (basic)-[:USES_WORD]->(w:Word)
            RETURN basic.pattern, basic.pattern_romaji, basic.example_sentence, 
                   prerequisite_count, collect(DISTINCT w.kanji)[0..3] as key_words
        """)
        
        for record in result:
            print(f"   📖 Essential Pattern: {record['basic.pattern']} → {record['basic.pattern_romaji']}")
            print(f"      Example: {record['basic.example_sentence']}")
            print(f"      Unlocks: {record['prerequisite_count']} advanced patterns")
            print(f"      Key words: {', '.join(record['key_words'])}")
            print()
        
        # Query 7: Relationship summary
        print(f"\n📊 Enhanced Graph Statistics:")
        result = session.run("""
            MATCH ()-[r]->()
            RETURN type(r) as relationship_type, count(r) as count
            ORDER BY count DESC
            LIMIT 10
        """)
        
        total_relationships = 0
        for record in result:
            count = record['count']
            total_relationships += count
            print(f"   {record['relationship_type']}: {count:,} relationships")
        
        print(f"\n🎉 Total Relationships: {total_relationships:,}")
        print(f"🎯 The grammar graph is now a powerful learning engine!")
    
    driver.close()

if __name__ == "__main__":
    test_enhanced_queries()
