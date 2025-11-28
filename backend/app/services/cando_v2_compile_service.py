from __future__ import annotations

import asyncio
import json
import os
import importlib.util
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, List
import logging

from neo4j import AsyncSession
from sqlalchemy.ext.asyncio import AsyncSession as PgSession
from sqlalchemy import text

from app.services.cando_image_service import ensure_image_paths_for_lesson
from app.services.cando_lesson_session_service import CanDoLessonSessionService


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


logger = logging.getLogger(__name__)


def _load_pipeline_module():
    """Dynamically load canDo_creation_new.py from backend/scripts to avoid duplication."""
    scripts_path = _project_root() / "scripts" / "canDo_creation_new.py"
    spec = importlib.util.spec_from_file_location("cando_pipeline_v2", scripts_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot_load_pipeline_module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[attr-defined]
    return module


def _make_llm_call_openai(model: str, timeout: int = 120):
    """Synchronous OpenAI chat completions adapter used inside server threadpool."""
    from openai import OpenAI

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY_missing")
    client = OpenAI(api_key=api_key)

    def llm_call(system: str, user: str) -> str:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.0,
        )
        return (resp.choices[0].message.content or "").strip()

    return llm_call


async def _fetch_cando_meta(neo: AsyncSession, can_do_id: str) -> Dict[str, Any]:
    q = (
        "MATCH (c:CanDoDescriptor {uid: $id})\n"
        "RETURN c.uid AS uid, toString(c.level) AS level, toString(c.primaryTopic) AS primaryTopic,\n"
        "coalesce(toString(c.primaryTopicEn), toString(c.primaryTopic)) AS primaryTopicEn,\n"
        "toString(c.skillDomain) AS skillDomain, toString(c.type) AS type,\n"
        "toString(c.descriptionEn) AS descriptionEn, toString(c.descriptionJa) AS descriptionJa,\n"
        "toString(c.titleEn) AS titleEn, toString(c.titleJa) AS titleJa,\n"
        "coalesce(toString(c.source), 'JFまるごと') AS source\n"
        "LIMIT 1"
    )
    result = await neo.run(q, id=can_do_id)
    rec = await result.single()
    if not rec:
        raise ValueError("cando_not_found")
    return dict(rec)


def _extract_dialogue_text(dialog: Any) -> str:
    """Extract all Japanese text from DialogueCard for entity extraction.
    
    Flattens dialogue setting and all turn texts into a single string.
    Uses std field from JPText if available, otherwise falls back to other fields.
    """
    lines: List[str] = []
    
    # Add setting if present
    if hasattr(dialog, 'setting') and dialog.setting:
        lines.append(str(dialog.setting))
    
    # Extract text from all turns
    if hasattr(dialog, 'turns') and dialog.turns:
        for turn in dialog.turns:
            if hasattr(turn, 'ja'):
                ja = turn.ja
                # Prefer std (standard form), fallback to other fields
                if hasattr(ja, 'std') and ja.std:
                    lines.append(str(ja.std))
                elif hasattr(ja, 'kanji') and ja.kanji:
                    lines.append(str(ja.kanji))
                elif hasattr(ja, 'furigana') and ja.furigana:
                    lines.append(str(ja.furigana))
    
    return "\n".join(lines)


def _extract_reading_text(reading: Any) -> str:
    """Extract all Japanese text from ReadingCard for entity extraction.
    
    Extracts text from reading.content and reading.title (JPText structure).
    Also includes comprehension questions for vocabulary/grammar extraction.
    """
    if not hasattr(reading, 'reading') or not reading.reading:
        return ""
    
    reading_section = reading.reading
    lines: List[str] = []
    
    # Add title if present
    if hasattr(reading_section, 'title') and reading_section.title:
        title = reading_section.title
        if hasattr(title, 'std') and title.std:
            lines.append(str(title.std))
        elif hasattr(title, 'kanji') and title.kanji:
            lines.append(str(title.kanji))
    
    # Add content text (main reading text - 200+ words)
    if hasattr(reading_section, 'content') and reading_section.content:
        content = reading_section.content
        if hasattr(content, 'std') and content.std:
            lines.append(str(content.std))
        elif hasattr(content, 'kanji') and content.kanji:
            lines.append(str(content.kanji))
    
    # Also extract from comprehension questions (they contain vocabulary/grammar)
    if hasattr(reading_section, 'comprehension') and reading_section.comprehension:
        for qa in reading_section.comprehension:
            if hasattr(qa, 'q') and qa.q:
                q = qa.q
                if hasattr(q, 'std') and q.std:
                    lines.append(str(q.std))
            if hasattr(qa, 'a') and qa.a:
                a = qa.a
                if hasattr(a, 'std') and a.std:
                    lines.append(str(a.std))
    
    return "\n".join(lines)


