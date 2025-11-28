#!/usr/bin/env python3
"""
Import PragmaticPattern instances for a given CanDoDescriptor compiled set into Neo4j.

Reads resources/compiled/cando/<can_do_id>/pragmatic_patterns.json and creates
(:PragmaticPattern {id}) nodes and [:USES_PRAGMA] edges from (:Lesson {lesson_id})
if a matching Lesson node exists. Otherwise imports only patterns.

Env: NEO4J_URI, NEO4J_USERNAME/NEO4J_USER, NEO4J_PASSWORD
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

from dotenv import load_dotenv
from neo4j import GraphDatabase, Session


ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")


def _normalize_uri(uri: str) -> str:
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


@dataclass
class PragmaticPattern:
    id: str
    pattern: str
    domain: str | None
    tags: List[str]
    examples: List[Dict[str, Any]]

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "PragmaticPattern":
        return PragmaticPattern(
            id=str(d.get("id") or d.get("pattern_id")),
            pattern=str(d.get("pattern")),
            domain=d.get("domain"),
            tags=list(d.get("tags") or []),
            examples=list(d.get("examples") or []),
        )


def ensure_constraints(session: Session) -> None:
    session.run(
        """
        CREATE CONSTRAINT pragmatic_pattern_id_unique IF NOT EXISTS
        FOR (p:PragmaticPattern) REQUIRE p.id IS UNIQUE
        """
    )


def import_patterns(session: Session, patterns: List[PragmaticPattern]) -> int:
    total = 0
    for p in patterns:
        session.run(
            """
            MERGE (pp:PragmaticPattern {id: $id})
            SET pp.pattern = $pattern,
                pp.domain = $domain,
                pp.tags = $tags,
                pp.examples = $examples
            """,
            {
                "id": p.id,
                "pattern": p.pattern,
                "domain": p.domain,
                "tags": p.tags,
                "examples": p.examples,
            },
        )
        total += 1
    return total


def link_lesson_uses_patterns(session: Session, lesson_id: str, pattern_ids: List[str]) -> int:
    if not lesson_id or not pattern_ids:
        return 0
    result = session.run(
        """
        MERGE (l:Lesson {lesson_id: $lesson_id})
        WITH l
        UNWIND $ids AS pid
        MATCH (p:PragmaticPattern {id: pid})
        MERGE (l)-[:USES_PRAGMA]->(p)
        RETURN count(p) AS linked
        """,
        {"lesson_id": lesson_id, "ids": pattern_ids},
    )
    rec = result.single()
    return int(rec["linked"]) if rec else 0


def load_patterns_file(can_do_id: str) -> tuple[list[PragmaticPattern], str | None]:
    compiled_dir = ROOT / "resources" / "compiled" / "cando" / can_do_id.replace(":", "_")
    path = compiled_dir / "pragmatic_patterns.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    patterns = [PragmaticPattern.from_dict(x) for x in (data.get("patterns") or data)]
    # Optional lesson_id alongside patterns file
    lesson_id = None
    manifest_path = compiled_dir / "lesson_plan.json"
    if manifest_path.exists():
        try:
            lesson = json.loads(manifest_path.read_text(encoding="utf-8"))
            lesson_id = lesson.get("lesson_id") or lesson.get("can_do_id")
        except Exception:
            lesson_id = None
    return patterns, lesson_id


def main() -> None:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--can-do-id", required=True, help="CanDoDescriptor id e.g. 'JFまるごと:13'")
    args = ap.parse_args()

    drv = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    patterns, lesson_id = load_patterns_file(args["can_do_id"] if isinstance(args, dict) else args.can_do_id)
    with drv.session() as s:
        ensure_constraints(s)
        imported = import_patterns(s, patterns)
        linked = link_lesson_uses_patterns(s, lesson_id or args.can_do_id, [p.id for p in patterns])
    drv.close()
    print(f"Imported {imported} pragmatic patterns; linked {linked} to lesson '{lesson_id or args.can_do_id}'.")


if __name__ == "__main__":
    main()


