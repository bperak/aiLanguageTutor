#!/usr/bin/env python3
"""
Analyze word distribution in our database
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
    # Check word length distribution
    result = session.run('''
        MATCH (w:Word)
        WHERE w.lemma IS NOT NULL
        RETURN 
            CASE 
                WHEN size(w.lemma) = 1 THEN '1 char'
                WHEN size(w.lemma) = 2 THEN '2 chars'
                WHEN size(w.lemma) = 3 THEN '3 chars'
                WHEN size(w.lemma) = 4 THEN '4 chars'
                WHEN size(w.lemma) = 5 THEN '5 chars'
                ELSE '6+ chars'
            END as length_category,
            count(w) as count
        ORDER BY 
            CASE 
                WHEN size(w.lemma) = 1 THEN 1
                WHEN size(w.lemma) = 2 THEN 2
                WHEN size(w.lemma) = 3 THEN 3
                WHEN size(w.lemma) = 4 THEN 4
                WHEN size(w.lemma) = 5 THEN 5
                ELSE 6
            END
    ''')
    
    print('Word length distribution:')
    for record in result:
        length_cat = record['length_category']
        count = record['count']
        print(f'{length_cat}: {count} words')
    
    # Check for common Japanese words that might be in VDRJ
    common_words = ['人', '年', '日', '時', '分', '秒', '月', '火', '水', '木', '金', '土', '大', '小', '新', '古', '高', '低', '長', '短', '多', '少', '早', '遅', '美', '醜', '強', '弱', '重', '軽', '熱', '冷', '明', '暗', '正', '負', '上', '下', '前', '後', '左', '右', '中', '外', '内', '東', '西', '南', '北']
    
    result = session.run('''
        MATCH (w:Word)
        WHERE w.lemma IN $common_words
        RETURN w.lemma, w.kanji, w.hiragana, w.romaji
        LIMIT 20
    ''', common_words=common_words)
    
    print('\nCommon Japanese words found:')
    for record in result:
        lemma = record['w.lemma']
        kanji = record['w.kanji']
        hiragana = record['w.hiragana']
        romaji = record['w.romaji']
        print(f'Lemma: {repr(lemma)}, Kanji: {repr(kanji)}, Hiragana: {repr(hiragana)}, Romaji: {repr(romaji)}')

driver.close()


