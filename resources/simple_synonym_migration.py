#!/usr/bin/env python
"""Simple migration focused ONLY on synonyms with key attributes: mutual_sense, synonymy_domain, hiragana, translation"""

import pickle
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

if not PASSWORD:
    print("ERROR: NEO4J_PASSWORD not found in .env file")
    print(f"Looking for .env at: {env_path}")
    exit(1)

AUTH = (USER, PASSWORD)
print(f"Connecting to Neo4j at: {URI}")

def update_nodes_with_missing_attributes(session, batch_size=1000):
    """Update existing nodes with hiragana and translation from pickle if missing"""
    print("=" * 80)
    print("UPDATING NODES WITH MISSING HIRAGANA AND TRANSLATION")
    print("=" * 80)
    
    # Load NetworkX graph
    with open('G_synonyms_2024_09_18.pickle', 'rb') as f:
        g = pickle.load(f)
    
    print(f"NetworkX nodes available: {g.number_of_nodes():,}")
    
    # Get nodes that need updating
    nodes_data = []
    for node, attrs in g.nodes(data=True):
        hiragana = attrs.get('hiragana')
        translation = attrs.get('translation')
        
        if hiragana or translation:
            nodes_data.append({
                'lemma': node,
                'hiragana': hiragana,
                'translation': translation
            })
    
    print(f"Nodes with hiragana/translation to update: {len(nodes_data):,}")
    
    # Process in batches
    updated = 0
    for i in range(0, len(nodes_data), batch_size):
        batch = nodes_data[i:i+batch_size]
        
        result = session.run("""
            UNWIND $batch AS item
            MATCH (w:Word {lemma: item.lemma})
            SET w.hiragana = COALESCE(w.hiragana, item.hiragana),
                w.translation = COALESCE(w.translation, item.translation)
            RETURN count(w) as updated_count
        """, batch=batch)
        
        stats = result.single()
        updated += stats['updated_count'] if stats else 0
        
        if (i + batch_size) % 5000 == 0:
            print(f"  Updated {min(i + batch_size, len(nodes_data)):,}/{len(nodes_data):,} nodes...")
    
    print(f"✓ Updated {updated:,} nodes with hiragana/translation")

def import_synonym_relationships_only(session, batch_size=500):
    """Import ONLY synonym relationships with all their rich attributes"""
    print("\n" + "=" * 80)
    print("IMPORTING SYNONYM RELATIONSHIPS WITH FULL ATTRIBUTES")
    print("=" * 80)
    
    # Load NetworkX graph
    with open('G_synonyms_2024_09_18.pickle', 'rb') as f:
        g = pickle.load(f)
    
    print(f"Total edges in NetworkX: {g.number_of_edges():,}")
    
    # Filter for synonym edges only (exclude antonyms and domain relations)
    synonym_edges = []
    edge_id = 0
    
    for u, v, key, attrs in g.edges(keys=True, data=True):
        edge_id += 1
        
        # Skip antonyms
        if ('antonym' in attrs and attrs['antonym']) or \
           ('type' in attrs and attrs['type'] == 'antonym'):
            continue
            
        # Skip domain relations (hypernym, hyponym, etc.)
        if 'relation_type' in attrs and attrs['relation_type']:
            rt = str(attrs['relation_type']).upper()
            if any(term in rt for term in ['HYPERNYM', 'HYPONYM', 'MERONYM', 'HOLONYM']):
                continue
        
        # This is a synonym - collect all attributes
        edge_data = {
            'from_word': u,
            'to_word': v,
            'edge_id': f"syn_{edge_id}",
            # Core synonym attributes
            'synonym_strength': attrs.get('synonym_strength'),
            'weight': attrs.get('weight'),
            'relation_type': attrs.get('relation_type'),
            # Mutual sense attributes
            'mutual_sense': attrs.get('mutual_sense'),
            'mutual_sense_hiragana': attrs.get('mutual_sense_hiragana'),
            'mutual_sense_translation': attrs.get('mutual_sense_translation'),
            # Domain attributes  
            'synonymy_domain': attrs.get('synonymy_domain'),
            'synonymy_domain_hiragana': attrs.get('synonymy_domain_hiragana'),
            'synonymy_domain_translation': attrs.get('synonymy_domain_translation'),
            # Explanation
            'synonymy_explanation': attrs.get('synonymy_explanation'),
        }
        
        # Handle nested synonym dictionary if present
        if 'synonym' in attrs and isinstance(attrs['synonym'], dict):
            syn_dict = attrs['synonym']
            edge_data.update({
                'synonym_strength': edge_data['synonym_strength'] or syn_dict.get('synonym_strength'),
                'mutual_sense': edge_data['mutual_sense'] or syn_dict.get('mutual_sense'),
                'mutual_sense_hiragana': edge_data['mutual_sense_hiragana'] or syn_dict.get('mutual_sense_hiragana'),
                'mutual_sense_translation': edge_data['mutual_sense_translation'] or syn_dict.get('mutual_sense_translation'),
                'synonymy_domain': edge_data['synonymy_domain'] or syn_dict.get('synonymy_domain'),
                'synonymy_domain_hiragana': edge_data['synonymy_domain_hiragana'] or syn_dict.get('synonymy_domain_hiragana'),
                'synonymy_domain_translation': edge_data['synonymy_domain_translation'] or syn_dict.get('synonymy_domain_translation'),
                'synonymy_explanation': edge_data['synonymy_explanation'] or syn_dict.get('synonymy_explanation'),
            })
        
        synonym_edges.append(edge_data)
    
    print(f"Synonym edges to import: {len(synonym_edges):,}")
    
    # Import synonym relationships in batches
    created = 0
    for i in range(0, len(synonym_edges), batch_size):
        batch = synonym_edges[i:i+batch_size]
        
        result = session.run("""
            UNWIND $batch AS item
            MATCH (a:Word {lemma: item.from_word})
            MATCH (b:Word {lemma: item.to_word})
            WHERE a <> b
            MERGE (a)-[r:SYNONYM_OF {edge_id: item.edge_id}]->(b)
            SET r.source = 'G_synonyms_2024_09_18',
                r.synonym_strength = item.synonym_strength,
                r.weight = item.weight,
                r.relation_type = item.relation_type,
                r.mutual_sense = item.mutual_sense,
                r.mutual_sense_hiragana = item.mutual_sense_hiragana,
                r.mutual_sense_translation = item.mutual_sense_translation,
                r.synonymy_domain = item.synonymy_domain,
                r.synonymy_domain_hiragana = item.synonymy_domain_hiragana,
                r.synonymy_domain_translation = item.synonymy_domain_translation,
                r.synonymy_explanation = item.synonymy_explanation
            RETURN count(r) as created_count
        """, batch=batch)
        
        stats = result.single()
        created += stats['created_count'] if stats else 0
        
        if (i + batch_size) % 5000 == 0:
            print(f"  Processed {min(i + batch_size, len(synonym_edges)):,}/{len(synonym_edges):,} synonym edges...")
    
    print(f"✓ Created {created:,} SYNONYM_OF relationships with full attributes")

