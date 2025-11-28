#!/usr/bin/env python3
"""
Check for basic Japanese words in our database
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
    # Check for basic Japanese words
    basic_words = ['の', 'て', 'は', 'だ', 'た', 'が', 'を', 'に', 'で', 'と', 'から', 'まで', 'より', 'へ', 'も', 'か', 'ね', 'よ', 'わ', 'な', 'です', 'である', 'ます', 'る', 'う', 'よう', 'まい', 'ない', 'ぬ', 'ず', 'れる', 'られる', 'せる', 'させる']
    
    result = session.run('''
        MATCH (w:Word)
        WHERE w.lemma IN $basic_words
        RETURN w.lemma, w.kanji, w.hiragana, w.romaji
        LIMIT 20
    ''', basic_words=basic_words)
    
    print('Basic Japanese words found:')
    count = 0
    for record in result:
        lemma = record['w.lemma']
        kanji = record['w.kanji']
        hiragana = record['w.hiragana']
        romaji = record['w.romaji']
        print(f'Lemma: {repr(lemma)}, Kanji: {repr(kanji)}, Hiragana: {repr(hiragana)}, Romaji: {repr(romaji)}')
        count += 1
    
    print(f'\nTotal basic words found: {count}')
    
    # Check total Word count
    result = session.run('MATCH (w:Word) RETURN count(w) as total')
    total = result.single()['total']
    print(f'Total Word nodes: {total}')
    
    # Check for any single character words
    result = session.run('''
        MATCH (w:Word)
        WHERE size(w.lemma) = 1
        RETURN w.lemma, w.kanji, w.hiragana, w.romaji
        LIMIT 10
    ''')
    
    print('\nSingle character words:')
    for record in result:
        lemma = record['w.lemma']
        kanji = record['w.kanji']
        hiragana = record['w.hiragana']
        romaji = record['w.romaji']
        print(f'Lemma: {repr(lemma)}, Kanji: {repr(kanji)}, Hiragana: {repr(hiragana)}, Romaji: {repr(romaji)}')

driver.close()


