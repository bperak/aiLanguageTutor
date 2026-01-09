"""
Grammar Patterns API Endpoints
=============================

API endpoints for accessing and managing Japanese grammar patterns
from the Marugoto textbook series integrated with the knowledge graph.
"""

from typing import List, Optional, Dict, Any, Union
from datetime import datetime, date, timedelta
from collections import Counter
import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from neo4j import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession as AsyncDBSession

from app.core.config import settings
from app.db import get_neo4j_session, get_postgresql_session
from app.services.grammar_service import GrammarService
from app.models.database_models import User, ConversationSession, ConversationMessage, ConversationInteraction
from app.api.v1.endpoints.auth import get_current_user
from app.services.ai_conversation_practice import AIConversationPractice, ConversationScenario, DialogueTurn, ConversationContext
from app.services.grammar_ai_content_service import GrammarAIContentService

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
    what_is: Optional[str] = None

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

# Progress tracking schemas
class PatternProgressRequest(BaseModel):
    """Request model for updating pattern progress"""
    pattern_id: str = Field(..., description="Grammar pattern ID")
    grade: str = Field(..., pattern="^(again|hard|good|easy)$", description="SRS grade")
    study_time_seconds: Optional[int] = Field(None, ge=0, description="Time spent studying")
    confidence_self_reported: Optional[int] = Field(None, ge=1, le=5, description="Self-reported confidence")

class PatternProgressResponse(BaseModel):
    """Response model for pattern progress"""
    pattern_id: str
    pattern_name: str
    mastery_level: int
    last_studied: Optional[str]
    next_review_date: Optional[str]
    is_completed: bool
    study_count: int
    ease_factor: float
    interval_days: int

class LearningPathStatsResponse(BaseModel):
    """Response model for learning path statistics"""
    total_patterns: int
    completed_patterns: int
    average_mastery: float
    estimated_completion_days: int
    total_study_time_minutes: int

class UserProgressSummaryResponse(BaseModel):
    """Response model for user progress summary"""
    total_patterns_studied: int
    total_patterns_mastered: int
    current_streak_days: int
    weekly_study_minutes: int
    average_mastery_level: float
    patterns_due_today: int
    patterns_overdue: int

