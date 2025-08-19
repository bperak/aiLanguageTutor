#!/usr/bin/env python
"""Unify :Word node properties to a consistent schema"""
import os
import json
from datetime import datetime
from pathlib import Path
from neo4j import GraphDatabase  # type: ignore
from dotenv import load_dotenv

# Load environment variables
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

# Define unified schema attributes
UNIFIED_ATTRS = [
    'lemma',
    'reading_hiragana',
    'reading_katakana',
    'pos_primary',
    'pos_detailed',
    'difficulty_level',
    'difficulty_numeric',
    'etymology',
    'old_jlpt_level',
    'translation',
    'lee_id',
    'source',
    'created_at',
    'updated_at'
]

def unify_properties(session, batch_size=1000):
    """Fetch Word nodes and ensure they have the unified properties"""
    # Current timestamp for updated_at
    now = datetime.utcnow().isoformat() + 'Z'

    # Build Cypher to fetch in batches
    query_get_ids = ("MATCH (w:Word) RETURN w.source AS source, w.source_id AS id SKIP $skip LIMIT $limit")
    skip = 0
    total = session.run("MATCH (w:Word) RETURN count(w) AS c").single()['c']
    print(f"Total Word nodes: {total}")
    updated_count = 0

    while skip < total:
        records = session.run(query_get_ids, skip=skip, limit=batch_size)
        batch = []
        for rec in records:
            src = rec['source']
            sid = rec['id']
            # Prepare property update map
            props = {'updated_at': now}
            # created_at: set if missing
            props['created_at'] = None  # will use COALESCE in Cypher

            # lee_id
            if src == 'LeeGoi':
                props['lee_id'] = sid
            elif 'LeeGoi' in src:
                props['lee_id'] = sid

            # difficulty parsing
            # Assume difficulty_level is level or old_jlpt_level
            # We'll leave it as-is if exists

            # etymology: existing word_type
            # reading_hiragana: existing hiragana
            # reading_katakana: existing katakana or reading

            # Build batch row
            batch.append({'source': src, 'id': sid, 'props': props})

        # Run batch update
        session.run(
            """
            UNWIND $batch AS row
            MATCH (w:Word {source: row.source, source_id: row.id})
            SET w.updated_at = row.props.updated_at
            SET w.created_at = coalesce(w.created_at, row.props.created_at)
            SET w.lee_id = coalesce(w.lee_id, row.props.lee_id)
            """,
            batch=batch
        )
        updated_count += len(batch)
        print(f"Unified schema for {updated_count}/{total} nodes...")
        skip += batch_size

if __name__ == '__main__':
    with driver.session() as session:
        unify_properties(session)
    driver.close()
