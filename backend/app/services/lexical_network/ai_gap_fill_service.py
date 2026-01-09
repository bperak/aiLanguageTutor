"""
AI Gap-Filling Service for Word Node Attributes

Uses AI (GPT-4o-mini, etc.) to fill missing attributes on Word nodes
when dictionary sources don't have them.
"""

import json
from dataclasses import dataclass
from typing import Dict, List, Optional, Set

import structlog

from app.services.lexical_network.ai_providers import AIProviderManager, AIGenerationResult

logger = structlog.get_logger()

# Attributes that AI can reliably fill
AI_FILLABLE_ATTRIBUTES = {
    "translation",           # High confidence
    "pos_primary",           # High confidence  
    "etymology",             # Medium confidence (4 fixed categories)
    "bunrui_class",          # Medium confidence (1/2/3/4 only, not full code)
}

# Prompt version for tracking
PROMPT_VERSION = "gap_fill_v1.0"

SYSTEM_PROMPT = """You are an expert Japanese lexicographer with deep knowledge of:
- Japanese vocabulary and word origins (和語、漢語、外来語、混種語)
- Part-of-speech classification
- Semantic classification based on 分類語彙表

Your task is to fill in missing attributes for Japanese words.

CRITICAL RULES:
1. Output ONLY valid JSON - no other text
2. Be conservative - if uncertain, use null rather than guessing
3. For etymology: 和語 (native), 漢語 (Sino-Japanese), 外来語 (loanword), 混種語 (hybrid)
4. For bunrui_class: 1=体の類(nouns), 2=用の類(verbs), 3=相の類(adjectives), 4=その他(other)
5. Provide confidence score (0.0-1.0) for each attribute
6. Only fill attributes that were requested
7. Use null for attributes you're uncertain about (confidence < 0.6)"""


@dataclass
class GapFillResult:
    """Result from AI gap-filling for a single word."""
    word: str
    filled_attributes: Dict[str, any]
    confidence_scores: Dict[str, float]
    ai_provider: str
    ai_model: str
    ai_request_id: str
    tokens_used: int
    cost_usd: float


def build_gap_fill_prompt(
    word: str,
    reading: Optional[str],
    existing_data: Dict[str, any],
    attributes_to_fill: Set[str],
) -> str:
    """
    Build prompt for AI gap-filling.
    
    Args:
        word: The Japanese word (standard_orthography)
        reading: Hiragana reading if available
        existing_data: Currently known attributes
        attributes_to_fill: Set of attribute names to fill
        
    Returns:
        Formatted prompt string
    """
    prompt = f"""Fill in the missing attributes for this Japanese word:

## Word Information
- **Word**: {word}
- **Reading**: {reading or 'unknown'}
"""
    
    # Add existing data for context
    if existing_data:
        prompt += "\n## Existing Data (for context)\n"
        for key, value in existing_data.items():
            if value is not None and key not in attributes_to_fill:
                prompt += f"- {key}: {value}\n"
    
    # Specify what to fill
    prompt += f"""
## Attributes to Fill
Fill these missing attributes: {', '.join(sorted(attributes_to_fill))}

## Output Format
Return a JSON object with this exact structure:
{{
    "translation": "English translation" or null,
    "pos_primary": "名詞|動詞|形容詞|形容動詞|副詞|etc" or null,
    "etymology": "和語|漢語|外来語|混種語" or null,
    "bunrui_class": "1|2|3|4" or null,
    "confidence": {{
        "translation": 0.0-1.0,
        "pos_primary": 0.0-1.0,
        "etymology": 0.0-1.0,
        "bunrui_class": 0.0-1.0
    }},
    "reasoning": "Brief explanation of your analysis"
}}

Only fill attributes that were requested. Use null for attributes you're uncertain about (confidence < 0.6).
"""
    return prompt


