"""
CanDo Exercises Service

Generates exercises specifically for CanDo descriptors, using graph data
and AI to create concise, level-appropriate practice content.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import structlog

from neo4j import AsyncSession

from app.services.ai_chat_service import AIChatService
from app.core.config import settings
from app.services.readability_service import readability_service


logger = structlog.get_logger()


class CanDoExercisesService:
    def __init__(self) -> None:
        self.ai = AIChatService()

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

    def _build_exercise_prompt(self, meta: Dict[str, Any], target: Dict[str, Any], neighbors: List[Dict[str, Any]], level: int, phase: Optional[str]) -> str:
        topic = meta.get("primaryTopic") or "topic"
        word = target.get("kanji") or target.get("hiragana") or "(target)"
        translation = target.get("translation") or ""
        neighbor_list = ", ".join([n.get("kanji") or n.get("hiragana") or "" for n in neighbors if n])
        level_desc = {
            1: "Beginner 1 - romaji + simple sentences",
            2: "Beginner 2 - hiragana focus, limited romaji",
            3: "Intermediate 1 - basic kanji",
            4: "Intermediate 2 - more complex patterns",
            5: "Advanced 1 - sophisticated vocabulary",
            6: "Advanced 2 - native-like nuance",
        }.get(level, "Intermediate level")

        phase_hint = (phase or "lexicon_and_patterns").replace("_", " ")
        base = f"""
You are a Japanese language tutor. Create a short interactive exercise aligned to the CanDo topic "{topic}".

Target word: "{word}" (meaning: "{translation}")
Related words to sprinkle where natural: {neighbor_list}

Level: {level} - {level_desc}
Phase: {phase_hint}

Requirements:
1) Introduce the word naturally and show it in 1-2 short example sentences.
2) Use 2-3 related words naturally.
3) Finish with ONE concise prompt inviting a reply.
4) Keep output focused and compact (<= 180 words total).

Output format: Intro / Examples / Prompt
"""
        if level <= 2:
            base += "\nBeginner formatting: include romaji for JP lines and English translations; keep syntax simple."
        elif level <= 4:
            base += "\nIntermediate formatting: partial romaji; everyday tone; translate only if necessary."
        else:
            base += "\nAdvanced formatting: natural Japanese; minimal translations; emphasize nuance."
        return base.strip()

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

    async def generate_exercise_for_seed(self, *, session: AsyncSession, meta: Dict[str, Any], seed: Dict[str, Any], level: int, phase: Optional[str]) -> Dict[str, Any]:
        word = seed.get("kanji") or seed.get("hiragana") or ""
        neighbors = await self.get_neighbors(session, word, limit=7)
        prompt = self._build_exercise_prompt(meta, seed, neighbors, level, phase)
        provider = (settings.CANDO_AI_PROVIDER or "openai").lower()
        primary_model = settings.CANDO_AI_MODEL or "gpt-4o"
        fallback_model = settings.CANDO_AI_FALLBACK_MODEL or "gpt-4o"
        try:
            reply = await self.ai.generate_reply(
                provider="gemini" if provider == "gemini" else "openai",
                model=primary_model,
                messages=[{"role": "user", "content": prompt}],
                system_prompt="You are an expert Japanese tutor generating concise, level-appropriate CanDo practice.",
            )
        except Exception as primary_err:
            logger.warn("cando_ai_primary_failed", error=str(primary_err), model=primary_model, provider=provider)
            reply = await self.ai.generate_reply(
                provider="gemini" if provider == "gemini" else "openai",
                model=fallback_model,
                messages=[{"role": "user", "content": prompt}],
                system_prompt="You are an expert Japanese tutor generating concise, level-appropriate CanDo practice.",
            )
        content = reply.get("content", "")
        result: Dict[str, Any] = {
            "type": "ai_text",
            "prompt": content,
            "target": seed,
            "ai": {"provider": reply.get("provider"), "model": reply.get("model")},
        }
        if content:
            result["readability"] = readability_service.analyze(content)
        return result

    async def generate_for_cando(
        self,
        *,
        session: AsyncSession,
        can_do_id: str,
        phase: Optional[str] = None,
        n: int = 3,
    ) -> Dict[str, Any]:
        meta = await self._get_cando_meta(session, can_do_id)
        level_num = self._map_cando_level_to_numeric(meta.get("level"))
        seeds = await self.seed_words_by_level(session, level=level_num, count=max(5, n))
        exercises: List[Dict[str, Any]] = []
        # If no lexical seeds are available, generate a topic-only exercise as a guaranteed fallback
        if not seeds:
            try:
                topic = meta.get("primaryTopic") or "everyday conversation"
                prompt = (
                    f"Create one short interactive exercise for the CanDo topic '{topic}'.\n"
                    f"Level: {level_num}. Keep it under 180 words. Format: Intro / Examples / Prompt."
                )
                try:
                    reply = await self.ai.generate_reply(
                        provider=(settings.CANDO_AI_PROVIDER or "openai"),
                        model=(settings.CANDO_AI_MODEL or "gpt-4o"),
                        messages=[{"role": "user", "content": prompt}],
                        system_prompt="You are an expert Japanese tutor generating concise, level-appropriate CanDo practice.",
                    )
                except Exception as primary_err:
                    logger.warn("cando_topic_primary_failed", error=str(primary_err))
                    reply = await self.ai.generate_reply(
                        provider=(settings.CANDO_AI_PROVIDER or "openai"),
                        model=(settings.CANDO_AI_FALLBACK_MODEL or "gpt-4o"),
                        messages=[{"role": "user", "content": prompt}],
                        system_prompt="You are an expert Japanese tutor generating concise, level-appropriate CanDo practice.",
                    )
                content = reply.get("content", "")
                exercises.append({"type": "ai_text", "prompt": content})
            except Exception as e:
                logger.warn("cando_topic_fallback_failed", error=str(e))
        for seed in seeds:
            try:
                ex = await self.generate_exercise_for_seed(session=session, meta=meta, seed=seed, level=level_num, phase=phase)
                exercises.append(ex)
                if len(exercises) >= n:
                    break
            except Exception as gen_err:
                logger.warn("cando_exercise_generation_failed", can_do_id=can_do_id, seed=seed.get("kanji") or seed.get("hiragana"), error=str(gen_err))
                continue
        # Final guarantee: if no exercises could be generated, try a last-resort topic-only prompt
        if not exercises:
            try:
                topic = meta.get("primaryTopic") or "everyday conversation"
                prompt = (
                    f"Create one short interactive exercise for the CanDo topic '{topic}'.\n"
                    f"Level: {level_num}. Keep it under 180 words. Format: Intro / Examples / Prompt."
                )
                reply = await self.ai.generate_reply(
                    provider=(settings.CANDO_AI_PROVIDER or "openai"),
                    model=(settings.CANDO_AI_FALLBACK_MODEL or "gpt-4o"),
                    messages=[{"role": "user", "content": prompt}],
                    system_prompt="You are an expert Japanese tutor generating concise, level-appropriate CanDo practice.",
                )
                content = reply.get("content", "")
                exercises.append({"type": "ai_text", "prompt": content})
            except Exception as e:
                logger.warn("cando_final_fallback_failed", error=str(e))

        return {"can_do_id": can_do_id, "phase": phase or "lexicon_and_patterns", "exercises": exercises}


cando_exercises = CanDoExercisesService()


