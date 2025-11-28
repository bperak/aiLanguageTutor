"""
Grammar AI Content Service
=========================

Generates AI-based overview content for grammar patterns and stores it in Neo4j
to avoid regenerating on subsequent requests.

Overview fields include:
- what_is: concise explanation of the pattern
- usage: guidance on when/how to use it
- cultural_context: cultural/usage setting notes
- examples: 3-5 short example sentences (JP + romaji + EN)
- tips: learning tips and common pitfalls
- related_patterns: optional list of similar/prereq patterns with reasons
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
import json
import logging

from neo4j import AsyncSession

from app.services.ai_chat_service import AIChatService
from app.services.grammar_service import GrammarService


logger = logging.getLogger(__name__)


class GrammarAIContentService:
    """Service to generate and persist AI overview content for grammar patterns."""

    def __init__(self) -> None:
        self.ai = AIChatService()

    async def get_stored_overview(self, session: AsyncSession, pattern_id: str) -> Optional[Dict[str, Any]]:
        """Return stored overview JSON if present on the node."""
        query = """
        MATCH (g:GrammarPattern {id: $pattern_id})
        RETURN g.ai_overview as ai_overview,
               g.ai_overview_model as ai_model,
               g.ai_overview_generated_at as generated_at
        """
        result = await session.run(query, pattern_id=pattern_id)
        record = await result.single()
        if not record:
            return None
        raw = record.get("ai_overview")
        if not raw:
            return None
        try:
            overview = json.loads(raw) if isinstance(raw, str) else raw
        except Exception:
            # If stored as map already, return as-is
            overview = raw
        overview = overview or {}
        overview["model_used"] = record.get("ai_model")
        overview["generated_at"] = record.get("generated_at")
        return overview

    async def _store_overview(
        self,
        session: AsyncSession,
        pattern_id: str,
        overview: Dict[str, Any],
        model: str,
    ) -> None:
        """Persist overview JSON and metadata on the GrammarPattern node."""
        now_iso = datetime.utcnow().isoformat()
        query = """
        MATCH (g:GrammarPattern {id: $pattern_id})
        SET g.ai_overview = $overview_json,
            g.ai_overview_model = $model,
            g.ai_overview_generated_at = $generated_at,
            g.what_is = coalesce($what_is, g.what_is)
        RETURN g.id AS id
        """
        await session.run(
            query,
            pattern_id=pattern_id,
            overview_json=json.dumps(overview, ensure_ascii=False),
            model=model,
            generated_at=now_iso,
            what_is=(overview.get("what_is") if isinstance(overview, dict) else None),
        )

    def _build_prompt(self, pattern: Dict[str, Any], similar: List[Dict[str, Any]], prerequisites: List[Dict[str, Any]]) -> str:
        """Create a focused prompt for the AI model using graph context."""
        pattern_line = (
            f"Pattern: {pattern.get('pattern','')} ({pattern.get('pattern_romaji','')})\n"
            f"Textbook form: {pattern.get('textbook_form','')} ({pattern.get('textbook_form_romaji','')})\n"
            f"Example: {pattern.get('example_sentence','')} ({pattern.get('example_romaji','')})\n"
            f"Classification: {pattern.get('classification','')} | Level: {pattern.get('textbook','')} | Topic: {pattern.get('topic','')}"
        )

        def _fmt(items: List[Dict[str, Any]], key: str) -> List[str]:
            vals: List[str] = []
            for it in items:
                txt = it.get(key) or it.get("pattern") or it.get("example_sentence")
                if txt:
                    vals.append(str(txt))
            return vals

        similar_list = _fmt(similar, "pattern")
        prereq_list = _fmt(prerequisites, "pattern")

        json_instructions = (
            "Respond STRICTLY as compact JSON with these keys (no markdown, no commentary):\n"
            "{\n"
            '  "what_is": "1-2 sentences explaining the pattern",\n'
            '  "usage": "When/how to use; particles, formality, common mistakes; keep concise",\n'
            '  "cultural_context": "Cultural or usage setting notes (if any)",\n'
            '  "examples": [\n'
            '    {"jp": "Japanese sentence", "romaji": "Hepburn transliteration (romaji)", "en": "Natural English translation"},\n'
            '    {"jp": "...", "romaji": "...", "en": "..."}\n'
            "  ],\n"
            '  "tips": "Short learning advice",\n'
            '  "related_patterns": ["pattern A", "pattern B"]\n'
            "}\n"
            "Only JSON. No extra commentary."
        )

        prompt = (
            "You are a Japanese language tutor. Create a concise teaching overview for this grammar pattern.\n\n"
            f"{pattern_line}\n\n"
            f"Similar patterns (for contrast): {', '.join(similar_list[:5])}\n"
            f"Prerequisites (foundational): {', '.join(prereq_list[:5])}\n\n"
            + json_instructions
        ).strip()
        return prompt

    async def generate_overview(
        self,
        *,
        session: AsyncSession,
        pattern_id: str,
        provider: str = "openai",
        model: str = "gpt-4o-mini",
        force: bool = False,
    ) -> Dict[str, Any]:
        """Generate or return cached overview for a grammar pattern."""
        if not force:
            stored = await self.get_stored_overview(session, pattern_id)
            if stored:
                return stored

        # Gather context
        grammar_service = GrammarService(session)
        pattern = await grammar_service.get_pattern_by_id(pattern_id)
        if not pattern:
            raise ValueError("Grammar pattern not found")
        similar = await grammar_service.get_similar_patterns(pattern_id, limit=5)
        prereq = await grammar_service.get_prerequisites(pattern_id)

        prompt = self._build_prompt(pattern, similar, prereq)
        try:
            result = await self.ai.generate_reply(
                provider=provider, model=model, messages=[{"role": "user", "content": prompt}]
            )
        except Exception:
            # Fallback to a strong, widely available model if requested one fails
            fallback_model = "gpt-4o" if provider == "openai" else model
            result = await self.ai.generate_reply(
                provider=provider, model=fallback_model, messages=[{"role": "user", "content": prompt}]
            )
        content = result.get("content") or "{}"
        try:
            overview = json.loads(content)
        except Exception:
            # Try to sanitize common JSON issues
            cleaned = content.strip().strip("` ")
            try:
                overview = json.loads(cleaned)
            except Exception:
                logger.error("Failed to parse AI overview JSON", content_preview=content[:200])
                raise

        await self._store_overview(session, pattern_id, overview, result.get("model", model))
        overview["model_used"] = result.get("model", model)
        overview["generated_at"] = datetime.utcnow().isoformat()
        return overview


