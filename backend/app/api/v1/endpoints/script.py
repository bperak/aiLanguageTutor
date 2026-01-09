"""
Script Learning API Endpoints
=============================

API endpoints for learning Japanese scripts (Hiragana/Katakana)
with practice modes and progress tracking.
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from collections import defaultdict
import time

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession as AsyncDBSession

from app.core.config import settings
from app.db import get_postgresql_session
from app.models.database_models import User, ConversationSession, ConversationInteraction, ConversationMessage
from app.api.v1.endpoints.auth import get_current_user
from app.schemas.script import (
    ScriptItemResponse,
    ScriptPracticeCheckRequest,
    ScriptPracticeCheckResponse,
    ScriptProgressSummaryResponse,
    ScriptItemProgressResponse,
)
from app.services.script_service import get_script_service

router = APIRouter(tags=["script"])

# Simple in-memory rate limiter for practice/check endpoint
# Key: user_id, Value: list of timestamps
_rate_limit_store: Dict[str, List[float]] = {}


def _check_rate_limit(user_id: str, max_requests: int = None, window_seconds: int = 60) -> bool:
    """
    Check if user has exceeded rate limit.
    
    Args:
        user_id: User identifier
        max_requests: Maximum requests per window (defaults to RATE_LIMIT_PER_MINUTE)
        window_seconds: Time window in seconds (default 60)
    
    Returns:
        True if within limit, False if exceeded
    """
    if max_requests is None:
        max_requests = settings.RATE_LIMIT_PER_MINUTE
    
    now = time.time()
    user_key = str(user_id)
    
    # Clean old entries
    if user_key in _rate_limit_store:
        _rate_limit_store[user_key] = [
            ts for ts in _rate_limit_store[user_key]
            if now - ts < window_seconds
        ]
    else:
        _rate_limit_store[user_key] = []
    
    # Check limit
    if len(_rate_limit_store[user_key]) >= max_requests:
        return False
    
    # Record this request
    _rate_limit_store[user_key].append(now)
    return True


@router.get("/items", response_model=List[ScriptItemResponse])
async def get_script_items(
    script_type: Optional[str] = Query(None, description="Filter by script type (hiragana/katakana)"),
    tags: Optional[List[str]] = Query(None, description="Filter by tags"),
    search: Optional[str] = Query(None, description="Search in kana or romaji"),
    limit: int = Query(20, ge=1, le=500, description="Number of results to return"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    current_user: User = Depends(get_current_user),
):
    """
    Get script items with optional filtering and pagination.
    
    - **script_type**: Filter by script type (hiragana/katakana)
    - **tags**: Filter by tags (must match any)
    - **search**: Search in kana or romaji
    - **limit**: Maximum number of results (1-100)
    - **offset**: Number of results to skip for pagination
    """
    try:
        # Validate script_type
        if script_type and script_type not in ['hiragana', 'katakana']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid script_type: {script_type}. Must be 'hiragana' or 'katakana'"
            )
        
        service = get_script_service()
        items = service.get_items(
            script_type=script_type,
            tags=tags,
            search=search,
            limit=limit,
            offset=offset
        )
        
        return [ScriptItemResponse(**item) for item in items]
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving script items: {str(e)}"
        )


@router.get("/items/{item_id}", response_model=ScriptItemResponse)
async def get_script_item(
    item_id: str,
    current_user: User = Depends(get_current_user),
):
    """Get a specific script item by ID."""
    try:
        service = get_script_service()
        item = service.get_item_by_id(item_id)
        
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Script item not found: {item_id}"
            )
        
        return ScriptItemResponse(**item)
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving script item: {str(e)}"
        )


@router.post("/practice/check", response_model=ScriptPracticeCheckResponse)
async def check_script_practice(
    request: ScriptPracticeCheckRequest,
    db: AsyncDBSession = Depends(get_postgresql_session),
    current_user: User = Depends(get_current_user),
):
    """
    Check a script practice answer and record the attempt.
    
    Records the interaction in conversation_interactions table for progress tracking.
    """
    try:
        # Rate limiting
        if not _check_rate_limit(str(current_user.id)):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please try again later.",
                headers={"Retry-After": "60"}
            )
        
        # Validate request
        if request.mode in ['kana_to_romaji', 'romaji_to_kana'] and not request.user_answer.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="user_answer cannot be empty for typing modes"
            )
        
        if request.mode == 'mcq' and request.choices:
            if request.user_answer not in request.choices:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="user_answer must be one of the provided choices"
                )
        
        # Get item first (needed for both check_answer and metadata)
        service = get_script_service()
        item = service.get_item_by_id(request.item_id)
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Script item not found: {request.item_id}"
            )
        
        # Check answer
        result = service.check_answer(
            item_id=request.item_id,
            mode=request.mode,
            user_answer=request.user_answer,
            choices=request.choices
        )
        
        # Get or create a script practice session
        # Query for existing script practice session
        session_query = select(ConversationSession).where(
            and_(
                ConversationSession.user_id == current_user.id,
                ConversationSession.session_type == 'practice',
                ConversationSession.status == 'active',
                # Check if conversation_context exists and has practice_type='script'
                ConversationSession.conversation_context.isnot(None),
                ConversationSession.conversation_context['practice_type'].as_string() == 'script'
            )
        ).order_by(ConversationSession.created_at.desc()).limit(1)
        
        result_query = await db.execute(session_query)
        session = result_query.scalar_one_or_none()
        
        if not session:
            # Create new session
            session = ConversationSession(
                user_id=current_user.id,
                title="Script Practice",
                language_code='ja',
                session_type='practice',
                status='active',
                ai_provider='none',
                ai_model='none',
                conversation_context={
                    'practice_type': 'script'
                },
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.add(session)
            await db.flush()
        
        # Get existing interaction count for this item
        existing_query = select(func.count(ConversationInteraction.id)).where(
            and_(
                ConversationInteraction.user_id == current_user.id,
                ConversationInteraction.concept_id == request.item_id,
                ConversationInteraction.concept_type == 'script_item'
            )
        )
        existing_result = await db.execute(existing_query)
        attempts_count = existing_result.scalar() or 0
        
        # Create a message for this practice attempt (required for message_id foreign key)
        
        # Get next message order
        max_order_query = select(func.max(ConversationMessage.message_order)).where(
            ConversationMessage.session_id == session.id
        )
        max_order_result = await db.execute(max_order_query)
        next_order = (max_order_result.scalar() or 0) + 1
        
        # Create user message for this practice attempt
        user_msg = ConversationMessage(
            session_id=session.id,
            role='user',
            content=f"Practice: {item['kana']} → {request.user_answer}",
            content_type='text',
            message_order=next_order,
            created_at=datetime.utcnow(),
            grammar_points_mentioned=[]  # Not a grammar point
        )
        db.add(user_msg)
        await db.flush()  # Get message.id
        
        # Record interaction
        interaction = ConversationInteraction(
            user_id=current_user.id,
            session_id=session.id,
            message_id=user_msg.id,  # Use the created message ID
            interaction_type='script_practice',
            concept_id=request.item_id,
            concept_type='script_item',
            user_response=request.user_answer,
            is_correct=result['is_correct'],
            attempts_count=attempts_count + 1,
            hint_used=False,
            evidence_metadata={
                'mode': request.mode,
                'prompt': item['kana'] if request.mode == 'kana_to_romaji' else item['romaji'],
                'expected': result['expected_answer'],
                'user_answer': request.user_answer,
                'normalized_user_answer': (
                    service.normalize_romaji(request.user_answer) if request.mode in ['kana_to_romaji', 'mcq']
                    else service.normalize_kana(request.user_answer)
                )
            },
            created_at=datetime.utcnow()
        )
        db.add(interaction)
        
        # Update session stats
        session.total_messages = (session.total_messages or 0) + 1
        session.user_messages = (session.user_messages or 0) + 1
        session.updated_at = datetime.utcnow()
        
        await db.commit()
        
        return ScriptPracticeCheckResponse(
            item_id=request.item_id,
            mode=request.mode,
            is_correct=result['is_correct'],
            expected_answer=result['expected_answer'],
            accepted_answers=result['accepted_answers'],
            feedback=result['feedback']
        )
    
    except HTTPException:
        raise
    except ValueError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        await db.rollback()
        import traceback
        error_detail = f"Error checking practice answer: {str(e)}"
        # Log full traceback for debugging
        import structlog
        logger = structlog.get_logger()
        logger.error("Script practice check failed", error=str(e), traceback=traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_detail
        )


@router.get("/progress/summary", response_model=ScriptProgressSummaryResponse)
async def get_script_progress_summary(
    script_type: Optional[str] = Query(None, description="Filter by script type"),
    db: AsyncDBSession = Depends(get_postgresql_session),
    current_user: User = Depends(get_current_user),
):
    """
    Get comprehensive progress summary for script learning.
    
    Returns aggregated metrics across all script practice attempts.
    """
    try:
        # Get all script practice interactions
        query = select(ConversationInteraction).where(
            and_(
                ConversationInteraction.user_id == current_user.id,
                ConversationInteraction.concept_type == 'script_item',
                ConversationInteraction.interaction_type == 'script_practice'
            )
        )
        
        result = await db.execute(query)
        interactions = result.scalars().all()
        
        if not interactions:
            return ScriptProgressSummaryResponse(
                total_attempts=0,
                correct_rate=0.0,
                items_practiced=0,
                mastered_items=0
            )
        
        # Aggregate metrics
        total_attempts = len(interactions)
        correct_count = sum(1 for i in interactions if i.is_correct)
        correct_rate = correct_count / total_attempts if total_attempts > 0 else 0.0
        
        # Count unique items practiced
        items_practiced = len(set(i.concept_id for i in interactions))
        
        # Count mastered items (last 3 attempts correct)
        # Group by item_id and check last 3
        item_attempts: Dict[str, List[bool]] = defaultdict(list)
        for interaction in sorted(interactions, key=lambda x: x.created_at):
            item_attempts[interaction.concept_id].append(interaction.is_correct)
        
        mastered_items = 0
        for item_id, attempts in item_attempts.items():
            if len(attempts) >= 3 and all(attempts[-3:]):
                mastered_items += 1
        
        return ScriptProgressSummaryResponse(
            total_attempts=total_attempts,
            correct_rate=correct_rate,
            items_practiced=items_practiced,
            mastered_items=mastered_items
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving progress summary: {str(e)}"
        )


@router.get("/progress/items", response_model=List[ScriptItemProgressResponse])
async def get_script_item_progress(
    script_type: Optional[str] = Query(None, description="Filter by script type"),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    db: AsyncDBSession = Depends(get_postgresql_session),
    current_user: User = Depends(get_current_user),
):
    """
    Get progress for individual script items.
    
    Returns per-item statistics including attempts, correct rate, and mastery level.
    """
    try:
        # Get all script practice interactions
        query = select(ConversationInteraction).where(
            and_(
                ConversationInteraction.user_id == current_user.id,
                ConversationInteraction.concept_type == 'script_item',
                ConversationInteraction.interaction_type == 'script_practice'
            )
        ).order_by(ConversationInteraction.created_at.desc())
        
        result = await db.execute(query)
        interactions = result.scalars().all()
        
        # Group by item_id
        item_stats: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            'attempts': [],
            'last_attempted': None
        })
        
        for interaction in interactions:
            item_id = interaction.concept_id
            item_stats[item_id]['attempts'].append(interaction.is_correct)
            if not item_stats[item_id]['last_attempted'] or interaction.created_at > item_stats[item_id]['last_attempted']:
                item_stats[item_id]['last_attempted'] = interaction.created_at
        
        # Filter by script_type if provided
        service = get_script_service()
        if script_type:
            valid_item_ids = {item['id'] for item in service.get_items(script_type=script_type, limit=10000)}
            item_stats = {k: v for k, v in item_stats.items() if k in valid_item_ids}
        
        # Build response
        progress_list = []
        for item_id, stats in item_stats.items():
            attempts = stats['attempts']
            total_attempts = len(attempts)
            correct_count = sum(attempts)
            correct_rate = correct_count / total_attempts if total_attempts > 0 else 0.0
            
            # Simple mastery level (1-5) based on recent performance
            if total_attempts >= 5:
                recent_correct = sum(attempts[-5:])
                mastery_level = min(5, 1 + (recent_correct // 2))
            elif total_attempts >= 3:
                recent_correct = sum(attempts[-3:])
                mastery_level = min(4, 1 + recent_correct)
            else:
                mastery_level = 1
            
            progress_list.append(ScriptItemProgressResponse(
                item_id=item_id,
                last_attempted=stats['last_attempted'].isoformat() if stats['last_attempted'] else None,
                attempts=total_attempts,
                correct_rate=correct_rate,
                mastery_level=mastery_level
            ))
        
        # Sort by mastery level (lowest first) then by attempts
        progress_list.sort(key=lambda x: (x.mastery_level, -x.attempts))
        
        # Apply pagination
        return progress_list[offset:offset + limit]
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving item progress: {str(e)}"
        )

