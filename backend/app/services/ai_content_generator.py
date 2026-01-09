"""
Enhanced AI Content Generator
Leverages the rich knowledge graph to generate intelligent learning content.
"""

import asyncio
from typing import List, Dict, Optional, Any, Tuple
from enum import Enum
import structlog
from pydantic import BaseModel
import json
from openai import AsyncOpenAI
from google import genai

from app.core.config import settings
from app.db import get_neo4j_session

logger = structlog.get_logger()


class ContentType(str, Enum):
    """Types of content that can be generated."""
    GRAMMAR_EXPLANATION = "grammar_explanation"
    USAGE_EXAMPLES = "usage_examples"
    CULTURAL_NOTES = "cultural_notes"
    PRACTICE_EXERCISES = "practice_exercises"
    MNEMONICS = "mnemonics"
    SYNONYM_EXPLANATION = "synonym_explanation"
    DIFFICULTY_PROGRESSION = "difficulty_progression"


class GeneratedContent(BaseModel):
    """Generated content model."""
    content_type: ContentType
    target_word: str
    content: str
    confidence_score: float
    ai_provider: str
    ai_model: str
    source_data: Dict[str, Any]
    validation_status: str = "pending"


class AIContentGenerator:
    """Advanced AI content generator using knowledge graph context."""
    
    def __init__(self):
        # Initialize AI clients
        self.openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        if settings.GEMINI_API_KEY:
            self.genai_client = genai.Client(api_key=settings.GEMINI_API_KEY)
        else:
            self.genai_client = None
    
    async def get_word_context(
        self, 
        neo4j_session,
        word_kanji: str
    ) -> Dict[str, Any]:
        """
        Get rich context for a word from the knowledge graph.
        
        Args:
            neo4j_session: Neo4j session
            word_kanji: Kanji representation of the word
            
        Returns:
            Rich context dictionary
        """
        query = """
        MATCH (w:Word)
        WHERE coalesce(w.standard_orthography, w.kanji) = $kanji
        
        // Get basic word information
        OPTIONAL MATCH (w)-[:HAS_DIFFICULTY]->(d:DifficultyLevel)
        OPTIONAL MATCH (w)-[:HAS_ETYMOLOGY]->(e:Etymology)
        OPTIONAL MATCH (w)-[:HAS_POS]->(p:POSTag)
        
        // Get semantic context
        OPTIONAL MATCH (w)-[:BELONGS_TO_DOMAIN]->(sd:SemanticDomain)
        OPTIONAL MATCH (w)-[:HAS_MUTUAL_SENSE]->(ms:MutualSense)
        
        // Get synonyms with strength
        OPTIONAL MATCH (w)-[r:SYNONYM_OF]->(syn:Word)
        WHERE r.synonym_strength > 0.5
        
        // Get words in same difficulty level
        OPTIONAL MATCH (w)-[:HAS_DIFFICULTY]->(d)<-[:HAS_DIFFICULTY]-(similar:Word)
        WHERE similar.translation IS NOT NULL AND similar <> w
        
        // Get words in same semantic domain
        OPTIONAL MATCH (w)-[:BELONGS_TO_DOMAIN]->(sd)<-[:BELONGS_TO_DOMAIN]-(related:Word)
        WHERE related.translation IS NOT NULL AND related <> w
        
        WITH w, d, e, p,
             collect(DISTINCT {
                 name: sd.name, 
                 translation: sd.translation
             }) as semantic_domains,
             collect(DISTINCT {
                 sense: ms.sense,
                 translation: ms.translation
             }) as mutual_senses,
             collect(DISTINCT {
                 kanji: coalesce(syn.standard_orthography, syn.kanji),
                 translation: syn.translation,
                 strength: r.synonym_strength,
                 explanation: r.synonymy_explanation
             }) as synonyms,
             collect(DISTINCT {
                 kanji: coalesce(similar.standard_orthography, similar.kanji),
                 translation: similar.translation
             })[0..5] as similar_difficulty,
             collect(DISTINCT {
                 kanji: coalesce(related.standard_orthography, related.kanji),
                 translation: related.translation
             })[0..5] as related_words
        
        RETURN {
            kanji: coalesce(w.standard_orthography, w.kanji),
            katakana: coalesce(w.reading_katakana, w.katakana),
            hiragana: coalesce(w.reading_hiragana, w.hiragana),
            translation: w.translation,
            difficulty: d.level,
            difficulty_numeric: d.numeric_level,
            etymology: e.type,
            etymology_description: e.description,
            pos_primary: p.primary_pos,
            pos_detailed: p.tag,
            semantic_domains: semantic_domains,
            mutual_senses: mutual_senses,
            synonyms: synonyms,
            similar_difficulty_words: similar_difficulty,
            related_words: related_words
        } as word_context
        """
        
        result = await neo4j_session.run(query, kanji=word_kanji)
        record = await result.single()
        
        if record:
            return record['word_context']
        else:
            return {}
    
    async def generate_grammar_explanation(
        self,
        word_context: Dict[str, Any],
        provider: str = "openai"
    ) -> GeneratedContent:
        """
        Generate detailed grammar explanation for a word.
        
        Args:
            word_context: Rich word context from knowledge graph
            provider: AI provider to use
            
        Returns:
            Generated grammar explanation
        """
        # Create rich prompt with context
        prompt = self._create_grammar_prompt(word_context)
        
        if provider == "openai":
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert Japanese language teacher. Create clear, educational grammar explanations that help learners understand how to use words correctly."
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                temperature=0.7,
                max_completion_tokens=500
            )
            
            content = response.choices[0].message.content
            model = "gpt-4o-mini"
            
        elif provider == "gemini":
            if not self.genai_client:
                raise ValueError("Gemini API key not configured")
            
            response = self.genai_client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt
            )
            content = response.text
            model = "gemini-2.5-flash"
        
        return GeneratedContent(
            content_type=ContentType.GRAMMAR_EXPLANATION,
            target_word=word_context.get('kanji', ''),
            content=content,
            confidence_score=0.85,  # Could be calculated based on context richness
            ai_provider=provider,
            ai_model=model,
            source_data=word_context
        )
    
    async def generate_usage_examples(
        self,
        word_context: Dict[str, Any],
        count: int = 5,
        provider: str = "openai"
    ) -> GeneratedContent:
        """
        Generate contextual usage examples leveraging synonym relationships.
        
        Args:
            word_context: Rich word context
            count: Number of examples to generate
            provider: AI provider
            
        Returns:
            Generated usage examples
        """
        prompt = self._create_usage_examples_prompt(word_context, count)
        
        if provider == "openai":
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a Japanese language expert. Create natural, practical example sentences that show how words are used in real contexts. Include both formal and casual usage when appropriate."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.8,
                max_completion_tokens=800
            )
            
            content = response.choices[0].message.content
            model = "gpt-4o-mini"
        
        elif provider == "gemini":
            if not self.genai_client:
                raise ValueError("Gemini API key not configured")
            
            response = self.genai_client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt
            )
            content = response.text
            model = "gemini-2.5-flash"
        
        return GeneratedContent(
            content_type=ContentType.USAGE_EXAMPLES,
            target_word=word_context.get('kanji', ''),
            content=content,
            confidence_score=0.9,
            ai_provider=provider,
            ai_model=model,
            source_data=word_context
        )
    
    async def generate_cultural_notes(
        self,
        word_context: Dict[str, Any],
        provider: str = "openai"
    ) -> GeneratedContent:
        """
        Generate cultural context notes based on etymology and semantic domains.
        
        Args:
            word_context: Rich word context
            provider: AI provider
            
        Returns:
            Generated cultural notes
        """
        prompt = self._create_cultural_notes_prompt(word_context)
        
        if provider == "openai":
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o",  # Use more powerful model for cultural nuances
                messages=[
                    {
                        "role": "system",
                        "content": "You are a Japanese cultural expert and language teacher. Provide insightful cultural context that helps learners understand not just what words mean, but how they reflect Japanese culture, history, and social concepts."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.7,
                max_completion_tokens=400
            )
            
            content = response.choices[0].message.content
            model = "gpt-4o"
        
        return GeneratedContent(
            content_type=ContentType.CULTURAL_NOTES,
            target_word=word_context.get('kanji', ''),
            content=content,
            confidence_score=0.8,
            ai_provider=provider,
            ai_model=model,
            source_data=word_context
        )
    
    async def generate_synonym_explanation(
        self,
        word_context: Dict[str, Any],
        provider: str = "openai"
    ) -> GeneratedContent:
        """
        Generate explanations for synonym relationships using graph data.
        
        Args:
            word_context: Rich word context with synonyms
            provider: AI provider
            
        Returns:
            Generated synonym explanation
        """
        if not word_context.get('synonyms'):
            return None
        
        prompt = self._create_synonym_explanation_prompt(word_context)
        
        if provider == "openai":
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a Japanese linguistics expert. Explain the subtle differences between synonymous words, helping learners understand when and how to use each one appropriately."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.6,
                max_completion_tokens=600
            )
            
            content = response.choices[0].message.content
            model = "gpt-4o-mini"
        
        return GeneratedContent(
            content_type=ContentType.SYNONYM_EXPLANATION,
            target_word=word_context.get('kanji', ''),
            content=content,
            confidence_score=0.85,
            ai_provider=provider,
            ai_model=model,
            source_data=word_context
        )
    
    def _create_grammar_prompt(self, word_context: Dict[str, Any]) -> str:
        """Create grammar explanation prompt with rich context."""
        word = word_context.get('kanji', '')
        reading = word_context.get('katakana', word_context.get('hiragana', ''))
        translation = word_context.get('translation', '')
        pos = word_context.get('pos_primary', '')
        difficulty = word_context.get('difficulty', '')
        etymology = word_context.get('etymology', '')
        
        prompt = f"""
Create a clear grammar explanation for the Japanese word:

Word: {word} ({reading}) - {translation}
Part of Speech: {pos}
Difficulty Level: {difficulty}
Etymology: {etymology}

Please explain:
1. How this word functions grammatically
2. What particles it typically takes
3. Common sentence patterns it appears in
4. Any conjugation rules if applicable
5. Formality level and appropriate usage contexts

Make the explanation clear for language learners at the {difficulty} level.
"""
        
        return prompt.strip()
    
    def _create_usage_examples_prompt(self, word_context: Dict[str, Any], count: int) -> str:
        """Create usage examples prompt with semantic context."""
        word = word_context.get('kanji', '')
        reading = word_context.get('katakana', word_context.get('hiragana', ''))
        translation = word_context.get('translation', '')
        
        # Add semantic context
        semantic_info = ""
        if word_context.get('semantic_domains'):
            domains = [d.get('translation', d.get('name', '')) for d in word_context['semantic_domains'][:3]]
            semantic_info = f"Semantic domains: {', '.join(domains)}"
        
        # Add synonym context
        synonym_info = ""
        if word_context.get('synonyms'):
            synonyms = [f"{s.get('kanji', '')} ({s.get('translation', '')})" 
                       for s in word_context['synonyms'][:3]]
            synonym_info = f"Related words: {', '.join(synonyms)}"
        
        prompt = f"""
Create {count} natural Japanese example sentences for:

Word: {word} ({reading}) - {translation}
{semantic_info}
{synonym_info}

Requirements:
1. Show the word in different contexts
2. Include both formal and casual examples
3. Vary sentence complexity appropriately
4. Add English translations
5. Show natural, realistic usage

Format each example as:
Japanese: [sentence]
English: [translation]
Context: [when/how this would be used]
"""
        
        return prompt.strip()
    
    def _create_cultural_notes_prompt(self, word_context: Dict[str, Any]) -> str:
        """Create cultural notes prompt using etymology and semantic domains."""
        word = word_context.get('kanji', '')
        translation = word_context.get('translation', '')
        etymology = word_context.get('etymology', '')
        etymology_desc = word_context.get('etymology_description', '')
        
        # Semantic context
        domains = word_context.get('semantic_domains', [])
        domain_context = ""
        if domains:
            domain_names = [d.get('translation', d.get('name', '')) for d in domains[:2]]
            domain_context = f"Semantic areas: {', '.join(domain_names)}"
        
        prompt = f"""
Provide cultural insights for the Japanese word:

Word: {word} - {translation}
Etymology: {etymology} ({etymology_desc})
{domain_context}

Explain:
1. Cultural or historical significance
2. How this word reflects Japanese values or concepts
3. Social contexts where it's particularly important
4. Any cultural nuances learners should understand
5. How usage might differ from direct English equivalents

Focus on cultural understanding that helps learners use the word appropriately in Japanese society.
"""
        
        return prompt.strip()
    
    def _create_synonym_explanation_prompt(self, word_context: Dict[str, Any]) -> str:
        """Create synonym explanation prompt using graph relationships."""
        word = word_context.get('kanji', '')
        translation = word_context.get('translation', '')
        synonyms = word_context.get('synonyms', [])
        
        synonym_details = []
        for syn in synonyms[:4]:  # Limit to top 4 synonyms
            kanji = syn.get('kanji', '')
            trans = syn.get('translation', '')
            strength = syn.get('strength', 0)
            explanation = syn.get('explanation', '')
            synonym_details.append(f"- {kanji} ({trans}) - similarity: {strength:.2f}")
            if explanation:
                synonym_details.append(f"  Relationship: {explanation}")
        
        prompt = f"""
Explain the differences between these Japanese synonyms:

Main word: {word} ({translation})

Synonyms:
{chr(10).join(synonym_details)}

Please explain:
1. Subtle meaning differences between these words
2. When to use each word appropriately
3. Formality levels and contexts
4. Any connotational differences
5. Example situations for each word

Help learners understand which word to choose in different situations.
"""
        
        return prompt.strip()
    
    async def generate_comprehensive_content(
        self,
        neo4j_session,
        word_kanji: str,
        content_types: List[ContentType] = None,
        provider: str = "openai"
    ) -> List[GeneratedContent]:
        """
        Generate comprehensive learning content for a word.
        
        Args:
            neo4j_session: Neo4j session
            word_kanji: Target word
            content_types: Types of content to generate
            provider: AI provider
            
        Returns:
            List of generated content items
        """
        if content_types is None:
            content_types = [
                ContentType.GRAMMAR_EXPLANATION,
                ContentType.USAGE_EXAMPLES,
                ContentType.CULTURAL_NOTES,
                ContentType.SYNONYM_EXPLANATION
            ]
        
        # Get rich context from knowledge graph
        word_context = await self.get_word_context(neo4j_session, word_kanji)
        
        if not word_context:
            logger.warning("No context found for word", word=word_kanji)
            return []
        
        generated_content = []
        
        for content_type in content_types:
            try:
                if content_type == ContentType.GRAMMAR_EXPLANATION:
                    content = await self.generate_grammar_explanation(word_context, provider)
                elif content_type == ContentType.USAGE_EXAMPLES:
                    content = await self.generate_usage_examples(word_context, provider=provider)
                elif content_type == ContentType.CULTURAL_NOTES:
                    content = await self.generate_cultural_notes(word_context, provider)
                elif content_type == ContentType.SYNONYM_EXPLANATION:
                    content = await self.generate_synonym_explanation(word_context, provider)
                
                if content:
                    generated_content.append(content)
                    
            except Exception as e:
                logger.error("Failed to generate content", 
                           content_type=content_type,
                           word=word_kanji,
                           error=str(e))
        
        logger.info("Generated comprehensive content", 
                   word=word_kanji,
                   content_count=len(generated_content))
        
        return generated_content


async def demo_content_generation():
    """Demo function to test content generation."""
    generator = AIContentGenerator()
    
    async with get_neo4j_session() as session:
        # Test with a word that should have rich context
        content_items = await generator.generate_comprehensive_content(
            session,
            "物",  # "thing/object" - should have many relationships
            provider="openai"
        )
        
        for item in content_items:
            print(f"\n=== {item.content_type.value.upper()} ===")
            print(f"Target: {item.target_word}")
            print(f"Provider: {item.ai_provider} ({item.ai_model})")
            print(f"Confidence: {item.confidence_score}")
            print(f"Content:\n{item.content}")


if __name__ == "__main__":
    asyncio.run(demo_content_generation())
