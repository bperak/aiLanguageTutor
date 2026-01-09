"""
AI Content API Endpoints

Provides endpoints for generating and retrieving AI-enhanced word content
"""

from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.db import get_neo4j_session
from app.services.ai_word_content_service import ai_word_content_service, AIWordContent
from .auth import get_current_user
from app.models.database_models import User
from neo4j.exceptions import ServiceUnavailable

router = APIRouter(tags=["ai-content"])


async def get_neo4j_session_authenticated(
    current_user: User = Depends(get_current_user),
):
    """
    Get a Neo4j session, but only after the request is authenticated.

    Reason: some routes should return 401/403 without touching Neo4j. By making
    the Neo4j session depend on auth, we prevent unauthenticated requests from
    triggering Neo4j init/connection errors (which would surface as 500s).
    """
    async for session in get_neo4j_session():
        yield session


async def get_neo4j_session_safe():
    """
    Get a Neo4j session but convert connection failures into an HTTP 503.

    This keeps public routes from crashing test runs when Neo4j isn't available.
    """
    try:
        async for session in get_neo4j_session():
            yield session
    except ServiceUnavailable as e:
        raise HTTPException(status_code=503, detail=f"Neo4j unavailable: {str(e)}")


def _isoformat_any(value: Any) -> str:
    """Safely convert Neo4j or Python datetime to ISO8601 string."""
    try:
        if hasattr(value, "to_native"):
            # neo4j.time.DateTime -> python datetime
            return value.to_native().isoformat()
        if hasattr(value, "isoformat"):
            return value.isoformat()
        return str(value)
    except Exception:
        from datetime import datetime
        return datetime.now().isoformat()

class WordContentRequest(BaseModel):
    """Request model for generating word content"""
    word_kanji: str
    force_regenerate: bool = False

class WordContentResponse(BaseModel):
    """Response model for word content"""
    word_kanji: str
    definitions: list[str]
    examples: list[str]
    cultural_notes: str
    kanji_breakdown: str
    grammar_patterns: list[str]
    collocations: list[str]
    learning_tips: str
    confidence_score: float
    model_used: str
    generated_at: str
    has_existing_content: bool

@router.post("/generate", response_model=WordContentResponse)
async def generate_word_content(
    request: WordContentRequest,
    session = Depends(get_neo4j_session_authenticated),
    current_user: User = Depends(get_current_user)
) -> WordContentResponse:
    """
    Generate AI-enhanced content for a word
    
    Args:
        request: Word content generation request
        session: Neo4j database session
        current_user: Current authenticated user
        
    Returns:
        Generated word content with AI enhancements
    """
    try:
        # Generate or retrieve AI content
        content = await ai_word_content_service.generate_word_content(
            word_kanji=request.word_kanji,
            session=session,
            force_regenerate=request.force_regenerate
        )
        
        if not content:
            raise HTTPException(
                status_code=404, 
                detail=f"Could not generate content for word: {request.word_kanji}"
            )
        
        return WordContentResponse(
            word_kanji=request.word_kanji,
            definitions=content.definitions,
            examples=content.examples,
            cultural_notes=content.cultural_notes,
            kanji_breakdown=content.kanji_breakdown,
            grammar_patterns=content.grammar_patterns,
            collocations=content.collocations,
            learning_tips=content.learning_tips,
            confidence_score=content.confidence_score,
            model_used=content.model_used,
            generated_at=_isoformat_any(content.generated_at),
            has_existing_content=not request.force_regenerate
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating content: {str(e)}"
        )

@router.get("/word/{word_kanji}")
async def get_word_content(
    word_kanji: str,
    session = Depends(get_neo4j_session_safe),
) -> WordContentResponse:
    """
    Get AI-enhanced content for a word
    
    Args:
        word_kanji: The kanji of the word
        session: Neo4j database session
    Returns:
        Word content with AI enhancements
    """
    try:
        # Fetch existing content only; do NOT auto-generate on GET
        content = await ai_word_content_service.fetch_existing_word_content(
            word_kanji=word_kanji,
            session=session,
        )
        
        if not content:
            raise HTTPException(
                status_code=404,
                detail=f"No content available for word: {word_kanji}"
            )

        return {
            "word_kanji": word_kanji,
            "definitions": content.definitions,
            "examples": content.examples,
            "cultural_notes": content.cultural_notes,
            "kanji_breakdown": content.kanji_breakdown,
            "grammar_patterns": content.grammar_patterns,
            "collocations": content.collocations,
            "learning_tips": content.learning_tips,
            "confidence_score": float(content.confidence_score),
            "model_used": content.model_used,
            "generated_at": _isoformat_any(content.generated_at),
            "has_existing_content": True,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving content: {str(e)}"
        )

