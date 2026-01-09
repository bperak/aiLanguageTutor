"""
AI Word Content Generation Service

Generates comprehensive word information using Gemini AI:
- Definitions with context
- Usage examples
- Cultural notes and learning tips
- Kanji breakdown analysis
- Grammar pattern connections
- Collocation suggestions
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from app.services.ai_chat_service import AIChatService
from app.db import get_neo4j_session

logger = logging.getLogger(__name__)

@dataclass
class AIWordContent:
    """Structured AI-generated content for a word"""
    definitions: List[str]
    examples: List[str]
    cultural_notes: str
    kanji_breakdown: str
    grammar_patterns: List[str]
    collocations: List[str]
    learning_tips: str
    confidence_score: float
    model_used: str
    generated_at: datetime

class AIWordContentService:
    """Service for generating AI-enhanced word content"""
    
    def __init__(self):
        self.ai = AIChatService()
        self.model = "gemini-2.5-flash"
    
    def _build_word_analysis_prompt(self, word_data: Dict[str, Any], neighbors: List[Dict[str, Any]]) -> str:
        """Build comprehensive prompt for word analysis"""
        
        # Extract word information
        kanji = word_data.get('kanji', '')
        hiragana = word_data.get('hiragana', '')
        translation = word_data.get('translation', '')
        pos = word_data.get('pos_primary', '')
        level = word_data.get('difficulty_numeric', 0)
        etymology = word_data.get('etymology', '')
        
        # Build neighbor context
        neighbor_context = ""
        if neighbors:
            neighbor_words = [f"{n.get('kanji', '')} ({n.get('translation', '')})" for n in neighbors[:5]]
            neighbor_context = f"\nRelated words: {', '.join(neighbor_words)}"
        
        prompt = f"""
You are an expert Japanese language tutor. Generate comprehensive educational content for the word: {kanji}

Word Information:
- Kanji: {kanji}
- Hiragana: {hiragana}
- Translation: {translation}
- Part of Speech: {pos}
- Difficulty Level: {level}/6
- Etymology: {etymology}{neighbor_context}

Please provide a JSON response with the following structure:

{{
    "definitions": [
        "Primary definition with context",
        "Secondary definition if applicable",
        "Specialized usage definition"
    ],
    "examples": [
        "Example sentence with hiragana reading and English translation",
        "Another example showing different usage",
        "Common phrase or expression"
    ],
    "cultural_notes": "Cultural context, usage tips, formality levels, and when to use this word",
    "kanji_breakdown": "Analysis of kanji components, radicals, and meaning",
    "grammar_patterns": [
        "Common grammar patterns using this word",
        "Sentence structures where this word appears"
    ],
    "collocations": [
        "Common word combinations",
        "Frequently used phrases"
    ],
    "learning_tips": "Specific advice for learners, common mistakes to avoid, memory techniques",
    "confidence_score": 0.95
}}

