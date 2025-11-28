"""
CanDo Lesson Session Service

Maintains short-lived in-memory lesson sessions per CanDo descriptor and
drives interactive dialogue using AIConversationPractice.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, List, Set, Union
import json
from uuid import uuid4
import time
import re
import unicodedata
import asyncio
from datetime import datetime, timedelta

from neo4j import AsyncSession
from sqlalchemy.ext.asyncio import AsyncSession as PgSession
from sqlalchemy import text
from pydantic import BaseModel, Field, ValidationError
import structlog

from app.services.ai_conversation_practice import (
    AIConversationPractice,
    ConversationContext,
    ConversationScenario,
    DialogueTurn,
)
from app.services.ai_chat_service import AIChatService
from app.services.lexical_lessons_service import lexical_lessons
from app.models.multilingual import (
    JapaneseText,
    Stage1Content,
    ReadingSection,
    DialogueTurn as Stage2DialogueTurn,
    GrammarPoint,
    Stage2DialogueTurnList,
    GrammarPointList,
    CultureNoteList,
    CultureNoteML,
    VocabularyEntry,
)
from app.utils.json_helpers import extract_balanced_json
from app.core.config import settings
from app.core.japanese_utils import (
    kata_to_hira,
    hira_to_kata,
    normalize_jp_text,
    extract_japanese_runs,
    generate_text_variants,
    fallback_multilingual,
    dedupe_sentences_jp,
)

logger = structlog.get_logger()


class UICard(BaseModel):
    id: str
    kind: str  # "text" | "dialogue" | "reading" | "grammar" | "practice"
    title: Optional[Union[str, JapaneseText]] = None
    subtitle: Optional[str] = None
    
    # For dialogue cards (new multilingual structure)
    dialogue_turns: Optional[List[Stage2DialogueTurn]] = None
    
    # For reading cards (new multilingual structure)
    reading: Optional[ReadingSection] = None
    
    # For simple text/grammar cards (backward compatible)
    body: Optional[Dict[str, Any]] = None
    # Bullets can be either simple strings OR multilingual JapaneseText objects
    bullets: Optional[List[Union[str, JapaneseText]]] = None
    badges: Optional[List[str]] = None
    media: Optional[List[Dict[str, Any]]] = None


class UISection(BaseModel):
    id: str
    type: str
    title: Optional[str] = None
    cards: List[UICard] = Field(default_factory=list)


class LessonUI(BaseModel):
    header: Dict[str, Any] = Field(default_factory=dict)
    sections: List[UISection] = Field(default_factory=list)
    gallery: Optional[List[Dict[str, Any]]] = None


class MasterSchema(BaseModel):
    uiVersion: int
    lessonId: str
    canDoId: str
    originalLevel: Optional[int] = None
    metadata: Dict[str, Any]
    learningObjectives: List[str] = Field(default_factory=list)
    ui: LessonUI
    exercises: Optional[List[Dict[str, Any]]] = None
    extractedEntities: Optional[Dict[str, Any]] = None
    readability: Optional[Dict[str, Any]] = None
    pdf: Optional[Dict[str, Any]] = None


class CanDoLessonSessionService:
    def __init__(self) -> None:
        # Postgres sessions replaced in-memory dict; kept for backward compat reference
        # Now using _store_session, _retrieve_session for persistence
        self._practice = AIConversationPractice()

        # Master lesson cache: key="{can_do_id}:{topic}", value=(master,
        # timestamp)
        self._master_cache: Dict[str, tuple[Dict[str, Any], float]] = {}
        # Cache TTL in seconds (default 1 hour; configurable via
        # MASTER_CACHE_TTL)
        self._cache_ttl = int(getattr(settings, "MASTER_CACHE_TTL", 3600))
        # Stage 2 cache to avoid recomputing enhanced sections for identical inputs
        self._stage2_cache: Dict[str, tuple[Any, float]] = {}
        self._stage2_cache_ttl = int(getattr(settings, "STAGE2_CACHE_TTL", 600))

    def _stage2_cache_get(self, key: str) -> Optional[Any]:
        rec = self._stage2_cache.get(key)
        if not rec:
            return None
        value, ts = rec
        if (time.time() - ts) > self._stage2_cache_ttl:
            try:
                del self._stage2_cache[key]
            except Exception:
                pass
            return None
        return value

    def _stage2_cache_set(self, key: str, value: Any) -> None:
        self._stage2_cache[key] = (value, time.time())

    async def _cleanup_expired_sessions(self, pg: PgSession) -> None:
        """Delete expired sessions from Postgres (TTL-based cleanup).

        Called on service init and can be scheduled periodically.
        """
        try:
            await pg.execute(
                text(
                    "DELETE FROM lesson_sessions WHERE expires_at < NOW()"
                )
            )
            await pg.commit()
        except Exception as e:
            logger.warning("session_cleanup_failed", error=str(e))

    def _get_cached_master(self, can_do_id: str,
                           topic: str) -> Optional[Dict[str, Any]]:
        """Retrieve cached master lesson if not expired.

        Args:
            can_do_id: CanDo descriptor ID.
            topic: Lesson topic.

        Returns:
            Cached master lesson dict if valid; None if expired or not found.
        """
        cache_key = f"{can_do_id}:{topic}"
        if cache_key not in self._master_cache:
            return None

        master, cached_time = self._master_cache[cache_key]
        elapsed = time.time() - cached_time

        if elapsed > self._cache_ttl:
            # Expired; remove from cache
            del self._master_cache[cache_key]
            logger.debug(
                "master_cache_expired",
                cache_key=cache_key,
                ttl_sec=self._cache_ttl)
            return None

        logger.debug(
            "master_cache_hit",
            cache_key=cache_key,
            age_sec=round(
                elapsed,
                1))
        return master

    def _cache_master(self, can_do_id: str, topic: str,
                      master: Dict[str, Any]) -> None:
        """Store master lesson in cache.

        Args:
            can_do_id: CanDo descriptor ID.
            topic: Lesson topic.
            master: Master lesson dict to cache.
        """
        cache_key = f"{can_do_id}:{topic}"
        self._master_cache[cache_key] = (master, time.time())
        logger.debug(
            "master_cached",
            cache_key=cache_key,
            ttl_sec=self._cache_ttl)

    async def _store_session(
        self, pg: PgSession, session_id: str, session_data: Dict[str, Any]
    ) -> None:
        """Store session to Postgres."""
        try:
            await pg.execute(
                text(
                    "INSERT INTO lesson_sessions (id, can_do_id, phase, completed_count, scenario_json, master_json, variant_json, package_json, expires_at) "
                    "VALUES (:id, :can_do_id, :phase, :completed_count, :scenario_json, :master_json, :variant_json, :package_json, :expires_at) "
                    "ON CONFLICT (id) DO UPDATE SET "
                    "  phase = :phase, completed_count = :completed_count, "
                    "  scenario_json = :scenario_json, master_json = :master_json, "
                    "  variant_json = :variant_json, package_json = :package_json, "
                    "  updated_at = CURRENT_TIMESTAMP"
                ),
                {
                    "id": session_id,
                    "can_do_id": session_data.get("can_do_id", ""),
                    "phase": session_data.get("phase", "lexicon_and_patterns"),
                    "completed_count": session_data.get("completed_count", 0),
                    "scenario_json": json.dumps(
                        session_data.get("scenario").model_dump(mode='python')
                        if hasattr(session_data.get("scenario"), "model_dump")
                        else (session_data.get("scenario") if session_data.get("scenario") else {})
                    ),
                    "master_json": json.dumps(session_data.get("master", {})),
                    "variant_json": json.dumps(session_data.get("variant", {})),
                    "package_json": json.dumps(session_data.get("package", {})),
                    "expires_at": datetime.utcnow() + timedelta(hours=24),
                },
            )
            await pg.commit()
        except Exception as e:
            logger.error(
                "session_store_failed",
                session_id=session_id,
                error=str(e))

    async def _retrieve_session(
            self, pg: PgSession, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve session from Postgres if not expired."""
        try:
            result = await pg.execute(
                text(
                    "SELECT id, can_do_id, phase, completed_count, scenario_json, master_json, variant_json, package_json, expires_at "
                    "FROM lesson_sessions WHERE id = :id AND expires_at > NOW() LIMIT 1"
                ),
                {"id": session_id},
            )
            row = result.first()
            if not row:
                return None
            return {
                "id": row[0],
                "can_do_id": row[1],
                "phase": row[2],
                "completed_count": row[3],
                "scenario": (
                    ConversationScenario.model_validate(json.loads(row[4]) if isinstance(row[4], str) else row[4])
                    if row[4]
                    else None
                ),
                "master": json.loads(row[5]) if isinstance(row[5], str) else (row[5] if row[5] else {}),
                "variant": json.loads(row[6]) if isinstance(row[6], str) else (row[6] if row[6] else {}),
                "package": json.loads(row[7]) if isinstance(row[7], str) else (row[7] if row[7] else {}),
                "expires_at": row[8],
            }
        except Exception as e:
            logger.error(
                "session_retrieve_failed",
                session_id=session_id,
                error=str(e))
            return None

    async def _delete_session(self, pg: PgSession, session_id: str) -> None:
        """Delete session from Postgres."""
        try:
            await pg.execute(
                text("DELETE FROM lesson_sessions WHERE id = :id"),
                {"id": session_id},
            )
            await pg.commit()
        except Exception as e:
            logger.warning(
                "session_delete_failed",
                session_id=session_id,
                error=str(e))

    async def _get_cando_meta(
            self, session: AsyncSession, can_do_id: str) -> Dict[str, Any]:
        query = """
        MATCH (c:CanDoDescriptor {uid: $can_do_id})
        RETURN c.uid AS uid,
               toString(c.primaryTopic) AS primaryTopic,
               toString(c.level) AS level,
               toString(c.type) AS type,
               toString(c.skillDomain) AS skillDomain,
               toString(c.example_sentence) AS exampleSentence,
               coalesce(toString(c.description), toString(c.what_is)) AS description,
               toString(c.id) AS canDoNumericId,
               toString(c.category) AS category,
               toString(c.descriptionEn) AS descriptionEn,
               toString(c.descriptionJa) AS descriptionJa,
               toString(c.titleEn) AS titleEn,
               toString(c.titleJa) AS titleJa
        LIMIT 1
        """
        result = await session.run(query, can_do_id=can_do_id)
        rec = await result.single()
        if not rec:
            return {"uid": can_do_id, "primaryTopic": "general", "level": "B1"}
        return dict(rec)

    # Pydantic schema moved to module scope (see
    # UICard/UISection/LessonUI/MasterSchema above)

    def _flatten_ui_text(self, master: Dict[str, Any]) -> str:
        ui = master.get("ui", {}) or {}
        lines: List[str] = []
        header = ui.get("header") or {}
        if header.get("title"):
            lines.append(str(header.get("title")))
        if header.get("subtitle"):
            lines.append(str(header.get("subtitle")))
        for sec in ui.get("sections", []) or []:
            title = sec.get("title")
            if title:
                lines.append(str(title))
            for card in sec.get("cards", []) or []:
                if card.get("title"):
                    lines.append(str(card.get("title")))
                body = card.get("body") or {}
                jp = body.get("jp")
                meta = body.get("meta")
                if jp:
                    lines.append(str(jp))
                if meta:
                    lines.append(str(meta))
                for b in card.get("bullets", []) or []:
                    lines.append(str(b))
        return "\n".join(lines)[:12000]

    def _extract_json_block(self, text: str) -> Optional[str]:
        """Extract JSON from AI response with repair attempts."""
        if not text:
            return None
        t = text.strip()
        
        # Prefer fenced code blocks
        if "```" in t:
            parts = [p.strip() for p in t.split("```")]
            # Filter candidates and strip language identifiers
            candidates = []
            for p in parts:
                # Remove common language identifiers
                clean = p
                for lang in ["json", "JSON", "javascript", "js"]:
                    if p.startswith(lang):
                        clean = p[len(lang):].strip()
                        break
                if clean.startswith("{") or clean.startswith("["):
                    candidates.append(clean)
            if candidates:
                # choose the largest candidate
                return max(candidates, key=len)
        
        # Fallback: find first { or [ and last matching brace/bracket
        for start_char, end_char in (("{", "}"), ("[", "]")):
            s = t.find(start_char)
            e = t.rfind(end_char)
            if s != -1 and e != -1 and e > s:
                extracted = t[s: e + 1]
                # Basic repair: try to fix common trailing comma issues
                try:
                    # Attempt parse first
                    json.loads(extracted)
                    return extracted
                except json.JSONDecodeError:
                    # Try basic repairs
                    repaired = extracted.replace(",]", "]").replace(",}", "}")
                    try:
                        json.loads(repaired)
                        logger.info("json_repair_successful", repair="trailing_commas")
                        return repaired
                    except:
                        pass
                return extracted
        return None

    async def _extract_entities_from_text(
            self, *, text_blob: str, provider: str) -> Dict[str, Any]:
        """Ask the model to extract words and grammar patterns from lesson text.

        Returns a dict {words: [...], grammarPatterns: [...]} with minimal fields.
        """
        prompt = (
            "Extract key words and grammar patterns from the lesson text below and return STRICT JSON only.\n"
            "JSON shape: {\n  \"words\": [{\"text\": string, \"kanji\": string, \"hiragana\": string}],\n"
            "  \"grammarPatterns\": [{\"pattern\": string}]\n}\n"
            "IMPORTANT: Include common Japanese particles (と, を, は, が, に, で, など) as grammar patterns.\n"
            "Include both simple particles and complex patterns (e.g., \"～と～\", \"～を～\", \"～は～です\").\n"
            "Select up to 20 words and up to 15 grammar patterns (including particles).\n"
            "Text begins:\n" + text_blob)
        try:
            reply = await self._practice.ai_chat.generate_reply(
                provider="openai" if provider == "openai" else "gemini",
                model=("gpt-4.1" if provider == "openai" else "gemini-2.5-pro"),
                messages=[{"role": "user", "content": prompt}],
                system_prompt="Return strict JSON only. No commentary.",
            )
            content = reply.get("content", "{}")
            block = self._extract_json_block(content) or content
            data = json.loads(block)
            if not isinstance(data, dict):
                raise ValueError("invalid_extraction")
            return {
                "words": data.get("words") or [],
                "grammarPatterns": data.get("grammarPatterns") or []}
        except Exception:
            return {"words": [], "grammarPatterns": []}

    def _validate_vocabulary(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validate raw word items into VocabularyEntry list.

        Accepts items with keys like orth/katakana/romaji/pos/translation.
        Returns standardized dicts {surface, reading, pos, translation}.
        Invalid entries are dropped.
        """
        validated: List[Dict[str, Any]] = []
        for w in items or []:
            try:
                surface = str(w.get("orth") or w.get("standard_orthography") or w.get("text") or "").strip()
                reading_src = str(w.get("katakana") or w.get("hiragana") or "").strip()
                reading = kata_to_hira(reading_src) if reading_src else ""
                pos = str(w.get("pos") or w.get("pos_primary") or "noun").strip()
                translation = str(w.get("translation") or "").strip()
                ve = VocabularyEntry(surface=surface, reading=reading, pos=pos, translation=translation)
                validated.append(ve.model_dump())
            except Exception as e:
                logger.debug("vocabulary_entry_invalid", error=str(e), item=w)
                continue
        return validated

    async def _resolve_words(self, graph: AsyncSession,
                             items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        for w in items or []:
            k = (str(w.get("kanji") or w.get("text") or "").strip())
            h = (str(w.get("hiragana") or "").strip())
            if not (k or h):
                continue
            variants = list({
                k, h,
                unicodedata.normalize("NFKC", k),
                unicodedata.normalize("NFKC", h),
                kata_to_hira(k), kata_to_hira(h),
                hira_to_kata(k), hira_to_kata(h),
            })
            q = (
                "MATCH (w:Word)\n"
                "WHERE ANY(x IN $vars WHERE "
                " w.standard_orthography = x OR w.reading_katakana = x OR w.romaji = x OR "
                " w.lemma = x OR w.hiragana = x OR w.kanji = x)\n"
                "RETURN elementId(w) AS elementId, w.standard_orthography AS orth, w.reading_katakana AS katakana, "
                " w.romaji AS romaji, w.pos_primary AS pos, w.translation AS translation\n"
                "LIMIT 1")
            rec = await (await graph.run(q, vars=variants)).single()
            if rec:
                d = dict(rec)
                d["source_text"] = w.get("text")
                out.append(d)
        return out

    async def _resolve_grammar(
            self, graph: AsyncSession, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        for g in items or []:
            pid = str(g.get("patternId") or "").strip()
            pat = str(g.get("pattern") or "").strip()
            if pid:
                q = "MATCH (p:GrammarPattern {id: $id}) RETURN p.id AS id, p.pattern AS pattern, p.classification AS classification LIMIT 1"
                rec = await (await graph.run(q, id=pid)).single()
            else:
                q = "MATCH (p:GrammarPattern) WHERE p.pattern = $p RETURN p.id AS id, p.pattern AS pattern, p.classification AS classification LIMIT 1"
                rec = await (await graph.run(q, p=pat)).single()
            if rec:
                out.append(dict(rec))
        return out

    def _extract_jp_tokens(self, text_blob: str) -> List[str]:
        """Extract Japanese character runs from text using centralized utility.

        Returns a deduplicated list of Japanese lexical items (1-6 chars).
        """
        return extract_japanese_runs(text_blob)

    async def _deterministic_words(
            self, graph: AsyncSession, text_blob: str) -> List[Dict[str, Any]]:
        candidates = self._extract_jp_tokens(text_blob)
        results: List[Dict[str, Any]] = []
        seen_ids: Set[str] = set()
        for tok in candidates:
            variants = list({
                tok,
                unicodedata.normalize("NFKC", tok),
                kata_to_hira(tok),
                hira_to_kata(tok),
            })
            q = (
                "MATCH (w:Word)\n"
                "WHERE ANY(x IN $vars WHERE "
                " w.standard_orthography = x OR w.reading_katakana = x OR w.romaji = x OR "
                " w.lemma = x OR w.hiragana = x OR w.kanji = x)\n"
                "RETURN elementId(w) AS elementId, w.standard_orthography AS orth, w.reading_katakana AS katakana, "
                " w.romaji AS romaji, w.pos_primary AS pos, w.translation AS translation\n"
                "LIMIT 1")
            rec = await (await graph.run(q, vars=variants)).single()
            if rec:
                d = dict(rec)
                gid = str(d.get("elementId")) if d.get(
                    "elementId") is not None else f"tok::{tok}"
                if gid in seen_ids:
                    continue
                seen_ids.add(gid)
                d["source_text"] = tok
                results.append(d)
            if len(results) >= 20:
                break
        return results

    def _pattern_matches_text(self, pattern: str, text: str, jp_tokens: Set[str]) -> bool:
        """Check if a grammar pattern matches the text using multiple strategies.
        
        Handles patterns like:
        - Direct matches: "～は～です" in text
        - Particle patterns: "～と～" where "と" appears in text
        - Single character particles: "と" appears in text
        - Partial matches: "～てもいい" matches "てもいいですか"
        """
        norm_text = unicodedata.normalize("NFKC", text)
        norm_pattern = unicodedata.normalize("NFKC", pattern)
        
        # Strategy 1: Direct substring match (for full patterns)
        if norm_pattern in norm_text:
            return True
        
        # Strategy 2: Extract meaningful characters from pattern
        # Remove placeholder markers (～, 〜) and whitespace
        pattern_chars = ''.join(c for c in norm_pattern if c not in ['～', '〜', ' ', '\n', '\t'])
        
        # For single-character patterns (particles), check if they appear in text
        if len(pattern_chars) == 1:
            return pattern_chars in norm_text
        
        # For multi-character patterns, extract Japanese characters
        jp_chars = ''.join(c for c in pattern_chars if '\u3040' <= c <= '\u30FF' or '\u4E00' <= c <= '\u9FAF')
        
        if jp_chars and len(jp_chars) >= 1:
            # Always check if the core pattern (without placeholders) appears as substring
            # This handles cases like "～てもいい" matching "てもいいですか"
            if jp_chars in norm_text:
                return True
            
            # For short patterns (≤3 chars), also check if all individual chars appear
            # (helps with flexible ordering)
            if len(jp_chars) <= 3:
                return all(char in norm_text for char in jp_chars)
            else:
                # For longer patterns, check if significant substrings appear
                # Check 2-3 character subsequences that might appear in text
                for start in range(len(jp_chars) - 1):
                    for end in range(start + 2, min(start + 4, len(jp_chars) + 1)):
                        substr = jp_chars[start:end]
                        if len(substr) >= 2 and substr in norm_text:
                            return True
                # Also check if any token from the text matches the pattern
                return any(token in jp_chars or jp_chars in token for token in jp_tokens if len(token) >= 2)
        
        return False

    async def _deterministic_grammar(
            self, graph: AsyncSession, text_blob: str) -> List[Dict[str, Any]]:
        """Deterministically extract grammar patterns from text using improved token-aware pattern matching."""
        norm = unicodedata.normalize("NFKC", text_blob or "")
        # Extract Japanese tokens for better matching
        jp_tokens = extract_japanese_runs(norm)
        jp_text_set = set(jp_tokens)
        
        # Fetch patterns - increased limit for better coverage
        q = "MATCH (p:GrammarPattern) RETURN p.id AS id, p.pattern AS pattern, p.classification AS classification LIMIT 2000"
        cursor = await graph.run(q)
        out: List[Dict[str, Any]] = []
        seen_ids: Set[str] = set()
        
        async for rec in cursor:
            rid = rec.get("id")
            pat = rec.get("pattern")
            if not pat or rid in seen_ids:
                continue
            
            # Use improved pattern matching
            if self._pattern_matches_text(pat, norm, jp_text_set):
                out.append({"id": rid, "pattern": pat, "classification": rec.get("classification")})
                seen_ids.add(rid)
                if len(out) >= 20:  # Increased from 10
                    break
        
        logger.info("deterministic_grammar_extracted", count=len(out))
        return out

    def _map_cando_level_to_numeric(self, level_str: Optional[str]) -> int:
        s = (level_str or "").strip().upper()
        mapping = {"A1": 1, "A2": 2, "B1": 3, "B2": 4, "C1": 5, "C2": 6}
        return mapping.get(s, 3)

    async def _fetch_lesson_package(
            self, pg: PgSession, can_do_id: str) -> Optional[Dict[str, Any]]:
        """Return the latest stored lesson package for a given can_do_id from Postgres.

        The package aggregates lesson_plan, exercises, manifest, dialogs from the highest version.
        """
        # Get lesson id
        res = await pg.execute(text("SELECT id FROM lessons WHERE can_do_id = :can LIMIT 1"), {"can": can_do_id})
        row = res.first()
        if not row:
            return None
        lesson_id = int(row[0])
        # Get latest version payload
        res2 = await pg.execute(
            text(
                "SELECT version, lesson_plan, exercises, manifest, dialogs "
                "FROM lesson_versions WHERE lesson_id = :lid ORDER BY version DESC LIMIT 1"
            ),
            {"lid": lesson_id},
        )
        row2 = res2.first()
        if not row2:
            return None
        version, lesson_plan, exercises, manifest, dialogs = row2
        return {
            "can_do_id": can_do_id,
            "lesson_id": lesson_id,
            "version": int(version),
            "lesson_plan": lesson_plan,
            "exercises": exercises,
            "manifest": manifest,
            "dialogs": dialogs,
        }

    def _validate_topic_relevance(
        self, 
        master: MasterSchema, 
        expected_topic: str, 
        can_do_id: str
    ) -> None:
        """Validate that lesson content is relevant to the topic.
        
        Raises ValueError if generic/mismatched content is detected.
        """
        # Check for generic station/travel content
        generic_station_indicators = [
            "駅での案内所", "道を聞く", "乗り換えの説明"
        ]
        
        # Only allow these if topic is actually about travel/transportation
        travel_keywords = ["旅行", "交通", "Travel", "Transportation"]
        topic_is_travel = any(kw in expected_topic for kw in travel_keywords)
        
        if not topic_is_travel:
            for section in master.ui.sections:
                for card in section.cards:
                    if card.body:
                        body_jp = str(card.body.get("jp", ""))
                        
                        # Check for generic content
                        if any(ind in body_jp for ind in generic_station_indicators):
                            logger.error(
                                "master_lesson_generic_content_detected",
                                can_do_id=can_do_id,
                                expected_topic=expected_topic,
                                section_type=section.type,
                                card_id=card.id)
                            raise ValueError(
                                f"Generated lesson contains generic station/travel content "
                                f"but topic is '{expected_topic}', not travel-related. "
                                f"Content must match the topic."
                            )

    # ========== TWO-STAGE GENERATION METHODS ==========

    async def _generate_simple_content(
        self,
        *,
        can_do_id: str,
        topic: str,
        level: str,
        provider: str = "openai",
        model: str = "gpt-5",
        timeout: int = 180,
        meta_extra: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Stage 1: Generate lesson content structure.
        Uses powerful model (GPT-5) for creative content generation.

        Returns plain Japanese text without multilingual structure.
        Stage 2 will enhance these with romaji, furigana, and translation.
        """
        # Compose extra context
        meta_lines: List[str] = []
        if meta_extra:
            if meta_extra.get("type"):
                meta_lines.append(f"type={meta_extra.get('type')}")
            if meta_extra.get("skillDomain"):
                meta_lines.append(f"skillDomain={meta_extra.get('skillDomain')}")
            if meta_extra.get("exampleSentence"):
                meta_lines.append(f"example_sentence={meta_extra.get('exampleSentence')}")
            if meta_extra.get("description"):
                meta_lines.append(f"descriptor={meta_extra.get('description')}")

        from app.models.multilingual import Stage1Content
        stage1_schema = json.dumps(Stage1Content.model_json_schema(), ensure_ascii=False)
        prompt = f"""
You are an expert Japanese language tutor creating a comprehensive lesson package.

Task: Create a COMPLETE, DETAILED lesson for topic "{topic}" at level {level}".

STRICT JSON SCHEMA REQUIREMENTS:
Return ONLY JSON conforming to this JSON Schema (no extra properties):
{stage1_schema}

Rules:
- Do not add properties not present in the schema
- Satisfy all min/max item constraints
- Keep sentences short and level-appropriate

Output: Start with {{ and end with }}. No markdown.
""".strip()

        messages = [{"role": "user", "content": prompt}]
        
        result = await self._practice.ai_chat.generate_reply(
            messages=messages,
            system_prompt="You are a strict JSON generator. Output ONLY valid JSON.",
            provider=provider,
            model=model,
            timeout=timeout
        )
        
        content = result.get("content", "")
        
        # Log the raw response for debugging
        logger.debug(
            "stage1_ai_response_received",
            can_do_id=can_do_id,
            response_length=len(content),
            response_preview=content[:500] if len(content) > 500 else content
        )
        
        # Use robust JSON extraction
        try:
            json_str = extract_balanced_json(content)
        except ValueError as e:
            logger.error(
                "stage1_json_extraction_failed",
                can_do_id=can_do_id,
                error=str(e),
                full_response=content[:2000]  # Log first 2000 chars
            )
            raise
        
        # Use Pydantic for robust validation (with a targeted retry if reading is too short)
        try:
            stage1_data = Stage1Content.model_validate_json(json_str)
            out = stage1_data.model_dump()
            # Align objective to CanDo description when available
            try:
                if meta_extra:
                    desired_obj = (
                        (meta_extra.get("descriptionEn") or "").strip()
                        or (meta_extra.get("description") or "").strip()
                        or (meta_extra.get("descriptionJa") or "").strip()
                    )
                    if desired_obj:
                        out["objective"] = desired_obj
            except Exception:
                pass
            # Ensure topic is set from the resolved CanDo topic
            try:
                if topic:
                    out["topic"] = topic
            except Exception:
                pass
            # Surface meta for inspection
            try:
                out.setdefault("__meta", {})
                out["__meta"].update(meta_extra or {})
            except Exception:
                pass
            return out
        except ValidationError as ve:
            # If the only blocking error is reading.text too short, ask the model to expand it once
            errors = ve.errors()
            need_expand = any(
                (e.get("loc") == ("reading", "text") or list(e.get("loc", [])) == ["reading", "text"]) and
                ("string_too_short" in str(e.get("type") or "") or "min_length" in str(e))
                for e in errors
            )
            if need_expand:
                repair_prompt = (
                    "Take the following JSON and fix ONLY reading.text by expanding it to at least 250 Japanese characters. "
                    "Keep topic, level, and all other fields unchanged. Return strict JSON with the SAME shape.\n\n" + json_str
                )
                repair = await self._practice.ai_chat.generate_reply(
                    messages=[{"role": "user", "content": repair_prompt}],
                    system_prompt="You are a strict JSON editor. Output ONLY valid JSON.",
                    provider=provider,
                    model=model,
                    timeout=min(timeout, 60),
                )
                repaired_block = extract_balanced_json(repair.get("content", ""))
                stage1_data = Stage1Content.model_validate_json(repaired_block)
                out2 = stage1_data.model_dump()
                try:
                    if meta_extra:
                        desired_obj = (
                            (meta_extra.get("descriptionEn") or "").strip()
                            or (meta_extra.get("description") or "").strip()
                            or (meta_extra.get("descriptionJa") or "").strip()
                        )
                        if desired_obj:
                            out2["objective"] = desired_obj
                except Exception:
                    pass
                try:
                    if topic:
                        out2["topic"] = topic
                except Exception:
                    pass
                try:
                    out2.setdefault("__meta", {})
                    out2["__meta"].update(meta_extra or {})
                except Exception:
                    pass
                return out2
            # otherwise, bubble up
            raise

    async def _enhance_section_with_multilingual(
        self,
        section_name: str,
        section_data: Any,
        provider: str = "openai",
        model: str = "gpt-4o",
        timeout: int = 60,
        max_retries: int = 1
    ) -> Dict[str, Any]:
        """
        Stage 2: Convert simple Japanese text to multilingual JapaneseText format.
        Uses reliable model (GPT-4.1) for JSON structuring.
        Processes items one-at-a-time for maximum reliability.
        """
        # Stronger system prompt
        system_prompt = """You are a strict JSON generator. Rules:
1. Output ONLY JSON - no explanations, no markdown, no commentary
2. Do NOT add text before or after the JSON
3. Do NOT wrap JSON in code blocks
4. Start immediately with {{ or [
5. End immediately with }} or ]"""
        
        # Hard per-section time budget (seconds)
        section_deadline = time.perf_counter() + 30.0
        eff_timeout = min(timeout, 30)
        for attempt in range(max_retries):
            if time.perf_counter() > section_deadline:
                # Time budget exceeded → deterministic fallback
                if section_name == "reading":
                    jt = section_data.get("text", "") if isinstance(section_data, dict) else ""
                    fb = {
                        "title": fallback_multilingual(section_data.get('title', '') if isinstance(section_data, dict) else ""),
                        "content": fallback_multilingual(jt),
                        "comprehension": []
                    }
                    return {"success": True, "data": fb, "fallback": True}
                if section_name == "dialogue":
                    turns = section_data if isinstance(section_data, list) else []
                    return {"success": True, "data": [
                        {"speaker": (t.get("speaker") if isinstance(t, dict) else ""), "japanese": fallback_multilingual((t.get("text") if isinstance(t, dict) else ""))}
                        for t in turns
                    ], "fallback": True}
                if section_name == "grammar":
                    points = section_data if isinstance(section_data, list) else []
                    return {"success": True, "data": [
                        {"pattern": (p.get("pattern") if isinstance(p, dict) else ""), "explanation": (p.get("explanation") if isinstance(p, dict) else ""), "examples": [fallback_multilingual(x) for x in (p.get("examples") or [])[:2]]}
                        for p in points
                    ], "fallback": True}
                if section_name == "culture":
                    notes = section_data if isinstance(section_data, list) else []
                    return {"success": True, "data": [
                        {"title": (n.get("title") if isinstance(n, dict) else "Cultural Note"), "body": fallback_multilingual((n.get("content") if isinstance(n, dict) else ""))}
                        for n in notes
                    ], "fallback": True}
            try:
                if section_name == "reading":
                    japanese_text = section_data.get("text", "")
                    from app.models.multilingual import ReadingSection
                    schema = json.dumps(ReadingSection.model_json_schema(), ensure_ascii=False)
                    prompt = f"""
Convert this Japanese reading to multilingual JSON.

Inputs:
- Title: {section_data.get('title', '')}
- Text: {japanese_text}

STRICT JSON SCHEMA (no extra properties):
{schema}

Output: JSON only. Start with {{ or [ and end with }} or ].
"""
                    
                    result = await self._practice.ai_chat.generate_reply(
                        messages=[{"role": "user", "content": prompt}],
                        system_prompt=system_prompt,
                        provider=provider,
                        model=model,
                        timeout=eff_timeout
                    )
                    
                    content = result.get("content", "")
                    json_str = extract_balanced_json(content)
                    try:
                        reading = ReadingSection.model_validate_json(json_str)
                        return {"success": True, "data": reading.model_dump()}
                    except ValidationError as e:
                        # Fallback: deterministic multilingual from Stage 1
                        fb = {
                            "title": fallback_multilingual(section_data.get('title', '')),
                            "content": fallback_multilingual(japanese_text),
                            "comprehension": []
                        }
                        return {"success": True, "data": fb, "fallback": True, "errors": e.errors()[:3]}
                
                elif section_name == "dialogue":
                    # Process ALL TURNS IN BATCH for better performance
                    dialogue_turns = section_data if isinstance(section_data, list) else []
                    
                    if not dialogue_turns:
                        return {"success": True, "data": []}
                    
                    # Create batch prompt for all turns
                    turns_data = []
                    for turn in dialogue_turns:
                        turns_data.append({
                            "speaker": turn.get("speaker", ""),
                            "text": turn.get("text", "")
                        })
                    
                    from app.models.multilingual import Stage2DialogueTurnList
                    schema = json.dumps(Stage2DialogueTurnList.model_json_schema(), ensure_ascii=False)
                    prompt = f"""
Convert all dialogue turns to multilingual format.

Turns: {json.dumps(turns_data, ensure_ascii=False)}

STRICT JSON SCHEMA (no extra properties):
{schema}

Output: JSON only. Start with {{ or [ and end with }} or ].
"""
                    
                    result = await self._practice.ai_chat.generate_reply(
                        messages=[{"role": "user", "content": prompt}],
                        system_prompt=system_prompt,
                        provider=provider,
                        model=model,
                        timeout=eff_timeout
                    )
                    
                    content = result.get("content", "")
                    json_str = extract_balanced_json(content)
                    try:
                        turns_list = Stage2DialogueTurnList.model_validate_json(json_str)
                        return {"success": True, "data": turns_list.turns}
                    except ValidationError:
                        # Per-item retry: attempt single-turn conversion before fallback
                        per_items: List[Dict[str, Any]] = []
                    for turn in dialogue_turns:
                        speaker = turn.get("speaker", "")
                        text = turn.get("text", "")
                        single_prompt = f"""Convert to multilingual format.

Speaker: {speaker}
Japanese: {text}

Output JSON:
{{
  "speaker": "{speaker}",
  "japanese": {{
    "kanji": "{text}",
    "romaji": "romanized",
    "furigana": [{{"text": "word", "ruby": "reading"}}],
    "translation": "English"
  }}
}}
"""
                        try:
                            r = await self._practice.ai_chat.generate_reply(
                                messages=[{"role": "user", "content": single_prompt}],
                                system_prompt=system_prompt,
                                provider=provider,
                                model=model,
                                timeout=min(eff_timeout, 5)
                            )
                            c2 = r.get("content", "")
                            j2 = extract_balanced_json(c2)
                            t2 = Stage2DialogueTurn.model_validate_json(j2)
                            per_items.append(t2.model_dump())
                        except Exception:
                            per_items.append({
                                "speaker": speaker,
                                "japanese": fallback_multilingual(text)
                            })
                        return {"success": True, "data": per_items, "fallback": True}
                
                elif section_name == "grammar":
                    # Process ALL GRAMMAR POINTS IN BATCH for better performance
                    grammar_points = section_data if isinstance(section_data, list) else []

                    if not grammar_points:
                        return {"success": True, "data": []}

                    # Create batch prompt for all grammar points
                    points_data = []
                    for point in grammar_points:
                        points_data.append({
                            "pattern": point.get("pattern", ""),
                            "explanation": point.get("explanation", ""),
                            "examples": point.get("examples", [])
                        })

                    from app.models.multilingual import GrammarPointList
                    schema = json.dumps(GrammarPointList.model_json_schema(), ensure_ascii=False)
                    prompt = f"""
Convert all grammar points to multilingual format.

Grammar points: {json.dumps(points_data, ensure_ascii=False)}

STRICT JSON SCHEMA (no extra properties):
{schema}

Output: JSON only. Start with {{ or [ and end with }} or ].
"""
                    
                    result = await self._practice.ai_chat.generate_reply(
                        messages=[{"role": "user", "content": prompt}],
                        system_prompt=system_prompt,
                        provider=provider,
                        model=model,
                        timeout=timeout
                    )
                    
                    content = result.get("content", "")
                    json_str = extract_balanced_json(content)
                    try:
                        points_list = GrammarPointList.model_validate_json(json_str)
                        return {"success": True, "data": points_list.points}
                    except ValidationError:
                        # Per-item retry for each grammar point
                        per_points: List[Dict[str, Any]] = []
                        for point in grammar_points:
                            examples_str = "\n".join(f"- {ex}" for ex in point.get("examples", []))
                            single_prompt = f"""Convert grammar point to multilingual format.

Pattern: {point.get('pattern', '')}
Explanation: {point.get('explanation', '')}
Examples:
{examples_str}

Output JSON:
{{
  "pattern": "{point.get('pattern', '')}",
  "explanation": "{point.get('explanation', '')}",
  "examples": [{{"kanji":"example","romaji":"romanized","furigana":[{{"text":"exa","ruby":"..."}}],"translation":"English"}}]
}}
"""
                            try:
                                r = await self._practice.ai_chat.generate_reply(
                                    messages=[{"role": "user", "content": single_prompt}],
                                    system_prompt=system_prompt,
                                    provider=provider,
                                    model=model,
                                    timeout=timeout
                                )
                                c2 = r.get("content", "")
                                j2 = extract_balanced_json(c2)
                                gp = GrammarPoint.model_validate_json(j2)
                                per_points.append(gp.model_dump())
                            except Exception:
                                exs = point.get("examples", [])
                                per_points.append({
                                    "pattern": point.get("pattern", ""),
                                    "explanation": point.get("explanation", ""),
                                    "examples": [fallback_multilingual(x) for x in exs[:2]]
                                })
                        return {"success": True, "data": per_points, "fallback": True}
                
                elif section_name == "culture":
                    # Process ALL CULTURE NOTES IN BATCH
                    notes = section_data if isinstance(section_data, list) else []
                    if not notes:
                        return {"success": True, "data": []}
                    
                    notes_data = []
                    for note in notes:
                        notes_data.append({
                            "title": note.get("title", ""),
                            "bodyJP": note.get("content", "")
                        })
                    
                    from app.models.multilingual import CultureNoteList
                    schema = json.dumps(CultureNoteList.model_json_schema(), ensure_ascii=False)
                    prompt = f"""
Convert all culture notes to multilingual JSON.

Notes: {json.dumps(notes_data, ensure_ascii=False)}

STRICT JSON SCHEMA (no extra properties):
{schema}

Output: JSON only. Start with {{ or [ and end with }} or ].
"""
                    
                    result = await self._practice.ai_chat.generate_reply(
                        messages=[{"role": "user", "content": prompt}],
                        system_prompt=system_prompt,
                        provider=provider,
                        model=model,
                        timeout=timeout
                    )
                    content = result.get("content", "")
                    json_str = extract_balanced_json(content)
                    try:
                        notes_list = CultureNoteList.model_validate_json(json_str)
                        return {"success": True, "data": notes_list.notes}
                    except ValidationError:
                        per_notes: List[Dict[str, Any]] = []
                        for n in notes:
                            single_prompt = f"""Convert culture note to multilingual JSON.

Title: {n.get('title','')}
Body: {n.get('content','')}

Output JSON:
{{"title":"{n.get('title','')}","body":{{"kanji":"...","romaji":"...","furigana":[{{"text":"...","ruby":"..."}}],"translation":"..."}}}}
"""
                            try:
                                r = await self._practice.ai_chat.generate_reply(
                                    messages=[{"role": "user", "content": single_prompt}],
                                    system_prompt=system_prompt,
                                    provider=provider,
                                    model=model,
                                    timeout=timeout
                                )
                                c2 = r.get("content", "")
                                j2 = extract_balanced_json(c2)
                                cn = CultureNoteML.model_validate_json(j2)
                                per_notes.append(cn.model_dump())
                            except Exception:
                                per_notes.append({
                                    "title": n.get("title", "Cultural Note"),
                                    "body": fallback_multilingual(n.get("content", ""))
                                })
                        return {"success": True, "data": per_notes, "fallback": True}
                
                else:
                    # For other sections, return as-is
                    return {"success": True, "data": section_data}
                    
            except ValidationError as e:
                error_details = e.errors()
                if attempt == max_retries - 1:
                    return {
                        "success": False,
                        "error": f"Validation failed: {len(error_details)} errors",
                        "details": error_details[:3]
                    }
                await asyncio.sleep(1)
                continue
            
            except json.JSONDecodeError as e:
                if attempt == max_retries - 1:
                    return {
                        "success": False,
                        "error": f"JSON parse error: {str(e)[:80]}"
                    }
                await asyncio.sleep(1)
                continue
            
            except Exception as e:
                return {"success": False, "error": str(e)[:80]}

    def _merge_enhanced_sections(
        self,
        simple_content: Dict[str, Any],
        enhanced_sections: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Merge Stage 1 simple content with Stage 2 enhanced sections.
        Creates final master lesson structure compatible with frontend.
        """
        lesson_id = str(uuid4())
        
        # Build UI sections
        ui_sections = []
        
        # Lesson Plan section
        if "lessonPlan" in simple_content:
            plan_cards = []
            for idx, step in enumerate(simple_content["lessonPlan"]):
                plan_cards.append({
                    "id": str(uuid4()),
                    "kind": "text",
                    "title": step.get("step", f"Step {idx+1}"),
                    "body": {
                        "meta": f"**Teacher Notes:** {step.get('teacherNotes', '')}\n\n**Student Task:** {step.get('studentTask', '')}"
                    }
                })
            ui_sections.append({
                "id": "lessonPlan",
                "type": "teach",
                "title": "Lesson Plan",
                "cards": plan_cards
            })
        
        # Reading section (enhanced preferred; fallback to Stage 1)
        if "reading" in enhanced_sections:
            reading_data = enhanced_sections["reading"]
            ui_sections.append({
                "id": "reading",
                "type": "reading",
                "title": "Reading",
                "cards": [{
                    "id": str(uuid4()),
                    "kind": "reading",
                    # Avoid duplicate title rendering; ReadingCard shows its own title
                    "reading": reading_data
                }]
            })
        elif "reading" in simple_content:
            # Fallback simple reading
            sr = simple_content.get("reading", {})
            # Dedupe any repeated sentences in Stage 1 fallback
            try:
                if isinstance(sr, dict) and sr.get("text"):
                    sr["text"] = dedupe_sentences_jp(str(sr.get("text")))
            except Exception:
                pass
            ui_sections.append({
                "id": "reading",
                "type": "reading",
                "title": "Reading",
                "cards": [{
                    "id": str(uuid4()),
                    "kind": "text",
                    "title": sr.get("title", "Reading"),
                    "body": {"jp": sr.get("text", "")}
                }]
            })
        
        # Dialogue section (enhanced)
        if "dialogue" in enhanced_sections:
            dialogue_turns = enhanced_sections["dialogue"]
            ui_sections.append({
                "id": "dialogue",
                "type": "dialogue",
                "title": "Dialogue",
                "cards": [{
                    "id": str(uuid4()),
                    "kind": "dialogue",
                    "title": "Conversation Practice",
                    "dialogue_turns": dialogue_turns
                }]
            })
        
        # Grammar section (enhanced)
        if "grammar" in enhanced_sections:
            grammar_cards = []
            for point in enhanced_sections["grammar"]:
                grammar_cards.append({
                    "id": str(uuid4()),
                    "kind": "text",
                    "title": point.get("pattern", "Grammar Point"),
                    "body": {"meta": point.get("explanation", "")},
                    "bullets": point.get("examples", [])
                })
            ui_sections.append({
                "id": "grammar",
                "type": "teach",
                "title": "Grammar Points",
                "cards": grammar_cards
            })
        
        # Practice section (supports rich Stage 1 shapes)
        if "practice" in simple_content:
            practice_cards = []
            for exercise in simple_content["practice"]:
                etype = exercise.get("type", "Exercise").title()
                instruction = exercise.get("instruction", "")
                body_lines = [f"**Instructions:** {instruction}"]
                if "content" in exercise and exercise.get("content"):
                    body_lines.append(str(exercise.get("content")))
                if exercise.get("items"):
                    # Render items as bullets
                    try:
                        items = exercise.get("items", [])[:5]
                        body_lines.append("\n" + "\n".join([
                            f"- {it.get('prompt', '')}"
                            for it in items
                        ]))
                    except Exception:
                        pass
                if exercise.get("pairs"):
                    try:
                        pairs = exercise.get("pairs", [])[:8]
                        body_lines.append("\nPairs:\n" + "\n".join([
                            f"- {p.get('jp','')} -> {p.get('en','')}"
                            for p in pairs
                        ]))
                    except Exception:
                        pass
                practice_cards.append({
                    "id": str(uuid4()),
                    "kind": "text",
                    "title": etype,
                    "body": {"meta": "\n\n".join(body_lines)}
                })
            ui_sections.append({
                "id": "practice",
                "type": "practice",
                "title": "Practice",
                "cards": practice_cards
            })
        
        # Culture section (prefer Stage 2 multilingual; fallback to Stage 1)
        if "culture" in enhanced_sections or "culture" in simple_content:
            culture_cards = []
            if "culture" in enhanced_sections:
                for note in enhanced_sections["culture"]:
                    culture_cards.append({
                        "id": str(uuid4()),
                        "kind": "text",
                        "title": note.get("title", "Cultural Note"),
                        "body": {"meta": note.get("body")}
                    })
            else:
                for note in simple_content.get("culture", []):
                    culture_cards.append({
                        "id": str(uuid4()),
                        "kind": "text",
                        "title": note.get("title", "Cultural Note"),
                        "body": {"meta": note.get("content", "")}
                    })
            ui_sections.append({
                "id": "culture",
                "type": "teach",
                "title": "Culture",
                "cards": culture_cards
            })
        
        # Optional Overview section (high-level CanDo description)
        overview_cards = []
        try:
            desc = simple_content.get("objective") or ""
            topic = simple_content.get("topic") or ""
            if topic or desc:
                overview_cards.append({
                    "id": str(uuid4()),
                    "kind": "text",
                    "title": topic or "Overview",
                    "body": {"meta": desc or "This lesson compiles reading, dialogue, grammar and practice for the CanDo."}
                })
        except Exception:
            pass
        if overview_cards:
            ui_sections.insert(0, {
                "id": "overview",
                "type": "intro",
                "title": "Overview",
                "cards": overview_cards
            })
        
        # Build final master lesson
        master = {
            "uiVersion": 2,
            "lessonId": lesson_id,
            "canDoId": simple_content.get("canDoId", "unknown"),
            "originalLevel": simple_content.get("originalLevel", 3),
                "metadata": {
                "topic": simple_content.get("topic", ""),
                    "languageCode": "ja",
                "multilingualVersion": True,
                    "createdAt": int(time.time()),
                "estimatedDurationMin": 25,
                "tags": [],
                "stage2EnhancedMap": {
                    "reading": bool(enhanced_sections.get("reading")),
                    "dialogue": bool(enhanced_sections.get("dialogue")),
                    "grammar": bool(enhanced_sections.get("grammar")),
                    "culture": bool(enhanced_sections.get("culture")),
                }
            },
            "learningObjectives": [],
                "ui": {
                "header": {
                    "title": simple_content.get("topic", "Japanese Lesson"),
                    "subtitle": "Complete lesson package",
                    "chips": ["objective", "level", "topic"]
                },
                "sections": ui_sections,
                    "gallery": []
                },
                "exercises": [],
                "extractedEntities": {"words": [], "grammarPatterns": []},
                "readability": {"jlptEstimate": "N5", "metrics": {"chars": 0, "sentences": 0}},
                "pdf": {"renderTemplate": "default-a4", "assetPaths": []}
            }

        return master

    # ========== END TWO-STAGE METHODS ==========

    async def _generate_master_lesson_twostage_with_fallback(
        self,
        *,
        can_do_id: str,
        topic: str,
        original_level_str: Optional[str],
        original_level_num: int,
        meta_extra: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Generate master lesson using two-stage approach with fallback strategies.
        
        Fallback Strategy:
        1. Try two-stage with GPT-5 + GPT-4.1
        2. If Stage 2 fails for all sections, retry with GPT-4o-mini
        3. If still fails, return partial lesson with Stage 1 content only
        """
        start_total = time.perf_counter()
        
        logger.info(
            "twostage_generation_started",
            can_do_id=can_do_id,
            topic=topic,
            level=original_level_str
        )
        
        try:
            # STAGE 1: Generate simple content using powerful model
            start_stage1 = time.perf_counter()
            simple_content = await self._generate_simple_content(
                can_do_id=can_do_id,
                topic=topic,
                level=original_level_str or f"Level {original_level_num}",
                provider="openai",
                model="gpt-4o",
                timeout=max(120, int(getattr(settings, "AI_STAGE1_TIMEOUT_SECONDS", 180))),
                meta_extra=meta_extra
            )
            
            # Add metadata to simple_content for merging
            simple_content["canDoId"] = can_do_id
            simple_content["originalLevel"] = original_level_num
            simple_content["topic"] = topic
            # Pass-through meta extra for overview/metadata enrichment downstream
            simple_content["__meta_extra"] = meta_extra or {}
            
            stage1_duration = time.perf_counter() - start_stage1
            
            logger.info(
                "stage1_completed",
                duration=round(stage1_duration, 2),
                sections_count=len(simple_content)
            )
            
            # STAGE 2: Enhance sections with multilingual structure (with fallback)
            # Force OpenAI gpt-4o for structured JSON unless overridden in settings
            stage2_model = "gpt-4o"
            stage2_attempts = 0
            max_stage2_attempts = 2
            enhanced_sections = {}
            
            while stage2_attempts < max_stage2_attempts and len(enhanced_sections) == 0:
                stage2_attempts += 1
                start_stage2 = time.perf_counter()
                section_errors = []
                
                # Process all sections in parallel for better performance
                tasks = []
                section_names = []
                
                for section_name in ["reading", "dialogue", "grammar", "culture"]:
                    if section_name in simple_content:
                        # Check cache first
                        try:
                            cache_key = json.dumps({
                                "k": [can_do_id, topic, section_name],
                                "d": simple_content[section_name]
                            }, ensure_ascii=False, sort_keys=True)
                        except Exception:
                            cache_key = f"{can_do_id}:{topic}:{section_name}:{hash(str(simple_content[section_name]))}"
                        cached = self._stage2_cache_get(cache_key)
                        if cached is not None:
                            enhanced_sections[section_name] = cached
                            continue
                        task = self._enhance_section_with_multilingual(
                            section_name=section_name,
                            section_data=simple_content[section_name],
                            provider="openai",
                            model=stage2_model,
                            timeout=settings.AI_STAGE2_TIMEOUT_SECONDS
                        )
                        tasks.append((task, cache_key, section_name))
                
                # Execute all section enhancements in parallel
                if tasks:
                    results = await asyncio.gather(*[t[0] for t in tasks], return_exceptions=True)
                    
                    for i, result in enumerate(results):
                        cache_key = tasks[i][1]
                        section_name = tasks[i][2]
                        
                        if isinstance(result, Exception):
                            error_msg = str(result)
                            section_errors.append(f"{section_name}: {error_msg}")
                            logger.warning(
                                "section_enhancement_failed",
                                section=section_name,
                                error=error_msg,
                                attempt=stage2_attempts,
                                model=stage2_model
                            )
                        elif result.get("success"):
                            enhanced_sections[section_name] = result["data"]
                            # cache successful result
                            try:
                                self._stage2_cache_set(cache_key, result["data"])
                            except Exception:
                                pass
                        else:
                            error_msg = result.get("error", "Unknown error")
                            section_errors.append(f"{section_name}: {error_msg}")
                # Note: detailed per-section errors are already logged above
                
                stage2_duration = time.perf_counter() - start_stage2
                
                # If all sections failed and we have attempts left, try fallback model
                if len(enhanced_sections) == 0 and stage2_attempts < max_stage2_attempts:
                    logger.warning(
                        "stage2_all_sections_failed_retrying_with_fallback",
                        attempt=stage2_attempts,
                        fallback_model="gpt-4o-mini"
                    )
                    stage2_model = "gpt-4o-mini"  # Fallback to more reliable model
                    enhanced_sections = {}  # Reset for retry
                else:
                    logger.info(
                        "stage2_completed",
                        sections_succeeded=len(enhanced_sections),
                        sections_total=3,
                        duration=round(stage2_duration, 2),
                        attempt=stage2_attempts,
                        model=stage2_model
                    )
                    break
            
            # If still no sections enhanced, return partial lesson with Stage 1 only
            if len(enhanced_sections) == 0:
                logger.warning(
                    "stage2_all_attempts_failed_returning_partial",
                    can_do_id=can_do_id,
                    errors="; ".join(section_errors)
                )
                # Return lesson with Stage 1 content only (no multilingual enhancement)
                # This is still a valid lesson, just without furigana/romaji/translation
            
            # MERGE: Combine into final master lesson
            master = self._merge_enhanced_sections(simple_content, enhanced_sections)
            
            total_duration = time.perf_counter() - start_total

            logger.info(
                "twostage_generation_completed",
                success=True,
                total_duration=round(total_duration, 2),
                stage1_duration=round(stage1_duration, 2),
                stage2_duration=round(stage2_duration, 2),
                sections_enhanced=len(enhanced_sections),
                partial_success=len(enhanced_sections) < 3
            )
            
            return master
            
        except ValidationError as e:
            logger.error(
                "twostage_pydantic_validation_failed",
                can_do_id=can_do_id,
                topic=topic,
                errors=e.errors()
            )
            raise ValueError(
                f"AI generated lesson with invalid structure for {can_do_id}. "
                f"Validation errors: {len(e.errors())}. Please retry."
            ) from e
        except json.JSONDecodeError as e:
            logger.error(
                "twostage_json_parse_failed",
                can_do_id=can_do_id,
                topic=topic,
                error=str(e)
            )
            raise ValueError(
                f"AI generated invalid JSON for lesson {can_do_id}. "
                f"Topic: {topic}. Please retry."
            ) from e
        except Exception as e:
            logger.error(
                "twostage_generation_failed",
                can_do_id=can_do_id,
                topic=topic,
                error=str(e)
            )
            raise ValueError(
                f"Failed to generate lesson for {can_do_id}. "
                f"Topic: {topic}. Error: {str(e)}"
            ) from e

    async def _generate_master_lesson(
        self,
        *,
        can_do_id: str,
        topic: str,
        original_level_str: Optional[str],
        provider: str,
        model: str,
        timeout: int,
        meta_extra: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Main entry point for master lesson generation.
        
        Routes to two-stage or legacy approach based on feature flag.
        Two-stage achieves 100% success rate vs 0% with legacy single-stage.
        """
        original_level_num = self._map_cando_level_to_numeric(original_level_str)
        
        # Route based on feature flag
        if settings.USE_TWOSTAGE_GENERATION:
            logger.info(
                "using_twostage_generation",
                can_do_id=can_do_id,
                feature_flag_enabled=True
            )
            return await self._generate_master_lesson_twostage_with_fallback(
                can_do_id=can_do_id,
                topic=topic,
                original_level_str=original_level_str,
                original_level_num=original_level_num,
                meta_extra=meta_extra
            )
        else:
            logger.warning(
                "using_legacy_single_stage_generation",
                can_do_id=can_do_id,
                feature_flag_enabled=False,
                note="Legacy mode has 0% success rate - consider enabling two-stage"
            )
            # Fallback to legacy single-stage approach (low success rate)
            # This is kept for backward compatibility only
            raise NotImplementedError(
                "Legacy single-stage generation is deprecated. "
                "Please enable USE_TWOSTAGE_GENERATION in config. "
                "Two-stage achieves 100% success vs 0% with legacy approach."
            )

    async def start_lesson(
        self,
        *,
        graph: AsyncSession,
        pg: PgSession,
        can_do_id: str,
        phase: Optional[str] = None,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[int] = None,
        learner_level: Optional[int] = None,
    ) -> Dict[str, Any]:
        from app.core.config import settings
        
        # Use defaults if not specified
        provider = provider or settings.CANDO_AI_PROVIDER
        timeout = timeout or settings.AI_REQUEST_TIMEOUT_SECONDS
        
        # Smart model selection
        if not model:
            if provider == "openai":
                model = settings.CANDO_AI_MODEL
            else:
                model = "gemini-2.5-flash"  # Fast Gemini by default
        
        logger.info(
            "start_lesson_begin",
            can_do_id=can_do_id,
            phase=phase,
            level=learner_level,
            provider=provider,
            model=model,
            timeout=timeout)
        start_time = time.time()

        # Check if there's an existing active session for this can_do_id
        logger.debug("checking_for_existing_session", can_do_id=can_do_id)
        try:
            result = await pg.execute(
                text(
                    "SELECT id, can_do_id, phase, completed_count, scenario_json, master_json, variant_json, package_json, expires_at "
                    "FROM lesson_sessions WHERE can_do_id = :can_do_id AND expires_at > NOW() "
                    "ORDER BY created_at DESC LIMIT 1"
                ),
                {"can_do_id": can_do_id},
            )
            row = result.first()
            logger.debug("session_query_result", row_found=row is not None, can_do_id=can_do_id)
            if row:
                # Found existing session - return it
                existing_session = {
                    "id": row[0],
                    "can_do_id": row[1],
                    "phase": row[2],
                    "completed_count": row[3],
                    "scenario": (
                        ConversationScenario.model_validate(json.loads(row[4]) if isinstance(row[4], str) else row[4])
                        if row[4]
                        else None
                    ),
                    "master": json.loads(row[5]) if isinstance(row[5], str) else (row[5] if row[5] else {}),
                    "variant": json.loads(row[6]) if isinstance(row[6], str) else (row[6] if row[6] else {}),
                    "package": json.loads(row[7]) if isinstance(row[7], str) else (row[7] if row[7] else {}),
                }
                logger.info(
                    "existing_session_found",
                    session_id=existing_session["id"],
                    can_do_id=can_do_id,
                    phase=existing_session["phase"])
                
                # Use master UI directly - no variant generation needed
                requested_level = int(learner_level or 3)
                requested_level = max(1, min(6, requested_level))
                
                existing_master = existing_session.get("master", {})
                selected_variant = {
                    "lessonId": existing_master.get("lessonId"),
                    "level": requested_level,
                    "ui": existing_master.get("ui", {}),
                    "exercises": existing_master.get("exercises", [])
                }
                logger.info(
                    "using_cached_master_ui_directly",
                    session_id=existing_session["id"],
                    level=requested_level)
                
                return {
                    "session_id": existing_session["id"],
                    "scenario": (
                        existing_session["scenario"].model_dump(mode='python')
                        if hasattr(existing_session["scenario"], "model_dump")
                        else existing_session["scenario"]
                    ),
                    "master": existing_session["master"],
                    "variant": selected_variant,  # Return only requested variant
                    "package": existing_session.get("package", {}),
                    "phase": existing_session["phase"],
                    "completed_count": existing_session["completed_count"],
                }
        except Exception as e:
            logger.warning("existing_session_check_failed", error=str(e))
            # Continue to create new session if check fails

        meta = await self._get_cando_meta(graph, can_do_id)
        topic = meta.get("primaryTopic") or "general conversation"
        logger.debug(
            "cando_meta_fetched",
            can_do_id=can_do_id,
            topic=topic,
            level=meta.get("level"))

        # Map topic into a pseudo pattern for conversation practice
        pattern = f"Topic practice: {topic}"
        scenario: ConversationScenario = await self._practice.generate_conversation_scenario(
            pattern_id=f"cando:{can_do_id}",
            pattern=pattern,
            pattern_classification="topic",
            example_sentence=f"Talking about {topic}",
            context=ConversationContext.INTRODUCTION,
            difficulty_level="intermediate",
            provider=provider,
        )
        logger.debug(
            "conversation_scenario_generated",
            pattern_id=f"cando:{can_do_id}")

        gen_start = time.time()
        master = self._get_cached_master(can_do_id, topic)
        if master:
            logger.debug(
                "master_lesson_from_cache",
                can_do_id=can_do_id,
                topic=topic)
        else:
            master = None  # Initialize before attempting to load
            # Check if a compiled lesson exists in the database
            try:
                result = await pg.execute(
                    text("SELECT id FROM lessons WHERE can_do_id = :can_do_id LIMIT 1"),
                    {"can_do_id": can_do_id}
                )
                lesson_row = result.first()
                if lesson_row:
                    # Load compiled lesson from lesson_versions table (get latest version)
                    lesson_id = lesson_row[0]
                    result2 = await pg.execute(
                        text("SELECT lesson_plan, version FROM lesson_versions WHERE lesson_id = :lesson_id ORDER BY version DESC LIMIT 1"),
                        {"lesson_id": lesson_id}
                    )
                    version_row = result2.first()
                    if version_row and version_row[0]:
                        import json as json_module
                        master = json_module.loads(version_row[0]) if isinstance(version_row[0], str) else version_row[0]
                        version = version_row[1]
                        # Add metadata to indicate this is from permanent storage
                        master["lessonSource"] = "permanent"
                        master["permanentVersion"] = version
                        logger.info(
                            "master_lesson_from_permanent_storage",
                            can_do_id=can_do_id,
                            lesson_id=lesson_id,
                            version=version,
                            approved_by=master.get("approvedBy"))
                        # Cache for future use
                        self._cache_master(can_do_id, topic, master)
            except Exception as db_err:
                logger.warning(
                    "compiled_lesson_check_failed",
                    can_do_id=can_do_id,
                    error=str(db_err))
                # Rollback the transaction to clear the aborted state
                try:
                    await pg.rollback()
                except Exception:
                    pass  # Ignore rollback errors
            
            # If still no master, generate it
            if not master:
                master = await self._generate_master_lesson(
                    can_do_id=can_do_id,
                    topic=topic,
                    original_level_str=str(meta.get("level")),
                    provider=provider,
                    model=model,
                    timeout=timeout,
                    meta_extra={
                        "type": meta.get("type"),
                        "skillDomain": meta.get("skillDomain"),
                        "exampleSentence": meta.get("exampleSentence"),
                        "description": meta.get("description"),
                    },
                )
            gen_time = time.time() - gen_start
            logger.info(
                "master_lesson_generated",
                can_do_id=can_do_id,
                duration_sec=round(
                    gen_time,
                    2))

            # Cache the generated master lesson
            self._cache_master(can_do_id, topic, master)
            
            # Mark as AI-generated (not from permanent storage)
            master["lessonSource"] = "ai_generated"

        # Validate master lesson structure
        if master and isinstance(master, dict):
            has_validation_issues = False
            
            # Validate structure
            if "ui" not in master or "sections" not in master.get("ui", {}):
                logger.warning(
                    "master_lesson_invalid_structure",
                    can_do_id=can_do_id,
                    has_ui="ui" in master,
                    has_sections="sections" in master.get("ui", {}))
                has_validation_issues = True
            
            # Check if any section contains prompt text or generic template content
            if master and not has_validation_issues:
                sections = master.get("ui", {}).get("sections", [])
                lesson_topic = topic or ""
                
                for section in sections:
                    for card in section.get("cards", []):
                        body_jp = str(card.get("body", {}).get("jp", ""))
                        body_meta = str(card.get("body", {}).get("meta", ""))
                        combined_text = body_jp + body_meta
                        
                        # Check for prompt indicators
                        if any(indicator in combined_text for indicator in [
                            "Output JSON schema:",
                            "Return exactly this structure",
                            "Authoring rules:",
                            "Task: Compile a complete",
                            "{{lessonId}}"  # Template placeholder not replaced
                        ]):
                            logger.error(
                                "master_lesson_contains_prompt",
                                can_do_id=can_do_id,
                                section_id=section.get("id"),
                                card_id=card.get("id"))
                            has_validation_issues = True
                            break
                        
                        # Check for generic station/direction content that doesn't match topic
                        generic_indicators = ["駅での案内所", "道を聞く", "乗り換えの説明"]
                        topic_mismatch_keywords = ["駅", "旅行", "交通"]
                        
                        has_generic = any(ind in body_jp for ind in generic_indicators)
                        topic_mentions_travel = any(kw in lesson_topic for kw in topic_mismatch_keywords)
                        
                        if has_generic and not topic_mentions_travel:
                            logger.warning(
                                "master_lesson_generic_content_mismatch",
                                can_do_id=can_do_id,
                                topic=lesson_topic,
                                section_id=section.get("id"),
                                card_id=card.get("id"))
                            has_validation_issues = True
                            break
                    if has_validation_issues:
                        break
            
            # If validation found issues, prevent session storage and return error
            if has_validation_issues:
                logger.error(
                    "master_lesson_validation_failed_rejecting_session", 
                    can_do_id=can_do_id)
                # Clear from cache so next request regenerates
                cache_key = f"master:{can_do_id}:{topic}"
                if cache_key in self._master_cache:
                    del self._master_cache[cache_key]
                # Don't save this bad session - force client to retry
                raise ValueError(
                    f"Generated lesson content for {can_do_id} failed validation. "
                    "The content appears to be generic or mismatched with the topic. "
                    "Please try again - the system will regenerate fresh content."
                )

        # Log master lesson structure for debugging
        logger.info(
            "master_lesson_structure",
            has_lessonId=bool(master.get("lessonId")),
            has_ui=bool(master.get("ui")),
            has_sections=bool(master.get("ui", {}).get("sections")),
            section_count=len(master.get("ui", {}).get("sections", [])),
            has_exercises=bool(master.get("exercises")),
            exercise_count=len(master.get("exercises", [])),
        )

        # Extract and resolve entities to ensure Key items are populated
        try:
            text_blob = self._flatten_ui_text(master)
            # First pass: model-based extraction
            extracted = await self._extract_entities_from_text(text_blob=text_blob, provider=provider)
            resolved_words = await self._resolve_words(graph, extracted.get("words") or [])
            resolved_gram = await self._resolve_grammar(graph, extracted.get("grammarPatterns") or [])

            logger.debug(
                "entity_extraction_initial",
                words_found=len(resolved_words),
                patterns_found=len(resolved_gram))

            # Backstop: deterministic extractors if sparse
            if len(resolved_words) < 8:
                logger.info(
                    "entity_resolution_fallback_words",
                    threshold=8,
                    found=len(resolved_words))
                resolved_words = await self._deterministic_words(graph, text_blob)
                logger.debug(
                    "deterministic_words_extracted",
                    count=len(resolved_words))

            if len(resolved_gram) < 4:
                logger.info(
                    "entity_resolution_fallback_grammar",
                    threshold=4,
                    found=len(resolved_gram))
                resolved_gram = await self._deterministic_grammar(graph, text_blob)
                logger.debug(
                    "deterministic_grammar_extracted",
                    count=len(resolved_gram))

            master.setdefault("extractedEntities", {})
            master["extractedEntities"]["words"] = resolved_words
            # Add validated vocabulary list without altering legacy words shape
            try:
                master["extractedEntities"]["vocabulary"] = self._validate_vocabulary(resolved_words)
            except Exception:
                master["extractedEntities"]["vocabulary"] = []
            master["extractedEntities"]["grammarPatterns"] = resolved_gram
            logger.info(
                "entities_resolved",
                words=len(resolved_words),
                patterns=len(resolved_gram))
        except Exception as e:
            # Non-fatal; UI will still render master
            logger.warning(
                "entity_extraction_failed",
                error=str(e),
                can_do_id=can_do_id)
            pass

        # Use master UI directly - no variant generation needed
        target_level = int(learner_level or master.get("originalLevel") or 3)
        target_level = max(1, min(6, target_level))  # Clamp 1-6

        # Use master content directly (variants removed for simplicity)
        requested_variant = {
            "lessonId": master.get("lessonId"),
            "level": target_level,
            "ui": master.get("ui", {}),
            "exercises": master.get("exercises", []),
            "metadata": master.get("metadata", {}),
        }
        logger.info("using_master_ui_directly", level=target_level)

        # Store as sparse dict {level: variant} for progressive loading
        variants = {target_level: requested_variant}

        # Attempt to load a compiled lesson package to anchor the session
        package = await self._fetch_lesson_package(pg, can_do_id)
        if package:
            logger.debug(
                "lesson_package_loaded",
                can_do_id=can_do_id,
                version=package.get("version"))

        session_id = str(uuid4())

        # Store session in Postgres instead of in-memory
        session_data = {
            "scenario": scenario,
            "can_do_id": can_do_id,
            "phase": phase or "lexicon_and_patterns",
            "completed_count": 0,
            "createdAt": int(time.time()),
            "master": master,
            "variant": variants,  # Store all variants
            "package": package,
        }
        await self._store_session(pg, session_id, session_data)
        logger.info(
            "session_stored_postgres",
            session_id=session_id,
            can_do_id=can_do_id,
            phase=session_data.get("phase"))

        opening: List[Dict[str, Any]] = [
            {"speaker": t.speaker, "message": t.message}
            for t in scenario.dialogue_turns
            if t.message
        ]

        total_time = time.time() - start_time
        logger.info(
            "start_lesson_complete",
            session_id=session_id,
            total_duration_sec=round(
                total_time,
                2))

        return {
            "sessionId": session_id,
            "objective": scenario.learning_objective,
            "ai_character": scenario.ai_character,
            "user_role": scenario.user_role,
            "opening_turns": opening,
            "master": master,
            "variant": requested_variant,  # Return only the requested variant
            "package": package,
        }

    async def user_turn(
        self,
        *,
        session_id: str,
        user_message: str,
        provider: str = "openai",
        pg: Optional[PgSession] = None,
    ) -> Dict[str, Any]:
        if not pg:
            raise ValueError("postgres_session_required")

        logger.info(
            "user_turn_begin",
            session_id=session_id,
            provider=provider)

        # Retrieve session from Postgres
        data = await self._retrieve_session(pg, session_id)
        if not data:
            logger.error("session_not_found", session_id=session_id)
            raise ValueError("session_not_found")

        logger.debug(
            "session_retrieved",
            session_id=session_id,
            phase=data.get("phase"),
            completed_count=data.get("completed_count"))

        scenario: ConversationScenario = data.get("scenario", {})
        # Reconstruct scenario from stored JSON
        if isinstance(scenario, dict) and scenario:
            scenario = ConversationScenario(**scenario)
        else:
            logger.error(
                "scenario_reconstruction_failed",
                session_id=session_id)
            raise ValueError("scenario_reconstruction_failed")

        ai_turn: DialogueTurn = await self._practice.continue_conversation(
            scenario, user_message=user_message, provider=provider
        )
        logger.debug(
            "ai_response_generated",
            session_id=session_id,
            has_feedback=bool(
                ai_turn.feedback),
            has_corrections=bool(
                ai_turn.corrections))

        # Update completion count and compute phase gating
        data["completed_count"] = int(data.get("completed_count", 0)) + 1
        gating = lexical_lessons.compute_next_phase(
            current_phase=data.get("phase", "lexicon_and_patterns"),
            completed_count=data["completed_count"],
            score=None,
        )

        old_phase = data.get("phase", "lexicon_and_patterns")
        if gating.get("advanced"):
            data["phase"] = gating.get("phase")
            logger.info(
                "phase_advanced",
                session_id=session_id,
                old_phase=old_phase,
                new_phase=data["phase"],
                completed_count=data["completed_count"])
        else:
            logger.debug(
                "phase_not_advanced",
                session_id=session_id,
                phase=old_phase,
                completed_count=data["completed_count"],
                required=int(
                    settings.GATING_N or 2))

        # Persist updated session back to Postgres
        await self._store_session(pg, session_id, data)
        logger.debug(
            "session_updated_postgres",
            session_id=session_id,
            phase=data.get("phase"))

        # Expose minimal payload; scenario is updated in-place by service
        logger.info(
            "user_turn_complete",
            session_id=session_id,
            phase=data.get("phase"),
            advanced=gating.get(
                "advanced",
                False))

        return {
            "turn": {
                "speaker": ai_turn.speaker,
                "message": ai_turn.message,
                "feedback": ai_turn.feedback,
                "corrections": ai_turn.corrections or [],
                "hints": ai_turn.hints or [],
            },
            "dialogue": [
                {"speaker": t.speaker, "message": t.message}
                for t in scenario.dialogue_turns[-6:]
            ],
            "phase": data.get("phase"),
            "advanced": gating.get("advanced", False),
        }


cando_lesson_sessions = CanDoLessonSessionService()
