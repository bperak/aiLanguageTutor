#!/usr/bin/env python3
"""
Check Word node matching with VDRJ data
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
    # Check sample Word nodes
    result = session.run('''
        MATCH (w:Word)
        WHERE w.lemma IS NOT NULL
        RETURN w.lemma, w.kanji, w.hiragana, w.romaji
        LIMIT 10
    ''')
    
    print('Sample Word nodes:')
    for record in result:
        lemma = record['w.lemma']
        kanji = record['w.kanji']
        hiragana = record['w.hiragana']
        romaji = record['w.romaji']
        print(f'Lemma: {repr(lemma)}, Kanji: {repr(kanji)}, Hiragana: {repr(hiragana)}, Romaji: {repr(romaji)}')
    
    # Check if any match the VDRJ sample
    result = session.run('''
        MATCH (w:Word)
        WHERE w.lemma IN ['の', 'て', 'は', 'だ', 'た']
        RETURN w.lemma, w.kanji, w.hiragana, w.romaji
        LIMIT 10
    ''')
    
    print('\nMatching VDRJ sample words:')
    for record in result:
        lemma = record['w.lemma']
        kanji = record['w.kanji']
        hiragana = record['w.hiragana']
        romaji = record['w.romaji']
        print(f'Lemma: {repr(lemma)}, Kanji: {repr(kanji)}, Hiragana: {repr(hiragana)}, Romaji: {repr(romaji)}')

driver.close()


