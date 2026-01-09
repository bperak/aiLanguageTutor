"""
Pre-Lesson Kit Service

Generates pre-lesson preparation kits with necessary words, grammar patterns,
and fixed phrases appropriate for a given CanDo descriptor and learner level.
"""

from typing import Dict, Any, Optional, List
import json
import structlog
from neo4j import AsyncSession

from app.services.ai_chat_service import AIChatService
from app.models.multilingual import (
    VocabularyEntry,
    GrammarPoint,
    FixedPhrase,
    JapaneseText,
)
from app.schemas.profile import PreLessonKit, CanDoContext
from app.core.config import settings
from app.services.pragmatics_service import pragmatics_service

logger = structlog.get_logger()


class PreLessonKitService:
    """Service for generating pre-lesson preparation kits."""
    
    def __init__(self):
        self.ai_service = AIChatService()
        self.default_provider = "openai"
        self.default_model = "gpt-4o-mini"
    
    async def _get_cando_meta(
        self, neo4j_session: AsyncSession, can_do_id: str
    ) -> Dict[str, Any]:
        """Fetch CanDo descriptor metadata from Neo4j."""
        try:
            query = """
            MATCH (c:CanDoDescriptor {uid: $can_do_id})
            RETURN c.uid AS uid,
                   toString(c.primaryTopic) AS primaryTopic,
                   toString(c.level) AS level,
                   toString(c.type) AS type,
                   toString(c.skillDomain) AS skillDomain,
                   coalesce(toString(c.descriptionEn), toString(c.description)) AS descriptionEn,
                   toString(c.descriptionJa) AS descriptionJa,
                   coalesce(toString(c.titleEn), toString(c.primaryTopic)) AS titleEn,
                   toString(c.titleJa) AS titleJa
            LIMIT 1
            """
            result = await neo4j_session.run(query, can_do_id=can_do_id)
            rec = await result.single()
            if not rec:
                return {
                    "uid": can_do_id,
                    "primaryTopic": "general",
                    "level": "B1",
                    "descriptionEn": "General conversation practice",
                }
            return dict(rec)
        except Exception as e:
            logger.warning("failed_to_fetch_cando_meta", can_do_id=can_do_id, error=str(e))
            return {
                "uid": can_do_id,
                "primaryTopic": "general",
                "level": "B1",
                "descriptionEn": "General conversation practice",
            }
    
    async def _generate_cando_context(
        self,
        can_do_id: str,
        cando_meta: Dict[str, Any],
        neo4j_session: Optional[AsyncSession] = None
    ) -> CanDoContext:
        """
        Generate CanDo context (situation + pragmatic act).
        
        Tries to use graph pragmatics first, then generates via AI if missing.
        """
        situation = ""
        pragmatic_act = ""
        notes = None
        
        # Try to get pragmatics from graph first
        if neo4j_session:
            try:
                pragmatics = await pragmatics_service.get_pragmatics(
                    session=neo4j_session,
                    can_do_id=can_do_id
                )
                if pragmatics and len(pragmatics) > 0:
                    # Use first pragmatic pattern as context
                    first_pragma = pragmatics[0]
                    situation = first_pragma.get("situation", "") or cando_meta.get("descriptionEn", "")
                    pragmatic_act = first_pragma.get("act", "") or first_pragma.get("name", "")
                    if not pragmatic_act:
                        # Infer from pragmatic pattern fields
                        pragmatic_act = f"{first_pragma.get('register', 'neutral')} {first_pragma.get('type', 'communication')}"
            except Exception as e:
                logger.warning("failed_to_fetch_pragmatics", can_do_id=can_do_id, error=str(e))
        
        # If missing, generate via AI
        if not situation or not pragmatic_act:
            try:
                description = cando_meta.get("descriptionEn", "") or cando_meta.get("descriptionJa", "")
                topic = cando_meta.get("primaryTopicEn", "") or cando_meta.get("primaryTopic", "")
                skill_domain = cando_meta.get("skillDomain", "")
                
                context_prompt = f"""Analyze this CanDo descriptor and extract:
1. Situation: A brief scenario description (1-2 sentences) of when/where this communication happens
2. Pragmatic act: The communication act (e.g., "request (polite)", "offer (casual)", "apology (formal)", "ask-info (neutral)")

CanDo: {can_do_id}
Description: {description}
Topic: {topic}
Skill Domain: {skill_domain}

Return JSON:
{{
  "situation": "...",
  "pragmatic_act": "...",
  "notes": "optional cultural or usage notes"
}}"""
                
                response = await self.ai_service.generate_reply(
                    provider=self.default_provider,
                    model=self.default_model,
                    messages=[{"role": "user", "content": context_prompt}],
                    system_prompt="You are a Japanese pragmatics expert. Extract situational context and communication acts from CanDo descriptors. Return only valid JSON.",
                    temperature=0.3,
                )
                
                content = response.get("content", "")
                if isinstance(content, str):
                    try:
                        if "```json" in content:
                            start = content.find("```json") + 7
                            end = content.find("```", start)
                            content = content[start:end].strip()
                        elif "```" in content:
                            start = content.find("```") + 3
                            end = content.find("```", start)
                            content = content[start:end].strip()
                        
                        context_data = json.loads(content)
                        situation = context_data.get("situation", description)
                        pragmatic_act = context_data.get("pragmatic_act", "general communication")
                        notes = context_data.get("notes")
                    except json.JSONDecodeError:
                        logger.warning("failed_to_parse_cando_context", can_do_id=can_do_id)
                        situation = description
                        pragmatic_act = "general communication"
            except Exception as e:
                logger.warning("failed_to_generate_cando_context", can_do_id=can_do_id, error=str(e))
                situation = cando_meta.get("descriptionEn", "General conversation practice")
                pragmatic_act = "general communication"
        
        return CanDoContext(
            situation=situation or cando_meta.get("descriptionEn", "General conversation practice"),
            pragmatic_act=pragmatic_act or "general communication",
            notes=notes
        )
    
    def _create_fallback_kit(self, can_do_id: str, level: str) -> PreLessonKit:
        """Create a minimal fallback kit when AI generation fails."""
        logger.warning("using_fallback_prelesson_kit", can_do_id=can_do_id, level=level)
        
        # Minimal fallback can_do_context
        fallback_context = CanDoContext(
            situation="General conversation practice",
            pragmatic_act="general communication (neutral)",
            notes="Basic conversational practice"
        )
        
        # Minimal fallback words
        fallback_words = [
            {
                "surface": "こんにちは",
                "reading": "こんにちは",
                "pos": "expression",
                "translation": "Hello (daytime greeting)",
            },
            {
                "surface": "ありがとう",
                "reading": "ありがとう",
                "pos": "expression",
                "translation": "Thank you",
            },
        ]
        
        # Minimal fallback grammar
        fallback_grammar = [
            {
                "pattern": "〜です",
                "explanation": "Polite copula for stating facts",
                "examples": [
                    {
                        "kanji": "学生です",
                        "romaji": "gakusei desu",
                        "furigana": [{"text": "学生", "ruby": "がくせい"}, {"text": "です"}],
                        "translation": "I am a student",
                    }
                ],
            }
        ]
        
        # Minimal fallback phrases
        fallback_phrases = [
            {
                "phrase": {
                    "kanji": "よろしくお願いします",
                    "romaji": "yoroshiku onegaishimasu",
                    "furigana": [
                        {"text": "よろしく", "ruby": "よろしく"},
                        {"text": "お", "ruby": "お"},
                        {"text": "願い", "ruby": "ねがい"},
                        {"text": "します", "ruby": "します"},
                    ],
                    "translation": "Nice to meet you / Please treat me well",
                },
                "usage_note": "Used when meeting someone for the first time",
                "register": "polite",
            }
        ]
        
        return PreLessonKit(
            can_do_context=fallback_context,
            necessary_words=fallback_words,
            necessary_grammar_patterns=fallback_grammar,
            necessary_fixed_phrases=fallback_phrases,
        )
    
    async def generate_kit(
        self,
        can_do_id: str,
        learner_level: Optional[str] = None,
        neo4j_session: Optional[AsyncSession] = None,
    ) -> PreLessonKit:
        """
        Generate a pre-lesson kit for a CanDo descriptor.
        
        Args:
            can_do_id: CanDo descriptor ID
            learner_level: Optional learner level (beginner_1, intermediate_1, etc.)
            neo4j_session: Optional Neo4j session for fetching CanDo metadata
            
        Returns:
            PreLessonKit with necessary words, grammar patterns, and fixed phrases
        """
        try:
            # Fetch CanDo metadata if session provided
            cando_meta = {}
            if neo4j_session:
                cando_meta = await self._get_cando_meta(neo4j_session, can_do_id)
            
            level = learner_level or cando_meta.get("level", "B1")
            description = cando_meta.get("descriptionEn", "conversational practice")
            topic = cando_meta.get("primaryTopic", "general")
            
            # Map learner level to CEFR if needed
            level_mapping = {
                "beginner_1": "A1",
                "beginner_2": "A2",
                "intermediate_1": "B1",
                "intermediate_2": "B2",
                "advanced_1": "C1",
                "advanced_2": "C2",
            }
            cefr_level = level_mapping.get(level.lower(), level)
            
            # Generate CanDo context (component 0)
            can_do_context = await self._generate_cando_context(
                can_do_id=can_do_id,
                cando_meta=cando_meta,
                neo4j_session=neo4j_session
            )
            
            # Build AI prompt
            prompt = f"""Generate a pre-lesson preparation kit for this conversational situation:

CanDo Descriptor: {can_do_id}
Topic: {topic}
Description: {description}
Situation: {can_do_context.situation}
Pragmatic Act: {can_do_context.pragmatic_act}
Learner Level: {cefr_level} (CEFR)

Generate a JSON object with three lists:

1. **necessary_words**: 8-12 essential vocabulary words for this situation
   - Each word must have: surface (Japanese), reading (hiragana/katakana), pos (part of speech: noun/verb/adjective/adverb/particle/expression), translation (English)
   - Example: {{"surface": "レストラン", "reading": "れすとらん", "pos": "noun", "translation": "restaurant"}}

2. **necessary_grammar_patterns**: 3-5 essential grammar patterns for this situation
   - Each pattern must have: pattern (grammar point name), explanation (English), examples (list of 2-3 JapaneseText objects with kanji, romaji, furigana segments, translation)
   - Example: {{"pattern": "〜たいです", "explanation": "Expresses desire (want to...)", "examples": [{{"kanji": "食べたいです", "romaji": "tabetai desu", "furigana": [{{"text": "食べ", "ruby": "たべ"}}, {{"text": "たい", "ruby": "たい"}}, {{"text": "です"}}], "translation": "I want to eat"}}]}}

3. **necessary_fixed_phrases**: 4-6 essential fixed phrases/conversational motifs for this situation
   - Each phrase must have: phrase (JapaneseText object), usage_note (when/how to use), register (formality: formal/casual/polite/humble)
   - Example: {{"phrase": {{"kanji": "いらっしゃいませ", "romaji": "irasshaimase", "furigana": [{{"text": "いらっしゃい", "ruby": "いらっしゃい"}}, {{"text": "ませ"}}], "translation": "Welcome (to a store/restaurant)"}}, "usage_note": "Used by staff to greet customers", "register": "polite"}}

All content must be appropriate for {cefr_level} level learners and directly relevant to the conversational situation: {description}.

Return ONLY valid JSON matching this structure:
{{
  "necessary_words": [...],
  "necessary_grammar_patterns": [...],
  "necessary_fixed_phrases": [...]
}}"""
            
            system_prompt = """You are a Japanese language curriculum expert. Generate structured pre-lesson preparation kits with vocabulary, grammar, and fixed phrases appropriate for specific conversational situations and learner levels. Always return valid JSON."""
            
            # Generate with AI
            response = await self.ai_service.generate_reply(
                provider=self.default_provider,
                model=self.default_model,
                messages=[{"role": "user", "content": prompt}],
                system_prompt=system_prompt,
                temperature=0.3,  # Lower temperature for more structured output
            )
            
            content = response.get("content", "")
            if isinstance(content, str):
                # Try to extract JSON from response
                try:
                    # Look for JSON block
                    if "```json" in content:
                        start = content.find("```json") + 7
                        end = content.find("```", start)
                        content = content[start:end].strip()
                    elif "```" in content:
                        start = content.find("```") + 3
                        end = content.find("```", start)
                        content = content[start:end].strip()
                    
                    # Parse JSON
                    kit_data = json.loads(content)
                except json.JSONDecodeError:
                    logger.warning("failed_to_parse_ai_response", can_do_id=can_do_id)
                    return self._create_fallback_kit(can_do_id, level)
            else:
                kit_data = content
            
            # Validate and convert to Pydantic models
            try:
                # Validate words
                words = []
                for word_data in kit_data.get("necessary_words", []):
                    try:
                        word = VocabularyEntry(**word_data)
                        words.append(word.model_dump())
                    except Exception as e:
                        logger.warning("invalid_word_entry", word_data=word_data, error=str(e))
                        continue
                
                # Validate grammar patterns
                grammar = []
                for grammar_data in kit_data.get("necessary_grammar_patterns", []):
                    try:
                        # Convert examples to JapaneseText objects
                        examples = []
                        for ex_data in grammar_data.get("examples", []):
                            try:
                                jp_text = JapaneseText(**ex_data)
                                examples.append(jp_text.model_dump())
                            except Exception as e:
                                logger.warning("invalid_grammar_example", example=ex_data, error=str(e))
                                continue
                        
                        if examples:
                            grammar.append({
                                "pattern": grammar_data.get("pattern", ""),
                                "explanation": grammar_data.get("explanation", ""),
                                "examples": examples,
                            })
                    except Exception as e:
                        logger.warning("invalid_grammar_entry", grammar_data=grammar_data, error=str(e))
                        continue
                
                # Validate fixed phrases
                phrases = []
                for phrase_data in kit_data.get("necessary_fixed_phrases", []):
                    try:
                        phrase_obj = phrase_data.get("phrase", {})
                        jp_text = JapaneseText(**phrase_obj)
                        phrases.append({
                            "phrase": jp_text.model_dump(),
                            "usage_note": phrase_data.get("usage_note"),
                            "register": phrase_data.get("register"),
                        })
                    except Exception as e:
                        logger.warning("invalid_phrase_entry", phrase_data=phrase_data, error=str(e))
                        continue
                
                # Create PreLessonKit with can_do_context
                kit = PreLessonKit(
                    can_do_context=can_do_context,
                    necessary_words=words,
                    necessary_grammar_patterns=grammar,
                    necessary_fixed_phrases=phrases,
                )
                
                logger.info("prelesson_kit_generated", can_do_id=can_do_id, words=len(words), grammar=len(grammar), phrases=len(phrases))
                return kit
                
            except Exception as e:
                logger.error("kit_validation_failed", can_do_id=can_do_id, error=str(e))
                return self._create_fallback_kit(can_do_id, level)
                
        except Exception as e:
            logger.error("kit_generation_failed", can_do_id=can_do_id, error=str(e))
            return self._create_fallback_kit(can_do_id, learner_level or "B1")


# Singleton instance
prelesson_kit_service = PreLessonKitService()

