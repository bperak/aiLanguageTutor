#!/usr/bin/env python
"""Safe migration script that preserves existing Neo4j data"""

import pickle
import pandas as pd
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

def check_current_state(session):
    """Check what's currently in Neo4j"""
    print("=" * 60)
    print("CHECKING CURRENT NEO4J STATE")
    print("=" * 60)
    
    # Count existing nodes
    result = session.run("MATCH (w:Word) RETURN count(w) as count")
    word_count = result.single()['count']
    print(f"Existing :Word nodes: {word_count}")
    
    # Check for existing sources
    result = session.run("""
        MATCH (w:Word)
        WHERE w.source IS NOT NULL
        RETURN DISTINCT w.source as source, count(w) as count
    """)
    print("\nExisting sources:")
    for record in result:
        print(f"  {record['source']}: {record['count']} nodes")
    
    # Check relationships
    result = session.run("MATCH ()-[r:SYNONYM_OF]->() RETURN count(r) as count")
    rel_count = result.single()
    print(f"\nExisting :SYNONYM_OF relationships: {rel_count['count'] if rel_count else 0}")
    
    return word_count

def migrate_jlpt_property(session):
    """Migrate jlpt_level to old_jlpt_level if needed"""
    print("\n" + "=" * 60)
    print("MIGRATING JLPT PROPERTY")
    print("=" * 60)
    
    result = session.run("""
        MATCH (w:Word)
        WHERE w.jlpt_level IS NOT NULL
        RETURN count(w) as count
    """)
    count = result.single()['count']
    
    if count > 0:
        print(f"Found {count} nodes with jlpt_level, migrating...")
        session.run("""
            MATCH (w:Word)
            WHERE w.jlpt_level IS NOT NULL AND w.old_jlpt_level IS NULL
            SET w.old_jlpt_level = w.jlpt_level
            REMOVE w.jlpt_level
        """)
        print("Migration complete")
    else:
        print("No nodes with jlpt_level found, skipping migration")

def create_constraints(session):
    """Create constraints and indexes if they don't exist"""
    print("\n" + "=" * 60)
    print("CREATING CONSTRAINTS AND INDEXES")
    print("=" * 60)
    
    constraints = [
        ("word_source_id_unique", """
            CREATE CONSTRAINT word_source_id_unique IF NOT EXISTS
            FOR (w:Word) REQUIRE (w.source, w.source_id) IS UNIQUE
        """),
    ]
    
    indexes = [
        ("word_lemma", "CREATE INDEX word_lemma IF NOT EXISTS FOR (w:Word) ON (w.lemma)"),
        ("word_reading", "CREATE INDEX word_reading IF NOT EXISTS FOR (w:Word) ON (w.reading)"),
        ("word_pos", "CREATE INDEX word_pos IF NOT EXISTS FOR (w:Word) ON (w.pos)"),
        ("word_source", "CREATE INDEX word_source IF NOT EXISTS FOR (w:Word) ON (w.source)"),
    ]
    
    for name, query in constraints:
        try:
            session.run(query)
            print(f"✓ Created constraint: {name}")
        except Exception as e:
            if "already exists" in str(e).lower():
                print(f"  Constraint {name} already exists")
            else:
                print(f"✗ Error creating constraint {name}: {e}")
    
    for name, query in indexes:
        try:
            session.run(query)
            print(f"✓ Created index: {name}")
        except Exception as e:
            if "already exists" in str(e).lower():
                print(f"  Index {name} already exists")
            else:
                print(f"✗ Error creating index {name}: {e}")

def import_lee_words(session, batch_size=1000):
    """Import Lee TSV words, preserving existing data"""
    print("\n" + "=" * 60)
    print("PHASE 1: IMPORTING LEE WORDS")
    print("=" * 60)
    
    # Read TSV
    df = pd.read_csv('Lee李  分類語彙表学習者用goi.xlsx - Sheet1.tsv', sep='\t')
    print(f"Total Lee words to process: {len(df)}")
    
    # Process in batches
    created = 0
    updated = 0
    
    for i in range(0, len(df), batch_size):
        batch = df.iloc[i:i+batch_size]
        
        # Prepare batch data
        batch_data = []
        for _, row in batch.iterrows():
            batch_data.append({
                'source_id': str(row['No']),
                'lemma': row['Standard orthography (kanji or other) 標準的な表記'],
                'reading': row['Katakana reading 読み'],
                'old_jlpt_level': row['Level 語彙の難易度'],
                'pos': row['品詞1'],
                'pos_detail': row['品詞2(詳細)'],
                'word_type': row['語種']
            })
        
        # MERGE nodes (won't overwrite existing)
        result = session.run("""
            UNWIND $batch AS item
            MERGE (w:Word {source: 'LeeGoi', source_id: item.source_id})
            ON CREATE SET
                w.lemma = item.lemma,
                w.reading = item.reading,
                w.old_jlpt_level = item.old_jlpt_level,
                w.pos = item.pos,
                w.pos_detail = item.pos_detail,
                w.word_type = item.word_type,
                w.lang = 'ja'
            ON MATCH SET
                w.lemma = COALESCE(w.lemma, item.lemma),
                w.reading = COALESCE(w.reading, item.reading),
                w.old_jlpt_level = COALESCE(w.old_jlpt_level, item.old_jlpt_level),
                w.pos = COALESCE(w.pos, item.pos),
                w.pos_detail = COALESCE(w.pos_detail, item.pos_detail),
                w.word_type = COALESCE(w.word_type, item.word_type)
            RETURN 
                SUM(CASE WHEN w.lemma = item.lemma THEN 0 ELSE 1 END) as created_count
        """, batch=batch_data)
        
        stats = result.single()
        batch_created = stats['created_count'] if stats else 0
        created += batch_created
        updated += len(batch) - batch_created
        
        if (i + batch_size) % 5000 == 0:
            print(f"  Processed {min(i + batch_size, len(df))}/{len(df)} Lee words...")
    
    print(f"✓ Lee import complete: {created} created, {updated} updated")

