#!/usr/bin/env python
"""Import relationships with proper types: SYNONYM_OF, ANTONYM_OF, DOMAIN_OF"""

import pickle
import json
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

def flatten_attributes(attrs, prefix=''):
    """Flatten nested dictionaries for Neo4j compatibility"""
    flattened = {}
    
    for key, value in attrs.items():
        full_key = f"{prefix}{key}" if prefix else key
        
        if value is None:
            continue
        elif isinstance(value, (str, int, float, bool)):
            flattened[full_key] = value
        elif isinstance(value, dict):
            # Flatten nested dict with prefix
            nested_flat = flatten_attributes(value, prefix=f"{key}_")
            flattened.update(nested_flat)
        elif isinstance(value, (list, tuple)):
            if all(isinstance(item, (str, int, float, bool)) for item in value):
                flattened[full_key] = list(value)
            else:
                flattened[f"{full_key}_json"] = json.dumps(value, ensure_ascii=False)
        else:
            flattened[f"{full_key}_str"] = str(value)
    
    return flattened

def determine_relationship_type(attrs):
    """Determine the Neo4j relationship type based on attributes"""
    
    # Check for antonym
    if ('antonym' in attrs and (isinstance(attrs['antonym'], dict) or attrs['antonym'] == True)) or \
       ('type' in attrs and attrs['type'] == 'antonym'):
        return 'ANTONYM_OF', 'antonym'
    
    # Check for hierarchical (domain relations)
    if 'relation_type' in attrs and attrs['relation_type'] and \
       isinstance(attrs['relation_type'], str):
        rt = attrs['relation_type'].upper()
        if 'HYPERNYM' in rt:
            return 'DOMAIN_OF', 'hypernym'
        elif 'HYPONYM' in rt:
            return 'DOMAIN_OF', 'hyponym'
        elif 'MERONYM' in rt:
            return 'DOMAIN_OF', 'meronym'
        elif 'HOLONYM' in rt:
            return 'DOMAIN_OF', 'holonym'
    
    # Default to synonym
    return 'SYNONYM_OF', 'synonym'

def import_relationships(session, batch_size=500):
    """Import relationships with proper types"""
    print("=" * 60)
    print("IMPORTING RELATIONSHIPS WITH PROPER TYPES")
    print("=" * 60)
    
    # Load NetworkX graph
    with open('G_synonyms_2024_09_18.pickle', 'rb') as f:
        g = pickle.load(f)
    
    print(f"Total edges to process: {g.number_of_edges()}")
    
    # Group edges by relationship type
    synonym_edges = []
    antonym_edges = []
    domain_edges = []
    
    edge_id = 0
    for u, v, key, attrs in g.edges(keys=True, data=True):
        edge_id += 1
        rel_type, subtype = determine_relationship_type(attrs)
        
        # Flatten attributes
        flattened = flatten_attributes(attrs)
        
        edge_data = {
            'from_word': u,
            'to_word': v,
            'edge_id': f"nx_{edge_id}",
            'subtype': subtype,
            'attrs': flattened
        }
        
        if rel_type == 'SYNONYM_OF':
            synonym_edges.append(edge_data)
        elif rel_type == 'ANTONYM_OF':
            antonym_edges.append(edge_data)
        elif rel_type == 'DOMAIN_OF':
            domain_edges.append(edge_data)
    
    print(f"\nEdges by type:")
    print(f"  SYNONYM_OF: {len(synonym_edges):,}")
    print(f"  ANTONYM_OF: {len(antonym_edges):,}")
    print(f"  DOMAIN_OF:  {len(domain_edges):,}")
    
    # Import SYNONYM_OF relationships
    print("\nImporting SYNONYM_OF relationships...")
    created = 0
    for i in range(0, len(synonym_edges), batch_size):
        batch = synonym_edges[i:i+batch_size]
        
        batch_data = []
        for edge in batch:
            data = {
                'from_word': edge['from_word'],
                'to_word': edge['to_word'],
                'edge_id': edge['edge_id']
            }
            # Add flattened attributes
            data.update(edge['attrs'])
            batch_data.append(data)
        
        result = session.run("""
            UNWIND $batch AS item
            MATCH (a:Word {lemma: item.from_word})
            MATCH (b:Word {lemma: item.to_word})
            WHERE a <> b
            MERGE (a)-[r:SYNONYM_OF {edge_id: item.edge_id}]->(b)
            SET r += item
            RETURN count(r) as created_count
        """, batch=batch_data)
        
        stats = result.single()
        created += stats['created_count'] if stats else 0
        
        if (i + batch_size) % 10000 == 0:
            print(f"  Processed {min(i + batch_size, len(synonym_edges)):,}/{len(synonym_edges):,}")
    
    print(f"  ✓ Created {created:,} SYNONYM_OF relationships")
    
    # Import ANTONYM_OF relationships
    print("\nImporting ANTONYM_OF relationships...")
    created = 0
    for i in range(0, len(antonym_edges), batch_size):
        batch = antonym_edges[i:i+batch_size]
        
        batch_data = []
        for edge in batch:
            data = {
                'from_word': edge['from_word'],
                'to_word': edge['to_word'],
                'edge_id': edge['edge_id']
            }
            # Add flattened attributes
            data.update(edge['attrs'])
            batch_data.append(data)
        
        result = session.run("""
            UNWIND $batch AS item
            MATCH (a:Word {lemma: item.from_word})
            MATCH (b:Word {lemma: item.to_word})
            WHERE a <> b
            MERGE (a)-[r:ANTONYM_OF {edge_id: item.edge_id}]->(b)
            SET r += item
            RETURN count(r) as created_count
        """, batch=batch_data)
        
        stats = result.single()
        created += stats['created_count'] if stats else 0
    
    print(f"  ✓ Created {created:,} ANTONYM_OF relationships")
    
    # Import DOMAIN_OF relationships
    print("\nImporting DOMAIN_OF relationships...")
    created = 0
    for i in range(0, len(domain_edges), batch_size):
        batch = domain_edges[i:i+batch_size]
        
        batch_data = []
        for edge in batch:
            data = {
                'from_word': edge['from_word'],
                'to_word': edge['to_word'],
                'edge_id': edge['edge_id'],
                'subtype': edge['subtype']
            }
            # Add flattened attributes
            data.update(edge['attrs'])
            batch_data.append(data)
        
        result = session.run("""
            UNWIND $batch AS item
            MATCH (a:Word {lemma: item.from_word})
            MATCH (b:Word {lemma: item.to_word})
            WHERE a <> b
            MERGE (a)-[r:DOMAIN_OF {edge_id: item.edge_id}]->(b)
            SET r.subtype = item.subtype
            SET r += item
            RETURN count(r) as created_count
        """, batch=batch_data)
        
        stats = result.single()
        created += stats['created_count'] if stats else 0
    
    print(f"  ✓ Created {created:,} DOMAIN_OF relationships")

