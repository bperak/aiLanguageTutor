#!/usr/bin/env python
"""Enrich NetworkX-only :Word nodes with all node attributes from the NetworkX pickle"""
import os
import pickle
import json
from pathlib import Path
from neo4j import GraphDatabase  # type: ignore
from dotenv import load_dotenv
import pandas as pd

# Load environment variables from project .env
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

# Neo4j connection setup
URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
if URI.startswith("neo4j://neo4j:"):
    URI = URI.replace("neo4j://neo4j:", "bolt://localhost:")
elif URI.startswith("neo4j://"):
    URI = URI.replace("neo4j://", "bolt://")
USER = os.getenv("NEO4J_USER", "neo4j")
PASSWORD = os.getenv("NEO4J_PASSWORD")
if not PASSWORD:
    raise RuntimeError("NEO4J_PASSWORD not set in .env")

driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))

# Read Lee lemmas to identify NetworkX-only nodes
tsv_path = Path(__file__).parent / 'Lee李  分類語彙表学習者用goi.xlsx - Sheet1.tsv'
df = pd.read_csv(tsv_path, sep='\t')
lee_lemmas = set(df['Standard orthography (kanji or other) 標準的な表記'].dropna())

# Load NetworkX graph with attributes
pickle_path = Path(__file__).parent / 'G_synonyms_2024_09_18.pickle'
graph = pickle.load(open(pickle_path, 'rb'))

batch_size = 1000
batch = []
enriched = 0

with driver.session() as session:
    for node, attrs in graph.nodes(data=True):
        if node in lee_lemmas:
            continue
        # Prepare properties dict
        props = {'lemma': node, 'source': 'NetworkX', 'source_id': node, 'lang': 'ja'}
        # Merge all attrs
        for k, v in attrs.items():
            key = k.lower().replace(' ', '_')
            if v is None:
                continue
            if isinstance(v, (str, int, float, bool)):
                props[key] = v
            else:
                # Serialize complex values
                props[f"{key}_json"] = json.dumps(v, ensure_ascii=False)
        batch.append(props)
        if len(batch) >= batch_size:
            session.run(
                """
                UNWIND $batch AS row
                MERGE (w:Word {source:'NetworkX', source_id: row.source_id})
                SET w += row
                """,
                batch=batch
            )
            enriched += len(batch)
            print(f"Enriched {enriched:,} NetworkX nodes...")
            batch.clear()
    # Final batch
    if batch:
        session.run(
            """
            UNWIND $batch AS row
            MERGE (w:Word {source:'NetworkX', source_id: row.source_id})
            SET w += row
            """,
            batch=batch
        )
        enriched += len(batch)
        print(f"Enriched {enriched:,} NetworkX nodes (final batch)")

print(f"Done. Total NetworkX nodes enriched: {enriched:,}")

driver.close()
