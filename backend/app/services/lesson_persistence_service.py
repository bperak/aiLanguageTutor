"""
Lesson persistence service

Persists compiled lesson artifacts (lesson_plan.json, exercises.json, dialogs if present)
into PostgreSQL (tables: lessons, lesson_versions) and links a Neo4j (:Lesson)
node to the corresponding (:CanDoDescriptor {uid}).

This keeps the implementation minimal and avoids Alembic by issuing
CREATE TABLE IF NOT EXISTS statements before inserts.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, List, Tuple
import json
from pathlib import Path

import structlog
from sqlalchemy.ext.asyncio import AsyncSession as PgSession
from sqlalchemy import text, bindparam
from sqlalchemy.dialects.postgresql import JSONB

from neo4j import AsyncSession as Neo4jSession
from app.services.embedding_service import EmbeddingService


logger = structlog.get_logger()


class LessonPersistenceService:
    def __init__(self) -> None:
        self._embedding = EmbeddingService()

    """
    Service that loads compiled lesson JSON by can_do_id and persists it to Postgres,
    then ensures a corresponding Neo4j (:Lesson) node exists and is linked.
    """

    def _compiled_dir_for(self, can_do_id: str) -> Path:
        return Path(__file__).resolve().parents[2] / "resources" / "compiled" / "cando" / can_do_id.replace(":", "_")

    def _load_json_if_exists(self, path: Path) -> Optional[Dict[str, Any]]:
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except Exception as e:  # noqa: BLE001
                logger.warning("Failed to parse JSON", path=str(path), error=str(e))
        return None

    def _load_compiled_bundle(self, can_do_id: str) -> Dict[str, Any]:
        out_dir = self._compiled_dir_for(can_do_id)
        lp = self._load_json_if_exists(out_dir / "lesson_plan.json")
        if lp is None:
            raise FileNotFoundError(f"Compiled lesson not found: {out_dir / 'lesson_plan.json'}")
        ex = self._load_json_if_exists(out_dir / "exercises.json")
        dlg = self._load_json_if_exists(out_dir / "sample_dialog.json")
        man = self._load_json_if_exists(out_dir / "manifest.json")  # optional, may be created later
        return {
            "lesson_plan": lp,
            "exercises": ex,
            "dialogs": dlg,
            "manifest": man,
        }

    async def persist(
        self,
        *,
        can_do_id: str,
        version: int = 1,
        pg: PgSession,
        neo: Neo4jSession,
    ) -> Dict[str, Any]:
        """
        Persist compiled lesson by can_do_id to Postgres and link Neo4j Lesson node.

        Args:
            can_do_id: The CanDoDescriptor UID (e.g., "JFまるごと:13").
            version: Semantic version integer of the lesson artifacts.
            pg: Async SQLAlchemy session for PostgreSQL.
            neo: Async Neo4j session.

        Returns:
            Dict with {lesson_id, version, can_do_id}.
        """
        bundle = self._load_compiled_bundle(can_do_id)

        # Assumes tables are created by migrations.

        # Upsert lesson row
        lesson_row = await pg.execute(
            text("SELECT id FROM lessons WHERE can_do_id = :can_do_id LIMIT 1"),
            {"can_do_id": can_do_id},
        )
        lesson_id = lesson_row.scalar_one_or_none()
        if lesson_id is None:
            inserted = await pg.execute(
                text("INSERT INTO lessons (can_do_id, status) VALUES (:can_do_id, 'active') RETURNING id"),
                {"can_do_id": can_do_id},
            )
            lesson_id = inserted.scalar_one()

        # Upsert lesson version (update if exists, else insert)
        ver_row = await pg.execute(
            text("SELECT id FROM lesson_versions WHERE lesson_id = :lesson_id AND version = :version LIMIT 1"),
            {"lesson_id": lesson_id, "version": version},
        )
        ver_id = ver_row.scalar_one_or_none()
        payload = {
            "lesson_plan": json.dumps(bundle["lesson_plan"], ensure_ascii=False),
            "exercises": json.dumps(bundle["exercises"]) if bundle["exercises"] is not None else None,
            "manifest": json.dumps(bundle["manifest"]) if bundle["manifest"] is not None else None,
            "dialogs": json.dumps(bundle["dialogs"]) if bundle["dialogs"] is not None else None,
        }
        if ver_id is None:
            stmt = (
                text(
                    "INSERT INTO lesson_versions (lesson_id, version, lesson_plan, exercises, manifest, dialogs) "
                    "VALUES (:lesson_id, :version, :lesson_plan, :exercises, :manifest, :dialogs)"
                )
                .bindparams(
                    bindparam("lesson_plan", type_=JSONB),
                    bindparam("exercises", type_=JSONB),
                    bindparam("manifest", type_=JSONB),
                    bindparam("dialogs", type_=JSONB),
                )
            )
            await pg.execute(
                stmt,
                {"lesson_id": lesson_id, "version": version, **payload},
            )
        else:
            stmt = (
                text(
                    "UPDATE lesson_versions SET lesson_plan = :lesson_plan, "
                    "exercises = :exercises, manifest = :manifest, dialogs = :dialogs "
                    "WHERE id = :id"
                )
                .bindparams(
                    bindparam("lesson_plan", type_=JSONB),
                    bindparam("exercises", type_=JSONB),
                    bindparam("manifest", type_=JSONB),
                    bindparam("dialogs", type_=JSONB),
                )
            )
            await pg.execute(
                stmt,
                {"id": ver_id, **payload},
            )

        # Link Neo4j (:Lesson)-[:FOR]->(:CanDoDescriptor)
        await neo.run(
            """
            MERGE (l:Lesson {lesson_id: $lesson_id})
            SET l.can_do_id = $can_do_id, l.status = 'active'
            WITH l
            MERGE (c:CanDoDescriptor {uid: $can_do_id})
            MERGE (l)-[:FOR]->(c)
            RETURN l.lesson_id AS lesson_id
            """,
            lesson_id=int(lesson_id),
            can_do_id=can_do_id,
        )

        logger.info("Lesson persisted", can_do_id=can_do_id, lesson_id=int(lesson_id), version=int(version))
        return {"lesson_id": int(lesson_id), "version": int(version), "can_do_id": can_do_id}

    def _iter_chunks(self, master: Dict[str, Any]) -> List[Tuple[str, str, int, str]]:
        """Yield (section, card_id, position, lang_text) entries for embedding.

        Creates structure-aware chunks from reading paragraphs, dialogue windows,
        teach/practice/culture cards, and lesson plan steps.
        """
        chunks: List[Tuple[str, str, int, str]] = []
        ui = (master or {}).get("ui", {}) or {}
        sections = ui.get("sections", []) or []
        for sec in sections:
            s_type = str(sec.get("type") or "").strip()
            cards = sec.get("cards", []) or []
            pos = 0
            for c in cards:
                cid = str(c.get("id") or "")
                body = c.get("body") or {}
                # reading paragraphs
                if s_type == "reading" and isinstance(c.get("paragraphs"), list):
                    for i, para in enumerate(c.get("paragraphs") or []):
                        if not isinstance(para, dict):
                            continue
                        jp = str(para.get("jp") or "").strip()
                        en = str(para.get("en") or "").strip()
                        if jp:
                            chunks.append((s_type, cid, pos, jp))
                            pos += 1
                        if en:
                            chunks.append((s_type, cid, pos, en))
                            pos += 1
                else:
                    # generic body jp/en
                    for lang_key in ("jp", "en"):
                        txt = str(body.get(lang_key) or "").strip()
                        if txt:
                            chunks.append((s_type, cid, pos, txt))
                            pos += 1
                    # dialogue turns
                    if s_type == "dialogue" and isinstance(c.get("turns"), list):
                        for t in c.get("turns") or []:
                            for lang_key in ("jp", "en"):
                                ttxt = str(t.get(lang_key) or "").strip()
                                if ttxt:
                                    chunks.append((s_type, cid, pos, ttxt))
                                    pos += 1
        return chunks

    def _detect_lang(self, text_val: str) -> str:
        if any('\u3040' <= ch <= '\u30FF' or '\u4E00' <= ch <= '\u9FFF' for ch in text_val):
            return "jp"
        return "en"

    async def _insert_chunks_with_embeddings(
        self,
        *,
        pg: PgSession,
        lesson_id: int,
        version: int,
        can_do_id: str,
        master: Dict[str, Any],
    ) -> int:
        """Chunk master and insert into lesson_chunks with embeddings."""
        chunks = self._iter_chunks(master)
        inserted = 0
        for section, card_id, position, text_val in chunks:
            if not text_val:
                continue
            lang = self._detect_lang(text_val)
            try:
                embedding = await self._embedding.generate_content_embedding(text_val, provider="openai")
            except Exception:
                embedding = None
            await pg.execute(
                text(
                    """
                    INSERT INTO lesson_chunks (lesson_id, version, can_do_id, section, card_id, position, lang, text, tokens, embedding)
                    VALUES (:lesson_id, :version, :can_do_id, :section, :card_id, :position, :lang, :text, :tokens, :embedding)
                    """
                ),
                {
                    "lesson_id": int(lesson_id),
                    "version": int(version),
                    "can_do_id": can_do_id,
                    "section": section or "",
                    "card_id": card_id or "",
                    "position": int(position),
                    "lang": lang,
                    "text": text_val,
                    "tokens": len(text_val),
                    "embedding": embedding,
                },
            )
            inserted += 1
        return inserted

    async def persist_payload(
        self,
        *,
        can_do_id: str,
        lesson_plan: Dict[str, Any],
        pg: PgSession,
        neo: Neo4jSession,
        version: int = 1,
        exercises: Optional[Dict[str, Any]] = None,
        manifest: Optional[Dict[str, Any]] = None,
        dialogs: Optional[Dict[str, Any]] = None,
        master: Optional[Dict[str, Any]] = None,
        entities: Optional[Dict[str, Any]] = None,
        timings: Optional[Dict[str, Any]] = None,
        source: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        parent_version: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Persist an in-memory lesson package payload to Postgres and link Neo4j Lesson node.

        Stores the payload as lesson_versions.lesson_plan (JSONB). Optional parts stored when provided.
        """
        # Upsert lesson row
        res = await pg.execute(text("SELECT id FROM lessons WHERE can_do_id = :can LIMIT 1"), {"can": can_do_id})
        lesson_id = (res.scalar_one_or_none())
        if lesson_id is None:
            inserted = await pg.execute(
                text("INSERT INTO lessons (can_do_id, status) VALUES (:can, 'active') RETURNING id"),
                {"can": can_do_id},
            )
            lesson_id = inserted.scalar_one()

        # Upsert lesson version
        res2 = await pg.execute(
            text("SELECT id FROM lesson_versions WHERE lesson_id = :lid AND version = :ver LIMIT 1"),
            {"lid": int(lesson_id), "ver": int(version)},
        )
        ver_id = res2.scalar_one_or_none()
        payload = {
            "lesson_plan": json.dumps(lesson_plan, ensure_ascii=False),
            "exercises": json.dumps(exercises) if exercises is not None else None,
            "manifest": json.dumps(manifest) if manifest is not None else None,
            "dialogs": json.dumps(dialogs) if dialogs is not None else None,
            "master": json.dumps(master or lesson_plan, ensure_ascii=False) if (master or lesson_plan) is not None else None,
            "entities": json.dumps(entities) if entities is not None else None,
            "timings": json.dumps(timings) if timings is not None else None,
            "pdf_path": None,
            "source": source,
            "context": json.dumps(context) if context is not None else None,
            "parent_version": parent_version,
        }
        if ver_id is None:
            stmt = (
                text(
                    "INSERT INTO lesson_versions (lesson_id, version, lesson_plan, exercises, manifest, dialogs, master, entities, timings, pdf_path, source, context, parent_version) "
                    "VALUES (:lesson_id, :version, :lesson_plan, :exercises, :manifest, :dialogs, :master, :entities, :timings, :pdf_path, :source, :context, :parent_version)"
                )
                .bindparams(
                    bindparam("lesson_plan", type_=JSONB),
                    bindparam("exercises", type_=JSONB),
                    bindparam("manifest", type_=JSONB),
                    bindparam("dialogs", type_=JSONB),
                    bindparam("master", type_=JSONB),
                    bindparam("entities", type_=JSONB),
                    bindparam("timings", type_=JSONB),
                    bindparam("context", type_=JSONB),
                )
            )
            await pg.execute(stmt, {"lesson_id": int(lesson_id), "version": int(version), **payload})
        else:
            stmt = (
                text(
                    "UPDATE lesson_versions SET lesson_plan = :lesson_plan, exercises = :exercises, "
                    "manifest = :manifest, dialogs = :dialogs, master = :master, entities = :entities, timings = :timings, "
                    "pdf_path = :pdf_path, source = :source, context = :context, parent_version = :parent_version WHERE id = :id"
                )
                .bindparams(
                    bindparam("lesson_plan", type_=JSONB),
                    bindparam("exercises", type_=JSONB),
                    bindparam("manifest", type_=JSONB),
                    bindparam("dialogs", type_=JSONB),
                    bindparam("master", type_=JSONB),
                    bindparam("entities", type_=JSONB),
                    bindparam("timings", type_=JSONB),
                    bindparam("context", type_=JSONB),
                )
            )
            await pg.execute(stmt, {"id": int(ver_id), **payload})

        # Link Neo4j (:Lesson)-[:FOR]->(:CanDoDescriptor)
        await neo.run(
            """
            MERGE (l:Lesson {lesson_id: $lesson_id})
            SET l.can_do_id = $can_do_id, l.status = 'active'
            WITH l
            MERGE (c:CanDoDescriptor {uid: $can_do_id})
            MERGE (l)-[:FOR]->(c)
            RETURN l.lesson_id AS lesson_id
            """,
            lesson_id=int(lesson_id),
            can_do_id=can_do_id,
        )

        # Ensure persistence
        try:
            await pg.commit()
        except Exception:
            pass
        logger.info("Lesson payload persisted", can_do_id=can_do_id, lesson_id=int(lesson_id), version=int(version))
        # Insert chunks if master present
        if master:
            try:
                cnt = await self._insert_chunks_with_embeddings(
                    pg=pg,
                    lesson_id=int(lesson_id),
                    version=int(version),
                    can_do_id=can_do_id,
                    master=master,
                )
                try:
                    await pg.commit()
                except Exception:
                    pass
                logger.info("lesson_chunks inserted", count=cnt, lesson_id=int(lesson_id), version=int(version))
            except Exception as e:  # noqa: BLE001
                logger.warning("lesson_chunks insertion failed", error=str(e))
        return {"lesson_id": int(lesson_id), "version": int(version), "can_do_id": can_do_id}


lesson_persistence_service = LessonPersistenceService()


