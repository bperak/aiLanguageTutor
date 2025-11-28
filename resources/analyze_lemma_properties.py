#!/usr/bin/env python3
"""
Analyze all properties of nodes with 'lemma' property in Neo4j database
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from neo4j import GraphDatabase
import pandas as pd
from collections import Counter

def load_environment():
    """Load environment variables and setup Neo4j connection"""
    env_path = Path(__file__).parent.parent / '.env'
    load_dotenv(env_path)
    
    URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    USER = os.getenv("NEO4J_USERNAME", "neo4j")
    
    # Try environment password first, then fallback to Docker default
    env_password = os.getenv("NEO4J_PASSWORD")
    PASSWORD = env_password if env_password else "testpassword123"
    
    # Handle Docker container URIs
    if URI.startswith("neo4j://neo4j:"):
        URI = URI.replace("neo4j://neo4j:", "bolt://localhost:")
    elif URI.startswith("neo4j://"):
        URI = URI.replace("neo4j://", "bolt://localhost:")
    
    # Test connection with multiple password attempts
    passwords_to_try = [PASSWORD, "testpassword123"]
    
    for i, password in enumerate(passwords_to_try, 1):
        if password == PASSWORD and env_password:
            print(f"Trying environment password (attempt {i})")
        else:
            print(f"Trying fallback password (attempt {i})")
            
        try:
            driver = GraphDatabase.driver(URI, auth=(USER, password))
            with driver.session() as session:
                result = session.run("RETURN 'Connection successful' as status")
                status = result.single()['status']
                print(f"✅ {status}")
            return driver
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            if 'driver' in locals():
                driver.close()
            continue
    
    print("❌ All connection attempts failed")
    return None

def analyze_lemma_properties(driver):
    """Analyze all properties of nodes with lemma property"""
    if not driver:
        return None
    
    with driver.session() as session:
        print("=" * 80)
        print("LEMMA PROPERTIES ANALYSIS")
        print("=" * 80)
        
        # Get all unique properties for nodes with lemma
        print("\n1. ALL PROPERTIES FOUND ON NODES WITH LEMMA:")
        print("-" * 60)
        
        result = session.run("""
            MATCH (n)
            WHERE n.lemma IS NOT NULL
            WITH n LIMIT 10000
            UNWIND keys(n) as key
            WITH key, count(key) as frequency
            RETURN key, frequency
            ORDER BY frequency DESC
        """)
        
        all_properties = []
        for record in result:
            prop_name = record['key']
            frequency = record['frequency']
            all_properties.append((prop_name, frequency))
            print(f"  {prop_name:<30} : {frequency:>8,} occurrences")
        
        # Get sample values for each property
        print(f"\n2. SAMPLE VALUES FOR EACH PROPERTY:")
        print("-" * 60)
        
        for prop_name, frequency in all_properties[:15]:  # Show top 15 properties
            print(f"\n📋 Property: {prop_name} (found in {frequency:,} nodes)")
            
            # Get sample values
            result = session.run(f"""
                MATCH (n)
                WHERE n.lemma IS NOT NULL AND n.{prop_name} IS NOT NULL
                RETURN DISTINCT n.{prop_name} as value
                LIMIT 10
            """)
            
            sample_values = []
            for record in result:
                value = record['value']
                if isinstance(value, str) and len(value) > 50:
                    value = value[:47] + "..."
                sample_values.append(str(value))
            
            if sample_values:
                print(f"   Sample values: {', '.join(sample_values[:5])}")
                if len(sample_values) > 5:
                    print(f"   ... and {len(sample_values) - 5} more unique values")
            else:
                print("   No sample values found")
        
        # Analyze lemma values specifically
        print(f"\n3. LEMMA VALUE ANALYSIS:")
        print("-" * 60)
        
        # Get lemma statistics
        result = session.run("""
            MATCH (n)
            WHERE n.lemma IS NOT NULL
            RETURN 
                count(n) as total_with_lemma,
                count(DISTINCT n.lemma) as unique_lemmas,
                min(n.lemma) as min_lemma,
                max(n.lemma) as max_lemma
        """)
        
        lemma_stats = result.single()
        print(f"  Total nodes with lemma: {lemma_stats['total_with_lemma']:,}")
        print(f"  Unique lemma values: {lemma_stats['unique_lemmas']:,}")
        print(f"  First lemma (alphabetically): {lemma_stats['min_lemma']}")
        print(f"  Last lemma (alphabetically): {lemma_stats['max_lemma']}")
        
        # Get sample lemma values
        print(f"\n4. SAMPLE LEMMA VALUES:")
        print("-" * 60)
        
        result = session.run("""
            MATCH (n)
            WHERE n.lemma IS NOT NULL
            RETURN n.lemma as lemma, n.romaji as romaji, n.kanji as kanji, n.hiragana as hiragana
            LIMIT 20
        """)
        
        for i, record in enumerate(result, 1):
            lemma = record['lemma'] or 'N/A'
            romaji = record['romaji'] or 'N/A'
            kanji = record['kanji'] or 'N/A'
            hiragana = record['hiragana'] or 'N/A'
            print(f"  {i:2d}. Lemma: {lemma:<15} | Romaji: {romaji:<15} | Kanji: {kanji:<10} | Hiragana: {hiragana}")
        
        # Analyze property combinations
        print(f"\n5. PROPERTY COMBINATIONS ANALYSIS:")
        print("-" * 60)
        
        # Get most common property combinations
        result = session.run("""
            MATCH (n)
            WHERE n.lemma IS NOT NULL
            WITH n, keys(n) as props
            WITH props, count(n) as count
            ORDER BY count DESC
            LIMIT 10
            RETURN props, count
        """)
        
        print("  Most common property combinations:")
        for i, record in enumerate(result, 1):
            props = sorted(record['props'])
            count = record['count']
            print(f"  {i:2d}. {count:>6,} nodes: {', '.join(props[:8])}")
            if len(props) > 8:
                print(f"      ... and {len(props) - 8} more properties")
        
        # Analyze data types
        print(f"\n6. DATA TYPE ANALYSIS:")
        print("-" * 60)
        
        for prop_name, frequency in all_properties[:10]:  # Top 10 properties
            result = session.run(f"""
                MATCH (n)
                WHERE n.lemma IS NOT NULL AND n.{prop_name} IS NOT NULL
                WITH n.{prop_name} as value
                LIMIT 100
                RETURN 
                    count(value) as total,
                    count(CASE WHEN value IS NULL THEN 1 END) as null_count,
                    count(CASE WHEN value =~ '^[0-9]+$' THEN 1 END) as numeric_strings,
                    count(CASE WHEN value =~ '^[0-9]+\\.[0-9]+$' THEN 1 END) as decimal_strings,
                    count(CASE WHEN value =~ '^[a-zA-Z]+$' THEN 1 END) as alphabetic_strings,
                    count(CASE WHEN value =~ '^[\\u3040-\\u309F\\u30A0-\\u30FF\\u4E00-\\u9FAF]+$' THEN 1 END) as japanese_strings
            """)
            
            type_stats = result.single()
            total = type_stats['total']
            null_count = type_stats['null_count']
            numeric = type_stats['numeric_strings']
            decimal = type_stats['decimal_strings']
            alphabetic = type_stats['alphabetic_strings']
            japanese = type_stats['japanese_strings']
            
            print(f"  {prop_name}:")
            print(f"    Total values: {total:,}")
            print(f"    Numeric strings: {numeric:,} ({numeric/total*100:.1f}%)")
            print(f"    Decimal strings: {decimal:,} ({decimal/total*100:.1f}%)")
            print(f"    Alphabetic strings: {alphabetic:,} ({alphabetic/total*100:.1f}%)")
            print(f"    Japanese strings: {japanese:,} ({japanese/total*100:.1f}%)")
            print()
        
        return all_properties

def main():
    """Main function"""
    print("=" * 80)
    print("LEMMA PROPERTIES ANALYZER")
    print("=" * 80)
    
    driver = load_environment()
    if not driver:
        print("❌ Cannot proceed without database connection")
        return
    
    try:
        properties = analyze_lemma_properties(driver)
        
        print("\n" + "=" * 80)
        print("ANALYSIS COMPLETE!")
        print("=" * 80)
        print(f"✅ Found {len(properties)} unique properties on nodes with lemma")
        print("✅ Analyzed property combinations and data types")
        print("✅ Generated sample values and statistics")
        
    except Exception as e:
        print(f"❌ Error during analysis: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        if driver:
            driver.close()
            print("\n🔌 Database connection closed")

if __name__ == "__main__":
    main()
