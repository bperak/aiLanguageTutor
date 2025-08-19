#!/usr/bin/env python
"""Migrate existing SYNONYM_OF relationships to have complete attribute set"""
import os
from pathlib import Path
from neo4j import GraphDatabase  # type: ignore
from dotenv import load_dotenv

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

driver = GraphDatabase.driver(URI, auth=AUTH)

def analyze_missing_attributes(session):
    """Analyze which attributes are missing from existing SYNONYM_OF relationships"""
    print("=" * 80)
    print("ANALYZING MISSING ATTRIBUTES IN SYNONYM_OF RELATIONSHIPS")
    print("=" * 80)
    
    # Define the complete attribute set we want
    target_attributes = [
        'weight', 'synonym_strength', 'relation_type',
        'mutual_sense', 'mutual_sense_hiragana', 'mutual_sense_translation',
        'synonymy_domain', 'synonymy_domain_hiragana', 'synonymy_domain_translation',
        'synonymy_explanation', 'source', 'created_at'
    ]
    
    # Check availability by source
    result = session.run("""
        MATCH ()-[r:SYNONYM_OF]->()
        RETURN DISTINCT r.source as source, count(r) as count
        ORDER BY count DESC
    """)
    
    sources = []
    for record in result:
        source = record['source'] or 'NULL'
        sources.append((source, record['count']))
        print(f"Source: {source} - {record['count']:,} relationships")
    
    # Analyze each source
    for source, count in sources:
        print(f"\n--- Analyzing source: {source} ---")
        
        # Check which attributes are missing
        for attr in target_attributes:
            result = session.run(f"""
                MATCH ()-[r:SYNONYM_OF {{source: $source}}]->()
                RETURN 
                    count(r) as total,
                    sum(CASE WHEN r.{attr} IS NOT NULL THEN 1 ELSE 0 END) as has_attr,
                    sum(CASE WHEN r.{attr} IS NULL THEN 1 ELSE 0 END) as missing_attr
            """, source=source)
            
            stats = result.single()
            if stats and stats['total'] > 0:
                coverage = stats['has_attr'] / stats['total'] * 100
                missing = stats['missing_attr']
                
                status = "✓" if coverage > 90 else "⚠️" if coverage > 50 else "❌"
                print(f"  {status} {attr:<30}: {stats['has_attr']:>6,}/{stats['total']:,} ({coverage:5.1f}%) | Missing: {missing:,}")

def migrate_null_source_relationships(session):
    """Migrate relationships with NULL source"""
    print(f"\n" + "=" * 80)
    print("MIGRATING NULL SOURCE RELATIONSHIPS")
    print("=" * 80)
    
    # Check how many have NULL source
    result = session.run("""
        MATCH ()-[r:SYNONYM_OF]->()
        WHERE r.source IS NULL
        RETURN count(r) as count
    """)
    
    null_count = result.single()['count']
    print(f"Relationships with NULL source: {null_count:,}")
    
    if null_count > 0:
        # Set default source and basic attributes
        session.run("""
            MATCH ()-[r:SYNONYM_OF]->()
            WHERE r.source IS NULL
            SET r.source = 'Legacy_Import',
                r.weight = COALESCE(r.weight, r.synonym_strength, 0.5),
                r.synonym_strength = COALESCE(r.synonym_strength, r.weight, 0.5),
                r.relation_type = COALESCE(r.relation_type, 'LEGACY_SYNONYM'),
                r.created_at = COALESCE(r.created_at, datetime())
        """)
        
        print(f"✓ Updated {null_count:,} NULL source relationships")

