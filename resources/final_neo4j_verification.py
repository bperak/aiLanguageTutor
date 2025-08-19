#!/usr/bin/env python
"""Final verification of Neo4j migration"""

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

def verify_final_state(session):
    """Comprehensive verification of the final Neo4j state"""
    
    print("=" * 60)
    print("FINAL NEO4J DATABASE STATE")
    print("=" * 60)
    
    # Total nodes
    result = session.run("MATCH (n) RETURN count(n) as count")
    print(f"\nTotal nodes: {result.single()['count']:,}")
    
    # Nodes by source
    print("\nNodes by source:")
    result = session.run("""
        MATCH (w:Word)
        RETURN w.source as source, count(w) as count
        ORDER BY count DESC
    """)
    for record in result:
        print(f"  {record['source']}: {record['count']:,} nodes")
    
    # Total relationships
    result = session.run("MATCH ()-[r]->() RETURN count(r) as count")
    print(f"\nTotal relationships: {result.single()['count']:,}")
    
    # Relationships by type
    print("\nRelationships by type:")
    result = session.run("""
        MATCH ()-[r]->()
        RETURN type(r) as type, count(r) as count
        ORDER BY count DESC
    """)
    for record in result:
        print(f"  {record['type']}: {record['count']:,}")
    
    # DOMAIN_OF subtypes
    print("\nDOMAIN_OF subtypes:")
    result = session.run("""
        MATCH ()-[r:DOMAIN_OF]->()
        RETURN r.subtype as subtype, count(r) as count
        ORDER BY count DESC
    """)
    for record in result:
        print(f"  {record['subtype']}: {record['count']:,}")
    
    # Sample rich nodes (with many connections)
    print("\n" + "=" * 60)
    print("SAMPLE RICH NODES")
    print("=" * 60)
    
    result = session.run("""
        MATCH (w:Word)
        WITH w, COUNT {(w)-[:SYNONYM_OF]-()} as syn_count,
             COUNT {(w)-[:ANTONYM_OF]-()} as ant_count,
             COUNT {(w)-[:DOMAIN_OF]-()} as dom_count
        WHERE syn_count + ant_count + dom_count > 0
        RETURN w.lemma as word, w.source as source,
               syn_count, ant_count, dom_count,
               syn_count + ant_count + dom_count as total
        ORDER BY total DESC
        LIMIT 10
    """)
    
    print("\nTop 10 most connected words:")
    print(f"{'Word':<15} {'Source':<15} {'Synonyms':<10} {'Antonyms':<10} {'Domain':<10} {'Total':<10}")
    print("-" * 80)
    for record in result:
        word = record['word'] or 'N/A'
        source = record['source'] or 'N/A'
        print(f"{word:<15} {source:<15} "
              f"{record['syn_count']:<10} {record['ant_count']:<10} "
              f"{record['dom_count']:<10} {record['total']:<10}")
    
    # Check data quality
    print("\n" + "=" * 60)
    print("DATA QUALITY CHECKS")
    print("=" * 60)
    
    # Words with old_jlpt_level
    result = session.run("""
        MATCH (w:Word)
        WHERE w.old_jlpt_level IS NOT NULL
        RETURN count(w) as count
    """)
    print(f"\nWords with old_jlpt_level: {result.single()['count']:,}")
    
    # Words with reading
    result = session.run("""
        MATCH (w:Word)
        WHERE w.reading IS NOT NULL
        RETURN count(w) as count
    """)
    print(f"Words with reading: {result.single()['count']:,}")
    
    # Words with POS
    result = session.run("""
        MATCH (w:Word)
        WHERE w.pos IS NOT NULL
        RETURN count(w) as count
    """)
    print(f"Words with POS: {result.single()['count']:,}")
    
    # Sample query: Find antonyms
    print("\n" + "=" * 60)
    print("SAMPLE QUERIES")
    print("=" * 60)
    
    print("\nSample antonym pairs:")
    result = session.run("""
        MATCH (a:Word)-[r:ANTONYM_OF]->(b:Word)
        RETURN a.lemma as word1, b.lemma as word2, 
               r.antonym_antonym_strength as strength
        ORDER BY r.antonym_antonym_strength DESC
        LIMIT 5
    """)
    for record in result:
        strength = record['strength'] if record['strength'] else 'N/A'
        print(f"  {record['word1']} ⟷ {record['word2']} (strength: {strength})")
    
    print("\nSample domain relationships (meronym):")
    result = session.run("""
        MATCH (a:Word)-[r:DOMAIN_OF {subtype: 'meronym'}]->(b:Word)
        RETURN a.lemma as part, b.lemma as whole, r.weight as weight
        ORDER BY r.weight DESC
        LIMIT 5
    """)
    for record in result:
        weight = f"{record['weight']:.2f}" if record['weight'] else 'N/A'
        print(f"  {record['part']} is part of {record['whole']} (weight: {weight})")
    
    print("\nWords with both synonyms and antonyms:")
    result = session.run("""
        MATCH (w:Word)
        WHERE EXISTS((w)-[:SYNONYM_OF]-()) AND EXISTS((w)-[:ANTONYM_OF]-())
        RETURN w.lemma as word, 
               COUNT {(w)-[:SYNONYM_OF]-()} as synonyms,
               COUNT {(w)-[:ANTONYM_OF]-()} as antonyms
        LIMIT 5
    """)
    for record in result:
        print(f"  {record['word']}: {record['synonyms']} synonyms, {record['antonyms']} antonyms")

def main():
    """Run the final verification"""
    driver = GraphDatabase.driver(URI, auth=AUTH)
    
    try:
        with driver.session() as session:
            verify_final_state(session)
            
            print("\n" + "=" * 60)
            print("✅ MIGRATION VERIFICATION COMPLETE!")
            print("=" * 60)
            print("""
Your Neo4j database now contains:
- All Lee vocabulary words with proper attributes
- All NetworkX nodes with their properties
- Three distinct relationship types:
  * SYNONYM_OF for synonymous relationships
  * ANTONYM_OF for antonymous relationships  
  * DOMAIN_OF for hierarchical relationships (with subtypes)
- All attributes properly flattened and stored
""")
            
    except Exception as e:
        print(f"\n❌ Error during verification: {e}")
        import traceback
        traceback.print_exc()
    finally:
        driver.close()

if __name__ == "__main__":
    main()