@router.get("/patterns", response_model=List[GrammarPatternResponse])
async def get_grammar_patterns(
    level: Optional[str] = Query(None, description="Textbook level filter"),
    classification: Optional[str] = Query(None, description="Grammar classification filter"),
    jfs_category: Optional[str] = Query(None, description="JFS category filter"),
    search: Optional[str] = Query(None, description="Search in pattern or example"),
    limit: int = Query(20, ge=1, le=100, description="Number of results to return"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    neo4j_session: AsyncSession = Depends(get_neo4j_session),
    current_user: User = Depends(get_current_user),
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

@router.get("/patterns/count", response_model=Dict[str, int])
async def count_grammar_patterns(
    level: Optional[str] = Query(None, description="Textbook level filter"),
    classification: Optional[str] = Query(None, description="Grammar classification filter"),
    jfs_category: Optional[str] = Query(None, description="JFS category filter"),
    search: Optional[str] = Query(None, description="Search in pattern or example"),
    neo4j_session: AsyncSession = Depends(get_neo4j_session)
):
    """Return total count for patterns matching filters."""
    try:
        grammar_service = GrammarService(neo4j_session)
        total = await grammar_service.count_patterns(
            level=level,
            classification=classification,
            jfs_category=jfs_category,
            search=search,
        )
        return {"total": total}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error counting patterns: {str(e)}")

@router.get("/patterns/{pattern_id}", response_model=GrammarPatternResponse)
async def get_grammar_pattern(
    pattern_id: str,
    neo4j_session: AsyncSession = Depends(get_neo4j_session)
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
    neo4j_session: AsyncSession = Depends(get_neo4j_session),
    current_user: User = Depends(get_current_user),
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
    current_user: User = Depends(get_current_user),
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

## (moved count endpoint above dynamic route)

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

# Progress tracking endpoints
@router.post("/progress/study", response_model=PatternProgressResponse)
async def record_pattern_study(
    progress_request: PatternProgressRequest,
    neo4j_session: AsyncSession = Depends(get_neo4j_session),
    current_user: User = Depends(get_current_user)
):
    """Record a study session for a grammar pattern"""
    try:
        from app.services.grammar_progress_service import GrammarProgressService
        progress_service = GrammarProgressService(neo4j_session)
        
        progress = await progress_service.record_study_session(
            user_id=str(current_user.id),
            pattern_id=progress_request.pattern_id,
            grade=progress_request.grade,
            study_time_seconds=progress_request.study_time_seconds,
            confidence_self_reported=progress_request.confidence_self_reported
        )
        return progress
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error recording study session: {str(e)}")

@router.get("/progress/patterns", response_model=List[PatternProgressResponse])
async def get_user_pattern_progress(
    pattern_ids: Optional[List[str]] = Query(None, description="Specific pattern IDs to get progress for"),
    include_completed: bool = Query(True, description="Include completed patterns"),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of results"),
    neo4j_session: AsyncSession = Depends(get_neo4j_session),
    current_user: User = Depends(get_current_user)
):
    """Get user's progress for grammar patterns"""
    try:
        from app.services.grammar_progress_service import GrammarProgressService
        progress_service = GrammarProgressService(neo4j_session)
        
        progress_list = await progress_service.get_user_pattern_progress(
            user_id=str(current_user.id),
            pattern_ids=pattern_ids,
            include_completed=include_completed,
            limit=limit
        )
        return progress_list
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving pattern progress: {str(e)}")

@router.get("/progress/due", response_model=List[PatternProgressResponse])
async def get_patterns_due_for_review(
    include_overdue: bool = Query(True, description="Include overdue patterns"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of results"),
    neo4j_session: AsyncSession = Depends(get_neo4j_session),
    current_user: User = Depends(get_current_user)
):
    """Get patterns due for review today"""
    try:
        from app.services.grammar_progress_service import GrammarProgressService
        progress_service = GrammarProgressService(neo4j_session)
        
        due_patterns = await progress_service.get_patterns_due_for_review(
            user_id=str(current_user.id),
            include_overdue=include_overdue,
            limit=limit
        )
        return due_patterns
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving due patterns: {str(e)}")

@router.get("/progress/summary", response_model=UserProgressSummaryResponse)
async def get_user_progress_summary(
    neo4j_session: AsyncSession = Depends(get_neo4j_session),
    current_user: User = Depends(get_current_user)
):
    """Get comprehensive progress summary for the user"""
    try:
        from app.services.grammar_progress_service import GrammarProgressService
        progress_service = GrammarProgressService(neo4j_session)
        
        summary = await progress_service.get_user_progress_summary(str(current_user.id))
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving progress summary: {str(e)}")

@router.get("/progress/learning-path-stats", response_model=LearningPathStatsResponse)
async def get_learning_path_stats(
    pattern_ids: List[str] = Query(..., description="Pattern IDs in the learning path"),
    neo4j_session: AsyncSession = Depends(get_neo4j_session),
    current_user: User = Depends(get_current_user)
):
    """Get statistics for a specific learning path"""
    try:
        from app.services.grammar_progress_service import GrammarProgressService
        progress_service = GrammarProgressService(neo4j_session)
        
        stats = await progress_service.get_learning_path_stats(
            user_id=str(current_user.id),
            pattern_ids=pattern_ids
        )
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving learning path stats: {str(e)}")

# === AI CONVERSATIONAL PRACTICE ENDPOINTS ===

class ConversationScenarioRequest(BaseModel):
    """Request model for generating conversation scenarios"""
    pattern_id: str = Field(..., description="Grammar pattern ID")
    context: str = Field(..., description="Conversation context (restaurant, office, family, etc.)")
    difficulty_level: str = Field("intermediate", description="Difficulty level")
    provider: str = Field("openai", description="AI provider (openai/gemini)")
    custom_scenario: Optional[str] = Field(None, description="Custom scenario description")

class ConversationTurnRequest(BaseModel):
    """Request model for conversation turns"""
    scenario_id: str = Field(..., description="Scenario ID")
    user_message: str = Field(..., description="User's message in Japanese")
    provider: str = Field("openai", description="AI provider")
    pattern_id: Optional[str] = Field(None, description="Grammar pattern ID for learning focus")
    context: Optional[str] = Field(None, description="Conversation context")

class DialogueTurnResponse(BaseModel):
    """Response model for dialogue turns"""
    speaker: str
    message: str
    transliteration: Optional[str] = None  # New: romanized version
    translation: Optional[str] = None      # New: English translation
    feedback: Optional[str] = None
    user_feedback: Optional[str] = None  # New: feedback about user's input
    grammar_focus: Optional[str] = None
    corrections: Optional[List[str]] = None
    hints: Optional[List[str]] = None

class ConversationScenarioResponse(BaseModel):
    """Response model for conversation scenarios"""
    scenario_id: str
    pattern_id: str
    pattern: str
    context: str
    situation: str
    learning_objective: str
    ai_character: str
    user_role: str
    difficulty_level: str
    initial_dialogue: List[DialogueTurnResponse]


# === AI OVERVIEW CONTENT ENDPOINTS ===

class JapaneseTextItem(BaseModel):
    """
    A single Japanese text item with all representations for learners.
    Every Japanese string must have kana reading, romaji, and English translation.
    """
    jp: str = Field(default="", description="Japanese text (kanji + kana)")
    kana: str = Field(default="", description="Hiragana/katakana reading")
    romaji: str = Field(default="", description="Romanized reading with proper spacing")
    en: str = Field(default="", description="English translation")


class FormationStep(BaseModel):
    """A single step in the pattern formation explanation."""
    slot: str = Field(..., description="The slot/component name in English (e.g., 'Noun', 'Verb')")
    jp: str = Field("", description="Japanese representation")
    kana: str = Field("", description="Hiragana reading")
    romaji: str = Field("", description="Romaji representation")
    en: str = Field("", description="English description of what goes in this slot")


class HowToForm(BaseModel):
    """
    Structured formation explanation for learners who may not read Japanese yet.
    """
    summary_en: str = Field(..., description="Plain English explanation of how to form this pattern")
    pattern_template: str = Field("", description="Simple template like: [Noun] + ga + dekimasu")
    steps: List[FormationStep] = Field(default_factory=list, description="Step-by-step formation breakdown")
    casual_variant: Optional[JapaneseTextItem] = Field(None, description="Casual/informal version if applicable")
    formal_variant: Optional[JapaneseTextItem] = Field(None, description="Formal version if different")
    notes_en: List[str] = Field(default_factory=list, description="Additional notes in English")


class CommonMistake(BaseModel):
    """A common mistake learners make with this pattern."""
    mistake_en: str = Field(default="", description="Description of the mistake in English")
    wrong: Optional[JapaneseTextItem] = Field(None, description="Incorrect example")
    correct: Optional[JapaneseTextItem] = Field(None, description="Correct example")


class GrammarOverviewResponse(BaseModel):
    """
    AI-generated grammar pattern overview with learner-focused content.
    
    Designed to be usable by learners who cannot read Japanese yet.
    Every Japanese item includes kana reading, romaji, and English translation.
    """
    # Core explanation in English
    what_is_en: str = Field("", description="What this pattern means and when to use it (English)")
    
    # Structured formation explanation
    how_to_form: Optional[HowToForm] = Field(None, description="Step-by-step formation guide")
    
    # Usage and nuance
    usage_en: str = Field("", description="When and how to use this pattern (English)")
    nuance_en: str = Field("", description="Subtle meanings and comparisons (English)")
    
    # Common mistakes with examples (accepts both strings for legacy and structured objects)
    common_mistakes: List[Union[CommonMistake, str]] = Field(default_factory=list)
    
    # Cultural context
    cultural_context_en: Optional[str] = Field(None, description="Cultural notes (English)")
    
    # Examples with full representations (accepts both old format and new)
    examples: List[Union[JapaneseTextItem, Dict[str, str]]] = Field(default_factory=list)
    
    # Tips for learners
    tips_en: str = Field("", description="Practical tips for remembering/using (English)")
    
    # Related patterns
    related_patterns: List[str] = Field(default_factory=list)
    
    # Metadata
    model_used: Optional[str] = None
    generated_at: Optional[str] = None
    
    # Legacy fields for backward compatibility (will be migrated)
    what_is: Optional[str] = Field(None, description="LEGACY: Use what_is_en instead")
    formation: Optional[str] = Field(None, description="LEGACY: Use how_to_form instead")
    usage: Optional[str] = Field(None, description="LEGACY: Use usage_en instead")
    nuance: Optional[str] = Field(None, description="LEGACY: Use nuance_en instead")
    tips: Optional[str] = Field(None, description="LEGACY: Use tips_en instead")
    cultural_context: Optional[str] = Field(None, description="LEGACY: Use cultural_context_en instead")


@router.get("/patterns/{pattern_id}/ai-overview", response_model=GrammarOverviewResponse)
async def get_ai_overview(
    pattern_id: str,
    neo4j_session: AsyncSession = Depends(get_neo4j_session),
    current_user: User | None = Depends(get_current_user),
):
    """Get stored AI overview for a grammar pattern if available."""
    service = GrammarAIContentService()
    overview = await service.get_stored_overview(neo4j_session, pattern_id)
    if not overview:
        raise HTTPException(status_code=404, detail="AI overview not found")
    return overview


@router.post("/patterns/{pattern_id}/ai-overview", response_model=GrammarOverviewResponse)
async def generate_ai_overview(
    pattern_id: str,
    provider: str = Query("openai", pattern="^(openai|gemini)$"),
    model: str = Query("gpt-5.1"),
    force: bool = Query(False),
    neo4j_session: AsyncSession = Depends(get_neo4j_session),
    current_user: User = Depends(get_current_user),
):
    """Generate AI overview using graph context; persists to Neo4j for caching."""
    try:
        service = GrammarAIContentService()
        overview = await service.generate_overview(
            session=neo4j_session,
            pattern_id=pattern_id,
            provider=provider,
            model=model,
            force=force,
        )
        return overview
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate overview: {str(e)}")

async def _generate_initial_ai_message(
    pattern: str,
    context: str,
    situation: str,
    ai_character: str,
    user_role: str,
    learning_objective: str,
    provider: str = "openai"
) -> DialogueTurnResponse:
    """
    Generate initial AI greeting message with full meta structure.
    
    Args:
        pattern: Target grammar pattern
        context: Conversation context (e.g., "restaurant", "office")
        situation: Specific situation description
        ai_character: Description of AI character
        user_role: Description of user's role
        learning_objective: Learning objective for the session
        provider: AI provider to use
        
    Returns:
        DialogueTurnResponse with full meta structure (message, transliteration, translation, feedback)
    """
    from app.services.ai_conversation_practice import AIConversationPractice
    
    practice = AIConversationPractice()
    
    # Generate initial greeting with full meta structure
    initial_prompt = f"""
You are a Japanese grammar teacher starting a practice conversation. 

Situation: {situation}
Your character: {ai_character}
User's role: {user_role}
Target grammar pattern: {pattern}
Learning objective: {learning_objective}
Context: {context}

Provide an opening greeting in this format:

CONVERSATIONAL_RESPONSE: [A natural Japanese greeting (1-2 sentences) that introduces the situation and invites the learner to respond using the "{pattern}" pattern. Make it contextually appropriate and engaging. This should feel like a natural conversation starter, not a lesson.]

TRANSLITERATION: [Provide the romanized version (romaji) of your Japanese greeting to help with pronunciation]

TRANSLATION: [Provide the English translation of your Japanese greeting]

TEACHING_DIRECTION: [English explanation of: 1) Your teaching strategy for this opening, 2) How your greeting sets up the conversation to practice "{pattern}", 3) SPECIFIC HINT: "Try responding with..." - give them a concrete example of how to use "{pattern}" in their first response, 4) What they should focus on, 5) Overall dialogue direction for mastering "{pattern}"]

Make the greeting warm, natural, and contextually appropriate. Always include a specific response hint that shows exactly how they can use the target pattern in their first response.
"""
    
    # Get AI response
    ai_response = await practice.ai_chat.generate_reply(
        provider=provider,
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": initial_prompt}],
        system_prompt=f"You are both a conversation partner and language teacher. Focus on the grammar pattern '{pattern}' while maintaining natural conversation flow. Always provide CONVERSATIONAL_RESPONSE, TRANSLITERATION, TRANSLATION, and TEACHING_DIRECTION sections."
    )
    
    # Parse the response
    response_content = ai_response.get("content", "")
    
    # Extract all parts
    ai_message = "こんにちは！よろしくお願いします。"  # Default fallback
    transliteration = ""  # Default fallback
    translation = ""  # Default fallback
    teaching_direction = f"Welcome! Let's practice the '{pattern}' pattern together. Try using it in your response."  # Default fallback
    
    # Parse CONVERSATIONAL_RESPONSE
    if "CONVERSATIONAL_RESPONSE:" in response_content:
        conv_start = response_content.find("CONVERSATIONAL_RESPONSE:")
        translit_start = response_content.find("TRANSLITERATION:")
        
        if conv_start != -1 and translit_start != -1:
            ai_message = response_content[conv_start + 24:translit_start].strip()
        elif conv_start != -1:
            # Fallback if no transliteration section
            teach_start = response_content.find("TEACHING_DIRECTION:")
            if teach_start != -1:
                ai_message = response_content[conv_start + 24:teach_start].strip()
    
    # Parse TRANSLITERATION
    if "TRANSLITERATION:" in response_content:
        translit_start = response_content.find("TRANSLITERATION:")
        trans_start = response_content.find("TRANSLATION:")
        
        if translit_start != -1 and trans_start != -1:
            transliteration = response_content[translit_start + 16:trans_start].strip()
        elif translit_start != -1:
            # Fallback if no translation section
            teach_start = response_content.find("TEACHING_DIRECTION:")
            if teach_start != -1:
                transliteration = response_content[translit_start + 16:teach_start].strip()
    
    # Parse TRANSLATION
    if "TRANSLATION:" in response_content:
        trans_start = response_content.find("TRANSLATION:")
        teach_start = response_content.find("TEACHING_DIRECTION:")
        
        if trans_start != -1 and teach_start != -1:
            translation = response_content[trans_start + 12:teach_start].strip()
        elif trans_start != -1:
            translation = response_content[trans_start + 12:].strip()
    
    # Parse TEACHING_DIRECTION
    if "TEACHING_DIRECTION:" in response_content:
        teach_start = response_content.find("TEACHING_DIRECTION:")
        if teach_start != -1:
            teaching_direction = response_content[teach_start + 19:].strip()
    
    # Generate hints based on teaching direction
    hints = []
    if "Try responding with" in teaching_direction or "try responding with" in teaching_direction:
        hints.append("🎯 Follow the specific response hint in the teaching strategy above")
    else:
        hints.append(f"💡 Try using the target pattern '{pattern}' in your first response")
        hints.append("📖 The teaching strategy above shows you exactly how to respond")
    
    return DialogueTurnResponse(
        speaker="ai",
        message=ai_message,
        transliteration=transliteration if transliteration else None,
        translation=translation if translation else None,
        feedback=teaching_direction,
        user_feedback=None,  # No user input yet for initial message
        grammar_focus=pattern,
        corrections=None,
        hints=hints
    )


@router.post("/conversation/start", response_model=ConversationScenarioResponse)
async def start_conversation_practice(
    request: ConversationScenarioRequest,
    neo4j_session: AsyncSession = Depends(get_neo4j_session),
    current_user: User = Depends(get_current_user)
):
    """Start an AI-powered conversation practice session"""
    try:
        # Get pattern details
        grammar_service = GrammarService(neo4j_session)
        pattern_data = await grammar_service.get_pattern_by_id(request.pattern_id)
        
        if not pattern_data:
            raise HTTPException(status_code=404, detail="Grammar pattern not found")
        
        # Generate conversation scenario
        practice = AIConversationPractice()
        
        # If custom scenario provided, use it; otherwise use standard context
        if request.custom_scenario:
            # For custom scenarios, create a simplified scenario
            scenario_id = f"{request.pattern_id}_custom_{request.difficulty_level}"
            
            scenario = ConversationScenario(
                scenario_id=scenario_id,
                pattern_id=request.pattern_id,
                pattern=pattern_data["pattern"],
                context="custom",
                situation=request.custom_scenario,
                learning_objective=f"Practice using the {pattern_data['pattern']} pattern in a custom scenario: {request.custom_scenario[:50]}...",
                ai_character="A friendly conversation partner",
                user_role="Yourself in this custom situation",
                difficulty_level=request.difficulty_level,
                dialogue_turns=[]  # Not used anymore - we generate initial message separately
            )
        else:
            # Convert context string to enum for standard scenarios
            try:
                context_enum = ConversationContext(request.context.lower())
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid context: {request.context}")
            
            scenario = await practice.generate_conversation_scenario(
                pattern_id=request.pattern_id,
                pattern=pattern_data["pattern"],
                pattern_classification=pattern_data["classification"],
                example_sentence=pattern_data["example_sentence"],
                context=context_enum,
                difficulty_level=request.difficulty_level,
                provider=request.provider
            )
        
        # Generate initial AI message with full meta structure
        initial_message = await _generate_initial_ai_message(
            pattern=scenario.pattern,
            context=scenario.context,
            situation=scenario.situation,
            ai_character=scenario.ai_character,
            user_role=scenario.user_role,
            learning_objective=scenario.learning_objective,
            provider=request.provider or "openai"
        )
        
        return ConversationScenarioResponse(
            scenario_id=scenario.scenario_id,
            pattern_id=scenario.pattern_id,
            pattern=scenario.pattern,
            context=scenario.context,  # Already a string now, no need for .value
            situation=scenario.situation,
            learning_objective=scenario.learning_objective,
            ai_character=scenario.ai_character,
            user_role=scenario.user_role,
            difficulty_level=scenario.difficulty_level,
            initial_dialogue=[initial_message]  # Return single initial message with full meta structure
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start conversation practice: {str(e)}")

@router.post("/conversation/turn", response_model=DialogueTurnResponse)
async def continue_conversation(
    request: ConversationTurnRequest,
    neo4j_session: AsyncSession = Depends(get_neo4j_session),
    db: AsyncDBSession = Depends(get_postgresql_session),
    current_user: User = Depends(get_current_user)
):
    """Continue an AI conversation with user input and get feedback, persisting to DB and recording evidence"""
    try:
        practice = AIConversationPractice()
        
        # Extract pattern_id from scenario_id if not provided
        pattern_id = request.pattern_id
        if not pattern_id:
            # Extract pattern_id from scenario_id (format: "pattern_id_context_difficulty")
            scenario_parts = request.scenario_id.split('_')
            if len(scenario_parts) >= 2:
                pattern_id = '_'.join(scenario_parts[:2])  # e.g., "grammar_001" from "grammar_001_restaurant_intermediate"
            else:
                raise HTTPException(status_code=400, detail="Could not extract pattern_id from scenario_id")
        
        # Get pattern details to maintain focus on learning objective
        grammar_service = GrammarService(neo4j_session)
        pattern_data = await grammar_service.get_pattern_by_id(pattern_id)
        
        if not pattern_data:
            raise HTTPException(status_code=404, detail="Grammar pattern not found")
        
        user_message = request.user_message.strip()
        
        # Get pattern safely
        target_pattern = pattern_data.get('pattern', 'Japanese grammar') if isinstance(pattern_data, dict) else getattr(pattern_data, 'pattern', 'Japanese grammar')
        
        # Extract context from scenario_id or use provided context
        context = request.context
        if not context:
            # Extract context from scenario_id (format: "pattern_id_context_difficulty")
            scenario_parts = request.scenario_id.split('_')
            if len(scenario_parts) >= 3:
                context = scenario_parts[2]  # e.g., "restaurant" from "grammar_001_restaurant_intermediate"
            else:
                context = "general conversation"
        
        # First, get immediate user feedback
        user_feedback_prompt = f"""
As a Japanese language teacher, analyze this student's Japanese response in the context of our conversation:

Student input: "{user_message}"
Target grammar pattern: "{target_pattern}"
Conversation context: {context}
Learning scenario: We're practicing the "{target_pattern}" pattern in a {context} setting

Provide contextual feedback in this format:

USER_ANALYSIS: [Analyze: 1) How well does this fit the conversation flow? 2) Did they use the target pattern "{target_pattern}" effectively? 3) Grammar accuracy in context, 4) Naturalness for this scenario, 5) Brief improvement suggestion that maintains conversation flow. Be encouraging and conversational.]

Keep it conversational and contextually relevant.
"""

        # Get user-focused feedback
        user_feedback_response = await practice.ai_chat.generate_reply(
            provider=request.provider or "openai",
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": user_feedback_prompt}],
            system_prompt="You are analyzing a student's Japanese input for grammar learning. Be encouraging but precise."
        )

        # Then get coordinated teaching response  
        coordinated_prompt = f"""
You are a Japanese grammar teacher having a practice conversation. 

Student just said: "{user_message}"
Target grammar pattern: "{target_pattern}"  
Context: {context}
Their performance analysis: {user_feedback_response.get('content', '')}

Provide your response in this format:

CONVERSATIONAL_RESPONSE: [Brief Japanese response (1-2 sentences) that continues conversation while creating opportunities for them to practice "{target_pattern}" again. Focus on grammar practice, not just topic discussion.]

TRANSLITERATION: [Provide the romanized version (romaji) of your Japanese response to help with pronunciation]

TRANSLATION: [Provide the English translation of your Japanese response]

TEACHING_DIRECTION: [English explanation of: 1) Your teaching strategy in this turn, 2) How your Japanese response guides them toward better pattern usage, 3) SPECIFIC HINT: "Try responding with..." - give them a concrete example of how to use "{target_pattern}" in their next response, 4) What grammar point to focus on, 5) Overall dialogue direction for mastering "{target_pattern}"]

Always include a specific response hint that shows exactly how they can use the target pattern in their next turn.
"""
        
        # Get coordinated response
        coordinated_response = await practice.ai_chat.generate_reply(
            provider=request.provider or "openai",
            model="gpt-4o-mini", 
            messages=[{"role": "user", "content": coordinated_prompt}],
            system_prompt=f"You are both a conversation partner and language teacher. Focus on the grammar pattern '{target_pattern}' while maintaining natural conversation flow. Always provide both CONVERSATIONAL_RESPONSE and TECHNICAL_FEEDBACK sections."
        )
        
        # Parse the user feedback response
        user_feedback_content = user_feedback_response.get("content", "")
        user_analysis = "Good work! Keep practicing."  # Default fallback
        
        if "USER_ANALYSIS:" in user_feedback_content:
            user_analysis = user_feedback_content.replace("USER_ANALYSIS:", "").strip()
        
        # Parse the coordinated teaching response
        response_content = coordinated_response.get("content", "")
        
        # Extract all parts
        ai_message = "続けてみましょう。"  # Default fallback
        transliteration = ""  # Default fallback
        translation = ""  # Default fallback
        teaching_direction = "Continue practicing the target grammar pattern."  # Default fallback
        
        # Parse CONVERSATIONAL_RESPONSE
        if "CONVERSATIONAL_RESPONSE:" in response_content:
            conv_start = response_content.find("CONVERSATIONAL_RESPONSE:")
            translit_start = response_content.find("TRANSLITERATION:")
            
            if conv_start != -1 and translit_start != -1:
                ai_message = response_content[conv_start + 24:translit_start].strip()
            elif conv_start != -1:
                # Fallback if no transliteration section
                teach_start = response_content.find("TEACHING_DIRECTION:")
                if teach_start != -1:
                    ai_message = response_content[conv_start + 24:teach_start].strip()
        
        # Parse TRANSLITERATION
        if "TRANSLITERATION:" in response_content:
            translit_start = response_content.find("TRANSLITERATION:")
            trans_start = response_content.find("TRANSLATION:")
            
            if translit_start != -1 and trans_start != -1:
                transliteration = response_content[translit_start + 16:trans_start].strip()
            elif translit_start != -1:
                # Fallback if no translation section
                teach_start = response_content.find("TEACHING_DIRECTION:")
                if teach_start != -1:
                    transliteration = response_content[translit_start + 16:teach_start].strip()
        
        # Parse TRANSLATION
        if "TRANSLATION:" in response_content:
            trans_start = response_content.find("TRANSLATION:")
            teach_start = response_content.find("TEACHING_DIRECTION:")
            
            if trans_start != -1 and teach_start != -1:
                translation = response_content[trans_start + 12:teach_start].strip()
            elif trans_start != -1:
                translation = response_content[trans_start + 12:].strip()
        
        # Parse TEACHING_DIRECTION
        if "TEACHING_DIRECTION:" in response_content:
            teach_start = response_content.find("TEACHING_DIRECTION:")
            if teach_start != -1:
                teaching_direction = response_content[teach_start + 19:].strip()
        
        # Generate corrections and hints focused on the target pattern and coordinated feedback
        corrections = []
        hints = []
        
        # Use the same target pattern as above for consistency
        
        # Check if student used the target pattern
        pattern_used = target_pattern in user_message if target_pattern else False
        
        # Extract specific response hints from teaching direction
        if "Try responding with" in teaching_direction or "try responding with" in teaching_direction:
            # The teaching direction includes specific hints
            if "pattern" in teaching_direction.lower():
                hints.append(f"🎯 Follow the specific response hint in the teaching strategy above")
        else:
            # Generate pattern-focused hints as fallback
            if target_pattern:
                if not pattern_used:
                    hints.append(f"💡 Try using the target pattern '{target_pattern}' in your next response")
                    hints.append(f"📖 The teaching strategy above shows you exactly how to respond")
                else:
                    hints.append(f"✨ Great use of '{target_pattern}'! Check the hint above for your next response")
        
        # Extract specific corrections from the teaching direction feedback
        if "correction" in teaching_direction.lower() or "should be" in teaching_direction.lower():
            # The teaching direction will include specific corrections
            if "particle" in teaching_direction.lower():
                corrections.append("Check particle usage - refer to teaching direction above")
            if "tense" in teaching_direction.lower() or "form" in teaching_direction.lower():
                corrections.append("Review verb forms - see teaching analysis")
        
        # Persist conversation session and messages to Postgres
        try:
            # Get or create conversation session for this scenario
            session_query = select(ConversationSession).where(
                and_(
                    ConversationSession.user_id == current_user.id,
                    ConversationSession.conversation_context['scenario_id'].as_string() == request.scenario_id,
                    ConversationSession.status == 'active'
                )
            ).order_by(ConversationSession.created_at.desc()).limit(1)
            
            result = await db.execute(session_query)
            session = result.scalar_one_or_none()
            
            if not session:
                # Create new session
                session = ConversationSession(
                    user_id=current_user.id,
                    title=f"Grammar Conversation: {target_pattern}",
                    language_code='ja',
                    session_type='practice',
                    status='active',
                    ai_provider=request.provider or 'openai',
                    ai_model='gpt-4o-mini',
                    conversation_context={
                        'scenario_id': request.scenario_id,
                        'pattern_id': pattern_id,
                        'pattern': target_pattern,
                        'context': context,
                        'stage': 'interaction'
                    },
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                db.add(session)
                await db.flush()
            
            # Get next message order
            max_order_query = select(func.max(ConversationMessage.message_order)).where(
                ConversationMessage.session_id == session.id
            )
            max_order_result = await db.execute(max_order_query)
            next_order = (max_order_result.scalar() or 0) + 1
            
            # Save user message
            user_msg = ConversationMessage(
                session_id=session.id,
                role='user',
                content=user_message,
                content_type='text',
                message_order=next_order,
                created_at=datetime.utcnow(),
                grammar_points_mentioned=[pattern_id]
            )
            db.add(user_msg)
            await db.flush()
            
            # Save AI response message
            ai_msg = ConversationMessage(
                session_id=session.id,
                role='assistant',
                content=ai_message,
                content_type='text',
                message_order=next_order + 1,
                ai_provider=request.provider or 'openai',
                ai_model='gpt-4o-mini',
                created_at=datetime.utcnow(),
                grammar_points_mentioned=[pattern_id],
                contains_correction=len(corrections) > 0
            )
            db.add(ai_msg)
            await db.flush()
            
            # Record interaction evidence with rubric
            # Determine if pattern was used correctly
            pattern_used_correctly = pattern_used and len(corrections) == 0
            is_correct = pattern_used_correctly
            
            # Build rubric scores
            rubric_scores = {
                'pattern_used': pattern_used,
                'form_accurate': len(corrections) == 0,
                'meaning_matches': 'meaning' in user_analysis.lower() and 'good' in user_analysis.lower()
            }
            
            # Extract error tags from corrections
            error_tags = []
            if corrections:
                for correction in corrections:
                    if 'particle' in correction.lower():
                        error_tags.append('particle_usage')
                    if 'tense' in correction.lower() or 'form' in correction.lower():
                        error_tags.append('verb_form')
                    if 'pattern' in correction.lower():
                        error_tags.append('pattern_usage')
            
            # Record evidence
            interaction = ConversationInteraction(
                user_id=current_user.id,
                session_id=session.id,
                message_id=user_msg.id,
                interaction_type='grammar_practiced',
                concept_id=pattern_id,
                concept_type='grammar_point',
                user_response=user_message,
                is_correct=is_correct,
                attempts_count=1,
                hint_used=False,  # Could be enhanced to track hint usage
                confidence_self_reported=None,  # Could be added to request
                metadata={
                    'stage': 'interaction',
                    'rubric_scores': rubric_scores,
                    'error_tags': error_tags,
                    'stage_specific_data': {
                        'scenario_id': request.scenario_id,
                        'context': context,
                        'pattern_used': pattern_used,
                        'corrections_count': len(corrections)
                    }
                },
                created_at=datetime.utcnow()
            )
            db.add(interaction)
            
            # Update session stats
            session.total_messages = (session.total_messages or 0) + 2
            session.user_messages = (session.user_messages or 0) + 1
            session.ai_messages = (session.ai_messages or 0) + 1
            session.updated_at = datetime.utcnow()
            
            await db.commit()
            
        except Exception as db_error:
            await db.rollback()
            # Log but don't fail the request - conversation can continue without persistence
            logger = logging.getLogger(__name__)
            logger.error(f"Error persisting conversation: {db_error}")
        
        return DialogueTurnResponse(
            speaker="ai",
            message=ai_message,
            transliteration=transliteration if transliteration else None,
            translation=translation if translation else None,
            feedback=teaching_direction,  # AI teaching direction feedback  
            user_feedback=user_analysis,  # User input analysis feedback
            grammar_focus=target_pattern,
            corrections=corrections,
            hints=hints
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process conversation turn: {str(e)}")

@router.get("/conversation/contexts", response_model=List[Dict[str, str]])
async def get_conversation_contexts():
    """Get available conversation contexts for practice"""
    contexts = [
        {"value": "restaurant", "label": "Restaurant", "description": "Ordering food, talking with servers"},
        {"value": "office", "label": "Office", "description": "Workplace conversations, meetings"},
        {"value": "family", "label": "Family", "description": "Home conversations, daily life"},
        {"value": "shopping", "label": "Shopping", "description": "Store interactions, purchases"},
        {"value": "travel", "label": "Travel", "description": "Tourist situations, directions"},
        {"value": "school", "label": "School", "description": "Classroom settings, academic discussions"},
        {"value": "hospital", "label": "Hospital", "description": "Medical consultations"},
        {"value": "introduction", "label": "Introduction", "description": "Meeting new people, self-introduction"}
    ]
    return contexts

# === GRAMMAR EVIDENCE TRACKING ENDPOINTS ===

class EvidenceRecordRequest(BaseModel):
    """Request model for recording grammar learning evidence"""
    pattern_id: str = Field(..., description="Grammar pattern ID")
    stage: str = Field(..., pattern="^(presentation|comprehension|production|interaction)$", description="Learning stage")
    interaction_type: str = Field(..., description="Type of interaction (e.g., 'grammar_practiced', 'practice_completed')")
    is_correct: Optional[bool] = Field(None, description="Whether the attempt was correct")
    user_response: Optional[str] = Field(None, description="User's response/attempt")
    attempts_count: int = Field(1, ge=1, description="Number of attempts for this interaction")
    hint_used: bool = Field(False, description="Whether user used a hint")
    response_time_seconds: Optional[int] = Field(None, ge=0, description="Time taken to respond")
    confidence_self_reported: Optional[int] = Field(None, ge=1, le=5, description="Self-reported confidence (1-5)")
    rubric_scores: Optional[Dict[str, Any]] = Field(None, description="Rubric breakdown: pattern_used, form_accurate, meaning_matches")
    error_tags: Optional[List[str]] = Field(None, description="Tags for common errors")
    stage_specific_data: Optional[Dict[str, Any]] = Field(None, description="Stage-specific metadata")

class EvidenceRecordResponse(BaseModel):
    """Response model for evidence recording"""
    interaction_id: str
    pattern_id: str
    stage: str
    mastery_level: int
    next_review_date: Optional[str]
    message: str

class EvidenceSummaryResponse(BaseModel):
    """Response model for evidence summary"""
    pattern_id: str
    pattern_name: str
    total_attempts: int
    attempts_by_stage: Dict[str, int]
    correct_rate: float
    mastery_level: int
    last_attempted: Optional[str]
    next_review_date: Optional[str]
    common_error_tags: List[str]
    best_example: Optional[Dict[str, Any]]
    recent_attempts: List[Dict[str, Any]]

@router.post("/evidence/record", response_model=EvidenceRecordResponse)
async def record_grammar_evidence(
    evidence: EvidenceRecordRequest,
    db: AsyncDBSession = Depends(get_postgresql_session),
    current_user: User = Depends(get_current_user)
):
    """
    Record evidence of grammar learning from any stage (presentation, comprehension, production, interaction).
    
    Creates a conversation session if needed, stores the interaction, and updates SRS scheduling.
    """
    try:
        # Get or create a grammar practice session for this pattern
        session_query = select(ConversationSession).where(
            and_(
                ConversationSession.user_id == current_user.id,
                ConversationSession.session_type == 'practice',
                ConversationSession.conversation_context['pattern_id'].as_string() == evidence.pattern_id,
                ConversationSession.status == 'active'
            )
        ).order_by(ConversationSession.created_at.desc()).limit(1)
        
        result = await db.execute(session_query)
        session = result.scalar_one_or_none()
        
        if not session:
            # Create new session for this grammar pattern
            session = ConversationSession(
                user_id=current_user.id,
                title=f"Grammar Practice: {evidence.pattern_id}",
                language_code='ja',
                session_type='practice',
                status='active',
                ai_provider='openai',  # Default, can be overridden
                ai_model='gpt-4o-mini',
                conversation_context={
                    'pattern_id': evidence.pattern_id,
                    'stage': evidence.stage,
                    'topic_focus': 'grammar'
                },
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.add(session)
            await db.flush()  # Get session.id
        
        # Create a message if user_response provided
        message = None
        if evidence.user_response:
            # Get next message order
            max_order_query = select(func.max(ConversationMessage.message_order)).where(
                ConversationMessage.session_id == session.id
            )
            max_order_result = await db.execute(max_order_query)
            next_order = (max_order_result.scalar() or 0) + 1
            
            message = ConversationMessage(
                session_id=session.id,
                role='user',
                content=evidence.user_response,
                content_type='text',
                message_order=next_order,
                created_at=datetime.utcnow(),
                grammar_points_mentioned=[evidence.pattern_id]
            )
            db.add(message)
            await db.flush()  # Get message.id
        
        # Build metadata JSONB
        metadata = {
            'stage': evidence.stage,
            'rubric_scores': evidence.rubric_scores,
            'error_tags': evidence.error_tags,
            'stage_specific_data': evidence.stage_specific_data
        }
        
        # Calculate SRS scheduling (simplified)
        # Get existing progress for this pattern
        existing_query = select(ConversationInteraction).where(
            and_(
                ConversationInteraction.user_id == current_user.id,
                ConversationInteraction.concept_id == evidence.pattern_id,
                ConversationInteraction.concept_type == 'grammar_point'
            )
        ).order_by(ConversationInteraction.created_at.desc()).limit(1)
        
        existing_result = await db.execute(existing_query)
        existing = existing_result.scalar_one_or_none()
        
        current_mastery = existing.mastery_level if existing else 1
        current_ease = float(existing.ease_factor) if existing and existing.ease_factor else 2.5
        current_interval = existing.interval_days if existing else 1
        
        # Simple SRS calculation
        if evidence.is_correct:
            new_mastery = min(5, current_mastery + 1)
            new_ease = min(2.5, current_ease + 0.1)
            new_interval = max(1, int(current_interval * new_ease))
        else:
            new_mastery = max(1, current_mastery - 1)
            new_ease = max(1.3, current_ease - 0.2)
            new_interval = 1
        
        next_review = date.today() + timedelta(days=new_interval)
        
        # Create interaction record
        interaction = ConversationInteraction(
            user_id=current_user.id,
            session_id=session.id,
            message_id=message.id if message else session.id,  # Fallback to session if no message
            interaction_type=evidence.interaction_type,
            concept_id=evidence.pattern_id,
            concept_type='grammar_point',
            user_response=evidence.user_response,
            is_correct=evidence.is_correct,
            attempts_count=evidence.attempts_count,
            hint_used=evidence.hint_used,
            response_time_seconds=evidence.response_time_seconds,
            confidence_self_reported=evidence.confidence_self_reported,
            ease_factor=new_ease,
            interval_days=new_interval,
            next_review_date=next_review,
            mastery_level=new_mastery,
            evidence_metadata=metadata,
            created_at=datetime.utcnow()
        )
        
        db.add(interaction)
        await db.commit()
        
        return EvidenceRecordResponse(
            interaction_id=str(interaction.id),
            pattern_id=evidence.pattern_id,
            stage=evidence.stage,
            mastery_level=new_mastery,
            next_review_date=next_review.isoformat(),
            message="Evidence recorded successfully"
        )
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Error recording evidence: {str(e)}")

@router.get("/evidence/summary", response_model=EvidenceSummaryResponse)
async def get_grammar_evidence_summary(
    pattern_id: str = Query(..., description="Grammar pattern ID"),
    limit: int = Query(10, ge=1, le=50, description="Number of recent attempts to return"),
    db: AsyncDBSession = Depends(get_postgresql_session),
    neo4j_session: AsyncSession = Depends(get_neo4j_session),
    current_user: User = Depends(get_current_user)
):
    """
    Get evidence summary for a grammar pattern - dashboard-friendly view.
    
    Returns aggregated metrics, recent attempts, common errors, and best example.
    """
    try:
        # Get pattern name from Neo4j
        grammar_service = GrammarService(neo4j_session)
        pattern_data = await grammar_service.get_pattern_by_id(pattern_id)
        pattern_name = pattern_data.get('pattern', pattern_id) if pattern_data else pattern_id
        
        # Query all interactions for this pattern
        interactions_query = select(ConversationInteraction).where(
            and_(
                ConversationInteraction.user_id == current_user.id,
                ConversationInteraction.concept_id == pattern_id,
                ConversationInteraction.concept_type == 'grammar_point'
            )
        ).order_by(ConversationInteraction.created_at.desc())
        
        result = await db.execute(interactions_query)
        interactions = result.scalars().all()
        
        if not interactions:
            return EvidenceSummaryResponse(
                pattern_id=pattern_id,
                pattern_name=pattern_name,
                total_attempts=0,
                attempts_by_stage={},
                correct_rate=0.0,
                mastery_level=1,
                last_attempted=None,
                next_review_date=None,
                common_error_tags=[],
                best_example=None,
                recent_attempts=[]
            )
        
        # Aggregate metrics
        total_attempts = len(interactions)
        correct_count = sum(1 for i in interactions if i.is_correct)
        correct_rate = correct_count / total_attempts if total_attempts > 0 else 0.0
        
        # Count by stage
        attempts_by_stage = {}
        for interaction in interactions:
            stage = interaction.evidence_metadata.get('stage', 'unknown') if interaction.evidence_metadata else 'unknown'
            attempts_by_stage[stage] = attempts_by_stage.get(stage, 0) + 1
        
        # Get most recent mastery level and review date
        latest = interactions[0]
        mastery_level = latest.mastery_level
        next_review_date = latest.next_review_date.isoformat() if latest.next_review_date else None
        last_attempted = latest.created_at.isoformat() if latest.created_at else None
        
        # Extract common error tags
        error_tags = []
        for interaction in interactions:
            if interaction.evidence_metadata and interaction.evidence_metadata.get('error_tags'):
                error_tags.extend(interaction.evidence_metadata['error_tags'])
        # Count and get most common
        error_tag_counts = Counter(error_tags)
        common_error_tags = [tag for tag, _ in error_tag_counts.most_common(5)]
        
        # Find best example (most recent correct attempt with user_response)
        best_example = None
        for interaction in interactions:
            if interaction.is_correct and interaction.user_response:
                best_example = {
                    'user_response': interaction.user_response,
                    'stage': interaction.evidence_metadata.get('stage') if interaction.evidence_metadata else None,
                    'created_at': interaction.created_at.isoformat() if interaction.created_at else None
                }
                break
        
        # Get recent attempts
        recent_attempts = []
        for interaction in interactions[:limit]:
            recent_attempts.append({
                'stage': interaction.evidence_metadata.get('stage') if interaction.evidence_metadata else 'unknown',
                'is_correct': interaction.is_correct,
                'user_response': interaction.user_response,
                'created_at': interaction.created_at.isoformat() if interaction.created_at else None,
                'rubric_scores': interaction.evidence_metadata.get('rubric_scores') if interaction.evidence_metadata else None
            })
        
        return EvidenceSummaryResponse(
            pattern_id=pattern_id,
            pattern_name=pattern_name,
            total_attempts=total_attempts,
            attempts_by_stage=attempts_by_stage,
            correct_rate=correct_rate,
            mastery_level=mastery_level,
            last_attempted=last_attempted,
            next_review_date=next_review_date,
            common_error_tags=common_error_tags,
            best_example=best_example,
            recent_attempts=recent_attempts
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching evidence summary: {str(e)}")

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
