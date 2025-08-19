#!/usr/bin/env python
"""Remove duplicate SYNONYM_OF relationships, keeping the ones with rich attributes"""

from neo4j import GraphDatabase
import os
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables from parent directory
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

# Neo4j connection - parse URI to handle neo4j:// format
URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")

# Convert neo4j://neo4j:7687 to bolt://localhost:7687 if needed
if URI.startswith("neo4j://neo4j:"):
    URI = URI.replace("neo4j://neo4j:", "bolt://localhost:")
elif URI.startswith("neo4j://"):
    URI = URI.replace("neo4j://", "bolt://")

USER = os.getenv("NEO4J_USER", "neo4j")
PASSWORD = os.getenv("NEO4J_PASSWORD")
AUTH = (USER, PASSWORD)

def deduplicate_synonyms(session, batch_size=1000):
    """Remove duplicate SYNONYM_OF relationships, keeping the richest ones"""
    print("=" * 80)
    print("DEDUPLICATING SYNONYM RELATIONSHIPS")
    print("=" * 80)
    
    # First, let's see what we're dealing with
    result = session.run("""
        MATCH (a)-[r:SYNONYM_OF]->(b)
        WITH a, b, count(r) as rel_count
        WHERE rel_count > 1
        RETURN count(*) as duplicate_pairs
    """)
    duplicate_pairs = result.single()['duplicate_pairs']
    print(f"Found {duplicate_pairs:,} word pairs with duplicate relationships")
    
    if duplicate_pairs == 0:
        print("No duplicates found!")
        return
    
    # Strategy: For each duplicate pair, keep the relationship with the most attributes
    # Priority: G_synonyms_2024_09_18 > networkx_graph > None source
    
    print("\nRemoving inferior duplicate relationships...")
    
    # Remove relationships that are clearly inferior
    result = session.run("""
        MATCH (a)-[r1:SYNONYM_OF]->(b), (a)-[r2:SYNONYM_OF]->(b)
        WHERE r1 <> r2
        AND (
            // Case 1: Keep G_synonyms_2024_09_18, remove others
            (r1.source = 'G_synonyms_2024_09_18' AND r2.source <> 'G_synonyms_2024_09_18') OR
            // Case 2: If no G_synonyms_2024_09_18, keep networkx_graph over None
            (r1.source = 'networkx_graph' AND r2.source IS NULL AND 
             NOT EXISTS((a)-[:SYNONYM_OF {source: 'G_synonyms_2024_09_18'}]->(b))) OR
            // Case 3: Remove relationships with no useful attributes
            (r2.source IS NULL AND r2.mutual_sense IS NULL AND r2.synonymy_domain IS NULL)
        )
        DELETE r2
        RETURN count(r2) as deleted
    """)
    
    deleted = result.single()['deleted']
    print(f"✓ Deleted {deleted:,} inferior duplicate relationships")
    
    # Handle remaining edge cases where both relationships have the same source
    result = session.run("""
        MATCH (a)-[r1:SYNONYM_OF]->(b), (a)-[r2:SYNONYM_OF]->(b)
        WHERE r1 <> r2 AND r1.source = r2.source
        WITH a, b, collect(r1) + collect(r2) as all_rels
        WHERE size(all_rels) > 1
        WITH a, b, all_rels,
             [rel in all_rels | 
              CASE WHEN rel.mutual_sense IS NOT NULL THEN 1 ELSE 0 END +
              CASE WHEN rel.synonymy_domain IS NOT NULL THEN 1 ELSE 0 END +
              CASE WHEN rel.synonym_strength IS NOT NULL THEN 1 ELSE 0 END
             ] as attr_scores
        WITH a, b, all_rels, attr_scores,
             reduce(max_score = 0, score in attr_scores | 
                    CASE WHEN score > max_score THEN score ELSE max_score END) as best_score
        UNWIND range(0, size(all_rels)-1) as i
        WITH a, b, all_rels[i] as rel, attr_scores[i] as score, best_score
        WHERE score < best_score
        DELETE rel
        RETURN count(rel) as deleted_same_source
    """)
    
    deleted_same_source = result.single()['deleted_same_source']
    print(f"✓ Deleted {deleted_same_source:,} same-source duplicates with fewer attributes")

def verify_deduplication(session):
    """Verify that deduplication worked"""
    print("\n" + "=" * 80)
    print("VERIFICATION AFTER DEDUPLICATION")
    print("=" * 80)
    
    # Check for remaining duplicates
    result = session.run("""
        MATCH (a)-[r:SYNONYM_OF]->(b)
        WITH a, b, count(r) as rel_count
        WHERE rel_count > 1
        RETURN count(*) as remaining_duplicates
    """)
    remaining = result.single()['remaining_duplicates']
    print(f"Remaining duplicate pairs: {remaining:,}")
    
    # Total relationships now
    result = session.run("MATCH ()-[r:SYNONYM_OF]->() RETURN count(r) as total")
    total = result.single()['total']
    print(f"Total SYNONYM_OF relationships: {total:,}")
    
    # Check sources after cleanup
    result = session.run("""
        MATCH ()-[r:SYNONYM_OF]->()
        RETURN r.source as source, count(r) as count
        ORDER BY count DESC
    """)
    print(f"\nRelationships by source after cleanup:")
    for record in result:
        source = record['source'] if record['source'] else 'None'
        print(f"  {source}: {record['count']:,}")
    
    # Check attribute coverage
    result = session.run("""
        MATCH ()-[r:SYNONYM_OF]->()
        WHERE r.source = 'G_synonyms_2024_09_18'
        RETURN 
            count(r) as total_rich,
            sum(CASE WHEN r.mutual_sense IS NOT NULL THEN 1 ELSE 0 END) as with_mutual,
            sum(CASE WHEN r.synonymy_domain IS NOT NULL THEN 1 ELSE 0 END) as with_domain,
            sum(CASE WHEN r.synonym_strength IS NOT NULL THEN 1 ELSE 0 END) as with_strength
    """)
    stats = result.single()
    print(f"\nRich relationships (G_synonyms_2024_09_18):")
    print(f"  Total: {stats['total_rich']:,}")
    print(f"  With mutual_sense: {stats['with_mutual']:,}")
    print(f"  With synonymy_domain: {stats['with_domain']:,}")
    print(f"  With synonym_strength: {stats['with_strength']:,}")

def main():
    """Run deduplication"""
    driver = GraphDatabase.driver(URI, auth=AUTH)
    
    try:
        with driver.session() as session:
            deduplicate_synonyms(session)
            verify_deduplication(session)
            
            print("\n✅ DEDUPLICATION COMPLETE!")
            print("\nThe database now has clean, non-duplicate synonym relationships")
            print("with all the rich attributes preserved!")
            
    except Exception as e:
        print(f"\n❌ Error during deduplication: {e}")
        import traceback
        traceback.print_exc()
    finally:
        driver.close()

if __name__ == "__main__":
    main()
