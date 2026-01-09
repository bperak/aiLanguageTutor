"""
Grammar AI Content Service
=========================

Generates AI-based overview content for grammar patterns and stores it in Neo4j
to avoid regenerating on subsequent requests.

This service produces LEARNER-FIRST content designed for beginners who may not
be able to read Japanese yet. Every Japanese item includes:
- jp: The Japanese text (kanji + kana mixed)
- kana: Pure hiragana/katakana reading
- romaji: Romanized pronunciation with proper word spacing
- en: English translation

Overview fields include:
- what_is_en: plain English explanation of the pattern
- how_to_form: structured formation guide with steps
- usage_en: when and how to use it
- nuance_en: subtle meanings, register, formality notes
- common_mistakes: list of typical learner errors with examples
- cultural_context_en: cultural/usage setting notes
- examples: 4-5 example sentences with full jp/kana/romaji/en
- tips_en: learning tips
- related_patterns: similar/prereq patterns
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
import json
import logging
import re

from neo4j import AsyncSession

from app.services.ai_chat_service import AIChatService
from app.services.grammar_service import GrammarService
from app.utils.romaji import prettify_romaji_template


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
        """
        Persist overview JSON and key fields on the GrammarPattern node.
        """
        now_iso = datetime.utcnow().isoformat()
        
        query = """
        MATCH (g:GrammarPattern {id: $pattern_id})
        SET g.ai_overview = $overview_json,
            g.ai_overview_model = $model,
            g.ai_overview_generated_at = $generated_at
        RETURN g.id AS id
        """
        await session.run(
            query,
            pattern_id=pattern_id,
            overview_json=json.dumps(overview, ensure_ascii=False),
            model=model,
            generated_at=now_iso,
        )

    def _build_prompt(self, pattern: Dict[str, Any], similar: List[Dict[str, Any]], prerequisites: List[Dict[str, Any]]) -> str:
        """
        Create a learner-first prompt that produces structured output with
        every Japanese item having kana, romaji, and English translation.
        
        Designed for beginners who cannot read Japanese yet.
        """
        # === BUILD PATTERN CONTEXT ===
        pattern_context = []
        
        pattern_jp = pattern.get('pattern', '')
        pattern_romaji = pattern.get('pattern_romaji', '')
        pattern_context.append(f"PATTERN: {pattern_jp} (romaji: {pattern_romaji})")
        
        textbook_form = pattern.get('textbook_form', '')
        textbook_form_romaji = pattern.get('textbook_form_romaji', '')
        if textbook_form:
            pattern_context.append(f"TEMPLATE: {textbook_form}")
            if textbook_form_romaji:
                pattern_context.append(f"  Romaji: {textbook_form_romaji}")
        
        example_jp = pattern.get('example_sentence', '')
        example_romaji = pattern.get('example_romaji', '')
        if example_jp:
            pattern_context.append(f"EXAMPLE: {example_jp}")
            if example_romaji:
                pattern_context.append(f"  Romaji: {example_romaji}")
        
        classification = pattern.get('classification', '')
        if classification:
            pattern_context.append(f"FUNCTION: {classification}")
        
        textbook = pattern.get('textbook', '')
        topic = pattern.get('topic', '')
        lesson = pattern.get('lesson', '')
        jfs_category = pattern.get('jfs_category', '')
        
        curriculum_parts = []
        if textbook:
            curriculum_parts.append(f"Level: {textbook}")
        if topic:
            curriculum_parts.append(f"Topic: {topic}")
        if lesson:
            curriculum_parts.append(f"Lesson: {lesson}")
        if jfs_category:
            curriculum_parts.append(f"JFS: {jfs_category}")
        if curriculum_parts:
            pattern_context.append(f"CONTEXT: {' | '.join(curriculum_parts)}")

        # === BUILD SIMILAR PATTERNS CONTEXT ===
        similar_list = []
        for sim in similar[:5]:
            sim_pattern = sim.get('pattern', '')
            sim_romaji = sim.get('pattern_romaji', '')
            if sim_pattern:
                similar_list.append(f"- {sim_pattern} ({sim_romaji})")
        
        # === BUILD PREREQUISITES CONTEXT ===
        prereq_list = []
        for prereq in prerequisites[:5]:
            prereq_pattern = prereq.get('pattern', '')
            prereq_romaji = prereq.get('pattern_romaji', '')
            if prereq_pattern:
                prereq_list.append(f"- {prereq_pattern} ({prereq_romaji})")

        # === JSON SCHEMA FOR LEARNER-FIRST OUTPUT ===
        json_schema = '''{
  "what_is_en": "2-3 sentences in PLAIN ENGLISH explaining what this pattern means, when you use it, and what kind of meaning it expresses. Write as if explaining to someone who knows zero Japanese.",
  
  "how_to_form": {
    "summary_en": "Plain English explanation of how to build sentences with this pattern. Example: 'To say you CAN do something, take a noun (like a skill or language) and add ga dekimasu after it.'",
    "pattern_template": "Simple template using English labels, e.g.: [Noun] + ga + dekimasu",
    "steps": [
      {
        "slot": "What goes in the [Noun] slot",
        "jp": "Japanese example word",
        "kana": "Hiragana reading of that word",
        "romaji": "Romaji with spaces",
        "en": "English meaning"
      }
    ],
    "casual_variant": {
      "jp": "Casual form if applicable",
      "kana": "Hiragana reading",
      "romaji": "Romaji",
      "en": "English meaning"
    },
    "formal_variant": null,
    "notes_en": ["Additional notes in English"]
  },
  
  "usage_en": "2-3 sentences in English explaining WHEN to use this pattern (situations, contexts, who uses it).",
  
  "nuance_en": "2-3 sentences in English about subtle meanings, politeness level, and when to choose this over similar patterns.",
  
  "common_mistakes": [
    {
      "mistake_en": "Description of a common mistake in English",
      "wrong": {"jp": "Wrong sentence", "kana": "reading", "romaji": "ro ma ji", "en": "English"},
      "correct": {"jp": "Correct sentence", "kana": "reading", "romaji": "ro ma ji", "en": "English"}
    }
  ],
  
  "cultural_context_en": "Cultural notes in English (or null if not relevant)",
  
  "examples": [
    {"jp": "Full Japanese sentence", "kana": "Full hiragana reading", "romaji": "Full romaji WITH SPACES between words", "en": "Natural English translation"}
  ],
  
  "tips_en": "1-2 practical tips in English for remembering or using this pattern.",
  
  "related_patterns": ["pattern1", "pattern2"]
}'''

        # === BUILD FULL PROMPT ===
        prompt = f"""You are creating a grammar lesson card for BEGINNERS learning Japanese who CANNOT READ JAPANESE YET.

