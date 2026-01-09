"""
Lexical endpoints: lightweight graph data and lexical lesson seeds.

Initial focus: provide a small ego-graph for visualization
with react-force-graph 2D/3D.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from neo4j import AsyncSession
from neo4j.exceptions import Neo4jError, ServiceUnavailable, SessionExpired
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession as PgSession
from sqlalchemy import select

from app.db import get_neo4j_session
from app.services.lexical_lessons_service import lexical_lessons
from app.services.grading_service import grading_service
from app.services.mastery_service import mastery_service
from app.services.readability_service import readability_service
from app.db import get_postgresql_session
from app.api.v1.endpoints.auth import get_current_user
from app.models.database_models import ConversationSession, ConversationMessage, User
from app.services.lesson_persistence_service import lesson_persistence_service
from app.services.pragmatics_service import pragmatics_service
from sqlalchemy import text


router = APIRouter()


def _neo4j_unavailable_http(exc: Exception) -> HTTPException:
    """
    Convert transient Neo4j driver/database errors into a retryable HTTP error.

    Reason: the lexical graph UI calls Neo4j-heavy endpoints; returning 500 for
    transient issues causes confusing UX and masks "try again" semantics.
    """
    # Keep the message generic to avoid leaking internal details in prod.
    return HTTPException(status_code=503, detail="Lexical graph temporarily unavailable")
@router.get("/lessons/activate")
@router.get("/lessons/activate", include_in_schema=False)
@router.get("/lessons/activate", include_in_schema=False)
async def activate_cando(can_do_id: str) -> Dict[str, Any]:
    """Return a LessonPlan JSON for the given CanDoDescriptor id.

    MVP: loads compiled lesson_plan.json; later: graph-first enrichment.
    """
    try:
        lesson = await lexical_lessons.activate_cando(can_do_id=can_do_id)
        return lesson
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Lesson not found for can_do_id")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cando/levels", include_in_schema=False)
async def list_cando_levels(*args, **kwargs):
    raise HTTPException(status_code=410, detail="Moved to /api/v1/cando/levels")


@router.get("/cando/topics", include_in_schema=False)
async def list_cando_topics(*args, **kwargs):
    raise HTTPException(status_code=410, detail="Moved to /api/v1/cando/topics")
@router.post("/lessons/generate-exercises")
async def generate_exercises(
    can_do_id: str = Query(..., description="CanDoDescriptor ID"),
    n: int = Query(3, ge=1, le=20),
    modes: Optional[str] = Query(None, description="Comma-separated modes (e.g. writing,dialog)"),
    phase: Optional[str] = Query(None, description="Phase key (lexicon_and_patterns|guided_dialogue|open_dialogue)"),
) -> Dict[str, Any]:
    """Compatibility endpoint: returns a minimal exercise bundle from compiled resources.

    This satisfies initial MCP scenario expectations until full GenerateExercises is implemented.
    """
    try:
        modes_list = [m.strip() for m in modes.split(",")] if modes else None
        if phase:
            bundle = lexical_lessons.generate_exercises_phased(can_do_id=can_do_id, phase=phase, n=n)
        else:
            bundle = lexical_lessons.generate_exercises_minimal(can_do_id=can_do_id, n=n, modes=modes_list)
        return bundle
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Exercises not found for can_do_id")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class PhaseState(BaseModel):
    phase: str
    completed_count: int = 0
    score: float | None = None


@router.post("/lessons/phase-gate")
async def phase_gate(state: PhaseState) -> Dict[str, Any]:
    """Compute next phase based on completion or score mode (feature-flagged)."""
    try:
        result = lexical_lessons.compute_next_phase(
            current_phase=state.phase,
            completed_count=state.completed_count,
            score=state.score,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/lessons/sample-dialog")
async def get_sample_dialog(can_do_id: str = Query(...)) -> Dict[str, Any]:
    """Return compiled SampleDialog JSON (conventional expressions)."""
    try:
        data = lexical_lessons._load_compiled_sample_dialog(can_do_id)
        return {"can_do_id": can_do_id, **data}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Sample dialog not found for can_do_id")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/lessons/stages")
async def get_stages(can_do_id: str = Query(...)) -> Dict[str, Any]:
    """Return compiled StagedExercises (phased integration)."""
    try:
        data = lexical_lessons._load_compiled_stages(can_do_id)
        return {"can_do_id": can_do_id, **data}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Stages not found for can_do_id")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/lessons/package")
async def get_lesson_package(
    can_do_id: str = Query(..., description="CanDoDescriptor ID"),
    session: AsyncSession = Depends(get_neo4j_session),
) -> Dict[str, Any]:
    """Return a combined lesson package for the given CanDo (compiled + pragmatics)."""
    try:
        pkg = await lexical_lessons.assemble_package(can_do_id=can_do_id, session=session)
        return pkg
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Compiled lesson assets not found for can_do_id")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/lessons/version")
async def get_lesson_version(
    can_do_id: str = Query(...),
    version: int = Query(1, ge=1),
    db: PgSession = Depends(get_postgresql_session),
) -> Dict[str, Any]:
    """Return stored lesson version JSONs from Postgres (lesson_plan, exercises, manifest, dialogs)."""
    try:
        # Get lesson id
        res = await db.execute(text("SELECT id FROM lessons WHERE can_do_id = :can LIMIT 1"), {"can": can_do_id})
        row = res.first()
        if not row:
            raise HTTPException(status_code=404, detail="Lesson not found")
        lesson_id = int(row[0])
        # Get version
        res2 = await db.execute(
            text(
                "SELECT lesson_plan, exercises, manifest, dialogs FROM lesson_versions WHERE lesson_id = :lid AND version = :ver LIMIT 1"
            ),
            {"lid": lesson_id, "ver": version},
        )
        row2 = res2.first()
        if not row2:
            raise HTTPException(status_code=404, detail="Lesson version not found")
        # row2 columns are already JSON from PG async driver; convert to dicts
        lesson_plan, exercises, manifest, dialogs = row2
        return {
            "can_do_id": can_do_id,
            "version": version,
            "lesson_plan": lesson_plan,
            "exercises": exercises,
            "manifest": manifest,
            "dialogs": dialogs,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cando/list", include_in_schema=False)
async def list_cando(*args, **kwargs):
    raise HTTPException(status_code=410, detail="Moved to /api/v1/cando/list")


@router.get("/cando/count", include_in_schema=False)
async def count_cando(*args, **kwargs):
    raise HTTPException(status_code=410, detail="Moved to /api/v1/cando/count")


class GradeRequest(BaseModel):
    exercise: Dict[str, Any]
    answer: str


@router.post("/lessons/grade")
async def grade_response(payload: GradeRequest) -> Dict[str, Any]:
    """Grade an exercise response using the heuristic MVP grader."""
    try:
        return grading_service.grade_response(exercise=payload.exercise, answer=payload.answer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class GradeStoreRequest(BaseModel):
    user_id: str
    can_do_id: str
    exercise: Dict[str, Any]
    answer: str


@router.post("/lessons/grade-store")
async def grade_and_store(
    payload: GradeStoreRequest,
    pg: PgSession = Depends(get_postgresql_session),
    session: AsyncSession = Depends(get_neo4j_session),
) -> Dict[str, Any]:
    """Grade an exercise, persist attempt to Postgres, and update mastery in Neo4j."""
    try:
        # 1) Grade
        report = grading_service.grade_response(exercise=payload.exercise, answer=payload.answer)
        score = float(report.get("score", 0.0)) if report else 0.0

        # 2) Ensure attempts table exists and insert
        await pg.execute(
            text(
                "CREATE TABLE IF NOT EXISTS lesson_attempts (\n"
                "  id BIGSERIAL PRIMARY KEY,\n"
                "  user_id TEXT NOT NULL,\n"
                "  can_do_id TEXT NOT NULL,\n"
                "  exercise_id TEXT,\n"
                "  exercise_type TEXT,\n"
                "  score DOUBLE PRECISION,\n"
                "  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()\n"
                ")"
            )
        )
        await pg.execute(
            text(
                "INSERT INTO lesson_attempts (user_id, can_do_id, exercise_id, exercise_type, score) "
                "VALUES (:u, :c, :eid, :typ, :s)"
            ),
            {
                "u": payload.user_id,
                "c": payload.can_do_id,
                "eid": str(payload.exercise.get("id", "")),
                "typ": str(payload.exercise.get("type", "")),
                "s": score,
            },
        )

        # 3) Update mastery in Neo4j
        mastery = await mastery_service.upsert_mastery(
            session=session, user_id=payload.user_id, can_do_id=payload.can_do_id, score=score
        )

        return {"grade": report, "mastery": mastery}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class MasteryUpdateRequest(BaseModel):
    user_id: str
    can_do_id: str
    score: float


@router.post("/lessons/update-mastery")
async def update_mastery(payload: MasteryUpdateRequest, session: AsyncSession = Depends(get_neo4j_session)) -> Dict[str, Any]:
    try:
        return await mastery_service.upsert_mastery(session=session, user_id=payload.user_id, can_do_id=payload.can_do_id, score=payload.score)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/lessons/recommend-next")
async def recommend_next(can_do_id: str, limit: int = Query(5, ge=1, le=10), session: AsyncSession = Depends(get_neo4j_session)) -> Dict[str, Any]:
    try:
        items = await mastery_service.recommend_next(session=session, can_do_id=can_do_id, limit=limit)
        return {"can_do_id": can_do_id, "recommendations": items}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class PersistLessonIn(BaseModel):
    can_do_id: str
    version: int = 1


@router.post("/lessons/persist")
async def persist_lesson(
    payload: PersistLessonIn,
    pg: PgSession = Depends(get_postgresql_session),
    neo: AsyncSession = Depends(get_neo4j_session),
) -> Dict[str, Any]:
    """Persist compiled lesson artifacts to Postgres and link Neo4j Lesson node.

    Returns {lesson_id, version, can_do_id}.
    """
    try:
        result = await lesson_persistence_service.persist(
            can_do_id=payload.can_do_id,
            version=payload.version,
            pg=pg,
            neo=neo,
        )
        return result
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Compiled lesson not found for can_do_id")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/lessons/pragmatics")
async def get_pragmatics(
    can_do_id: str = Query(..., description="CanDoDescriptor ID"),
    session: AsyncSession = Depends(get_neo4j_session),
) -> Dict[str, Any]:
    """Fetch pragmatic patterns for a CanDo (graph-first, compiled fallback)."""
    try:
        items = await pragmatics_service.get_pragmatics(session=session, can_do_id=can_do_id)
        # Ensure non-empty by including compiled fallback if graph has none
        if not items:
            # call the compiled loader directly
            compiled = pragmatics_service._load_compiled(can_do_id)
            items = compiled or []
        return {"can_do_id": can_do_id, "pragmatics": items}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/lessons/pragmatics/import")
async def import_pragmatics(
    can_do_id: str = Query(..., description="CanDoDescriptor ID"),
    session: AsyncSession = Depends(get_neo4j_session),
) -> Dict[str, Any]:
    """Import pragmatic patterns from compiled JSON into Neo4j and link."""
    try:
        n = await pragmatics_service.import_compiled_to_graph(session=session, can_do_id=can_do_id)
        return {"can_do_id": can_do_id, "imported": n}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def _fetch_center(session: AsyncSession, center: str, search_field: str = "kanji") -> Optional[Dict[str, Any]]:
    # Build query based on search field
    if search_field == "translation":
        where_clause = "toLower(t.translation) CONTAINS toLower($center)"
    elif search_field == "hiragana":
        where_clause = "coalesce(t.reading_hiragana, t.hiragana) = $center"
    elif search_field == "kanji":
        where_clause = "coalesce(t.standard_orthography, t.kanji) = $center"
    else:
        # Default to kanji search
        where_clause = "coalesce(t.standard_orthography, t.kanji) = $center"
    
    query = f"""
    MATCH (t:Word)
    WHERE {where_clause}
    OPTIONAL MATCH (t)-[:BELONGS_TO_DOMAIN]->(d:SemanticDomain)
    OPTIONAL MATCH (t)-[:HAS_POS]->(p:POSTag)
    RETURN coalesce(t.standard_orthography, t.kanji) AS kanji,
           coalesce(t.reading_hiragana, t.hiragana) AS hiragana,
           t.translation AS translation,
           t.difficulty_numeric AS level,
           head(collect(d.name)) AS domain,
           head(collect(p.primary_pos)) AS pos
    LIMIT 1
    """
    result = await session.run(query, center=center)
    rec = await result.single()
    return dict(rec) if rec else None


async def _fetch_center_by_translation(session: AsyncSession, translation: str) -> Optional[Dict[str, Any]]:
    # Try exact match first
    query = """
    MATCH (t:Word)
    WHERE t.translation = $translation
    OPTIONAL MATCH (t)-[:BELONGS_TO_DOMAIN]->(d:SemanticDomain)
    OPTIONAL MATCH (t)-[:HAS_POS]->(p:POSTag)
    RETURN coalesce(t.standard_orthography, t.kanji) AS kanji,
           coalesce(t.reading_hiragana, t.hiragana) AS hiragana,
           t.translation AS translation,
           t.difficulty_numeric AS level,
           head(collect(d.name)) AS domain,
           head(collect(p.primary_pos)) AS pos
    LIMIT 1
    """
    result = await session.run(query, translation=translation)
    rec = await result.single()
    if rec:
        return dict(rec)
    
    # If no exact match, try partial match (contains)
    query_partial = """
    MATCH (t:Word)
    WHERE t.translation CONTAINS $translation OR $translation CONTAINS t.translation
    OPTIONAL MATCH (t)-[:BELONGS_TO_DOMAIN]->(d:SemanticDomain)
    OPTIONAL MATCH (t)-[:HAS_POS]->(p:POSTag)
    RETURN coalesce(t.standard_orthography, t.kanji) AS kanji,
           coalesce(t.reading_hiragana, t.hiragana) AS hiragana,
           t.translation AS translation,
           t.difficulty_numeric AS level,
           head(collect(d.name)) AS domain,
           head(collect(p.primary_pos)) AS pos
    ORDER BY size(t.translation) ASC
    LIMIT 1
    """
    result_partial = await session.run(query_partial, translation=translation)
    rec_partial = await result_partial.single()
    return dict(rec_partial) if rec_partial else None


async def _fetch_neighbors(session: AsyncSession, kanji: str, limit: int) -> Dict[str, Any]:
    # Depth-1 neighbors and edges around center word
    query = """
    MATCH (t:Word)
    WHERE coalesce(t.standard_orthography, t.kanji) = $kanji
    OPTIONAL MATCH (t)-[r:SYNONYM_OF]-(n:Word)
    OPTIONAL MATCH (n)-[:BELONGS_TO_DOMAIN]->(d:SemanticDomain)
    OPTIONAL MATCH (n)-[:HAS_POS]->(p:POSTag)
    WITH t, r, n,
         head(collect(d.name)) AS domain,
         head(collect(p.primary_pos)) AS pos
    ORDER BY coalesce(r.synonym_strength, r.weight, 0.0) DESC
    WITH t, r, n, domain, pos
    WHERE n IS NOT NULL
    WITH t,
    collect({
        id: coalesce(n.standard_orthography, n.kanji),
        name: coalesce(n.standard_orthography, n.kanji, n.reading_hiragana, n.hiragana),
        hiragana: coalesce(n.reading_hiragana, n.hiragana),
        translation: n.translation,
        level: n.difficulty_numeric,
        domain: domain,
        pos: pos
    })[0..$limit] AS neighbors,
    collect({
        source: coalesce(t.standard_orthography, t.kanji),
        target: coalesce(n.standard_orthography, n.kanji),
        weight: coalesce(r.synonym_strength, r.weight, 1.0)
    })[0..$limit] AS edges
    RETURN neighbors, edges
    """
    result = await session.run(query, kanji=kanji, limit=limit)
    rec = await result.single()
    if not rec:
        return {"neighbors": [], "edges": []}
    return {"neighbors": rec["neighbors"], "edges": rec["edges"]}


async def _fetch_ego_graph(
    session: AsyncSession,
    kanji: str,
    depth: int = 1,
    limit1: int = 40,
    limit2: int = 100,
) -> Dict[str, Any]:
    """Build an ego graph around a center word up to the requested depth.

    Depth 1:
      - Nodes: direct neighbors of center
      - Edges: all SYNONYM_OF edges among {center ∪ neighbors}

    Depth 2:
      - Nodes: neighbors of neighbors (excluding center and duplicates)
      - Edges: all SYNONYM_OF edges among {center ∪ depth1 ∪ depth2}
    """
    query = """
    MATCH (t:Word)
    WHERE coalesce(t.standard_orthography, t.kanji) = $kanji
    // Depth 1 neighbors
    OPTIONAL MATCH (t)-[:SYNONYM_OF]-(n1:Word)
    WITH t, [n IN collect(DISTINCT n1) WHERE n IS NOT NULL][0..$limit1] AS n1s
    // Depth 2 neighbors (if requested)
    WITH t, n1s, $depth AS depth, $limit2 AS limit2
    CALL {
      WITH t, n1s, depth, limit2
      CALL {
        WITH n1s
        UNWIND n1s AS n1
        OPTIONAL MATCH (n1)-[:SYNONYM_OF]-(n2:Word)
        RETURN collect(DISTINCT n2) AS n2s_all
      }
      WITH t, n1s, n2s_all, depth, limit2
      WITH t, n1s, [n IN n2s_all WHERE n IS NOT NULL AND NOT n IN n1s AND n <> t][0..limit2] AS n2s, depth
      RETURN CASE WHEN depth > 1 THEN n2s ELSE [] END AS n2s
    }
    WITH t, n1s, n2s
    WITH t, n1s, n2s, [t] + n1s + n2s AS egoNodes
    WITH egoNodes,
         [n IN egoNodes | coalesce(n.standard_orthography, n.kanji)] AS egoIds,
         [n IN egoNodes |
            {
              id: coalesce(n.standard_orthography, n.kanji),
              name: coalesce(n.standard_orthography, n.kanji, n.reading_hiragana, n.hiragana),
              hiragana: coalesce(n.reading_hiragana, n.hiragana),
              translation: n.translation,
              level: n.difficulty_numeric,
              domain: head([(n)-[:BELONGS_TO_DOMAIN]->(d:SemanticDomain) | d.name]),
              pos: head([(n)-[:HAS_POS]->(p:POSTag) | p.primary_pos])
            }
         ] AS nodeMaps
    MATCH (a:Word)-[r:SYNONYM_OF]-(b:Word)
    WHERE coalesce(a.standard_orthography, a.kanji) IN egoIds
      AND coalesce(b.standard_orthography, b.kanji) IN egoIds
      AND a <> b
    WITH nodeMaps AS nodes,
         collect(DISTINCT {
           source: coalesce(a.standard_orthography, a.kanji),
           target: coalesce(b.standard_orthography, b.kanji),
           weight: coalesce(r.synonym_strength, r.weight, 1.0)
         }) AS edges
    RETURN nodes, edges
    """
    result = await session.run(
        query,
        kanji=kanji,
        depth=depth,
        limit1=limit1,
        limit2=limit2,
    )
    rec = await result.single()
    if not rec:
        return {"nodes": [], "edges": []}
    return {"nodes": rec["nodes"], "edges": rec["edges"]}


def _sanitize_graph_response(nodes: List[Dict[str, Any]], links: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """Ensure nodes have non-empty ids and links reference existing nodes.

    This prevents client-side force-graph errors when a link's source/target
    cannot be resolved to a valid node (would become null and cause crashes).
    """
    # Deduplicate nodes by id and drop empties
    seen: set[str] = set()
    clean_nodes: List[Dict[str, Any]] = []
    for n in nodes:
        node_id = str(n.get("id", "")).strip()
        if not node_id or node_id in seen:
            continue
        seen.add(node_id)
        clean_nodes.append(n)

    id_set = seen

    def is_valid_link(l: Dict[str, Any]) -> bool:
        src = str(l.get("source", "")).strip()
        tgt = str(l.get("target", "")).strip()
        if not src or not tgt:
            return False
        if src == tgt:
            return False
        return (src in id_set) and (tgt in id_set)

    clean_links: List[Dict[str, Any]] = []
    for l in links:
        if is_valid_link(l):
            # coerce numeric weight if present
            w = l.get("weight")
            if isinstance(w, (int, float)):
                pass
            else:
                try:
                    l["weight"] = float(w) if w is not None else 1.0
                except Exception:
                    l["weight"] = 1.0
            clean_links.append(l)

    return {"nodes": clean_nodes, "links": clean_links}


@router.get("/node/{word}")
async def get_node_details(
    word: str,
    session: AsyncSession = Depends(get_neo4j_session),
) -> Dict[str, Any]:
    """
    Get detailed information about a specific word node.
    
    Returns comprehensive node information including:
    - Basic word data (kanji, hiragana, translation, POS, level)
    - Neighbors with relationship details (synonym strength, relation type)
    - Connection statistics
    - Domain and etymology information
    """
    try:
        # Get center node details (try multiple fields for robustness).
        center_node = await _fetch_center(session, word, "kanji")
        if not center_node:
            center_node = await _fetch_center(session, word, "hiragana")
        if not center_node:
            center_node = await _fetch_center_by_translation(session, word)
        if not center_node:
            raise HTTPException(status_code=404, detail="Word not found")

        # Get detailed neighbor information with relationship data.
        #
        # Reason: OPTIONAL MATCH can produce a single row with n=NULL; we must
        # ensure we don't return a neighbor object full of nulls.
        query = """
        MATCH (t:Word)
        WHERE coalesce(t.standard_orthography, t.kanji) = $kanji
        OPTIONAL MATCH (t)-[r:SYNONYM_OF]-(n:Word)
        OPTIONAL MATCH (n)-[:BELONGS_TO_DOMAIN]->(d:SemanticDomain)
        OPTIONAL MATCH (n)-[:HAS_POS]->(p:POSTag)
        WITH t, r, n,
             head(collect(d.name)) AS domain,
             head(collect(p.primary_pos)) AS pos
        ORDER BY coalesce(r.synonym_strength, r.weight, 0.0) DESC
        WITH t,
             collect(
               CASE
                 WHEN n IS NULL THEN NULL
                 ELSE {
                   kanji: coalesce(n.standard_orthography, n.kanji),
                   hiragana: coalesce(n.reading_hiragana, n.hiragana),
                   translation: n.translation,
                   level: n.difficulty_numeric,
                   pos: pos,
                   domain: domain,
                   synonym_strength: coalesce(r.synonym_strength, r.weight, 1.0),
                   relation_type: coalesce(r.relation_type, 'synonym'),
                   mutual_sense: r.mutual_sense
                 }
               END
             ) AS raw_neighbors
        RETURN coalesce(t.standard_orthography, t.kanji) AS center_kanji,
               coalesce(t.reading_hiragana, t.hiragana) AS center_hiragana,
               t.translation AS center_translation,
               t.difficulty_numeric AS center_level,
               coalesce(t.pos_primary_norm, t.pos1, t.pos_primary) AS center_pos,
               t.etymology AS center_etymology,
               [x IN raw_neighbors WHERE x IS NOT NULL] AS neighbors
        """

        result = await session.run(query, kanji=center_node["kanji"], timeout=10.0)
        rec = await result.single()

        # Get connection count
        count_query = """
        MATCH (t:Word)
        WHERE coalesce(t.standard_orthography, t.kanji) = $kanji
        MATCH (t)-[r:SYNONYM_OF]-()
        RETURN count(r) AS connection_count
        """
        count_result = await session.run(count_query, kanji=center_node["kanji"], timeout=10.0)
        count_rec = await count_result.single()
        connection_count = count_rec["connection_count"] if count_rec else 0

        if not rec:
            return {
                "node": {
                    "kanji": center_node.get("kanji", ""),
                    "hiragana": center_node.get("hiragana", ""),
                    "translation": center_node.get("translation", ""),
                    "level": center_node.get("level"),
                    "pos": center_node.get("pos"),
                    "etymology": "",
                    "connections": connection_count,
                },
                "neighbors": [],
                "total_connections": connection_count,
            }

        return {
            "node": {
                "kanji": rec["center_kanji"],
                "hiragana": rec["center_hiragana"],
                "translation": rec["center_translation"],
                "level": rec["center_level"],
                "pos": rec["center_pos"],
                "etymology": rec["center_etymology"],
                "connections": connection_count,
            },
            "neighbors": rec["neighbors"],
            "total_connections": connection_count,
        }
    except HTTPException:
        raise
    except (ServiceUnavailable, SessionExpired) as e:
        # Reason: temporary Neo4j availability issue; allow client to retry.
        raise _neo4j_unavailable_http(e)
    except Neo4jError as e:
        # Reason: Neo4j may return transient errors under load; treat as retryable.
        raise _neo4j_unavailable_http(e)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/graph")
async def get_lexical_graph(
    center: str = Query(..., description="Center word to search for"),
    searchField: str = Query("kanji", description="Search field: kanji, hiragana, or translation"),
    depth: int = Query(1, ge=1, le=3, description="Graph depth"),
    session: AsyncSession = Depends(get_neo4j_session),
) -> Dict[str, Any]:
    """
    Fetch a subgraph from the lexical graph centered on a specific node.
    """
    try:
        # Gracefully handle empty center
        if not center or center.strip() == "":
            return {"nodes": [], "links": [], "center": None}

        # Get center node
        # For translation searches, prefer exact match first, then partial
        if searchField == "translation":
            center_node = await _fetch_center_by_translation(session, center)
            if not center_node:
                center_node = await _fetch_center(session, center, searchField)
        else:
            center_node = await _fetch_center(session, center, searchField)
        # Graceful fallbacks if exact match not found for requested field
        if not center_node:
            # Try kanji form
            if searchField != "kanji":
                center_node = await _fetch_center(session, center, "kanji")
        if not center_node:
            # Try hiragana form
            if searchField != "hiragana":
                center_node = await _fetch_center(session, center, "hiragana")
        if not center_node and searchField != "translation":
            # As a last resort, try translation-based lookup (exact then contains)
            center_node = await _fetch_center_by_translation(session, center)
        if not center_node:
            raise HTTPException(status_code=404, detail="Center node not found")
        
        # Build ego graph up to requested depth
        ego = await _fetch_ego_graph(session, center_node["kanji"], depth=depth)

        # Build response - ensure all nodes have an 'id' field and include center
        nodes = []
        center_node_with_id = {**center_node, "id": center_node["kanji"]}
        nodes.append(center_node_with_id)
        for neighbor in ego["nodes"]:
            neighbor_with_id = {**neighbor, "id": neighbor.get("id", neighbor.get("kanji", ""))}
            if neighbor_with_id["id"] != center_node_with_id["id"]:
                nodes.append(neighbor_with_id)

        links = ego["edges"]

        # Sanitize before returning
        sanitized = _sanitize_graph_response(nodes, links)
        return {
            "nodes": sanitized["nodes"],
            "links": sanitized["links"],
            "center": {"id": center_node["kanji"]}
        }
    except HTTPException:
        raise
    except (ServiceUnavailable, SessionExpired) as e:
        raise _neo4j_unavailable_http(e)
    except Neo4jError as e:
        raise _neo4j_unavailable_http(e)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/lessons/seed")
async def seed_lexical_words(
    level: int = Query(1, ge=1, le=6),
    count: int = Query(12, ge=1, le=50),
    session: AsyncSession = Depends(get_neo4j_session),
) -> Dict[str, Any]:
    items = await lexical_lessons.seed_words_by_level(session, level, count)
    return {"level": level, "items": items}


@router.post("/lessons/generate")
async def generate_lexical_lesson(
    word: str = Query(..., description="Target word kanji/hiragana/lemma"),
    level: int = Query(1, ge=1, le=6),
    provider: str = Query("openai", pattern="^(openai|gemini)$"),
    model: str = Query("gpt-4o-mini"),
    analyze_readability: bool = Query(True),
    session: AsyncSession = Depends(get_neo4j_session),
) -> Dict[str, Any]:
    try:
        result = await lexical_lessons.generate_exercise(
            session=session, word_kanji=word, level=level, provider=provider, model=model, analyze_readability=analyze_readability
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/readability")
async def analyze_readability(text: str = Query(..., description="Japanese text to analyze")) -> Dict[str, Any]:
    result = readability_service.analyze(text)
    return result


class LessonAttemptIn(BaseModel):
    word: str
    level: int
    provider: Optional[str] = None
    model: Optional[str] = None
    readability_score: Optional[float] = None
    readability_level: Optional[str] = None
    content_len: Optional[int] = None


@router.post("/lessons/attempt")
async def record_lexical_lesson_attempt(
    payload: LessonAttemptIn,
    db: PgSession = Depends(get_postgresql_session),
    current_user: User = Depends(get_current_user),
):
    """Record a lexical lesson attempt as a conversation session/message for analytics.

    Creates (or reuses) an active 'lesson' session and stores a message summarizing the attempt.
    """
    # Reuse an active lesson session if present
    q = (
        select(ConversationSession)
        .where(
            ConversationSession.user_id == current_user.id,
            ConversationSession.session_type == "lesson",
            ConversationSession.status == "active",
        )
        .limit(1)
    )
    sess_row = (await db.execute(q)).scalar_one_or_none()
    now = datetime.utcnow()
    if not sess_row:
        sess_row = ConversationSession(
            user_id=current_user.id,
            title=f"Lexical lessons ({now.date().isoformat()})",
            language_code="ja",
            session_type="lesson",
            status="active",
            ai_provider=payload.provider or "openai",
            ai_model=payload.model or "gpt-4o-mini",
            created_at=now,
            updated_at=now,
            total_messages=0,
            user_messages=0,
            ai_messages=0,
        )
        db.add(sess_row)
        await db.flush()

    # Store an attempt as a message
    content = (
        f"lexical_lesson_attempt word={payload.word} level={payload.level} "
        f"readability_score={payload.readability_score} readability_level={payload.readability_level} "
        f"content_len={payload.content_len}"
    )
    msg = ConversationMessage(
        session_id=sess_row.id,
        role="user",
        content=content,
        content_type="lesson_attempt",
        created_at=now,
        message_order=(sess_row.total_messages or 0) + 1,
    )
    db.add(msg)
    # update session counters
    sess_row.total_messages = (sess_row.total_messages or 0) + 1
    sess_row.user_messages = (sess_row.user_messages or 0) + 1
    sess_row.updated_at = now
    await db.flush()
    return {"status": "ok", "session_id": str(sess_row.id), "message_id": str(msg.id)}