@router.get("/word/{word_kanji}/level/{target_level}")
async def get_word_content_by_level(
    word_kanji: str,
    target_level: str,
    session = Depends(get_neo4j_session_safe),
) -> WordContentResponse:
    """
    Get AI-enhanced content for a word filtered by JLPT level
    
    Args:
        word_kanji: The kanji of the word
        target_level: JLPT level (N5, N4, N3, N2, N1)
        session: Neo4j database session
    Returns:
        Word content with AI enhancements for the specified level
    """
    try:
        # Get content for the specific level
        content = await ai_word_content_service.get_word_content_by_level(
            word_kanji=word_kanji,
            target_level=target_level,
            session=session
        )
        
        if not content:
            raise HTTPException(
                status_code=404,
                detail=f"No content available for word: {word_kanji} at level: {target_level}"
            )
        
        return {
            "word_kanji": word_kanji,
            "definitions": content.definitions,
            "examples": content.examples,
            "cultural_notes": content.cultural_notes,
            "kanji_breakdown": content.kanji_breakdown,
            "grammar_patterns": content.grammar_patterns,
            "collocations": content.collocations,
            "learning_tips": content.learning_tips,
            "confidence_score": float(content.confidence_score),
            "model_used": content.model_used,
            "generated_at": _isoformat_any(content.generated_at),
            "has_existing_content": True,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving content: {str(e)}"
        )

@router.post("/regenerate/{word_kanji}", response_model=WordContentResponse)
async def regenerate_word_content(
    word_kanji: str,
    session = Depends(get_neo4j_session_authenticated),
    current_user: User = Depends(get_current_user)
) -> WordContentResponse:
    """
    Force regenerate AI content for a word
    
    Args:
        word_kanji: The kanji of the word
        session: Neo4j database session
        current_user: Current authenticated user
        
    Returns:
        Regenerated word content with AI enhancements
    """
    try:
        # Force regenerate content
        content = await ai_word_content_service.regenerate_word_content(
            word_kanji=word_kanji,
            session=session
        )
        
        if not content:
            raise HTTPException(
                status_code=404,
                detail=f"Could not regenerate content for word: {word_kanji}"
            )
        
        return WordContentResponse(
            word_kanji=word_kanji,
            definitions=content.definitions,
            examples=content.examples,
            cultural_notes=content.cultural_notes,
            kanji_breakdown=content.kanji_breakdown,
            grammar_patterns=content.grammar_patterns,
            collocations=content.collocations,
            learning_tips=content.learning_tips,
            confidence_score=content.confidence_score,
            model_used=content.model_used,
            generated_at=_isoformat_any(content.generated_at),
            has_existing_content=False
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error regenerating content: {str(e)}"
        )

@router.get("/status/{word_kanji}")
async def get_content_status(
    word_kanji: str,
    session = Depends(get_neo4j_session_safe),
) -> Dict[str, Any]:
    """
    Check the status of AI content for a word
    
    Args:
        word_kanji: The kanji of the word
        session: Neo4j database session
        current_user: Current authenticated user
        
    Returns:
        Content status information
    """
    try:
        # Check if content exists
        query = """
        MATCH (w:Word {kanji: $kanji})
        RETURN w.ai_generated_at IS NOT NULL AS has_content,
               w.ai_generated_at,
               w.ai_confidence_score,
               w.ai_model_used,
               w.ai_content_version
        """
        result = await session.run(query, kanji=word_kanji)
        record = await result.single()
        
        if not record:
            raise HTTPException(
                status_code=404,
                detail=f"Word not found: {word_kanji}"
            )
        
        return {
            "word_kanji": word_kanji,
            "has_content": record["has_content"],
            "generated_at": _isoformat_any(record["ai_generated_at"]) if record["ai_generated_at"] else None,
            "confidence_score": record["ai_confidence_score"],
            "model_used": record["ai_model_used"],
            "content_version": record["ai_content_version"]
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error checking content status: {str(e)}"
        )

@router.get("/words-needing-content")
async def get_words_needing_content(
    limit: int = Query(50, ge=1, le=200),
    difficulty_min: int = Query(1, ge=1, le=6),
    difficulty_max: int = Query(6, ge=1, le=6),
    session = Depends(get_neo4j_session_safe),
) -> Dict[str, Any]:
    """
    Get list of words that need AI content generation
    
    Args:
        limit: Maximum number of words to return
        difficulty_min: Minimum difficulty level
        difficulty_max: Maximum difficulty level
        session: Neo4j database session
        current_user: Current authenticated user
        
    Returns:
        List of words needing content generation
    """
    try:
        query = """
        MATCH (w:Word)
        WHERE w.ai_generated_at IS NULL
        AND w.difficulty_numeric >= $difficulty_min
        AND w.difficulty_numeric <= $difficulty_max
        RETURN w.kanji AS kanji, w.hiragana AS hiragana, w.translation AS translation, w.difficulty_numeric AS difficulty_numeric, coalesce(w.pos_primary_norm, w.pos1, w.pos_primary) AS pos_primary
        ORDER BY w.difficulty_numeric ASC, w.kanji ASC
        LIMIT $limit
        """
        
        result = await session.run(query, 
            difficulty_min=difficulty_min,
            difficulty_max=difficulty_max,
            limit=limit
        )
        
        words = []
        async for record in result:
            words.append({
                "kanji": record["kanji"],
                "hiragana": record["hiragana"],
                "translation": record["translation"],
                "difficulty_level": record["difficulty_numeric"],
                "pos": record["pos_primary"],  # Already canonical from query
            })
        
        return {
            "words": words,
            "count": len(words),
            "difficulty_range": f"{difficulty_min}-{difficulty_max}",
            "limit": limit
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving words needing content: {str(e)}"
        )
