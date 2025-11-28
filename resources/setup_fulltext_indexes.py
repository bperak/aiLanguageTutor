#!/usr/bin/env python3
"""
Safely create fulltext indexes for canonical Word fields.

Strategy:
- Prefer Neo4j 5 schema form: CREATE FULLTEXT INDEX ... FOR (w:Word) ON EACH [...]
- If schema form fails (older versions), try procedures if available:
  CALL db.index.fulltext.createNodeIndex(...)
- Skip gracefully if neither is supported.
"""

import os
from pathlib import Path
from neo4j import GraphDatabase  # type: ignore
from dotenv import load_dotenv


def load_env():
    env_path = Path(__file__).parent.parent / '.env'
    load_dotenv(env_path)
    uri = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
    if uri.startswith('neo4j://neo4j:'):
        uri = uri.replace('neo4j://neo4j:', 'bolt://localhost:')
    elif uri.startswith('neo4j://'):
        uri = uri.replace('neo4j://', 'bolt://')
    user = os.getenv('NEO4J_USERNAME') or os.getenv('NEO4J_USER', 'neo4j')
    password = os.getenv('NEO4J_PASSWORD')
    if not password:
        raise RuntimeError('NEO4J_PASSWORD not set in .env')
    return uri, user, password


def has_fulltext_procedures(session) -> bool:
    try:
        rec = session.run(
            "SHOW PROCEDURES YIELD name WHERE name STARTS WITH 'db.index.fulltext' RETURN count(*) AS c"
        ).single()
        return bool(rec and rec['c'] and rec['c'] > 0)
    except Exception:
        return False


def create_fulltext_schema(session, name: str, label: str, properties: list[str]) -> bool:
    props = ", ".join([f"w.{p}" for p in properties])
    cypher = (
        f"CREATE FULLTEXT INDEX {name} IF NOT EXISTS FOR (w:{label}) "
        f"ON EACH [{props}]"
    )
    try:
        session.run(cypher)
        print(f"OK schema fulltext created or exists: {name}")
        return True
    except Exception as e:
        print(f"Schema fulltext not available: {e}")
        return False


def drop_fulltext_schema(session, name: str):
    try:
        session.run(f"DROP INDEX {name} IF EXISTS")
        print(f"OK schema fulltext dropped (if existed): {name}")
    except Exception as e:
        print(f"Could not drop schema fulltext {name}: {e}")


def create_fulltext_procedure(session, name: str, label: str, properties: list[str]) -> bool:
    try:
        session.run(
            "CALL db.index.fulltext.createNodeIndex($name, $labels, $props)",
            name=name, labels=[label], props=properties,
        )
        print(f"OK procedure fulltext created: {name}")
        return True
    except Exception as e:
        print(f"Procedure fulltext create failed: {e}")
        return False


def drop_fulltext_procedure(session, name: str):
    try:
        session.run("CALL db.index.fulltext.drop($name)", name=name)
        print(f"OK procedure fulltext dropped: {name}")
    except Exception as e:
        print(f"Procedure fulltext drop failed (ignored): {e}")


def main():
    uri, user, password = load_env()
    driver = GraphDatabase.driver(uri, auth=(user, password))
    name = 'word_search'
    label = 'Word'
    props = ['standard_orthography', 'reading_hiragana', 'translation', 'pos_primary']

    with driver.session() as session:
        # Try schema form first (Neo4j 5+)
        created = create_fulltext_schema(session, name, label, props)
        if created:
            print('Fulltext index ensured via schema. Done.')
            driver.close()
            return

        # Fall back to procedures if available
        if has_fulltext_procedures(session):
            # Try dropping old index name, ignore errors
            drop_fulltext_procedure(session, name)
            ok = create_fulltext_procedure(session, name, label, props)
            if ok:
                print('Fulltext index ensured via procedures. Done.')
                driver.close()
                return
        else:
            print('Fulltext procedures not available; skipping fulltext index creation.')

    driver.close()


if __name__ == '__main__':
    main()

