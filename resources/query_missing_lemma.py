#!/usr/bin/env python3
"""
Query Word nodes without lemma property
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
    result = session.run('''
        MATCH (n:Word) 
        WHERE NOT EXISTS(n.lemma)
        RETURN n LIMIT 25
    ''')
    
    print('Word nodes without lemma property:')
    print('=' * 50)
    
    for i, record in enumerate(result, 1):
        node = record['n']
        print(f'{i:2d}. ID: {node.id}')
        print(f'    Properties: {dict(node)}')
        print()

driver.close()


