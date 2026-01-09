"""
Lexical Lessons Service

Generates lexical lessons by level and optionally uses AI to draft
exercise content around a target word with related vocabulary.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import json
from pathlib import Path
from app.core.config import settings
from app.services.pragmatics_service import pragmatics_service
import structlog
from neo4j import AsyncSession

from app.services.ai_chat_service import AIChatService
from app.services.readability_service import readability_service


logger = structlog.get_logger()


LEVEL_DESC = {
    1: "Beginner 1 - Basic vocabulary and simple sentence structures with full romaji support",
    2: "Beginner 2 - Elementary vocabulary with hiragana focus and partial romaji",
    3: "Intermediate 1 - Common everyday vocabulary with basic kanji, minimal romaji",
    4: "Intermediate 2 - Expanded vocabulary and more complex sentence patterns",
    5: "Advanced 1 - Sophisticated vocabulary and natural expressions",
    6: "Advanced 2 - Native-like vocabulary and cultural nuances",
}

PHASES: List[str] = [
    "lexicon_and_patterns",
    "guided_dialogue",
    "open_dialogue",
    "done",
]


class LexicalLessonsService:
    def __init__(self) -> None:
        self.ai = AIChatService()

    def _compiled_dir_for(self, can_do_id: str) -> Path:
        return Path(__file__).resolve().parents[2] / "resources" / "compiled" / "cando" / can_do_id.replace(":", "_")

    def _load_compiled_lesson(self, can_do_id: str) -> Dict[str, Any]:
        out_dir = self._compiled_dir_for(can_do_id)
        lp_path = out_dir / "lesson_plan.json"
        if not lp_path.exists():
            raise FileNotFoundError(f"Compiled lesson not found: {lp_path}")
        return json.loads(lp_path.read_text(encoding="utf-8"))

    def _load_compiled_exercises(self, can_do_id: str) -> Dict[str, Any]:
        """Load compiled exercises bundle from resources.

        Supports two formats:
        - { "exercises": [...] }
        - [ ... ] (list directly)
        """
        out_dir = self._compiled_dir_for(can_do_id)
        ex_path = out_dir / "exercises.json"
        if not ex_path.exists():
            raise FileNotFoundError(f"Compiled exercises not found: {ex_path}")
        data = json.loads(ex_path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and "exercises" in data:
            return {"exercises": data.get("exercises") or []}
        if isinstance(data, list):
            return {"exercises": data}
        # Fallback to empty list if unexpected shape
        return {"exercises": []}

    def _load_compiled_sample_dialog(self, can_do_id: str) -> Dict[str, Any]:
        out_dir = self._compiled_dir_for(can_do_id)
        path = out_dir / "sample_dialog.json"
        if not path.exists():
            raise FileNotFoundError(f"Compiled sample_dialog not found: {path}")
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {"dialog": data}

    def _load_compiled_stages(self, can_do_id: str) -> Dict[str, Any]:
        out_dir = self._compiled_dir_for(can_do_id)
        path = out_dir / "stages.json"
        if not path.exists():
            raise FileNotFoundError(f"Compiled stages not found: {path}")
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {"stages": data}

    def generate_exercises_phased(
        self,
        *,
        can_do_id: str,
        phase: str,
        n: int = 3,
    ) -> Dict[str, Any]:
        """Return exercises for a specific phase using compiled stages.json.

        Supports a few shapes of stages.json:
        - { "lexicon_and_patterns": [...], "guided_dialogue": [...], ... }
        - { "stages": { "lexicon_and_patterns": [...], ... } }
        - { "phases": { ... } }
        Falls back to minimal selection if phase not found.
        """
        stages = self._load_compiled_stages(can_do_id)
        candidates: List[Dict[str, Any]] = []

        # Normalize keys
        phase_l = (phase or "").strip().lower()
        search_maps: List[Dict[str, Any]] = []
        if isinstance(stages.get("stages"), dict):
            search_maps.append(stages["stages"]) 
        if isinstance(stages.get("phases"), dict):
            search_maps.append(stages["phases"]) 
        # Also try root-level
        search_maps.append(stages)

        for mp in search_maps:
            if not isinstance(mp, dict):
                continue
            # try direct match
            for k, v in mp.items():
                if not isinstance(k, str):
                    continue
                if k.strip().lower() == phase_l and isinstance(v, list):
                    candidates = [it for it in v if isinstance(it, dict)]
                    break
            if candidates:
                break

        if not candidates:
            # Fallback to minimal
            return self.generate_exercises_minimal(can_do_id=can_do_id, n=n)

        if n and isinstance(n, int) and n > 0:
            candidates = candidates[: n]

        return {"can_do_id": can_do_id, "phase": phase, "exercises": candidates}

    def _load_manifest(self, can_do_id: str) -> Dict[str, Any] | None:
        """Load manifest.json from frontend/public/images/ (or legacy images/ as fallback).
        
        NOTE: images/lessons/cando/ is legacy. All new images should be in frontend/public/images/.
        """
        repo_root = Path(__file__).resolve().parents[2]
        sanitized_id = can_do_id.replace(":", "_")
        
        # Try frontend/public/images/ first (where images are now generated)
        frontend_manifest = repo_root / "frontend" / "public" / "images" / "lessons" / "cando" / sanitized_id / "manifest.json"
        if frontend_manifest.exists():
            try:
                return json.loads(frontend_manifest.read_text(encoding="utf-8"))
            except Exception:
                pass
        
        # Fallback to legacy images/ directory (will be removed in the future)
        images_dir = repo_root / "images" / "lessons" / "cando" / sanitized_id
        mpath = images_dir / "manifest.json"
        if not mpath.exists():
            return None
        try:
            return json.loads(mpath.read_text(encoding="utf-8"))
        except Exception:
            return None

    async def assemble_package(self, *, can_do_id: str, session: Optional[AsyncSession] = None) -> Dict[str, Any]:
        """Assemble a combined lesson package for a CanDoDescriptor.

        Includes lesson_plan, exercises, sample_dialog, stages, pragmatics (graph-first with compiled fallback), and illustrations manifest if present.
        """
        lesson = self._load_compiled_lesson(can_do_id)
        exercises = self._load_compiled_exercises(can_do_id)
        dialog = self._load_compiled_sample_dialog(can_do_id)
        stages = self._load_compiled_stages(can_do_id)
        manifest = self._load_manifest(can_do_id)

        prag: List[Dict[str, Any]] = []
        if session is not None:
            try:
                prag = await pragmatics_service.get_pragmatics(session=session, can_do_id=can_do_id)
            except Exception:
                prag = []
        else:
            prag = []

        pkg: Dict[str, Any] = {
            "can_do_id": can_do_id,
            "lesson_plan": lesson,
            "exercises": exercises.get("exercises", []),
            "sample_dialog": dialog,
            "stages": stages,
            "pragmatics": prag,
        }
        if manifest is not None:
            pkg["illustrations_manifest"] = manifest
        return pkg

    async def activate_cando(self, *, can_do_id: str, session: Optional[AsyncSession] = None) -> Dict[str, Any]:
        """
        Activate a CanDo lesson using precedence policy.

        Current MVP: returns compiled lesson_plan.json; future: enrich from graph when available.
        """
        precedence = (settings.LESSON_SOURCE_PRECEDENCE or "graph_first").lower()
        # Graph-first not implemented yet; fall back to compiled
        try:
            lesson = self._load_compiled_lesson(can_do_id)
            return lesson
        except Exception as e:
            logger.error("activate_cando fallback failed", can_do_id=can_do_id, error=str(e))
            raise

    def generate_exercises_minimal(
        self,
        *,
        can_do_id: str,
        n: int = 3,
        modes: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Return a minimal exercise bundle from compiled artifacts.

        Filters by modes if the exercise items contain a 'mode' or 'type' field
        matching any of the requested modes (best-effort).
        """
        bundle = self._load_compiled_exercises(can_do_id)
        items: List[Dict[str, Any]] = list(bundle.get("exercises", []))

        original_items = list(items)
        if modes:
            modes_l = {m.lower() for m in modes}
            def match_mode(it: Dict[str, Any]) -> bool:
                raw = it.get("mode") or it.get("type")
                if raw is None:
                    # If items don't declare a mode/type, do not exclude them
                    return True
                mode = str(raw).lower()
                # accept partial matches like 'writing', 'dialog', etc.
                return any(m in mode for m in modes_l) if mode else True
            items = [it for it in items if match_mode(it)]
            # Fallback: if filtering produced nothing, return unfiltered items
            if not items:
                items = original_items

        if n and isinstance(n, int) and n > 0:
            items = items[: n]

        return {"can_do_id": can_do_id, "exercises": items}

    async def _get_cando_meta(self, session: AsyncSession, can_do_id: str) -> Dict[str, Any]:
        query = """
        MATCH (c:CanDoDescriptor {uid: $can_do_id})
        RETURN c.uid AS uid, toString(c.primaryTopic) AS primaryTopic, toString(c.level) AS level
        LIMIT 1
        """
        result = await session.run(query, can_do_id=can_do_id)
        rec = await result.single()
        if not rec:
            raise ValueError("CanDoDescriptor not found")
        return dict(rec)

    def _map_cando_level_to_numeric(self, level_str: Optional[str]) -> int:
        if not level_str:
            return 3
        s = level_str.strip().upper()
        mapping = {"A1": 1, "A2": 2, "B1": 3, "B2": 4, "C1": 5, "C2": 6}
        return mapping.get(s, 3)

    async def generate_exercises_for_cando_ai(
        self,
        *,
        session: AsyncSession,
        can_do_id: str,
        phase: Optional[str] = None,
        n: int = 3,
    ) -> Dict[str, Any]:
        """Generate exercises on-the-fly using AI and lexical graph seeds based on CanDo level.

        Strategy:
        - Read CanDo primaryTopic and level
        - Map CEFR level to numeric (1..6)
        - Seed target words by level
        - Generate up to n short exercises using AI for each seed
        """
        meta = await self._get_cando_meta(session, can_do_id)
        level_num = self._map_cando_level_to_numeric(meta.get("level"))
        seeds = await self.seed_words_by_level(session, level=level_num, count=max(5, n))
        exercises: List[Dict[str, Any]] = []
        for seed in seeds[: max(1, n)]:
            word = seed.get("kanji") or seed.get("hiragana") or ""
            try:
                ex = await self.generate_exercise(
                    session=session,
                    word_kanji=word,
                    level=level_num,
                    provider="openai",
                    model="gpt-4o-mini",
                    analyze_readability=True,
                )
                exercises.append(
                    {
                        "type": "ai_text",
                        "prompt": ex.get("content", ""),
                        "target": ex.get("target"),
                        "readability": ex.get("readability"),
                    }
                )
                if len(exercises) >= n:
                    break
            except Exception as gen_err:
                logger.warn("exercise_generation_failed", can_do_id=can_do_id, word=word, error=str(gen_err))
                continue
        return {"can_do_id": can_do_id, "phase": phase or "lexicon_and_patterns", "exercises": exercises}

    def compute_next_phase(
        self,
        *,
        current_phase: str,
        completed_count: int,
        score: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Simple, deterministic phase gating based on settings.

        - completion mode: advance when completed_count >= GATING_N
        - score mode: advance when (score or 0.0) >= 0.70
        """
        try:
            idx = PHASES.index(current_phase)
        except ValueError:
            logger.warning("unknown_phase", phase=current_phase, defaulting_to_idx_0=True)
            idx = 0

        if idx >= len(PHASES) - 1:
            logger.debug("already_at_final_phase", phase=current_phase)
            return {"phase": PHASES[-1], "advanced": False}

        mode = (settings.GATING_MODE or "completion").lower()
        advanced = False
        if mode == "completion":
            threshold = int(settings.GATING_N or 2)
            advanced = completed_count >= threshold
            logger.debug("phase_gating_completion_mode", current_phase=current_phase, completed_count=completed_count, threshold=threshold, advanced=advanced)
        elif mode == "score":
            s = float(score or 0.0)
            advanced = s >= 0.70
            logger.debug("phase_gating_score_mode", current_phase=current_phase, score=s, threshold=0.70, advanced=advanced)
        else:
            threshold = int(settings.GATING_N or 2)
            advanced = completed_count >= threshold
            logger.debug("phase_gating_default_mode", current_phase=current_phase, completed_count=completed_count, threshold=threshold, advanced=advanced)

        next_idx = idx + 1 if advanced else idx
        next_phase = PHASES[next_idx]
        
        if advanced and next_phase != current_phase:
            logger.info("phase_advancement", old_phase=current_phase, new_phase=next_phase, completed_count=completed_count, score=score)
        
        return {"phase": next_phase, "advanced": advanced}

    async def seed_words_by_level(self, session: AsyncSession, level: int, count: int = 12) -> List[Dict[str, Any]]:
        query = """
        MATCH (w:Word)-[:HAS_DIFFICULTY]->(d:DifficultyLevel {numeric_level: $level})
        WHERE w.translation IS NOT NULL
        WITH w ORDER BY rand() LIMIT $count
        RETURN w.kanji AS kanji, w.hiragana AS hiragana, w.translation AS translation,
               w.pos_primary AS pos, w.difficulty_numeric AS level
        """
        result = await session.run(query, level=level, count=count)
        items: List[Dict[str, Any]] = []
        async for rec in result:
            items.append(dict(rec))
        return items

    async def get_neighbors(self, session: AsyncSession, kanji: str, limit: int = 7) -> List[Dict[str, Any]]:
        query = """
        MATCH (t:Word {kanji: $kanji})-[r:SYNONYM_OF]-(n:Word)
        WITH n, r ORDER BY coalesce(r.synonym_strength, r.weight, 0.0) DESC
        RETURN n.kanji AS kanji, n.hiragana AS hiragana, n.translation AS translation,
               n.pos_primary AS pos, coalesce(r.synonym_strength, r.weight, 0.0) AS strength
        LIMIT $limit
        """
        result = await session.run(query, kanji=kanji, limit=limit)
        out: List[Dict[str, Any]] = []
        async for rec in result:
            out.append(dict(rec))
        return out

    def _build_exercise_prompt(self, target: Dict[str, Any], neighbors: List[Dict[str, Any]], level: int) -> str:
        word = target.get("kanji") or target.get("hiragana") or "(target)"
        translation = target.get("translation") or ""
        neighbor_list = ", ".join([n.get("kanji") or n.get("hiragana") or "" for n in neighbors if n])
        level_desc = LEVEL_DESC.get(level, "Intermediate level")
        base = f"""
You are a Japanese language teacher. Create a short interactive exercise centered on the word "{word}" (meaning "{translation}").

Level: {level} - {level_desc}

Requirements:
1) Introduce the word naturally and show it in 1-2 short example sentences.
2) Use 2-3 related words where natural: {neighbor_list}
3) End with one concise prompt inviting a reply.
4) Keep output focused and compact (<= 180 words total).
"""
        if level <= 2:
            base += "\nBeginner formatting: include romaji for all JP lines and English translations. Prefer hiragana and simple patterns."
        elif level <= 4:
            base += "\nIntermediate formatting: romaji only for difficult words; translate only when necessary; natural everyday tone."
        else:
            base += "\nAdvanced formatting: native-like Japanese with appropriate kanji; minimal translations; emphasize nuance."
        base += "\nFormat your response clearly as: Intro / Examples / Prompt."
        return base.strip()

    async def generate_exercise(
        self,
        *,
        session: AsyncSession,
        word_kanji: str,
        level: int = 1,
        provider: str = "openai",
        model: str = "gpt-4o-mini",
        analyze_readability: bool = True,
    ) -> Dict[str, Any]:
        # Fetch target details
        q = """
        MATCH (w:Word)
        WHERE w.kanji = $kanji OR w.hiragana = $kanji OR w.lemma = $kanji
        RETURN w.kanji AS kanji, w.hiragana AS hiragana, w.translation AS translation,
               w.pos_primary AS pos, w.difficulty_numeric AS level
        LIMIT 1
        """
        res = await session.run(q, kanji=word_kanji)
        rec = await res.single()
        if not rec:
            raise ValueError("Word not found in graph")
        target = dict(rec)
        neighbors = await self.get_neighbors(session, target["kanji"], limit=7)
        prompt = self._build_exercise_prompt(target, neighbors, level)

        reply = await self.ai.generate_reply(
            provider="gemini" if provider == "gemini" else "openai",
            model=(model if provider == "openai" else "gemini-2.5-flash"),
            messages=[{"role": "user", "content": prompt}],
            system_prompt="You are an expert Japanese tutor generating concise, level-appropriate lexical practice.",
        )
        content = reply.get("content", "")
        result: Dict[str, Any] = {
            "target": target,
            "neighbors": neighbors,
            "level": level,
            "ai": {"provider": reply.get("provider"), "model": reply.get("model")},
            "content": content,
        }
        if analyze_readability and content:
            result["readability"] = readability_service.analyze(content)
        return result


lexical_lessons = LexicalLessonsService()