def fill_missing_core_attributes(session):
    """Fill missing core attributes across all sources"""
    print(f"\n" + "=" * 80)
    print("FILLING MISSING CORE ATTRIBUTES")
    print("=" * 80)
    
    # Fill weight from synonym_strength or vice versa
    result = session.run("""
        MATCH ()-[r:SYNONYM_OF]->()
        WHERE (r.weight IS NULL AND r.synonym_strength IS NOT NULL)
        OR (r.synonym_strength IS NULL AND r.weight IS NOT NULL)
        SET r.weight = COALESCE(r.weight, r.synonym_strength),
            r.synonym_strength = COALESCE(r.synonym_strength, r.weight)
        RETURN count(r) as updated
    """)
    
    updated = result.single()['updated']
    print(f"✓ Synchronized weight/synonym_strength for {updated:,} relationships")
    
    # Add default relation_type where missing
    result = session.run("""
        MATCH ()-[r:SYNONYM_OF]->()
        WHERE r.relation_type IS NULL
        SET r.relation_type = CASE 
            WHEN r.source = 'AI_Generated' THEN 'AI_SYNONYM'
            WHEN r.source = 'G_synonyms_2024_09_18' THEN 'NETWORKX_SYNONYM'
            WHEN r.source = 'Legacy_Import' THEN 'LEGACY_SYNONYM'
            ELSE 'UNKNOWN_SYNONYM'
        END
        RETURN count(r) as updated
    """)
    
    updated = result.single()['updated']
    print(f"✓ Added relation_type to {updated:,} relationships")
    
    # Add created_at where missing
    result = session.run("""
        MATCH ()-[r:SYNONYM_OF]->()
        WHERE r.created_at IS NULL
        SET r.created_at = datetime()
        RETURN count(r) as updated
    """)
    
    updated = result.single()['updated']
    print(f"✓ Added created_at to {updated:,} relationships")

def add_default_semantic_structure(session):
    """Add default semantic structure to relationships missing it"""
    print(f"\n" + "=" * 80)
    print("ADDING DEFAULT SEMANTIC STRUCTURE")
    print("=" * 80)
    
    # For relationships missing mutual_sense, try to infer from word translations
    result = session.run("""
        MATCH (w1)-[r:SYNONYM_OF]->(w2)
        WHERE r.mutual_sense IS NULL
        AND w1.translation IS NOT NULL 
        AND w2.translation IS NOT NULL
        WITH r, w1, w2,
             CASE 
                 WHEN w1.translation = w2.translation THEN w1.translation
                 WHEN w1.pos = w2.pos THEN w1.pos + '_concept'
                 ELSE 'related_concept'
             END as inferred_sense
        SET r.mutual_sense_translation = inferred_sense,
            r.mutual_sense = CASE 
                WHEN inferred_sense = w1.translation THEN w1.kanji
                ELSE '関連概念'
            END,
            r.mutual_sense_hiragana = CASE 
                WHEN inferred_sense = w1.translation THEN w1.hiragana
                ELSE 'かんれんがいねん'
            END
        RETURN count(r) as updated
    """)
    
    updated = result.single()['updated']
    print(f"✓ Inferred mutual_sense for {updated:,} relationships")
    
    # Add default synonymy_domain based on POS
    result = session.run("""
        MATCH (w1)-[r:SYNONYM_OF]->(w2)
        WHERE r.synonymy_domain IS NULL
        AND w1.pos IS NOT NULL
        SET r.synonymy_domain_translation = CASE 
            WHEN w1.pos CONTAINS '名詞' THEN 'concepts'
            WHEN w1.pos CONTAINS '動詞' THEN 'actions' 
            WHEN w1.pos CONTAINS '形容詞' THEN 'qualities'
            WHEN w1.pos CONTAINS '副詞' THEN 'manner'
            ELSE 'general'
        END,
        r.synonymy_domain = CASE 
            WHEN w1.pos CONTAINS '名詞' THEN '概念'
            WHEN w1.pos CONTAINS '動詞' THEN '行為'
            WHEN w1.pos CONTAINS '形容詞' THEN '性質'
            WHEN w1.pos CONTAINS '副詞' THEN '様態'
            ELSE '一般'
        END,
        r.synonymy_domain_hiragana = CASE 
            WHEN w1.pos CONTAINS '名詞' THEN 'がいねん'
            WHEN w1.pos CONTAINS '動詞' THEN 'こうい'
            WHEN w1.pos CONTAINS '形容詞' THEN 'せいしつ'
            WHEN w1.pos CONTAINS '副詞' THEN 'ようたい'
            ELSE 'いっぱん'
        END
        RETURN count(r) as updated
    """)
    
    updated = result.single()['updated']
    print(f"✓ Added synonymy_domain to {updated:,} relationships")
    
    # Add default explanation where missing
    result = session.run("""
        MATCH (w1)-[r:SYNONYM_OF]->(w2)
        WHERE r.synonymy_explanation IS NULL
        SET r.synonymy_explanation = CASE 
            WHEN r.source = 'AI_Generated' THEN 'AI-generated semantic relationship'
            WHEN r.source = 'G_synonyms_2024_09_18' THEN 'NetworkX-derived relationship'
            WHEN r.source = 'Legacy_Import' THEN 'Legacy synonym relationship'
            ELSE 'Synonym relationship between ' + w1.kanji + ' and ' + w2.kanji
        END
        RETURN count(r) as updated
    """)
    
    updated = result.single()['updated']
    print(f"✓ Added explanations to {updated:,} relationships")

