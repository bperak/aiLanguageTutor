#!/usr/bin/env python
"""
Import JF Can-do descriptors from a TSV into Neo4j as CanDoDescriptor nodes.

Node label
- CanDoDescriptor

Properties (English keys)
- uid: unique stable id ("{source}:{entryNumber}")
- entryNumber: int from "No."
- source: str from "種別"
- type: str from "種類"
- level: str from "レベル" (A1..C2)
- skillDomain: str from "活動" (e.g., 産出/受容/やりとり)
- category: str from "カテゴリー"
- primaryTopic: str from "第1トピック"
- descriptionJa: str from "JF Can-do (日本語)"
- descriptionEn: str from "JF Can-do (English)"

Usage (PowerShell on Windows):
  # Ensure venv and environment
  python -m venv .venv ; .\.venv\Scripts\Activate.ps1 ; pip install neo4j python-dotenv
  # Configure Neo4j connection via .env in project root (NEO4J_URI, NEO4J_USER/NEO4J_USERNAME, NEO4J_PASSWORD)
  python resources\can_do_import.py --file resources\can_do.tsv --batch-size 500

Create SAME_* relationships (without re-importing):
  python resources\can_do_import.py --relations-only --create-relations

Notes
- This script reads .env from the project root using dotenv. Secrets must be set by you in .env.
- Keeps it simple: single pass, batched MERGE with a uniqueness constraint on uid.
"""

from __future__ import annotations

import csv
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List

from dotenv import load_dotenv
from neo4j import GraphDatabase, Session


# ---------- Configuration ----------

PROJECT_ROOT = Path(__file__).parent.parent
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


# ---------- Data parsing ----------

EXPECTED_HEADERS = [
    "No.",
    "種別",
    "種類",
    "レベル",
    "活動",
    "カテゴリー",
    "第1トピック",
    "JF Can-do (日本語)",
    "JF Can-do (English)",
]


@dataclass
class CanDoRow:
    entryNumber: int
    source: str
    type: str
    level: str
    skillDomain: str
    category: str
    primaryTopic: str
    descriptionJa: str
    descriptionEn: str

    @property
    def uid(self) -> str:
        return f"{self.source}:{self.entryNumber}"

    def to_dict(self) -> Dict[str, object]:
        return {
            "uid": self.uid,
            "entryNumber": self.entryNumber,
            "source": self.source,
            "type": self.type,
            "level": self.level,
            "skillDomain": self.skillDomain,
            "category": self.category,
            "primaryTopic": self.primaryTopic,
            "descriptionJa": self.descriptionJa,
            "descriptionEn": self.descriptionEn,
        }


def parse_can_do_tsv(path: Path) -> List[CanDoRow]:
    """
    Parse the can_do.tsv and return structured rows.

    Args:
        path: Path to resources/can_do.tsv

    Returns:
        List of CanDoRow
    """
    rows: List[CanDoRow] = []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f, delimiter="\t")
        header = next(reader, None)
        if header is None:
            return rows

        # Basic header validation (lenient; compare by order and membership)
        if len(header) < len(EXPECTED_HEADERS):
            raise ValueError("TSV header has fewer columns than expected.")

        # Build index map by expected Japanese header titles
        index: Dict[str, int] = {}
        for name in EXPECTED_HEADERS:
            try:
                index[name] = header.index(name)
            except ValueError:
                raise ValueError(f"Expected column not found in TSV: {name}")

        for raw in reader:
            if not raw or all(not c.strip() for c in raw):
                continue

            def col(key: str) -> str:
                i = index[key]
                return raw[i].strip()

            try:
                entry_number = int(col("No."))
            except ValueError:
                # Skip malformed rows
                continue

            rows.append(
                CanDoRow(
                    entryNumber=entry_number,
                    source=col("種別"),
                    type=col("種類"),
                    level=col("レベル"),
                    skillDomain=col("活動"),
                    category=col("カテゴリー"),
                    primaryTopic=col("第1トピック"),
                    descriptionJa=col("JF Can-do (日本語)"),
                    descriptionEn=col("JF Can-do (English)"),
                )
            )

    return rows


# ---------- Neo4j import ----------

def ensure_constraints(session: Session) -> None:
    session.run(
        """
        CREATE CONSTRAINT can_do_descriptor_uid_if_not_exists
        IF NOT EXISTS FOR (c:CanDoDescriptor)
        REQUIRE c.uid IS UNIQUE
        """
    )


