#!/usr/bin/env python
"""
Add English topic translations to CanDoDescriptor nodes.

This migration script adds the primaryTopicEn property to all CanDoDescriptor nodes
by translating the existing primaryTopic values.

Usage:
    python backend/migrations/add_topic_translations.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Add parent directory to path to import from app
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from neo4j import GraphDatabase

from app.core.topic_translations import TOPIC_TRANSLATIONS


# Load environment variables
PROJECT_ROOT = Path(__file__).parent.parent.parent
ENV_PATH = PROJECT_ROOT / ".env"
load_dotenv(ENV_PATH)


def _normalize_uri(uri: str) -> str:
    """Normalize docker-style neo4j scheme to bolt for local dev."""
    if uri.startswith("neo4j://neo4j:"):
        return uri.replace("neo4j://neo4j:", "bolt://localhost:")
    if uri.startswith("neo4j://"):
        return uri.replace("neo4j://", "bolt://")
    return uri


NEO4J_URI = _normalize_uri(os.getenv("NEO4J_URI", "bolt://localhost:7687"))
NEO4J_USER = os.getenv("NEO4J_USER", os.getenv("NEO4J_USERNAME", "neo4j"))
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

if not NEO4J_PASSWORD:
    raise RuntimeError("NEO4J_PASSWORD is not set. Please define it in your .env file.")


def add_topic_translations():
    """Add English topic translations to all CanDoDescriptor nodes."""
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    
    try:
        with driver.session() as session:
            # Get count of nodes to update
            result = session.run("MATCH (c:CanDoDescriptor) RETURN count(c) AS total")
            total = result.single()["total"]
            print(f"Found {total} CanDoDescriptor nodes")
            
            # Update each topic translation
            updated = 0
            for ja_topic, en_topic in TOPIC_TRANSLATIONS.items():
                result = session.run(
                    """
                    MATCH (c:CanDoDescriptor)
                    WHERE c.primaryTopic = $ja_topic
                    SET c.primaryTopicEn = $en_topic
                    RETURN count(c) AS updated
                    """,
                    ja_topic=ja_topic,
                    en_topic=en_topic
                )
                count = result.single()["updated"]
                updated += count
                if count > 0:
                    print(f"  Updated {count} nodes: '{ja_topic}' -> '{en_topic}'")
            
            print(f"\nTotal updated: {updated} / {total} nodes")
            print("Migration completed successfully!")
            
    finally:
        driver.close()


if __name__ == "__main__":
    print("Adding English topic translations to CanDoDescriptor nodes...")
    add_topic_translations()

