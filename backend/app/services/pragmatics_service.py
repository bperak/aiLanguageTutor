"""
Pragmatics service: fetch pragmatic patterns for a CanDoDescriptor.

Graph-first: reads (:CanDoDescriptor)-[:USES_PRAGMA]->(:PragmaticPattern).
Fallback: loads compiled resources/compiled/cando/{can_do_id}/pragmatic_patterns.json
and returns its 'instances' array.
"""

from __future__ import annotations

from typing import Any, Dict, List
import json
from pathlib import Path

from neo4j import AsyncSession


class PragmaticsService:
    def _compiled_dir_for(self, can_do_id: str) -> Path:
        return Path(__file__).resolve().parents[2] / "resources" / "compiled" / "cando" / can_do_id.replace(":", "_")

    def _load_compiled(self, can_do_id: str) -> List[Dict[str, Any]]:
        out_dir = self._compiled_dir_for(can_do_id)
        pp_path = out_dir / "pragmatic_patterns.json"
        if not pp_path.exists():
            return []
        data = json.loads(pp_path.read_text(encoding="utf-8"))
        # Accept multiple shapes: {instances: [...]}, {patterns: [...]}, or a raw list
        if isinstance(data, dict):
            if isinstance(data.get("instances"), list):
                return data["instances"]
            if isinstance(data.get("patterns"), list):
                return data["patterns"]
        if isinstance(data, list):
            return data
        return []

    async def get_pragmatics(self, *, session: AsyncSession, can_do_id: str) -> List[Dict[str, Any]]:
        # Try graph first
        query = """
        MATCH (c:CanDoDescriptor {uid: $can_do_id})-[:USES_PRAGMA]->(p:PragmaticPattern)
        RETURN properties(p) AS pattern
        """
        try:
            result = await session.run(query, can_do_id=can_do_id)
            items: List[Dict[str, Any]] = []
            async for rec in result:
                pat = rec.get("pattern")
                if isinstance(pat, dict):
                    # Ensure an id field for clients
                    if "id" not in pat and "uid" in pat:
                        pat["id"] = pat.get("uid")
                    items.append(pat)
            if items:
                return items
        except Exception:
            # Fall back silently on graph errors
            pass

        # Fallback to compiled
        return self._load_compiled(can_do_id)

    async def import_compiled_to_graph(self, *, session: AsyncSession, can_do_id: str) -> int:
        """Import compiled pragmatic pattern instances into Neo4j and link to CanDo.

        Returns number of patterns imported/linked.
        """
        items = self._load_compiled(can_do_id)
        if not items:
            return 0
        count = 0
        for pat in items:
            pid = pat.get("id") or pat.get("name")
            if not pid:
                continue
            # Prepare props without id
            props: Dict[str, Any] = {k: v for k, v in pat.items() if k != "id"}
            # Normalize small fields
            props.setdefault("locale", "ja-JP")
            # Upsert pattern and link to CanDo
            await session.run(
                """
                MERGE (p:PragmaticPattern {id: $id})
                SET p += $props,
                    p.register = coalesce(p.register, 'neutral'),
                    p.socialDistance = coalesce(p.socialDistance, 'equal')
                WITH p
                MERGE (c:CanDoDescriptor {uid: $can})
                MERGE (c)-[:USES_PRAGMA]->(p)
                """,
                id=pid,
                props=props,
                can=can_do_id,
            )
            count += 1
        return count


pragmatics_service = PragmaticsService()