class AIGapFillService:
    """Service for AI-driven attribute gap-filling on Word nodes."""
    
    def __init__(self, default_model: str = "gpt-4o-mini"):
        self.provider_manager = AIProviderManager()
        self.default_model = default_model
    
    async def fill_gaps_for_word(
        self,
        neo4j_session,
        word: str,
        model: Optional[str] = None,
        min_confidence: float = 0.7,
    ) -> GapFillResult:
        """
        Fill missing attributes for a single word using AI.
        
        Args:
            neo4j_session: Neo4j async session
            word: Word to fill gaps for
            model: AI model to use (default: gpt-4o-mini)
            min_confidence: Minimum confidence to accept (default: 0.7)
            
        Returns:
            GapFillResult with filled attributes
        """
        model = model or self.default_model
        
        # 1. Fetch current word data
        word_data = await self._fetch_word_data(neo4j_session, word)
        if not word_data:
            raise ValueError(f"Word not found: {word}")
        
        # 2. Determine which attributes need filling
        missing_attrs = self._find_missing_attributes(word_data)
        if not missing_attrs:
            logger.info("No gaps to fill", word=word)
            return GapFillResult(
                word=word,
                filled_attributes={},
                confidence_scores={},
                ai_provider="none",
                ai_model="none",
                ai_request_id="",
                tokens_used=0,
                cost_usd=0.0,
            )
        
        # 3. Build prompt
        prompt = build_gap_fill_prompt(
            word=word,
            reading=word_data.get("reading_hiragana"),
            existing_data=word_data,
            attributes_to_fill=missing_attrs,
        )
        
        # 4. Call AI (temperature=0 for reproducibility)
        provider = self.provider_manager.get_provider(model)
        ai_result = await provider.generate_relations(
            prompt=prompt,
            system_prompt=SYSTEM_PROMPT,
            max_tokens=1024,
        )
        
        # 5. Parse response
        filled_data, confidence = self._parse_ai_response(
            ai_result.content, min_confidence
        )
        
        # 6. Update Neo4j with filled attributes + AI metadata
        if filled_data:
            await self._update_word_with_ai_data(
                neo4j_session, word, filled_data, confidence, ai_result
            )
        
        return GapFillResult(
            word=word,
            filled_attributes=filled_data,
            confidence_scores=confidence,
            ai_provider=ai_result.provider,
            ai_model=ai_result.model,
            ai_request_id=ai_result.request_id,
            tokens_used=ai_result.tokens_input + ai_result.tokens_output,
            cost_usd=ai_result.cost_usd,
        )
    
    async def batch_fill_gaps(
        self,
        neo4j_session,
        limit: int = 100,
        model: Optional[str] = None,
        min_confidence: float = 0.7,
        pos_filter: Optional[str] = None,
    ) -> Dict[str, any]:
        """
        Batch fill gaps for multiple words.
        
        Args:
            neo4j_session: Neo4j async session
            limit: Maximum words to process
            model: AI model to use
            min_confidence: Minimum confidence threshold
            pos_filter: Optional POS filter
            
        Returns:
            Statistics dictionary
        """
        stats = {
            "processed": 0,
            "filled": 0,
            "skipped": 0,
            "errors": 0,
            "total_tokens": 0,
            "total_cost_usd": 0.0,
            "attributes_filled": {},
        }
        
        # Find words with missing attributes
        words = await self._find_words_with_gaps(
            neo4j_session, limit, pos_filter
        )
        
        total_words = len(words)
        logger.info(
            "Starting batch gap fill",
            word_count=total_words,
            model=model or self.default_model,
        )
        
        for idx, word in enumerate(words):
            try:
                result = await self.fill_gaps_for_word(
                    neo4j_session, word, model, min_confidence
                )
                
                stats["processed"] += 1
                stats["total_tokens"] += result.tokens_used
                stats["total_cost_usd"] += result.cost_usd
                
                if result.filled_attributes:
                    stats["filled"] += 1
                    for attr in result.filled_attributes:
                        stats["attributes_filled"][attr] = \
                            stats["attributes_filled"].get(attr, 0) + 1
                else:
                    stats["skipped"] += 1
                
                # Progress logging every 50 words
                if (idx + 1) % 50 == 0 or (idx + 1) == total_words:
                    progress_pct = round((idx + 1) / total_words * 100, 1)
                    logger.info(
                        "Progress",
                        processed=stats["processed"],
                        filled=stats["filled"],
                        errors=stats["errors"],
                        progress=f"{idx + 1}/{total_words} ({progress_pct}%)",
                        cost_usd=round(stats["total_cost_usd"], 4),
                        last_word=word,
                    )
                    
            except Exception as e:
                logger.error("Gap fill failed", word=word, error=str(e))
                stats["errors"] += 1
                
                # Also log progress on errors every 50
                if (idx + 1) % 50 == 0:
                    progress_pct = round((idx + 1) / total_words * 100, 1)
                    logger.info(
                        "Progress (with errors)",
                        processed=stats["processed"],
                        errors=stats["errors"],
                        progress=f"{idx + 1}/{total_words} ({progress_pct}%)",
                    )
        
        logger.info("Batch gap fill complete", **stats)
        return stats
    
    async def _fetch_word_data(
        self, session, word: str
    ) -> Optional[Dict[str, any]]:
        """Fetch current word data from Neo4j."""
        query = """
        MATCH (w:Word)
        WHERE w.standard_orthography = $word
        RETURN w {
            .standard_orthography,
            .reading_hiragana,
            .reading_katakana,
            .translation,
            .pos_primary,
            .pos_detailed,
            .pos1,
            .pos_source,
            .unidic_pos1,
            .etymology,
            .bunrui_class,
            .bunrui_number,
            .lee_difficulty_numeric,
            .matsushita_difficulty_numeric,
            .sources
        } AS data
        """
        result = await session.run(query, word=word)
        record = await result.single()
        return dict(record["data"]) if record else None
    
    def _find_missing_attributes(
        self, word_data: Dict[str, any]
    ) -> Set[str]:
        """
        Find which AI-fillable attributes are missing.
        
        For POS: only fill if no authoritative source exists (unidic/matsushita/lee).
        """
        missing = set()
        for attr in AI_FILLABLE_ATTRIBUTES:
            if attr == "pos_primary":
                # Only fill POS if no authoritative source exists
                pos_source = word_data.get("pos_source")
                has_authoritative_pos = (
                    pos_source in ("unidic", "matsushita", "lee") or
                    word_data.get("pos1") is not None or
                    word_data.get("unidic_pos1") is not None
                )
                if not has_authoritative_pos and word_data.get(attr) is None:
                    missing.add(attr)
            elif word_data.get(attr) is None:
                missing.add(attr)
        return missing
    
    async def _find_words_with_gaps(
        self,
        session,
        limit: int,
        pos_filter: Optional[str] = None,
    ) -> List[str]:
        """
        Find words that have missing AI-fillable attributes.
        
        For POS: only include words without authoritative POS (unidic/matsushita/lee).
        """
        query = """
        MATCH (w:Word)
        WHERE (w.translation IS NULL 
               OR w.etymology IS NULL 
               OR w.bunrui_class IS NULL
               OR (w.pos_primary IS NULL 
                   AND w.pos1 IS NULL 
                   AND w.unidic_pos1 IS NULL
                   AND (w.pos_source IS NULL OR w.pos_source = 'ai')))
        AND ($pos_filter IS NULL OR w.pos_primary = $pos_filter OR w.pos_primary_norm = $pos_filter)
        AND (w.ai_gap_filled IS NULL OR w.ai_gap_filled = false)
        AND (w.pos_source IS NULL OR w.pos_source = 'ai' OR w.pos_source NOT IN ['unidic', 'matsushita', 'lee'])
        RETURN w.standard_orthography AS word
        LIMIT $limit
        """
        result = await session.run(
            query, pos_filter=pos_filter, limit=limit
        )
        return [record["word"] for record in await result.data()]
    
    def _parse_ai_response(
        self,
        content: str,
        min_confidence: float,
    ) -> tuple[Dict[str, any], Dict[str, float]]:
        """Parse AI response and filter by confidence."""
        try:
            # Clean JSON from markdown
            content = content.strip()
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            content = content.strip()
            
            data = json.loads(content)
            
            filled = {}
            confidence = data.get("confidence", {})
            
            # Only keep attributes above confidence threshold
            for attr in AI_FILLABLE_ATTRIBUTES:
                if attr in data and data[attr] is not None:
                    attr_confidence = confidence.get(attr, 0.5)
                    if attr_confidence >= min_confidence:
                        filled[attr] = data[attr]
                        confidence[attr] = attr_confidence
            
            return filled, confidence
            
        except json.JSONDecodeError as e:
            logger.error("Failed to parse AI response", error=str(e), content=content[:500])
            return {}, {}
        except Exception as e:
            logger.error("Unexpected error parsing AI response", error=str(e))
            return {}, {}
    
    async def _update_word_with_ai_data(
        self,
        session,
        word: str,
        filled_data: Dict[str, any],
        confidence: Dict[str, float],
        ai_result: AIGenerationResult,
    ):
        """Update Word node with AI-filled data and metadata."""
        # Normalize etymology if filled
        if "etymology" in filled_data:
            from app.services.lexical_network.column_mappings import normalize_etymology
            normalized, _ = normalize_etymology(filled_data["etymology"], "ai")
            filled_data["etymology"] = normalized
            filled_data["etymology_source"] = "ai"
        
        # Handle POS: map to canonical format if filled
        canonical_pos = None
        if "pos_primary" in filled_data:
            from app.services.lexical_network.pos_mapper import parse_unidic_pos
            # AI provides simple POS, try to map to UniDic format
            ai_pos = filled_data["pos_primary"]
            # Try parsing as UniDic-style first, otherwise use as pos1
            if "-" in ai_pos:
                canonical_pos = parse_unidic_pos(ai_pos)
            else:
                canonical_pos = {
                    "pos1": ai_pos,
                    "pos2": None,
                    "pos3": None,
                    "pos4": None,
                    "pos_primary_norm": ai_pos,
                }
        
        # Remove POS from filled_data if we're handling it separately
        pos_primary_value = filled_data.pop("pos_primary", None)
        pos_confidence = confidence.pop("pos_primary", 0.0)
        
        query = """
        MATCH (w:Word {standard_orthography: $word})
        SET w += $filled_data,
            w.ai_gap_filled = true,
            w.ai_gap_fill_model = $model,
            w.ai_gap_fill_provider = $provider,
            w.ai_gap_fill_request_id = $request_id,
            w.ai_gap_fill_at = datetime(),
            w.ai_confidence_translation = $confidence_translation,
            w.ai_confidence_etymology = $confidence_etymology,
            w.ai_confidence_pos = $confidence_pos,
            w.ai_confidence_bunrui_class = $confidence_bunrui_class,
            w.sources = CASE 
                WHEN w.sources IS NULL THEN ['ai_gap_fill']
                WHEN NOT 'ai_gap_fill' IN w.sources 
                    THEN w.sources + ['ai_gap_fill']
                ELSE w.sources
            END,
            // BACKWARD COMPATIBILITY: Also maintain old source field
            w.source = CASE 
                WHEN w.source IS NULL THEN 'ai_gap_fill'
                ELSE w.source
            END,
            w.updated_at = datetime()
        """
        
        query_params = {
            "word": word,
            "filled_data": filled_data,
            "confidence_translation": confidence.get("translation"),
            "confidence_etymology": confidence.get("etymology"),
            "confidence_pos": pos_confidence,
            "confidence_bunrui_class": confidence.get("bunrui_class"),
            "model": ai_result.model,
            "provider": ai_result.provider,
            "request_id": ai_result.request_id,
        }
        
        await session.run(query, **query_params)
        
        # Update canonical POS only if no authoritative source exists
        if canonical_pos and pos_primary_value:
            # Check if authoritative POS exists
            check_query = """
            MATCH (w:Word {standard_orthography: $word})
            RETURN w.pos_source AS pos_source
            """
            check_result = await session.run(check_query, word=word)
            check_record = await check_result.single()
            
            existing_pos_source = check_record.get("pos_source") if check_record else None
            has_authoritative = existing_pos_source in ("unidic", "matsushita", "lee")
            
            if not has_authoritative:
                # Set canonical POS from AI (lowest priority)
                pos_query = """
                MATCH (w:Word {standard_orthography: $word})
                SET w.pos1 = $pos1,
                    w.pos2 = $pos2,
                    w.pos3 = $pos3,
                    w.pos4 = $pos4,
                    w.pos_primary_norm = $pos_primary_norm,
                    w.pos_primary = $pos_primary_value,
                    w.pos_source = 'ai',
                    w.pos_confidence = $pos_confidence,
                    w.updated_at = datetime()
                """
                await session.run(
                    pos_query,
                    word=word,
                    pos1=canonical_pos.get("pos1"),
                    pos2=canonical_pos.get("pos2"),
                    pos3=canonical_pos.get("pos3"),
                    pos4=canonical_pos.get("pos4"),
                    pos_primary_norm=canonical_pos.get("pos_primary_norm"),
                    pos_primary_value=pos_primary_value,
                    pos_confidence=pos_confidence,
                )
            else:
                # Store original POS but don't override canonical
                if pos_primary_value:
                    await session.run(
                        "MATCH (w:Word {standard_orthography: $word}) SET w.pos_primary = $pos_primary, w.updated_at = datetime()",
                        word=word,
                        pos_primary=pos_primary_value,
                    )
