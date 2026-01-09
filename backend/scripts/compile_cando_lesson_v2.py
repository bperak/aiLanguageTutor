# backend/scripts/compile_cando_lesson_v2.py
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import argparse
import json
import os
from typing import Any, Dict, Optional
import re

from dotenv import load_dotenv
from neo4j import GraphDatabase

# Reuse your new pipeline exactly as defined
from canDo_creation_new import (
    gen_domain_plan,
    gen_objective_card,
    gen_words_card,
    gen_grammar_card,
    gen_dialogue_card,
    gen_guided_dialogue_card,
    gen_exercises_card,
    gen_culture_card,
    gen_drills_card,
    assemble_lesson,
)


def _project_root() -> Path:
    # backend/scripts → backend → repo root
    return Path(__file__).resolve().parents[2]


def _normalize_uri(uri: str) -> str:
    if uri.startswith("neo4j://neo4j:"):
        return uri.replace("neo4j://neo4j:", "bolt://localhost:")
    if uri.startswith("neo4j://"):
        return uri.replace("neo4j://", "bolt://")
    return uri


def _load_env() -> None:
    # Load .env from repo root
    load_dotenv(_project_root() / ".env")


def _fetch_cando_meta(can_do_id: str) -> Dict[str, Any]:
    """
    Minimal Neo4j pull to feed the pipeline's CanDoDescriptor inputs.
    Requires NEO4J_URI, NEO4J_USER/NEO4J_USERNAME, NEO4J_PASSWORD in .env.
    """
    uri = _normalize_uri(os.getenv("NEO4J_URI", "bolt://localhost:7687"))
    user = os.getenv("NEO4J_USER") or os.getenv("NEO4J_USERNAME", "neo4j")
    pwd = os.getenv("NEO4J_PASSWORD", "neo4j")

    q = """
    MATCH (c:CanDoDescriptor {uid: $id})
    RETURN c.uid AS uid,
           toString(c.level) AS level,
           toString(c.primaryTopic) AS primaryTopic,
           coalesce(toString(c.primaryTopicEn), toString(c.primaryTopic)) AS primaryTopicEn,
           toString(c.skillDomain) AS skillDomain,
           toString(c.type) AS type,
           toString(c.descriptionEn) AS descriptionEn,
           toString(c.descriptionJa) AS descriptionJa,
           coalesce(toString(c.source), 'JFまるごと') AS source
    LIMIT 1
    """

    driver = GraphDatabase.driver(uri, auth=(user, pwd))
    try:
        with driver.session() as s:
            rec = s.run(q, id=can_do_id).single()
            if not rec:
                raise RuntimeError(f"CanDo not found: {can_do_id}")
            return dict(rec)
    finally:
        driver.close()


def _make_llm_call(provider: str, model: str, timeout: int = 120):
    """
    Sync LLM function compatible with canDo_creation_new.py validate_or_repair().
    OpenAI-only (no Google). Reads OPENAI_API_KEY from environment.
    """
    provider = (provider or "openai").lower()
    if provider != "openai":
        raise ValueError("Only provider='openai' is supported in this script (no Google).")

    # Ensure key is present (set in .env; this script loads it)
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("Missing OPENAI_API_KEY. Please set it in your .env.")

    from openai import OpenAI  # local import to keep deps minimal
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


def _ensure_out_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _sanitize_filename_component(component: str) -> str:
    """Make a safe filename component for Windows (no ADS/colon, no reserved chars)."""
    # Replace reserved characters <>:"/\|?* with underscore, collapse repeats
    sanitized = re.sub(r'[<>:"/\\|?*]+', '_', component)
    # Strip trailing spaces/dots which are invalid on Windows
    sanitized = sanitized.strip().rstrip('.')
    if not sanitized:
        sanitized = "item"
    return sanitized


def _pick_cando_by_level(level: str, offset: int = 0) -> str:
    uri = _normalize_uri(os.getenv("NEO4J_URI", "bolt://localhost:7687"))
    user = os.getenv("NEO4J_USER") or os.getenv("NEO4J_USERNAME", "neo4j")
    pwd = os.getenv("NEO4J_PASSWORD", "neo4j")
    q = (
        "MATCH (c:CanDoDescriptor) "
        "WHERE toString(c.level) = $lvl "
        "RETURN c.uid AS uid ORDER BY uid ASC SKIP $skip LIMIT 1"
    )
    drv = GraphDatabase.driver(uri, auth=(user, pwd))
    try:
        with drv.session() as s:
            rec = s.run(q, lvl=level, skip=int(offset)).single()
            if not rec or not rec.get("uid"):
                raise RuntimeError(f"No CanDoDescriptor found for level={level} (offset={offset})")
            return str(rec["uid"])
    finally:
        drv.close()


