#!/usr/bin/env python3
"""
Check the specific word 'いいえ' to see what romaji was generated
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from neo4j import GraphDatabase

def load_environment():
    """Load environment variables and setup Neo4j connection"""
    # Load environment variables from root directory
    env_path = Path(__file__).parent.parent / '.env'
    load_dotenv(env_path)
    
    # Neo4j connection configuration
    URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    USER = os.getenv("NEO4J_USERNAME", "neo4j")
    PASSWORD = "testpassword123"
    
    # Handle Docker container URIs
    if URI.startswith("neo4j://neo4j:"):
        URI = URI.replace("neo4j://neo4j:", "bolt://localhost:")
    elif URI.startswith("neo4j://"):
        URI = URI.replace("neo4j://", "bolt://localhost:")
    
    print(f"Connecting to Neo4j at: {URI}")
    
    try:
        driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))
        with driver.session() as session:
            result = session.run("RETURN 'Connection successful' as status")
            status = result.single()['status']
            print(f"✅ {status}")
        return driver
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return None

def check_iie_word(driver):
    """Check the specific word 'いいえ'"""
    with driver.session() as session:
        # Check the specific word
        result = session.run("""
            MATCH (w:Word)
            WHERE w.lemma = 'いいえ' OR w.kanji = 'いいえ' OR w.hiragana = 'いいえ'
            RETURN w.lemma, w.kanji, w.hiragana, w.romaji, w.vdrj_standard_reading
            LIMIT 5
        """)
        
        print("Checking word 'いいえ':")
        print("=" * 50)
        
        found = False
        for record in result:
            found = True
            print(f"Lemma: {record['w.lemma']}")
            print(f"Kanji: {record['w.kanji']}")
            print(f"Hiragana: {record['w.hiragana']}")
            print(f"Romaji: {record['w.romaji']}")
            print(f"Romaji (repr): {repr(record['w.romaji'])}")  # Show exact characters
            print(f"VDRJ katakana: {record['w.vdrj_standard_reading']}")
            print("---")
        
        if not found:
            print("Word 'いいえ' not found in database")
            
            # Check for similar words
            result2 = session.run("""
                MATCH (w:Word)
                WHERE w.hiragana CONTAINS 'いい' OR w.romaji CONTAINS 'iie' OR w.romaji CONTAINS 'I ie'
                RETURN w.lemma, w.kanji, w.hiragana, w.romaji
                LIMIT 10
            """)
            
            print("\nSimilar words found:")
            for record in result2:
                print(f"Lemma: {record['w.lemma']}, Kanji: {record['w.kanji']}, Hiragana: {record['w.hiragana']}, Romaji: {repr(record['w.romaji'])}")

def test_cutlet_iie():
    """Test cutlet with the specific word"""
    import cutlet
    
    print("\nTesting cutlet with 'いいえ':")
    print("=" * 50)
    
    katsu = cutlet.Cutlet()
    katsu.use_foreign_spelling = False
    test_text = 'いいえ'
    
    result = katsu.romaji(test_text)
    print(f"Cutlet result: '{test_text}' -> '{result}'")
    print(f"Cutlet result (repr): {repr(result)}")
    
    # Test if there are any spaces
    if ' ' in result:
        print("⚠️  WARNING: Result contains spaces!")
    else:
        print("✅ No spaces in result")

def main():
    """Main function"""
    print("Checking 'いいえ' word in database")
    print("=" * 60)
    
    # Test cutlet first
    test_cutlet_iie()
    
    # Check database
    driver = load_environment()
    if driver:
        try:
            check_iie_word(driver)
        finally:
            driver.close()
    else:
        print("Cannot connect to database")

if __name__ == "__main__":
    main()


