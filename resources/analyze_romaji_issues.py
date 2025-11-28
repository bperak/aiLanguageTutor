#!/usr/bin/env python3
"""
Analyze romaji issues in the database
"""

from neo4j import GraphDatabase
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

URI = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
USER = os.getenv('NEO4J_USERNAME', 'neo4j')
PASSWORD = 'testpassword123'

# Handle Docker URIs
if URI.startswith('neo4j://neo4j:'):
    URI = URI.replace('neo4j://neo4j:', 'bolt://localhost:')
elif URI.startswith('neo4j://'):
    URI = URI.replace('neo4j://', 'bolt://localhost:')

driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))

with driver.session() as session:
    # Check for words missing romaji
    result = session.run('''
        MATCH (w:Word)
        WHERE w.romaji IS NULL OR w.romaji = ''
        RETURN w.lemma, w.kanji, w.hiragana, w.romaji
        LIMIT 10
    ''')
    
    print('Words missing romaji:')
    for record in result:
        lemma = record['w.lemma']
        kanji = record['w.kanji']
        hiragana = record['w.hiragana']
        romaji = record['w.romaji']
        print(f'Lemma: {repr(lemma)}, Kanji: {repr(kanji)}, Hiragana: {repr(hiragana)}, Romaji: {repr(romaji)}')
    
    # Check for words with problematic romaji (no spaces)
    result = session.run('''
        MATCH (w:Word)
        WHERE w.romaji IS NOT NULL 
        AND w.romaji <> ''
        AND NOT w.romaji CONTAINS ' '
        AND size(w.romaji) > 8
        RETURN w.lemma, w.kanji, w.hiragana, w.romaji
        LIMIT 10
    ''')
    
    print('\nWords with potentially problematic romaji (long, no spaces):')
    for record in result:
        lemma = record['w.lemma']
        kanji = record['w.kanji']
        hiragana = record['w.hiragana']
        romaji = record['w.romaji']
        print(f'Lemma: {repr(lemma)}, Kanji: {repr(kanji)}, Hiragana: {repr(hiragana)}, Romaji: {repr(romaji)}')
    
    # Check for specific example
    result = session.run('''
        MATCH (w:Word)
        WHERE w.lemma = '結構です' OR w.kanji = '結構です'
        RETURN w.lemma, w.kanji, w.hiragana, w.romaji
    ''')
    
    print('\nSpecific example - 結構です:')
    for record in result:
        lemma = record['w.lemma']
        kanji = record['w.kanji']
        hiragana = record['w.hiragana']
        romaji = record['w.romaji']
        print(f'Lemma: {repr(lemma)}, Kanji: {repr(kanji)}, Hiragana: {repr(hiragana)}, Romaji: {repr(romaji)}')

driver.close()