async def _link_dialogue_entities(
    neo: AsyncSession, 
    can_do_id: str, 
    resolved_words: List[Dict[str, Any]], 
    resolved_grammar: List[Dict[str, Any]],
    lesson_id: Optional[int] = None
) -> None:
    """Link extracted words and grammar patterns from dialogue to CanDo in Neo4j."""
    try:
        # Extract element IDs for words
        word_element_ids = []
        for w in resolved_words:
            eid = w.get("elementId")
            if eid:
                word_element_ids.append(str(eid))
        
        # Extract pattern IDs for grammar
        grammar_ids = []
        for g in resolved_grammar:
            gid = g.get("id")
            if gid:
                grammar_ids.append(str(gid))
        
        # Link words to CanDo
        if word_element_ids:
            try:
                q = (
                    "MATCH (c:CanDoDescriptor {uid: $can_do_id})\n"
                    "MATCH (w:Word)\n"
                    "WHERE elementId(w) IN $word_element_ids\n"
                    "MERGE (c)-[r:USES_WORD]->(w)\n"
                    "RETURN count(r) AS linked"
                )
                result = await neo.run(q, can_do_id=can_do_id, word_element_ids=word_element_ids)
                rec = await result.single()
                if rec:
                    logger.info(
                        "Linked %s words to CanDo %s", 
                        rec.get("linked", 0), 
                        can_do_id
                    )
            except Exception as e:
                logger.warning("Failed to link words to CanDo: %s", e)
        
        # Link grammar patterns to CanDo
        if grammar_ids:
            try:
                q = (
                    "MATCH (c:CanDoDescriptor {uid: $can_do_id})\n"
                    "MATCH (g:GrammarPattern)\n"
                    "WHERE g.id IN $grammar_ids\n"
                    "MERGE (c)-[r:USES_PATTERN]->(g)\n"
                    "RETURN count(r) AS linked"
                )
                result = await neo.run(q, can_do_id=can_do_id, grammar_ids=grammar_ids)
                rec = await result.single()
                if rec:
                    logger.info(
                        "Linked %s grammar patterns to CanDo %s", 
                        rec.get("linked", 0), 
                        can_do_id
                    )
            except Exception as e:
                logger.warning("Failed to link grammar patterns to CanDo: %s", e)
                
    except Exception as e:
        logger.warning("Failed to link dialogue entities: %s", e)


async def _enrich_grammar_neo4j_ids(neo: AsyncSession, lesson: Dict[str, Any]) -> None:
    """Post-process: set neo4j_id on grammar pattern items when exact pattern matches. Do not alter text."""
    try:
        patterns: List[Dict[str, Any]] = (
            (lesson.get("lesson") or {}).get("cards", {}).get("grammar_patterns", {}).get("patterns", [])
        )
        if not isinstance(patterns, list):
            return
        for item in patterns:
            try:
                std = (((item or {}).get("form") or {}).get("ja") or {}).get("std")
                if not std or not isinstance(std, str):
                    continue
                q = (
                    "MATCH (p:GrammarPattern) WHERE toString(p.pattern) = $p "
                    "RETURN p.id AS id LIMIT 2"
                )
                result = [dict(r) async for r in (await neo.run(q, p=std))]
                if len(result) == 1 and result[0].get("id"):
                    item["neo4j_id"] = result[0]["id"]
                # else: leave unmatched or ambiguous per user decision
            except Exception:
                continue
    except Exception:
        pass


