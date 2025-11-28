#!/usr/bin/env python3
"""
Migrate Word orthography properties to a clearer schema.

Adds and populates the following properties on :Word nodes:
- standard_orthography: canonical surface form (copied from legacy 'kanji')
- reading_hiragana: copied from legacy 'hiragana'
- reading_katakana: copied from legacy 'katakana' or 'vdrj_standard_reading'

Also creates helpful indexes on these fields.

The script is additive and non-destructive: it does NOT remove legacy fields.
"""

import os
from pathlib import Path
from neo4j import GraphDatabase  # type: ignore
from dotenv import load_dotenv


def load_env():
    env_path = Path(__file__).parent.parent / '.env'
    load_dotenv(env_path)
    uri = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
    # Normalize docker "neo4j://" URIs to bolt
    if uri.startswith('neo4j://neo4j:'):
        uri = uri.replace('neo4j://neo4j:', 'bolt://localhost:')
    elif uri.startswith('neo4j://'):
        uri = uri.replace('neo4j://', 'bolt://')
    user = os.getenv('NEO4J_USERNAME') or os.getenv('NEO4J_USER', 'neo4j')
    password = os.getenv('NEO4J_PASSWORD')
    if not password:
        raise RuntimeError('NEO4J_PASSWORD not set in .env')
    return uri, user, password


def run_migration(session):
    print('Populating standard_orthography from kanji (where missing)...')
    res = session.run(
        """
        MATCH (w:Word)
        WHERE w.standard_orthography IS NULL AND w.kanji IS NOT NULL
        SET w.standard_orthography = w.kanji,
            w.updated_at = coalesce(w.updated_at, datetime())
        RETURN count(w) AS updated
        """
    ).single()
    print(f"  Updated: {res['updated']}")

    print('Populating reading_hiragana from hiragana (where missing)...')
    res = session.run(
        """
        MATCH (w:Word)
        WHERE w.reading_hiragana IS NULL AND w.hiragana IS NOT NULL
        SET w.reading_hiragana = w.hiragana,
            w.updated_at = coalesce(w.updated_at, datetime())
        RETURN count(w) AS updated
        """
    ).single()
    print(f"  Updated: {res['updated']}")

    print('Populating reading_katakana from katakana (where missing)...')
    res = session.run(
        """
        MATCH (w:Word)
        WHERE w.reading_katakana IS NULL AND w.katakana IS NOT NULL
        SET w.reading_katakana = w.katakana,
            w.updated_at = coalesce(w.updated_at, datetime())
        RETURN count(w) AS updated
        """
    ).single()
    print(f"  Updated: {res['updated']}")

    print('Filling reading_katakana from VDRJ standard reading (as fallback)...')
    res = session.run(
        """
        MATCH (w:Word)
        WHERE (w.reading_katakana IS NULL OR w.reading_katakana = '')
          AND w.vdrj_standard_reading IS NOT NULL AND w.vdrj_standard_reading <> ''
        SET w.reading_katakana = w.vdrj_standard_reading,
            w.updated_at = coalesce(w.updated_at, datetime())
        RETURN count(w) AS updated
        """
    ).single()
    print(f"  Updated: {res['updated']}")

    print('Creating indexes (if not exists)...')
    idx_queries = [
        "CREATE INDEX word_standard_orthography IF NOT EXISTS FOR (w:Word) ON (w.standard_orthography)",
        "CREATE INDEX word_reading_hiragana IF NOT EXISTS FOR (w:Word) ON (w.reading_hiragana)",
        "CREATE INDEX word_reading_katakana IF NOT EXISTS FOR (w:Word) ON (w.reading_katakana)",
        "CREATE INDEX word_std_ortho_hira IF NOT EXISTS FOR (w:Word) ON (w.standard_orthography, w.reading_hiragana)",
    ]
    for q in idx_queries:
        try:
            session.run(q)
            print(f"  OK {q}")
        except Exception as e:
            print(f"  WARN Index creation failed for: {q} | {e}")

    print('Summary counts for new properties:')
    res = session.run(
        """
        MATCH (w:Word)
        RETURN 
          sum(CASE WHEN w.standard_orthography IS NOT NULL THEN 1 ELSE 0 END) AS with_std_ortho,
          sum(CASE WHEN w.reading_hiragana IS NOT NULL THEN 1 ELSE 0 END) AS with_hira,
          sum(CASE WHEN w.reading_katakana IS NOT NULL THEN 1 ELSE 0 END) AS with_kata
        """
    ).single()
    print(f"  standard_orthography: {res['with_std_ortho']} nodes")
    print(f"  reading_hiragana:     {res['with_hira']} nodes")
    print(f"  reading_katakana:     {res['with_kata']} nodes")


def main():
    uri, user, password = load_env()
    driver = GraphDatabase.driver(uri, auth=(user, password))
    try:
        with driver.session() as session:
            run_migration(session)
    finally:
        driver.close()


if __name__ == '__main__':
    main()