CRITICAL RULES:
1. ALL explanations must be in ENGLISH - no Japanese in explanation text
2. EVERY Japanese item MUST have ALL 4 fields: jp, kana, romaji, en
3. Romaji MUST have SPACES between words (e.g., "Nihongo ga dekimasu" NOT "Nihongogadekimasu")
4. The "kana" field must be the PURE HIRAGANA reading (no kanji)
5. Write as if the learner knows ZERO Japanese
6. Avoid technical grammar jargon - use simple English
7. Do NOT use symbols like 【】 or other notation - use plain English

TARGET PATTERN:
{chr(10).join(pattern_context)}

SIMILAR PATTERNS (for comparison):
{chr(10).join(similar_list) if similar_list else "None"}

PREREQUISITES (learner should know):
{chr(10).join(prereq_list) if prereq_list else "None"}

OUTPUT FORMAT (respond with ONLY this JSON, no markdown):
{json_schema}

REQUIREMENTS:
- Provide 4-5 diverse examples showing different uses
- Each example must have jp, kana, romaji (with spaces!), and en
- common_mistakes should have 2-3 real errors with wrong/correct examples
- how_to_form.steps should break down each component of the pattern
- All romaji must have proper word spacing
- Output ONLY valid JSON"""

        return prompt

    def _migrate_legacy_overview(self, overview: Dict[str, Any]) -> Dict[str, Any]:
        """
        Migrate an older overview format to the new learner-first structure.
        
        Old format had: what_is, formation, usage, nuance, common_mistakes (strings), examples [{jp, romaji, en}]
        New format has: what_is_en, how_to_form (structured), usage_en, nuance_en, common_mistakes (structured), examples [{jp, kana, romaji, en}]
        """
        # Check if this is already in the new format
        if "what_is_en" in overview and overview.get("what_is_en"):
            return overview  # Already migrated
        
        migrated = {}
        
        # Migrate text fields
        migrated["what_is_en"] = overview.get("what_is", "") or ""
        migrated["usage_en"] = overview.get("usage", "") or ""
        migrated["nuance_en"] = overview.get("nuance", "") or ""
        migrated["tips_en"] = overview.get("tips", "") or ""
        migrated["cultural_context_en"] = overview.get("cultural_context")
        
        # Migrate formation to structured how_to_form
        old_formation = overview.get("formation", "")
        migrated["how_to_form"] = {
            "summary_en": old_formation if isinstance(old_formation, str) else "",
            "pattern_template": "",
            "steps": [],
            "casual_variant": None,
            "formal_variant": None,
            "notes_en": []
        }
        
        # Migrate common_mistakes
        old_mistakes = overview.get("common_mistakes", [])
        migrated["common_mistakes"] = []
        if isinstance(old_mistakes, list):
            for m in old_mistakes:
                if isinstance(m, str):
                    migrated["common_mistakes"].append({
                        "mistake_en": m,
                        "wrong": None,
                        "correct": None
                    })
                elif isinstance(m, dict):
                    migrated["common_mistakes"].append(m)
        
        # Migrate examples - add empty kana field if missing
        old_examples = overview.get("examples", [])
        migrated["examples"] = []
        if isinstance(old_examples, list):
            for ex in old_examples:
                if isinstance(ex, dict):
                    migrated["examples"].append({
                        "jp": ex.get("jp", ""),
                        "kana": ex.get("kana", ""),  # Will be empty for legacy
                        "romaji": prettify_romaji_template(ex.get("romaji", "")),
                        "en": ex.get("en", "")
                    })
        
        # Copy over other fields
        migrated["related_patterns"] = overview.get("related_patterns", [])
        migrated["model_used"] = overview.get("model_used")
        migrated["generated_at"] = overview.get("generated_at")
        
        # Keep legacy fields for backward compatibility
        migrated["what_is"] = overview.get("what_is")
        migrated["formation"] = overview.get("formation")
        migrated["usage"] = overview.get("usage")
        migrated["nuance"] = overview.get("nuance")
        migrated["tips"] = overview.get("tips")
        migrated["cultural_context"] = overview.get("cultural_context")
        
        return migrated

    def _postprocess_overview(self, overview: Dict[str, Any]) -> Dict[str, Any]:
        """
        Post-process AI-generated overview to ensure quality and consistency.
        
        - Migrates legacy format if needed
        - Ensures all expected fields exist (with defaults)
        - Prettifies romaji in examples
        - Validates structure
        """
        # First, migrate if it's an old format
        overview = self._migrate_legacy_overview(overview)
        
        # Ensure new required fields exist with defaults
        new_defaults = {
            "what_is_en": "",
            "how_to_form": {
                "summary_en": "",
                "pattern_template": "",
                "steps": [],
                "casual_variant": None,
                "formal_variant": None,
                "notes_en": []
            },
            "usage_en": "",
            "nuance_en": "",
            "common_mistakes": [],
            "cultural_context_en": None,
            "examples": [],
            "tips_en": "",
            "related_patterns": [],
        }
        
        for key, default in new_defaults.items():
            if key not in overview or overview[key] is None:
                overview[key] = default
        
        # Ensure how_to_form has all required subfields
        if isinstance(overview.get("how_to_form"), dict):
            htf = overview["how_to_form"]
            htf_defaults = {
                "summary_en": "",
                "pattern_template": "",
                "steps": [],
                "casual_variant": None,
                "formal_variant": None,
                "notes_en": []
            }
            for k, v in htf_defaults.items():
                if k not in htf or htf[k] is None:
                    htf[k] = v
        elif overview.get("how_to_form") is None:
            overview["how_to_form"] = new_defaults["how_to_form"]
        
        # Ensure common_mistakes is a list of structured objects
        if isinstance(overview.get("common_mistakes"), list):
            normalized_mistakes = []
            for m in overview["common_mistakes"]:
                if isinstance(m, str):
                    normalized_mistakes.append({
                        "mistake_en": m,
                        "wrong": None,
                        "correct": None
                    })
                elif isinstance(m, dict):
                    normalized_mistakes.append({
                        "mistake_en": m.get("mistake_en", ""),
                        "wrong": m.get("wrong"),
                        "correct": m.get("correct")
                    })
            overview["common_mistakes"] = normalized_mistakes
        else:
            overview["common_mistakes"] = []
        
        # Prettify romaji in all examples
        if isinstance(overview.get("examples"), list):
            for example in overview["examples"]:
                if isinstance(example, dict):
                    if "romaji" in example:
                        example["romaji"] = prettify_romaji_template(example.get("romaji", ""))
                    # Ensure all 4 fields exist
                    for field in ["jp", "kana", "romaji", "en"]:
                        if field not in example:
                            example[field] = ""
        
        # Prettify romaji in how_to_form steps
        if isinstance(overview.get("how_to_form"), dict):
            htf = overview["how_to_form"]
            if isinstance(htf.get("steps"), list):
                for step in htf["steps"]:
                    if isinstance(step, dict) and "romaji" in step:
                        step["romaji"] = prettify_romaji_template(step.get("romaji", ""))
            # Prettify casual/formal variants
            for variant_key in ["casual_variant", "formal_variant"]:
                variant = htf.get(variant_key)
                if isinstance(variant, dict) and "romaji" in variant:
                    variant["romaji"] = prettify_romaji_template(variant.get("romaji", ""))
        
        # Prettify romaji in common_mistakes examples
        if isinstance(overview.get("common_mistakes"), list):
            for mistake in overview["common_mistakes"]:
                if isinstance(mistake, dict):
                    for ex_key in ["wrong", "correct"]:
                        ex = mistake.get(ex_key)
                        if isinstance(ex, dict) and "romaji" in ex:
                            ex["romaji"] = prettify_romaji_template(ex.get("romaji", ""))
        
        # Ensure related_patterns is a list
        if isinstance(overview.get("related_patterns"), str):
            rp = overview["related_patterns"]
            if rp:
                overview["related_patterns"] = [p.strip() for p in rp.split(",") if p.strip()]
            else:
                overview["related_patterns"] = []
        
        # Clean up whitespace in text fields
        for key in ["what_is_en", "usage_en", "nuance_en", "tips_en"]:
            if isinstance(overview.get(key), str):
                overview[key] = overview[key].strip()
        
        return overview

    async def generate_overview(
        self,
        *,
        session: AsyncSession,
        pattern_id: str,
        provider: str = "openai",
        model: str = "gpt-5.1",
        force: bool = False,
    ) -> Dict[str, Any]:
        """Generate or return cached overview for a grammar pattern."""
        if not force:
            stored = await self.get_stored_overview(session, pattern_id)
            if stored:
                # Post-process (includes migration) even stored overviews for consistency
                return self._postprocess_overview(stored)

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
            # Remove markdown code fence if present
            if cleaned.startswith("```"):
                lines = cleaned.split("\n")
                # Remove first line (```json) and last line (```)
                cleaned = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
            try:
                overview = json.loads(cleaned)
            except Exception:
                logger.error("Failed to parse AI overview JSON: %s", content[:500])
                raise

        # Post-process the overview for quality
        overview = self._postprocess_overview(overview)

        await self._store_overview(session, pattern_id, overview, result.get("model", model))
        overview["model_used"] = result.get("model", model)
        overview["generated_at"] = datetime.utcnow().isoformat()
        return overview
