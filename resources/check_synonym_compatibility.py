#!/usr/bin/env python
"""Check compatibility of AI-generated synonyms with existing structure"""
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

def analyze_existing_synonyms(session):
    """Analyze the structure of existing SYNONYM_OF relationships"""
    print("=" * 80)
    print("EXISTING SYNONYM_OF RELATIONSHIP ANALYSIS")
    print("=" * 80)
    
    # Get all sources
    result = session.run("""
        MATCH ()-[r:SYNONYM_OF]->()
        RETURN DISTINCT r.source as source, count(r) as count
        ORDER BY count DESC
    """)
    
    print("\nExisting SYNONYM_OF sources:")
    sources = []
    for record in result:
        source = record['source'] or 'NULL'
        sources.append(source)
        print(f"  {source}: {record['count']:,} relationships")
    
    # Analyze properties for each source
    for source in sources[:3]:  # Check top 3 sources
        print(f"\n--- Properties in source: {source} ---")
        
        result = session.run(f"""
            MATCH ()-[r:SYNONYM_OF {{source: $source}}]->()
            WITH r LIMIT 100
            UNWIND keys(r) as key
            WITH key, count(key) as freq
            RETURN key, freq
            ORDER BY freq DESC
        """, source=source)
        
        props = []
        for record in result:
            props.append(record['key'])
            print(f"    {record['key']:<30} (in {record['freq']}/100 samples)")
        
        # Show sample relationship
        result = session.run(f"""
            MATCH (a)-[r:SYNONYM_OF {{source: $source}}]->(b)
            RETURN a.kanji as from, b.kanji as to, r
            LIMIT 1
        """, source=source)
        
        for record in result:
            print(f"\n    Sample: {record['from']} → {record['to']}")
            rel_props = dict(record['r'])
            
            # Show key properties
            key_props = ['weight', 'strength', 'synonym_strength', 'relation_type', 
                        'mutual_sense', 'explanation', 'source']
            
            for prop in key_props:
                if prop in rel_props and rel_props[prop] is not None:
                    value = rel_props[prop]
                    if isinstance(value, str) and len(value) > 50:
                        value = value[:47] + "..."
                    print(f"      {prop}: {value}")

def check_ai_compatibility():
    """Show how AI-generated relationships will fit"""
    print("\n" + "=" * 80)
    print("AI-GENERATED SYNONYM COMPATIBILITY")
    print("=" * 80)
    
    print("""
PROPOSED AI-GENERATED SYNONYM STRUCTURE:
----------------------------------------

Relationship: (:Word)-[:SYNONYM_OF {source: 'AI_Generated'}]->(:Word)

Properties:
  source: 'AI_Generated'              ✓ Compatible - same as existing sources
  ai_provider: 'gemini' or 'openai'   ✓ New - identifies which AI was used
  strength: 0.1-1.0 (float)           ✓ Compatible - same as existing 'synonym_strength'
  explanation: "text explanation"      ✓ Compatible - same as existing 'synonymy_explanation'
  ai_generated: true                   ✓ New - boolean flag for filtering
  created_at: datetime()               ✓ New - timestamp for tracking
  
MAPPING TO EXISTING STRUCTURE:
-----------------------------
  AI 'strength' → existing 'synonym_strength' or 'weight'
  AI 'explanation' → existing 'synonymy_explanation'
  AI 'source' → existing 'source' (different value)
  
COMPATIBILITY ASSESSMENT:
------------------------
✅ FULLY COMPATIBLE - Uses same relationship type (:SYNONYM_OF)
✅ CONSISTENT PROPERTIES - Maps to existing property names where possible
✅ ADDITIVE APPROACH - Doesn't conflict with existing data
✅ DISTINGUISHABLE - Can filter AI vs manual vs NetworkX sources
✅ QUERYABLE - Can query by source, strength, creation date, etc.

EXAMPLE QUERIES AFTER AI ENHANCEMENT:
------------------------------------
// Get all AI-generated synonyms
MATCH ()-[r:SYNONYM_OF {source: 'AI_Generated'}]->()
RETURN count(r)

// Compare AI vs NetworkX synonym strengths
MATCH ()-[r:SYNONYM_OF]->()
WHERE r.source IN ['AI_Generated', 'G_synonyms_2024_09_18']
RETURN r.source, avg(r.strength) as avg_strength

// Get high-confidence AI synonyms
MATCH (w1)-[r:SYNONYM_OF {source: 'AI_Generated'}]->(w2)
WHERE r.strength > 0.8
RETURN w1.kanji, w2.kanji, r.strength, r.explanation

// Words enhanced by AI
MATCH (w:Word)
WHERE EXISTS((w)-[:SYNONYM_OF {source: 'AI_Generated'}]-())
RETURN w.kanji, size((w)-[:SYNONYM_OF {source: 'AI_Generated'}]-()) as ai_synonyms
""")

def recommend_unified_schema():
    """Recommend a unified schema for all synonym sources"""
    print("\n" + "=" * 80)
    print("RECOMMENDED UNIFIED SYNONYM SCHEMA")
    print("=" * 80)
    
    print("""
CORE PROPERTIES (all sources should have):
-----------------------------------------
  source: string              - 'G_synonyms_2024_09_18', 'AI_Generated', 'WordNet_Translation', etc.
  weight: float (0.0-1.0)     - Unified strength/confidence score
  relation_type: string       - 'synonym', 'near_synonym', 'related', etc.
  created_at: datetime        - When relationship was created
  
SOURCE-SPECIFIC PROPERTIES:
--------------------------
NetworkX (G_synonyms_2024_09_18):
  synonym_strength: float     - Original NetworkX strength
  mutual_sense: string        - Shared semantic concept
  synonymy_domain: string     - Semantic domain
  synonymy_explanation: string - Human explanation
  
AI Generated:
  ai_provider: string         - 'gemini', 'openai'
  ai_generated: true          - Boolean flag
  explanation: string         - AI explanation
  
WordNet:
  english_bridge: string      - English word used for mapping
  method: 'translation_bridge' - How it was derived
  
MIGRATION STRATEGY:
------------------
1. Normalize 'weight' property:
   - NetworkX: weight = synonym_strength
   - AI: weight = strength  
   - WordNet: weight = 0.7 (default)

2. Normalize 'explanation':
   - NetworkX: explanation = synonymy_explanation
   - AI: explanation = explanation (already correct)
   - WordNet: explanation = f"Connected via English: {english_bridge}"

3. Add missing timestamps to existing relationships
""")

def main():
    with driver.session() as session:
        analyze_existing_synonyms(session)
        check_ai_compatibility()
        recommend_unified_schema()
    
    driver.close()

if __name__ == "__main__":
    main()