def ensure_property_indexes(session: Session) -> None:
    session.run(
        """
        CREATE INDEX cando_level_if_not_exists IF NOT EXISTS
        FOR (c:CanDoDescriptor) ON (c.level)
        """
    )
    session.run(
        """
        CREATE INDEX cando_topic_if_not_exists IF NOT EXISTS
        FOR (c:CanDoDescriptor) ON (c.primaryTopic)
        """
    )
    session.run(
        """
        CREATE INDEX cando_skilldomain_if_not_exists IF NOT EXISTS
        FOR (c:CanDoDescriptor) ON (c.skillDomain)
        """
    )
    session.run(
        """
        CREATE INDEX cando_type_if_not_exists IF NOT EXISTS
        FOR (c:CanDoDescriptor) ON (c.type)
        """
    )


def create_same_property_relationships(session: Session, property_key: str, rel_type: str) -> int:
    """Create SAME_* relationships for nodes sharing the same property value."""
    cypher = f"""
    MATCH (n:CanDoDescriptor)
    WHERE n.{property_key} IS NOT NULL AND n.{property_key} <> ''
    WITH n.{property_key} AS val, collect(n) AS nodes
    WHERE size(nodes) > 1
    UNWIND nodes AS a
    UNWIND nodes AS b
    WITH a, b
    WHERE a.uid < b.uid
    MERGE (a)-[:{rel_type}]->(b)
    RETURN count(*) AS created
    """
    result = session.run(cypher)
    record = result.single()
    return int(record["created"]) if record and "created" in record else 0


def create_all_same_relationships(session: Session) -> None:
    ensure_property_indexes(session)
    total_level = create_same_property_relationships(session, "level", "SAME_LEVEL")
    total_topic = create_same_property_relationships(session, "primaryTopic", "SAME_TOPIC")
    total_skill = create_same_property_relationships(session, "skillDomain", "SAME_SKILLDOMAIN")
    total_type = create_same_property_relationships(session, "type", "SAME_TYPE")
    print(
        f"Relationships created (pairs attempted): level={total_level}, topic={total_topic}, "
        f"skillDomain={total_skill}, type={total_type}"
    )


def import_rows(session: Session, rows: Iterable[CanDoRow], batch_size: int = 1000) -> int:
    """Batch MERGE all rows as CanDoDescriptor nodes. Returns total imported/updated count."""
    total = 0
    batch: List[Dict[str, object]] = []

    def flush(batch_payload: List[Dict[str, object]]) -> int:
        if not batch_payload:
            return 0
        session.run(
            """
            UNWIND $rows AS row
            MERGE (c:CanDoDescriptor {uid: row.uid})
            SET c.entryNumber = row.entryNumber,
                c.source = row.source,
                c.type = row.type,
                c.level = row.level,
                c.skillDomain = row.skillDomain,
                c.category = row.category,
                c.primaryTopic = row.primaryTopic,
                c.descriptionJa = row.descriptionJa,
                c.descriptionEn = row.descriptionEn
            """,
            {"rows": batch_payload},
        )
        return len(batch_payload)

    for row in rows:
        batch.append(row.to_dict())
        if len(batch) >= batch_size:
            total += flush(batch)
            batch.clear()

    total += flush(batch)
    return total


# ---------- CLI ----------

def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Import Can-do descriptors into Neo4j")
    parser.add_argument(
        "--file",
        type=str,
        default=str(Path(__file__).parent / "can_do.tsv"),
        help="Path to can_do.tsv",
    )
    parser.add_argument("--batch-size", type=int, default=1000, help="Batch size for import")
    parser.add_argument("--dry-run", action="store_true", help="Only parse and report counts")
    parser.add_argument("--create-relations", action="store_true", help="Create SAME_* relationships after import or standalone with --relations-only")
    parser.add_argument("--relations-only", action="store_true", help="Skip import; only create SAME_* relationships")

    args = parser.parse_args()
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    try:
        with driver.session() as session:
            if not args.relations_only:
                tsv_path = Path(args.file)
                if not tsv_path.exists():
                    raise FileNotFoundError(f"TSV file not found: {tsv_path}")

                rows = parse_can_do_tsv(tsv_path)
                print(f"Parsed rows: {len(rows):,}")
                if args.dry_run:
                    for sample in rows[:3]:
                        print({k: v for k, v in sample.to_dict().items() if k in ("uid", "level", "category")})
                    return

                ensure_constraints(session)
                total = import_rows(session, rows, batch_size=args.batch_size)
                print(f"Upserted {total:,} CanDoDescriptor nodes")

            if args.create_relations or args.relations_only:
                create_all_same_relationships(session)
    finally:
        driver.close()


if __name__ == "__main__":
    main()


