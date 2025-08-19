#!/usr/bin/env python
"""Check current Neo4j state before migration"""

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

print(f"Connecting to Neo4j at: {URI}")

def check_current_state():
    """Check what's currently in Neo4j"""
    driver = GraphDatabase.driver(URI, auth=AUTH)
    
    with driver.session() as session:
        print("=" * 60)
        print("CURRENT NEO4J STATE")
        print("=" * 60)
        
        # Check node labels and counts
        result = session.run("""
            CALL db.labels() YIELD label
            CALL {
                WITH label
                MATCH (n)
                WHERE label IN labels(n)
                RETURN count(n) as count
            }
            RETURN label, count
            ORDER BY label
        """)
        
        print("\nNode Labels and Counts:")
        for record in result:
            print(f"  :{record['label']} - {record['count']} nodes")
        
        # Check relationship types and counts
        result = session.run("""
            CALL db.relationshipTypes() YIELD relationshipType
            CALL {
                WITH relationshipType
                MATCH ()-[r]->()
                WHERE type(r) = relationshipType
                RETURN count(r) as count
            }
            RETURN relationshipType, count
            ORDER BY relationshipType
        """)
        
        print("\nRelationship Types and Counts:")
        for record in result:
            print(f"  :{record['relationshipType']} - {record['count']} relationships")
        
        # Sample Word nodes
        result = session.run("""
            MATCH (w:Word)
            RETURN w, keys(w) as props
            LIMIT 5
        """)
        
        print("\nSample :Word nodes:")
        for record in result:
            node = record['w']
            print(f"  Node properties: {dict(node)}")
            
        # Check for jlpt_level vs old_jlpt_level
        result = session.run("""
            MATCH (w:Word)
            WHERE w.jlpt_level IS NOT NULL
            RETURN count(w) as with_jlpt_level
        """)
        jlpt_count = result.single()
        
        result = session.run("""
            MATCH (w:Word)
            WHERE w.old_jlpt_level IS NOT NULL
            RETURN count(w) as with_old_jlpt_level
        """)
        old_jlpt_count = result.single()
        
        print(f"\nNodes with jlpt_level: {jlpt_count['with_jlpt_level'] if jlpt_count else 0}")
        print(f"Nodes with old_jlpt_level: {old_jlpt_count['with_old_jlpt_level'] if old_jlpt_count else 0}")
        
        # Check constraints and indexes
        result = session.run("SHOW CONSTRAINTS")
        print("\nConstraints:")
        for record in result:
            print(f"  {record}")
            
        result = session.run("SHOW INDEXES")
        print("\nIndexes:")
        for record in result:
            if record['type'] != 'LOOKUP':  # Skip system indexes
                print(f"  {record['name']} on {record['labelsOrTypes']} ({record['properties']})")
    
    driver.close()

if __name__ == "__main__":
    try:
        check_current_state()
    except Exception as e:
        print(f"Error connecting to Neo4j: {e}")
        print("\nMake sure Neo4j is running and credentials are correct in .env:")
        print("  NEO4J_URI=bolt://localhost:7687")
        print("  NEO4J_USER=neo4j")
        print("  NEO4J_PASSWORD=your_password")
