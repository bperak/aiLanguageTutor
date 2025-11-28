#!/usr/bin/env python3
"""
Ensure Neo4j schema elements for Lessons and PragmaticPatterns.

Creates uniqueness constraints and property indexes used by the app.
Env: NEO4J_URI, NEO4J_USERNAME (or NEO4J_USER), NEO4J_PASSWORD
"""

from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv
from neo4j import GraphDatabase


ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

URI = os.getenv("NEO4J_URI", "bolt://localhost:7687").replace("neo4j://", "bolt://")
USER = os.getenv("NEO4J_USERNAME", os.getenv("NEO4J_USER", "neo4j"))
PASSWORD = os.getenv("NEO4J_PASSWORD")
if not PASSWORD:
    raise RuntimeError("NEO4J_PASSWORD not set")


def main() -> None:
    driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))
    with driver.session() as session:
        # Lesson uniqueness on lesson_id
        session.run(
            """
            CREATE CONSTRAINT lesson_id_unique IF NOT EXISTS
            FOR (l:Lesson) REQUIRE l.lesson_id IS UNIQUE
            """
        )
        # PragmaticPattern uniqueness on id
        session.run(
            """
            CREATE CONSTRAINT pragmatic_pattern_id_unique IF NOT EXISTS
            FOR (p:PragmaticPattern) REQUIRE p.id IS UNIQUE
            """
        )
        # Helpful property indexes
        session.run(
            """
            CREATE INDEX pragmatic_pattern_tags_if_not_exists IF NOT EXISTS
            FOR (p:PragmaticPattern) ON (p.tags)
            """
        )
        session.run(
            """
            CREATE INDEX lesson_status_if_not_exists IF NOT EXISTS
            FOR (l:Lesson) ON (l.status)
            """
        )
    driver.close()
    print("Neo4j lesson/pragmatics constraints ensured.")


if __name__ == "__main__":
    main()