async def compile_lessonroot(
    *,
    neo: AsyncSession,
    pg: PgSession,
    can_do_id: str,
    metalanguage: str = "en",
    model: str = "gpt-4.1",
    timeout: int = 120,
) -> Dict[str, Any]:
    pipeline = _load_pipeline_module()
    meta = await _fetch_cando_meta(neo, can_do_id)
    cando_input = {
        "uid": meta["uid"],
        "level": meta["level"],
        "primaryTopic": meta["primaryTopic"],
        "primaryTopicEn": meta["primaryTopicEn"],
        "skillDomain": meta["skillDomain"],
        "type": meta["type"],
        "descriptionEn": meta.get("descriptionEn", ""),
        "descriptionJa": meta.get("descriptionJa", ""),
        "titleEn": meta.get("titleEn", ""),
        "titleJa": meta.get("titleJa", ""),
        "source": meta.get("source", "graph"),
    }

    llm_call = _make_llm_call_openai(model=model, timeout=timeout)

    # Sequence: Generate plan and objective first
    plan = pipeline.gen_domain_plan(llm_call, cando_input, metalanguage)
    obj = pipeline.gen_objective_card(
        llm_call,
        metalanguage,
        {
            "uid": cando_input["uid"],
            "level": cando_input["level"],
            "primaryTopic_ja": cando_input["primaryTopic"],
            "primaryTopic_en": cando_input["primaryTopicEn"],
            "skillDomain_ja": cando_input["skillDomain"],
            "type_ja": cando_input["type"],
            "description": {"en": cando_input["descriptionEn"], "ja": cando_input["descriptionJa"]},
            "source": cando_input["source"],
        },
        plan,
    )
    
    # Generate dialogue FIRST (before words/grammar)
    dialog = pipeline.gen_dialogue_card(llm_call, metalanguage, plan)
    
    # Generate reading card AFTER dialogue (focused on CanDo domain elaboration)
    reading = pipeline.gen_reading_card(llm_call, metalanguage, cando_input, plan, dialog)
    
    # Extract entities from BOTH dialogue AND reading (reading as primary source)
    session_service = CanDoLessonSessionService()
    dialogue_text = _extract_dialogue_text(dialog)
    reading_text = _extract_reading_text(reading)
    combined_text = "\n".join([reading_text, dialogue_text])  # Reading first (more content)
    
    # Safety check: if combined text is empty or too short, fall back to plan-based generation
    resolved_words: List[Dict[str, Any]] = []
    resolved_grammar: List[Dict[str, Any]] = []
    
    if combined_text and len(combined_text.strip()) > 10:
        # Extract words and grammar patterns from reading + dialogue (reading prioritized)
        extracted = await session_service._extract_entities_from_text(
            text_blob=combined_text, provider="openai"
        )
        
        # Resolve extracted entities to Neo4j
        resolved_words = await session_service._resolve_words(neo, extracted.get("words") or [])
        resolved_grammar = await session_service._resolve_grammar(neo, extracted.get("grammarPatterns") or [])
        
        # Fallback to deterministic methods if resolution sparse
        if len(resolved_words) < 8:
            logger.info("Entity resolution fallback: using deterministic word extraction")
            resolved_words = await session_service._deterministic_words(neo, combined_text)
        
        if len(resolved_grammar) < 4:
            logger.info("Entity resolution fallback: using deterministic grammar extraction")
            resolved_grammar = await session_service._deterministic_grammar(neo, combined_text)
    else:
        logger.warning("Dialogue text too short or empty, falling back to plan-based generation")
    
    # Generate words and grammar cards FROM extracted entities (or fallback to plan-based if no entities)
    if resolved_words or resolved_grammar:
        words = pipeline.gen_words_card_from_extracted(
            llm_call, metalanguage, plan, dialog, reading, resolved_words
        )
        grammar = pipeline.gen_grammar_card_from_extracted(
            llm_call, metalanguage, plan, dialog, reading, resolved_grammar
        )
    else:
        # Fallback to original plan-based generation if no entities extracted
        logger.info("No entities extracted from dialogue, using plan-based generation")
        words = pipeline.gen_words_card(llm_call, metalanguage, plan)
        grammar = pipeline.gen_grammar_card(llm_call, metalanguage, plan)
    guided = pipeline.gen_guided_dialogue_card(llm_call, metalanguage, plan)
    exercises = pipeline.gen_exercises_card(llm_call, metalanguage, plan)
    culture = pipeline.gen_culture_card(llm_call, metalanguage, plan)
    drills = pipeline.gen_drills_card(llm_call, metalanguage, plan)

    root = pipeline.assemble_lesson(
        metalanguage,
        cando_input,
        plan,
        obj,
        words,
        grammar,
        dialog,
        reading,
        guided,
        exercises,
        culture,
        drills,
        lesson_id=f"canDo_{can_do_id}_v1",
    )

    lesson_json = json.loads(root.model_dump_json())
    await _enrich_grammar_neo4j_ids(neo, lesson_json)
    
    # Link extracted entities in Neo4j (only if entities were extracted)
    if resolved_words or resolved_grammar:
        await _link_dialogue_entities(neo, can_do_id, resolved_words, resolved_grammar)

    images_generated = 0
    if os.getenv("GEMINI_API_KEY"):
        try:
            images_generated, _ = await asyncio.to_thread(
                ensure_image_paths_for_lesson,
                lesson_json,
                can_do_id=can_do_id,
            )
            if images_generated:
                logger.info(
                    "Generated %s lesson images for %s", images_generated, can_do_id
                )
        except Exception as exc:
            logger.warning("Image generation skipped for %s: %s", can_do_id, exc)

    # Persist in lessons/lesson_versions tables (JSONB as lesson_plan)
    # Upsert lesson
    result = await pg.execute(text("SELECT id FROM lessons WHERE can_do_id = :cid LIMIT 1"), {"cid": can_do_id})
    row = result.first()
    if row:
        lesson_id = int(row[0])
    else:
        ins = await pg.execute(text("INSERT INTO lessons (can_do_id, status) VALUES (:cid, 'draft') RETURNING id"), {"cid": can_do_id})
        lesson_id = int(ins.first()[0])
    # Next version
    ver_row = (await pg.execute(text("SELECT COALESCE(MAX(version),0) FROM lesson_versions WHERE lesson_id=:lid"), {"lid": lesson_id})).first()
    next_ver = int(ver_row[0]) + 1
    await pg.execute(
        text("INSERT INTO lesson_versions (lesson_id, version, lesson_plan) VALUES (:lid, :ver, :plan)"),
        {"lid": lesson_id, "ver": next_ver, "plan": json.dumps(lesson_json, ensure_ascii=False)},
    )
    await pg.commit()

    return {"lesson_id": lesson_id, "version": next_ver, "lesson": lesson_json}