def verify_migration(session):
    """Verify all relationships now have complete attributes"""
    print(f"\n" + "=" * 80)
    print("MIGRATION VERIFICATION")
    print("=" * 80)
    
    target_attributes = [
        'weight', 'synonym_strength', 'relation_type',
        'mutual_sense', 'mutual_sense_hiragana', 'mutual_sense_translation',
        'synonymy_domain', 'synonymy_domain_hiragana', 'synonymy_domain_translation',
        'synonymy_explanation', 'source', 'created_at'
    ]
    
    print("Final attribute coverage:")
    for attr in target_attributes:
        result = session.run(f"""
            MATCH ()-[r:SYNONYM_OF]->()
            RETURN 
                count(r) as total,
                sum(CASE WHEN r.{attr} IS NOT NULL THEN 1 ELSE 0 END) as has_attr
        """)
        
        stats = result.single()
        if stats and stats['total'] > 0:
            coverage = stats['has_attr'] / stats['total'] * 100
            status = "✅" if coverage > 95 else "⚠️" if coverage > 80 else "❌"
            print(f"  {status} {attr:<30}: {stats['has_attr']:>8,}/{stats['total']:,} ({coverage:5.1f}%)")
    
    # Show sample of complete relationships
    print(f"\nSample complete relationships:")
    result = session.run("""
        MATCH (w1)-[r:SYNONYM_OF]->(w2)
        WHERE r.mutual_sense IS NOT NULL 
        AND r.synonymy_domain IS NOT NULL
        RETURN w1.kanji as word1, w2.kanji as word2, r.source as source,
               r.weight as weight, r.mutual_sense as mutual_sense,
               r.synonymy_domain as domain
        LIMIT 5
    """)
    
    print(f"{'Word1':<10} {'Word2':<10} {'Source':<20} {'Weight':<8} {'Mutual Sense':<15} {'Domain':<10}")
    print("-" * 80)
    for record in result:
        word1 = record['word1'][:8] if record['word1'] else 'N/A'
        word2 = record['word2'][:8] if record['word2'] else 'N/A'
        source = record['source'][:18] if record['source'] else 'N/A'
        weight = f"{record['weight']:.2f}" if record['weight'] else 'N/A'
        mutual = record['mutual_sense'][:13] if record['mutual_sense'] else 'N/A'
        domain = record['domain'][:8] if record['domain'] else 'N/A'
        
        print(f"{word1:<10} {word2:<10} {source:<20} {weight:<8} {mutual:<15} {domain:<10}")

def main():
    """Run the migration for existing synonym relationships"""
    print("=" * 80)
    print("MIGRATING EXISTING SYNONYM_OF RELATIONSHIPS")
    print("=" * 80)
    
    with driver.session() as session:
        # Analyze current state
        analyze_missing_attributes(session)
        
        # Ask for confirmation
        response = input(f"\nProceed with migration to add missing attributes? (y/n): ")
        if response.lower() != 'y':
            print("Migration cancelled")
            return
        
        # Run migration steps
        migrate_null_source_relationships(session)
        fill_missing_core_attributes(session)
        add_default_semantic_structure(session)
        
        # Verify results
        verify_migration(session)
        
        print(f"\n✅ SYNONYM RELATIONSHIP MIGRATION COMPLETE!")
        print(f"All SYNONYM_OF relationships now have complete attribute structure")
    
    driver.close()

if __name__ == "__main__":
    main()