def import_networkx_nodes(session, batch_size=1000):
    """Import NetworkX nodes that aren't in Lee"""
    print("\n" + "=" * 60)
    print("PHASE 2: IMPORTING NETWORKX-ONLY NODES")
    print("=" * 60)
    
    # Load NetworkX graph
    with open('G_synonyms_2024_09_18.pickle', 'rb') as f:
        g = pickle.load(f)
    
    print(f"Total NetworkX nodes: {g.number_of_nodes()}")
    
    # Get Lee words
    df = pd.read_csv('Lee李  分類語彙表学習者用goi.xlsx - Sheet1.tsv', sep='\t')
    lee_words = set(df['Standard orthography (kanji or other) 標準的な表記'].dropna())
    
    # Find NetworkX-only nodes
    nx_only_nodes = []
    for node, attrs in g.nodes(data=True):
        if node not in lee_words:
            nx_only_nodes.append((node, attrs))
    
    print(f"NetworkX-only nodes to import: {len(nx_only_nodes)}")
    
    # Process in batches
    created = 0
    updated = 0
    
    for i in range(0, len(nx_only_nodes), batch_size):
        batch = nx_only_nodes[i:i+batch_size]
        
        # Prepare batch data
        batch_data = []
        for node, attrs in batch:
            batch_data.append({
                'source_id': node,  # Use word itself as ID
                'lemma': node,
                'reading': attrs.get('hiragana'),
                'pos': attrs.get('POS') or attrs.get('pos'),
                'translation': attrs.get('translation'),
                'jlpt_from_nx': attrs.get('JLPT'),
                'jlpt_jisho': attrs.get('jlpt_jisho_lemma')
            })
        
        # MERGE nodes
        result = session.run("""
            UNWIND $batch AS item
            MERGE (w:Word {source: 'NetworkX', source_id: item.source_id})
            ON CREATE SET
                w.lemma = item.lemma,
                w.reading = item.reading,
                w.pos = item.pos,
                w.translation = item.translation,
                w.jlpt_from_nx = item.jlpt_from_nx,
                w.jlpt_jisho = item.jlpt_jisho,
                w.lang = 'ja'
            ON MATCH SET
                w.reading = COALESCE(w.reading, item.reading),
                w.pos = COALESCE(w.pos, item.pos),
                w.translation = COALESCE(w.translation, item.translation),
                w.jlpt_from_nx = COALESCE(w.jlpt_from_nx, item.jlpt_from_nx),
                w.jlpt_jisho = COALESCE(w.jlpt_jisho, item.jlpt_jisho)
            RETURN 
                SUM(CASE WHEN w.lemma = item.lemma THEN 0 ELSE 1 END) as created_count
        """, batch=batch_data)
        
        stats = result.single()
        batch_created = stats['created_count'] if stats else 0
        created += batch_created
        updated += len(batch) - batch_created
        
        if (i + batch_size) % 5000 == 0:
            print(f"  Processed {min(i + batch_size, len(nx_only_nodes))}/{len(nx_only_nodes)} NetworkX nodes...")
    
    print(f"✓ NetworkX nodes import complete: {created} created, {updated} updated")

