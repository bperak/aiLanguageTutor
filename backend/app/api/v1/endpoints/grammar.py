"""
Grammar Patterns API Endpoints
=============================

API endpoints for accessing and managing Japanese grammar patterns
from the Marugoto textbook series integrated with the knowledge graph.
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from neo4j import AsyncSession

from app.core.config import settings
from app.db import get_neo4j_session
from app.services.grammar_service import GrammarService
from app.models.database_models import User
from app.api.v1.endpoints.auth import get_current_user

router = APIRouter(tags=["grammar"])

# Pydantic schemas
class GrammarPatternResponse(BaseModel):
    """Response model for grammar patterns"""
    id: str
    sequence_number: int
    pattern: str
    pattern_romaji: str
    textbook_form: str
    textbook_form_romaji: str
    example_sentence: str
    example_romaji: str
    classification: str
    textbook: str
    topic: str
    lesson: str
    jfs_category: str

class SimilarPatternResponse(BaseModel):
    """Response model for similar patterns"""
    pattern: str
    pattern_romaji: str
    example_sentence: str
    textbook: str
    similarity_reason: str

class LearningPathResponse(BaseModel):
    """Response model for learning paths"""
    from_pattern: str
    to_pattern: str
    path_length: int
    intermediate_patterns: List[str]

class PatternRecommendationResponse(BaseModel):
    """Response model for pattern recommendations"""
    recommended_patterns: List[GrammarPatternResponse]
    reasoning: str
    difficulty_match: float

@router.get("/patterns", response_model=List[GrammarPatternResponse])
async def get_grammar_patterns(
    level: Optional[str] = Query(None, description="Textbook level filter"),
    classification: Optional[str] = Query(None, description="Grammar classification filter"),
    jfs_category: Optional[str] = Query(None, description="JFS category filter"),
    search: Optional[str] = Query(None, description="Search in pattern or example"),
    limit: int = Query(20, ge=1, le=100, description="Number of results to return"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    neo4j_session: AsyncSession = Depends(get_neo4j_session),
    current_user: User = Depends(get_current_user)
):
    """
    Get grammar patterns with optional filtering and pagination.
    
    - **level**: Filter by textbook level (e.g., '入門(りかい)', '初級1(りかい)')
    - **classification**: Filter by grammar function (e.g., '説明', '時間的前後')
    - **jfs_category**: Filter by JFS topic (e.g., '自分と家族', '食生活')
    - **search**: Search in pattern text or example sentences
    - **limit**: Maximum number of results (1-100)
    - **offset**: Number of results to skip for pagination
    """
    try:
        grammar_service = GrammarService(neo4j_session)
        patterns = await grammar_service.get_patterns(
            level=level,
            classification=classification,
            jfs_category=jfs_category,
            search=search,
            limit=limit,
            offset=offset
        )
        return patterns
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving patterns: {str(e)}")

@router.get("/patterns/{pattern_id}", response_model=GrammarPatternResponse)
async def get_grammar_pattern(
    pattern_id: str,
    neo4j_session: AsyncSession = Depends(get_neo4j_session),
    current_user: User = Depends(get_current_user)
):
    """Get a specific grammar pattern by ID"""
    try:
        grammar_service = GrammarService(neo4j_session)
        pattern = await grammar_service.get_pattern_by_id(pattern_id)
        
        if not pattern:
            raise HTTPException(status_code=404, detail="Grammar pattern not found")
        
        return pattern
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving pattern: {str(e)}")

@router.get("/patterns/{pattern_id}/similar", response_model=List[SimilarPatternResponse])
async def get_similar_patterns(
    pattern_id: str,
    limit: int = Query(5, ge=1, le=20, description="Number of similar patterns to return"),
    neo4j_session: AsyncSession = Depends(get_neo4j_session)
):
    """Get patterns similar to the specified pattern"""
    try:
        grammar_service = GrammarService(neo4j_session)
        similar_patterns = await grammar_service.get_similar_patterns(pattern_id, limit)
        return similar_patterns
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error finding similar patterns: {str(e)}")

@router.get("/patterns/{pattern_id}/prerequisites", response_model=List[GrammarPatternResponse])
async def get_prerequisites(
    pattern_id: str,
    neo4j_session: AsyncSession = Depends(get_neo4j_session),
    current_user: User = Depends(get_current_user)
):
    """Get prerequisite patterns for the specified pattern"""
    try:
        grammar_service = GrammarService(neo4j_session)
        prerequisites = await grammar_service.get_prerequisites(pattern_id)
        return prerequisites
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error finding prerequisites: {str(e)}")

@router.get("/learning-path", response_model=List[LearningPathResponse])
async def get_learning_path(
    from_pattern: str = Query(..., description="Starting pattern ID"),
    to_level: str = Query(..., description="Target textbook level"),
    max_depth: int = Query(3, ge=1, le=5, description="Maximum path depth"),
    neo4j_session: AsyncSession = Depends(get_neo4j_session),
    current_user: User = Depends(get_current_user)
):
    """Generate a learning path from a pattern to a target level"""
    try:
        grammar_service = GrammarService(neo4j_session)
        learning_paths = await grammar_service.get_learning_path(
            from_pattern=from_pattern,
            to_level=to_level,
            max_depth=max_depth
        )
        return learning_paths
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating learning path: {str(e)}")

@router.get("/patterns/by-word/{word}", response_model=List[GrammarPatternResponse])
async def get_patterns_by_word(
    word: str,
    limit: int = Query(10, ge=1, le=50, description="Number of patterns to return"),
    neo4j_session: AsyncSession = Depends(get_neo4j_session),
    current_user: User = Depends(get_current_user)
):
    """Get grammar patterns that use a specific Japanese word"""
    try:
        grammar_service = GrammarService(neo4j_session)
        patterns = await grammar_service.get_patterns_by_word(word, limit)
        return patterns
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error finding patterns for word: {str(e)}")

@router.get("/recommendations", response_model=PatternRecommendationResponse)
async def get_pattern_recommendations(
    user_level: str = Query(..., description="User's current textbook level"),
    known_patterns: List[str] = Query([], description="List of pattern IDs user already knows"),
    focus_classification: Optional[str] = Query(None, description="Focus on specific classification"),
    limit: int = Query(5, ge=1, le=20, description="Number of recommendations"),
    neo4j_session: AsyncSession = Depends(get_neo4j_session),
    current_user: User = Depends(get_current_user)
):
    """Get personalized grammar pattern recommendations"""
    try:
        grammar_service = GrammarService(neo4j_session)
        recommendations = await grammar_service.get_personalized_recommendations(
            user_level=user_level,
            known_patterns=known_patterns,
            focus_classification=focus_classification,
            limit=limit
        )
        return recommendations
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating recommendations: {str(e)}")

@router.get("/classifications", response_model=List[Dict[str, Any]])
async def get_classifications(
    neo4j_session: AsyncSession = Depends(get_neo4j_session)
):
    """Get all available grammar classifications"""
    try:
        grammar_service = GrammarService(neo4j_session)
        classifications = await grammar_service.get_all_classifications()
        return classifications
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving classifications: {str(e)}")

@router.get("/levels", response_model=List[Dict[str, Any]])
async def get_textbook_levels(
    neo4j_session: AsyncSession = Depends(get_neo4j_session)
):
    """Get all available textbook levels"""
    try:
        grammar_service = GrammarService(neo4j_session)
        levels = await grammar_service.get_all_levels()
        return levels
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving levels: {str(e)}")

@router.get("/jfs-categories", response_model=List[Dict[str, Any]])
async def get_jfs_categories(
    neo4j_session: AsyncSession = Depends(get_neo4j_session)
):
    """Get all available JFS categories"""
    try:
        grammar_service = GrammarService(neo4j_session)
        categories = await grammar_service.get_all_jfs_categories()
        return categories
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving JFS categories: {str(e)}")

@router.get("/stats", response_model=Dict[str, Any])
async def get_grammar_stats(
    neo4j_session: AsyncSession = Depends(get_neo4j_session),
    current_user: User = Depends(get_current_user)
):
    """Get comprehensive statistics about the grammar graph"""
    try:
        grammar_service = GrammarService(neo4j_session)
        stats = await grammar_service.get_graph_statistics()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving statistics: {str(e)}")

# Admin endpoints (require admin privileges)
@router.post("/patterns/{pattern_id}/validate")
async def validate_pattern(
    pattern_id: str,
    neo4j_session: AsyncSession = Depends(get_neo4j_session),
    current_user: User = Depends(get_current_user)  # Add admin check
):
    """Validate a grammar pattern (admin only)"""
    # Implementation for pattern validation
    pass

@router.post("/import/marugoto")
async def import_marugoto_data(
    neo4j_session: AsyncSession = Depends(get_neo4j_session),
    current_user: User = Depends(get_current_user)  # Add admin check
):
    """Trigger Marugoto data import (admin only)"""
    # Implementation for triggering import
    pass