def verify_synonym_attributes(session):
    """Verify that synonym attributes were imported correctly"""
    print("\n" + "=" * 80)
    print("VERIFICATION - SYNONYM ATTRIBUTES")
    print("=" * 80)
    
    # Count synonyms with each attribute
    attributes = [
        'synonym_strength', 'mutual_sense', 'mutual_sense_hiragana', 'mutual_sense_translation',
        'synonymy_domain', 'synonymy_domain_hiragana', 'synonymy_domain_translation', 'synonymy_explanation'
    ]
    
    for attr in attributes:
        result = session.run(f"""
            MATCH ()-[r:SYNONYM_OF]->()
            WHERE r.source = 'G_synonyms_2024_09_18' AND r.{attr} IS NOT NULL
            RETURN count(r) as count
        """)
        count = result.single()['count']
        print(f"  {attr}: {count:,} relationships")
    
    # Sample rich synonym relationships
    print(f"\nSample synonym relationships with all attributes:")
    result = session.run("""
        MATCH (a)-[r:SYNONYM_OF]->(b)
        WHERE r.source = 'G_synonyms_2024_09_18'
        AND r.mutual_sense IS NOT NULL 
        AND r.synonymy_domain IS NOT NULL
        AND r.synonym_strength IS NOT NULL
        RETURN a.lemma as from_word, a.hiragana as from_hiragana, a.translation as from_translation,
               b.lemma as to_word, b.hiragana as to_hiragana, b.translation as to_translation,
               r.synonym_strength as strength,
               r.mutual_sense as mutual, r.mutual_sense_hiragana as mutual_hiragana, 
               r.mutual_sense_translation as mutual_translation,
               r.synonymy_domain as domain, r.synonymy_domain_hiragana as domain_hiragana,
               r.synonymy_domain_translation as domain_translation
        LIMIT 3
    """)
    
    for record in result:
        print(f"\n  '{record['from_word']}' ({record['from_hiragana']}) = {record['from_translation']}")
        print(f"  ↓ SYNONYM (strength: {record['strength']})")
        print(f"  '{record['to_word']}' ({record['to_hiragana']}) = {record['to_translation']}")
        print(f"    Mutual: {record['mutual']} ({record['mutual_hiragana']}) = {record['mutual_translation']}")
        print(f"    Domain: {record['domain']} ({record['domain_hiragana']}) = {record['domain_translation']}")

def main():
    """Run the simple synonym migration"""
    driver = GraphDatabase.driver(URI, auth=AUTH)
    
    try:
        with driver.session() as session:
            print("Starting simple synonym migration...")
            
            # Run migration phases
            update_nodes_with_missing_attributes(session)
            import_synonym_relationships_only(session)
            verify_synonym_attributes(session)
            
            print("\n✅ SYNONYM MIGRATION COMPLETE!")
            print("\nImported synonym relationships with attributes:")
            print("  - mutual_sense (+ hiragana + translation)")
            print("  - synonymy_domain (+ hiragana + translation)")
            print("  - synonym_strength, weight, explanation")
            print("  - Updated nodes with hiragana and translation from pickle")
            
    except Exception as e:
        print(f"\n❌ Error during synonym migration: {e}")
        import traceback
        traceback.print_exc()
    finally:
        driver.close()

if __name__ == "__main__":
    main()
