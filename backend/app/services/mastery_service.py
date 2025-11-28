from __future__ import annotations

from typing import Any, Dict, List

from neo4j import AsyncSession


class MasteryService:
    async def upsert_mastery(
        self,
        *,
        session: AsyncSession,
        user_id: str,
        can_do_id: str,
        score: float,
    ) -> Dict[str, Any]:
        # Clamp score
        s = max(0.0, min(1.0, float(score)))
        # Update rolling probability p' = 0.7*p + 0.3*s (or set to s if null)
        query = """
        MERGE (u:User {user_id: $user_id})
        MERGE (c:CanDoDescriptor {uid: $can_do_id})
        MERGE (u)-[r:MASTERED]->(c)
        ON CREATE SET r.p = $s, r.updatedAt = timestamp()
        ON MATCH SET r.p = coalesce(0.7 * r.p + 0.3 * $s, $s), r.updatedAt = timestamp()
        RETURN r.p AS p
        """
        result = await session.run(query, user_id=user_id, can_do_id=can_do_id, s=s)
        rec = await result.single()
        p = float(rec["p"]) if rec else s
        return {"user_id": user_id, "can_do_id": can_do_id, "p": round(p, 3)}

    async def recommend_next(
        self,
        *,
        session: AsyncSession,
        can_do_id: str,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        query = """
        MATCH (c:CanDoDescriptor {uid: $can_do_id})
        OPTIONAL MATCH (c)-[:SAME_LEVEL]-(n1:CanDoDescriptor)
        WITH c, collect(DISTINCT n1) AS s1
        OPTIONAL MATCH (c)-[:SAME_TOPIC]-(n2:CanDoDescriptor)
        WITH c, s1, collect(DISTINCT n2) AS s2
        WITH c, s1 + s2 AS cand
        UNWIND cand AS x
        WITH DISTINCT x
        WHERE x IS NOT NULL AND x.uid <> $can_do_id
        RETURN x.uid AS can_do_id, x.primaryTopic AS primaryTopic, x.level AS level, x.type AS type, x.skillDomain AS skillDomain
        LIMIT $limit
        """
        result = await session.run(query, can_do_id=can_do_id, limit=limit)
        out: List[Dict[str, Any]] = []
        async for rec in result:
            out.append(dict(rec))
        return out


mastery_service = MasteryService()