def verify_import(session):
    """Verify the relationship import"""
    print("\n" + "=" * 60)
    print("VERIFICATION")
    print("=" * 60)
    
    # Count relationships by type
    for rel_type in ['SYNONYM_OF', 'ANTONYM_OF', 'DOMAIN_OF']:
        result = session.run(f"""
            MATCH ()-[r:{rel_type}]->()
            RETURN count(r) as count
        """)
        count = result.single()['count']
        print(f"  {rel_type}: {count:,} relationships")
    
    # Sample relationships
    print("\nSample relationships:")
    
    for rel_type in ['SYNONYM_OF', 'ANTONYM_OF', 'DOMAIN_OF']:
        result = session.run(f"""
            MATCH (a)-[r:{rel_type}]->(b)
            RETURN a.lemma as from, b.lemma as to, 
                   r.weight as weight, r.subtype as subtype
            LIMIT 2
        """)
        
        print(f"\n  {rel_type}:")
        for record in result:
            subtype = f" ({record['subtype']})" if record['subtype'] else ""
            weight = f" [weight: {record['weight']:.2f}]" if record['weight'] else ""
            print(f"    '{record['from']}' -> '{record['to']}'{subtype}{weight}")
    
    # Check for failed matches
    print("\nChecking for unmatched edges...")
    with open('G_synonyms_2024_09_18.pickle', 'rb') as f:
        g = pickle.load(f)
    
    total_nx_edges = g.number_of_edges()
    
    result = session.run("""
        MATCH ()-[r]->()
        WHERE r.edge_id STARTS WITH 'nx_'
        RETURN count(r) as count
    """)
    imported_edges = result.single()['count']
    
    print(f"  NetworkX edges: {total_nx_edges:,}")
    print(f"  Imported edges: {imported_edges:,}")
    if imported_edges < total_nx_edges:
        print(f"  ⚠️  Missing edges: {total_nx_edges - imported_edges:,}")
        print("  (Likely due to words not found in the graph)")
    else:
        print("  ✅ All edges imported successfully!")

def main():
    """Run the relationship import"""
    driver = GraphDatabase.driver(URI, auth=AUTH)
    
    try:
        with driver.session() as session:
            import_relationships(session)
            verify_import(session)
            
            print("\n✅ RELATIONSHIP IMPORT COMPLETE!")
            
    except Exception as e:
        print(f"\n❌ Error during import: {e}")
        import traceback
        traceback.print_exc()
    finally:
        driver.close()

if __name__ == "__main__":
    main()