def compile_and_save(
    *,
    can_do_id: Optional[str],
    metalanguage: str = "en",
    provider: str = "openai",
    model: str = "gpt-4o",
    out_dir: Path,
    out_filename: Optional[str] = None,
    timeout: int = 120,
    pick_level: Optional[str] = None,
    pick_offset: int = 0,
) -> Path:
    _load_env()
    if not can_do_id:
        if not pick_level:
            raise ValueError("Provide --can-do-id or --pick-level.")
        can_do_id = _pick_cando_by_level(pick_level, offset=pick_offset)
    meta = _fetch_cando_meta(can_do_id)

    cando_input = {
        "uid": meta["uid"],
        "level": meta["level"],
        "primaryTopic": meta["primaryTopic"],
        "primaryTopicEn": meta["primaryTopicEn"],
        "skillDomain": meta["skillDomain"],
        "type": meta["type"],
        "descriptionEn": meta.get("descriptionEn", ""),
        "descriptionJa": meta.get("descriptionJa", ""),
        "source": meta.get("source", "graph"),
    }

    llm_call = _make_llm_call(provider=provider, model=model, timeout=timeout)

    # 1) Plan
    plan = gen_domain_plan(llm_call, cando_input, metalanguage)

    # 2) Cards
    obj = gen_objective_card(llm_call, metalanguage, {
        "uid": cando_input["uid"],
        "level": cando_input["level"],
        "primaryTopic_ja": cando_input["primaryTopic"],
        "primaryTopic_en": cando_input["primaryTopicEn"],
        "skillDomain_ja": cando_input["skillDomain"],
        "type_ja": cando_input["type"],
        "description": {"en": cando_input["descriptionEn"], "ja": cando_input["descriptionJa"]},
        "source": cando_input["source"],
    }, plan)

    words = gen_words_card(llm_call, metalanguage, plan)
    grammar = gen_grammar_card(llm_call, metalanguage, plan)
    dialog = gen_dialogue_card(llm_call, metalanguage, plan)
    guided = gen_guided_dialogue_card(llm_call, metalanguage, plan)
    exercises = gen_exercises_card(llm_call, metalanguage, plan)
    culture = gen_culture_card(llm_call, metalanguage, plan)
    drills = gen_drills_card(llm_call, metalanguage, plan)

    # 3) Assemble
    lesson = assemble_lesson(
        metalanguage,
        cando_input,
        plan,
        obj,
        words,
        grammar,
        dialog,
        guided,
        exercises,
        culture,
        drills,
        lesson_id=f"canDo_{can_do_id}_v1",
    )

    # 4) Save
    _ensure_out_dir(out_dir)
    safe_id = _sanitize_filename_component(can_do_id)
    filename = out_filename or f"canDo_{safe_id}_v1.json"
    out_path = out_dir / filename
    # Pydantic v2: use model_dump() + json.dumps for ensure_ascii/indent
    out_path.write_text(json.dumps(lesson.model_dump(), ensure_ascii=False, indent=2), encoding="utf-8")
    return out_path


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Compile a CanDo lesson (v2 pipeline) to a JSON file.")
    p.add_argument("--can-do-id", required=False, default=None, help="CanDoDescriptor uid (e.g., JFまるごと:14)")
    p.add_argument("--pick-level", required=False, default=None, help="Pick first CanDo for level (e.g., A1)")
    p.add_argument("--pick-offset", required=False, default=0, type=int, help="Offset within level when picking (default 0)")
    p.add_argument("--metalanguage", default="en", help="UI metalanguage (en/hr/ja/de/fr/it/es)")
    p.add_argument("--provider", default="openai", help="AI provider (openai only)")
    p.add_argument("--model", default="gpt-4o", help="OpenAI model name")
    p.add_argument("--timeout", type=int, default=120, help="Per-call timeout seconds")
    p.add_argument("--out-dir", default=str(_project_root() / "generated" / "lessons_v2"), help="Output directory")
    p.add_argument("--out-filename", default=None, help="Optional output filename")
    return p.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    out_path = compile_and_save(
        can_do_id=args.can_do_id,
        metalanguage=args.metalanguage,
        provider="openai",  # force openai only
        model=args.model,
        timeout=args.timeout,
        out_dir=Path(args.out_dir),
        out_filename=args.out_filename,
        pick_level=args.pick_level,
        pick_offset=args.pick_offset,
    )
    print(f"[cando_v2] Saved: {out_path}")