def import_synonym_relationships(session, batch_size=500):
    """Import synonym relationships from NetworkX"""
    print("\n" + "=" * 60)
    print("PHASE 3: IMPORTING SYNONYM RELATIONSHIPS")
    print("=" * 60)
    
    # Load NetworkX graph
    with open('G_synonyms_2024_09_18.pickle', 'rb') as f:
        g = pickle.load(f)
    
    print(f"Total edges in NetworkX: {g.number_of_edges()}")
    
    # Process edges
    edges_to_import = []
    edge_id = 0
    
    for u, v, key, attrs in g.edges(keys=True, data=True):
        edge_id += 1
        edges_to_import.append({
            'from_word': u,
            'to_word': v,
            'edge_id': f"nx_edge_{edge_id}",
            'attrs': attrs
        })
    
    print(f"Edges to process: {len(edges_to_import)}")
    
    # Process in batches
    created = 0
    
    for i in range(0, len(edges_to_import), batch_size):
        batch = edges_to_import[i:i+batch_size]
        
        # Prepare batch data
        batch_data = []
        for edge in batch:
            attrs = edge['attrs']
            batch_data.append({
                'from_word': edge['from_word'],
                'to_word': edge['to_word'],
                'edge_id': edge['edge_id'],
                'synonym_strength': attrs.get('synonym_strength'),
                'relation_type': attrs.get('relation_type'),
                'mutual_sense': attrs.get('mutual_sense'),
                'mutual_sense_hiragana': attrs.get('mutual_sense_hiragana'),
                'mutual_sense_translation': attrs.get('mutual_sense_translation'),
                'synonymy_domain': attrs.get('synonymy_domain'),
                'synonymy_domain_hiragana': attrs.get('synonymy_domain_hiragana'),
                'synonymy_domain_translation': attrs.get('synonymy_domain_translation'),
                'synonymy_explanation': attrs.get('synonymy_explanation'),
                'weight': attrs.get('weight'),
                'is_antonym': attrs.get('antonym', False),
                'is_synonym': attrs.get('synonym', True)
            })
        
        # Create relationships
        result = session.run("""
            UNWIND $batch AS item
            MATCH (a:Word {lemma: item.from_word})
            MATCH (b:Word {lemma: item.to_word})
            WHERE a <> b
            MERGE (a)-[r:SYNONYM_OF {edge_id: item.edge_id}]->(b)
            ON CREATE SET
                r.source = 'G_synonyms_2024_09_18',
                r.synonym_strength = item.synonym_strength,
                r.relation_type = item.relation_type,
                r.mutual_sense = item.mutual_sense,
                r.mutual_sense_hiragana = item.mutual_sense_hiragana,
                r.mutual_sense_translation = item.mutual_sense_translation,
                r.synonymy_domain = item.synonymy_domain,
                r.synonymy_domain_hiragana = item.synonymy_domain_hiragana,
                r.synonymy_domain_translation = item.synonymy_domain_translation,
                r.synonymy_explanation = item.synonymy_explanation,
                r.weight = item.weight,
                r.is_antonym = item.is_antonym,
                r.is_synonym = item.is_synonym
            RETURN count(r) as created_count
        """, batch=batch_data)
        
        stats = result.single()
        created += stats['created_count'] if stats else 0
        
        if (i + batch_size) % 5000 == 0:
            print(f"  Processed {min(i + batch_size, len(edges_to_import))}/{len(edges_to_import)} edges...")
    
    print(f"✓ Synonym relationships import complete: {created} created")

def verify_migration(session):
    """Verify the migration results"""
    print("\n" + "=" * 60)
    print("VERIFICATION")
    print("=" * 60)
    
    # Count nodes by source
    result = session.run("""
        MATCH (w:Word)
        RETURN w.source as source, count(w) as count
        ORDER BY source
    """)
    print("\nNodes by source:")
    for record in result:
        print(f"  {record['source']}: {record['count']} nodes")
    
    # Count relationships
    result = session.run("""
        MATCH ()-[r:SYNONYM_OF]->()
        RETURN count(r) as count
    """)
    print(f"\nTotal :SYNONYM_OF relationships: {result.single()['count']}")
    
    # Sample merged data
    result = session.run("""
        MATCH (w:Word {source: 'LeeGoi'})
        WHERE EXISTS((w)-[:SYNONYM_OF]-())
        RETURN w.lemma as word, w.reading as reading, 
               size((w)-[:SYNONYM_OF]-()) as synonym_count
        LIMIT 5
    """)
    print("\nSample Lee words with synonyms:")
    for record in result:
        print(f"  {record['word']} ({record['reading']}): {record['synonym_count']} synonyms")

def main():
    """Run the safe migration"""
    driver = GraphDatabase.driver(URI, auth=AUTH)
    
    try:
        with driver.session() as session:
            # Check current state
            existing_count = check_current_state(session)
            
            if existing_count > 0:
                response = input(f"\n⚠️  Found {existing_count} existing Word nodes. Continue with safe merge? (y/n): ")
                if response.lower() != 'y':
                    print("Migration cancelled")
                    return
            
            # Run migration phases
            migrate_jlpt_property(session)
            create_constraints(session)
            import_lee_words(session)
            import_networkx_nodes(session)
            import_synonym_relationships(session)
            verify_migration(session)
            
            print("\n✅ MIGRATION COMPLETE!")
            
    except Exception as e:
        print(f"\n❌ Error during migration: {e}")
        import traceback
        traceback.print_exc()
    finally:
        driver.close()

if __name__ == "__main__":
    main()