Guidelines:
- Make content appropriate for difficulty level {level}
- Focus on practical usage and learning
- Include cultural context relevant to Japanese language learning
- Provide clear, actionable learning tips
- Ensure examples are natural and commonly used
- Confidence score should reflect how certain you are about the content (0.0-1.0)
"""
        return prompt.strip()
    
    async def generate_word_content(
        self, 
        word_kanji: str, 
        session = None,
        force_regenerate: bool = False
    ) -> Optional[AIWordContent]:
        """
        Generate comprehensive AI content for a word
        
        Args:
            word_kanji: The kanji of the word to analyze
            session: Neo4j session (optional, will create if not provided)
            force_regenerate: Whether to regenerate even if content exists
            
        Returns:
            AIWordContent object or None if generation fails
        """
        
        if not session:
            # Use the same pattern as FastAPI endpoints
            async for session in get_neo4j_session():
                break
        
        try:
            # Check if content already exists; if so, return it without regenerating
            if not force_regenerate:
                existing_content = await self._get_existing_content(session, word_kanji)
                if existing_content:
                    logger.info(f"Using existing AI content for {word_kanji}")
                    return self._parse_existing_content(existing_content)
            
            # Fetch word data and neighbors
            word_data, neighbors = await self._fetch_word_context(session, word_kanji)
            if not word_data:
                logger.error(f"Word {word_kanji} not found in database")
                return None
            
            # Generate AI content
            prompt = self._build_word_analysis_prompt(word_data, neighbors)
            
            logger.info(f"Generating AI content for {word_kanji}")
            response = await self.ai.generate_reply(
                provider="gemini",
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                system_prompt="You are an expert Japanese language tutor. Provide accurate, educational content in valid JSON format."
            )
            
            content_text = response.get("content", "")
            if not content_text:
                logger.error(f"No content generated for {word_kanji}")
                return None
            
            # Parse AI response
            ai_content = self._parse_ai_response(content_text)
            if not ai_content:
                logger.error(f"Failed to parse AI response for {word_kanji}")
                return None
            
            # Store in database with level information
            word_level = word_data.get('jlpt_level', 'N/A')
            await self._store_content(session, word_kanji, ai_content, word_level)
            
            logger.info(f"Successfully generated and stored AI content for {word_kanji}")
            return ai_content
            
        except Exception as e:
            logger.error(f"Error generating content for {word_kanji}: {e}")
            return None
    
    async def _get_existing_content(self, session, word_kanji: str) -> Optional[Dict]:
        """Check if AI content already exists for the word"""
        query = """
        MATCH (w:Word)
        WHERE coalesce(w.standard_orthography, w.kanji) = $kanji
          AND w.ai_generated_at IS NOT NULL
        RETURN w.ai_definitions AS ai_definitions,
               w.ai_examples AS ai_examples,
               w.ai_cultural_notes AS ai_cultural_notes,
               w.ai_kanji_breakdown AS ai_kanji_breakdown,
               w.ai_grammar_patterns AS ai_grammar_patterns,
               w.ai_collocations AS ai_collocations,
               w.ai_learning_tips AS ai_learning_tips,
               w.ai_confidence_score AS ai_confidence_score,
               w.ai_model_used AS ai_model_used,
               w.ai_generated_at AS ai_generated_at,
               w.ai_content_version AS ai_content_version,
               w.ai_target_level AS ai_target_level
        """
        result = await session.run(query, kanji=word_kanji)
        record = await result.single()
        return dict(record) if record else None
    
    
    
    def _parse_existing_content(self, content: Dict) -> AIWordContent:
        """Parse existing database content into AIWordContent object with type coercion."""

        def to_str_list(value: Any) -> List[str]:
            if value is None:
                return []
            if isinstance(value, list):
                return [str(v) for v in value]
            # If stored as JSON string, try to decode
            if isinstance(value, str):
                try:
                    parsed = json.loads(value)
                    if isinstance(parsed, list):
                        return [str(v) for v in parsed]
                except Exception:
                    # Fall back to single-item list
                    return [value]
            # Fallback
            return [str(value)]

        def to_str(value: Any) -> str:
            if value is None:
                return ""
            return str(value)

        generated_at_value = content.get('ai_generated_at')
        if hasattr(generated_at_value, 'to_native'):
            generated_at_dt = generated_at_value.to_native()
        elif hasattr(generated_at_value, 'isoformat'):
            generated_at_dt = generated_at_value
        else:
            generated_at_dt = datetime.now()

        confidence = content.get('ai_confidence_score', 0.0)
        try:
            confidence = float(confidence) if confidence is not None else 0.0
        except Exception:
            confidence = 0.0

        return AIWordContent(
            definitions=to_str_list(content.get('ai_definitions')),
            examples=to_str_list(content.get('ai_examples')),
            cultural_notes=to_str(content.get('ai_cultural_notes')),
            kanji_breakdown=to_str(content.get('ai_kanji_breakdown')),
            grammar_patterns=to_str_list(content.get('ai_grammar_patterns')),
            collocations=to_str_list(content.get('ai_collocations')),
            learning_tips=to_str(content.get('ai_learning_tips')),
            confidence_score=confidence,
            model_used=to_str(content.get('ai_model_used')),
            generated_at=generated_at_dt,
        )
    
    async def _fetch_word_context(self, session, word_kanji: str) -> tuple[Optional[Dict], List[Dict]]:
        """Fetch word data and related neighbors for context"""
        
        logger.info(f"Fetching word context for: '{word_kanji}' (type: {type(word_kanji)})")
        
        # Get word data - use the same pattern as lexical endpoints
        word_query = """
        MATCH (w:Word)
        WHERE coalesce(w.standard_orthography, w.kanji) = $kanji
        OPTIONAL MATCH (w)-[:BELONGS_TO_DOMAIN]->(d:SemanticDomain)
        OPTIONAL MATCH (w)-[:HAS_POS]->(p:POSTag)
        RETURN coalesce(w.standard_orthography, w.kanji) AS kanji,
               coalesce(w.reading_hiragana, w.hiragana) AS hiragana,
               w.translation AS translation,
               COALESCE(w.difficulty_numeric, 1) AS difficulty_numeric, 
               COALESCE(w.etymology, '') AS etymology, 
               COALESCE(w.jlpt_level, '') AS jlpt_level,
               head(collect(d.name)) AS domain,
               head(collect(p.primary_pos)) AS pos_primary
        LIMIT 1
        """
        result = await session.run(word_query, kanji=word_kanji)
        word_record = await result.single()
        
        logger.info(f"Query result: {word_record}")
        
        if not word_record:
            logger.error(f"No word record found for: '{word_kanji}'")
            return None, []
        
        word_data = dict(word_record)
        
        # Get related neighbors for context
        neighbors_query = """
        MATCH (w:Word)
        WHERE coalesce(w.standard_orthography, w.kanji) = $kanji
        MATCH (w)-[r:SYNONYM_OF]-(n:Word)
        RETURN coalesce(n.standard_orthography, n.kanji) AS kanji,
               n.translation AS translation,
               r.synonym_strength AS synonym_strength
        ORDER BY r.synonym_strength DESC
        LIMIT 5
        """
        neighbors_result = await session.run(neighbors_query, kanji=word_kanji)
        neighbors = [dict(record) for record in await neighbors_result.data()]
        
        return word_data, neighbors
    
    def _parse_ai_response(self, content_text: str) -> Optional[AIWordContent]:
        """Parse AI response JSON into structured content"""
        try:
            # Clean up the response text
            content_text = content_text.strip()
            if content_text.startswith('```json'):
                content_text = content_text[7:]
            if content_text.endswith('```'):
                content_text = content_text[:-3]
            
            data = json.loads(content_text)
            
            return AIWordContent(
                definitions=data.get('definitions', []),
                examples=data.get('examples', []),
                cultural_notes=data.get('cultural_notes', ''),
                kanji_breakdown=data.get('kanji_breakdown', ''),
                grammar_patterns=data.get('grammar_patterns', []),
                collocations=data.get('collocations', []),
                learning_tips=data.get('learning_tips', ''),
                confidence_score=float(data.get('confidence_score', 0.8)),
                model_used=self.model,
                generated_at=datetime.now()
            )
            
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error(f"Failed to parse AI response: {e}")
            logger.error(f"Response content: {content_text[:500]}...")
            return None
    
    async def _store_content(self, session, word_kanji: str, content: AIWordContent, word_level: str = None):
        """Store AI content in Neo4j database with level-specific information"""
        query = """
        MATCH (w:Word)
        WHERE coalesce(w.standard_orthography, w.kanji) = $kanji
        SET w.ai_definitions = $definitions,
            w.ai_examples = $examples,
            w.ai_cultural_notes = $cultural_notes,
            w.ai_kanji_breakdown = $kanji_breakdown,
            w.ai_grammar_patterns = $grammar_patterns,
            w.ai_collocations = $collocations,
            w.ai_learning_tips = $learning_tips,
            w.ai_confidence_score = $confidence_score,
            w.ai_model_used = $model_used,
            w.ai_generated_at = $generated_at,
            w.ai_content_version = $version,
            w.ai_target_level = $target_level
        """
        
        await session.run(query, 
            kanji=word_kanji,
            definitions=content.definitions,
            examples=content.examples,
            cultural_notes=content.cultural_notes,
            kanji_breakdown=content.kanji_breakdown,
            grammar_patterns=content.grammar_patterns,
            collocations=content.collocations,
            learning_tips=content.learning_tips,
            confidence_score=content.confidence_score,
            model_used=content.model_used,
            generated_at=content.generated_at,
            version="1.0",
            target_level=word_level
        )
    
    async def get_word_content(self, word_kanji: str, session = None) -> Optional[AIWordContent]:
        """Get AI content for a word, generating if needed"""
        return await self.generate_word_content(word_kanji, session, force_regenerate=False)

    async def fetch_existing_word_content(self, word_kanji: str, session = None) -> Optional[AIWordContent]:
        """Fetch existing AI content for a word without triggering generation."""
        if not session:
            async for session in get_neo4j_session():
                break
        existing = await self._get_existing_content(session, word_kanji)
        if not existing:
            return None
        return self._parse_existing_content(existing)
    
    async def get_word_content_by_level(self, word_kanji: str, target_level: str = None, session = None) -> Optional[AIWordContent]:
        """
        Get AI content for a word filtered by target level
        
        Args:
            word_kanji: The kanji of the word
            target_level: JLPT level to filter by (e.g., 'N5', 'N4', etc.)
            session: Neo4j session (optional)
            
        Returns:
            AIWordContent object or None if not found
        """
        if not session:
            async for session in get_neo4j_session():
                break
        
        try:
            # First check if content exists for the specific level
            if target_level:
                query = """
                MATCH (w:Word {kanji: $kanji})
                WHERE w.ai_generated_at IS NOT NULL 
                AND (w.ai_target_level = $target_level OR w.ai_target_level IS NULL)
                RETURN w.ai_definitions AS ai_definitions,
                       w.ai_examples AS ai_examples,
                       w.ai_cultural_notes AS ai_cultural_notes,
                       w.ai_kanji_breakdown AS ai_kanji_breakdown,
                       w.ai_grammar_patterns AS ai_grammar_patterns,
                       w.ai_collocations AS ai_collocations,
                       w.ai_learning_tips AS ai_learning_tips,
                       w.ai_confidence_score AS ai_confidence_score,
                       w.ai_model_used AS ai_model_used,
                       w.ai_generated_at AS ai_generated_at,
                       w.ai_content_version AS ai_content_version,
                       w.ai_target_level AS ai_target_level
                ORDER BY w.ai_generated_at DESC
                LIMIT 1
                """
                result = await session.run(query, kanji=word_kanji, target_level=target_level)
            else:
                # Get any existing content
                result = await session.run(self._get_existing_content_query(), kanji=word_kanji)
            
            record = await result.single()
            if record:
                return self._parse_existing_content(dict(record))
            
            # If no content exists for the level, generate new content
            return await self.generate_word_content(word_kanji, session, force_regenerate=False)
            
        except Exception as e:
            logger.error(f"Error getting word content by level for {word_kanji}: {e}")
            return None
    
    def _get_existing_content_query(self) -> str:
        """Get the query for existing content"""
        return """
        MATCH (w:Word {kanji: $kanji})
        WHERE w.ai_generated_at IS NOT NULL
        RETURN w.ai_definitions AS ai_definitions,
               w.ai_examples AS ai_examples,
               w.ai_cultural_notes AS ai_cultural_notes,
               w.ai_kanji_breakdown AS ai_kanji_breakdown,
               w.ai_grammar_patterns AS ai_grammar_patterns,
               w.ai_collocations AS ai_collocations,
               w.ai_learning_tips AS ai_learning_tips,
               w.ai_confidence_score AS ai_confidence_score,
               w.ai_model_used AS ai_model_used,
               w.ai_generated_at AS ai_generated_at,
               w.ai_content_version AS ai_content_version,
               w.ai_target_level AS ai_target_level
        """
    
    async def regenerate_word_content(self, word_kanji: str, session = None) -> Optional[AIWordContent]:
        """Force regenerate AI content for a word"""
        return await self.generate_word_content(word_kanji, session, force_regenerate=True)

# Global service instance
ai_word_content_service = AIWordContentService()
