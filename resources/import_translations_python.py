#!/usr/bin/env python
"""Import translations from the NetworkX pickle directly into Neo4j via Python"""
import pickle
from pathlib import Path
from neo4j import GraphDatabase  # noqa: E0401 # type: ignore
import os
from dotenv import load_dotenv

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

# Load the pickle file
pickle_path = Path(__file__).parent / 'G_synonyms_2024_09_18.pickle'
w_graph = pickle.load(open(pickle_path, 'rb'))

# Prepare batches of (lemma, translation)
batch_size = 1000
batch = []
updated_total = 0

with driver.session() as session:
    for lemma, attrs in w_graph.nodes(data=True):
        translation = attrs.get('translation')
        if translation:
            batch.append({'lemma': lemma, 'translation': translation})
        if len(batch) >= batch_size:
            # Run batch update
            session.run(
                """
                UNWIND $batch AS row
                MATCH (w:Word {lemma: row.lemma})
                SET w.translation = coalesce(w.translation, row.translation)
                """,
                batch=batch
            )
            updated_total += len(batch)
            print(f"  Updated translations for {updated_total:,} words...")
            batch.clear()
    # Final batch
    if batch:
        session.run(
            """
            UNWIND $batch AS row
            MATCH (w:Word {lemma: row.lemma})
            SET w.translation = coalesce(w.translation, row.translation)
            """,
            batch=batch
        )
        updated_total += len(batch)
        print(f"  Updated translations for {updated_total:,} words (final batch)")

print(f"Done. Total translations applied: {updated_total:,}")
driver.close()
