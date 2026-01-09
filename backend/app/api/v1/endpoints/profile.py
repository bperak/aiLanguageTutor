"""
Profile endpoints for profile building, completion, and learning path management.
"""

from typing import Dict, Any, Optional
from datetime import datetime
import asyncio
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
import uuid

from app.db import get_postgresql_session
from app.db import get_neo4j_session
from app.api.v1.endpoints.auth import get_current_user
from app.models.database_models import User, UserProfile, LearningPath, ConversationSession, ConversationMessage
from app.schemas.profile import (
    ProfileStatusResponse, ProfileDataResponse, ProfileCompleteRequest,
    ProfileSkipRequest, LearningPathResponse, LearningPathGenerateRequest
)
from app.services.profile_building_service import profile_building_service
from app.services.learning_path_service import learning_path_service
from app.services.conversation_service import ConversationService
from app.services.prelesson_kit_service import prelesson_kit_service
from app.db import get_neo4j_session
router = APIRouter()


@router.get("/status", response_model=ProfileStatusResponse)
async def get_profile_status(
    db: AsyncSession = Depends(get_postgresql_session),
    current_user: User = Depends(get_current_user)
):
    """Get profile completion status with detailed information."""
    # #region agent log
    import time
    import json
    perf_start = time.time()
    try:
        with open("/home/benedikt/.cursor/debug.log", "a") as f:
            f.write(json.dumps({
                "sessionId": "debug-session",
                "runId": "perf1",
                "hypothesisId": "P7",
                "location": "profile.py:get_profile_status",
                "message": "Profile status endpoint called",
                "data": {"user_id": str(current_user.id), "timestamp": int(time.time() * 1000)},
                "timestamp": int(time.time() * 1000)
            }) + "\n")
    except: pass
    # #endregion
    # #region agent log
    check_start = time.time()
    # #endregion
    status_data = await profile_building_service.check_profile_completion(
        db, current_user.id
    )
    # #region agent log
    check_end = time.time()
    try:
        with open("/home/benedikt/.cursor/debug.log", "a") as f:
            f.write(json.dumps({
                "sessionId": "debug-session",
                "runId": "perf1",
                "hypothesisId": "P7",
                "location": "profile.py:get_profile_status",
                "message": "Profile completion check completed",
                "data": {"duration_ms": (check_end - check_start) * 1000},
                "timestamp": int(time.time() * 1000)
            }) + "\n")
    except: pass
    # #endregion
    
    # Check if profile data exists and calculate completion
    missing_fields = []
    completion_percentage = 0.0
    suggestions = []
    has_profile_data = False
    profile_completed_at = None
    
    try:
        profile_result = await db.execute(
            select(UserProfile).where(UserProfile.user_id == current_user.id)
        )
        profile = profile_result.scalar_one_or_none()
        has_profile_data = profile is not None
        
        if profile:
            profile_completed_at = profile.updated_at if status_data["completed"] else None
            
            # Calculate completion percentage
            total_fields = 5  # goals, previous_knowledge, learning_experiences, usage_context, additional_notes
            completed_fields = 0
            
            if profile.learning_goals and len(profile.learning_goals) > 0:
                completed_fields += 1
            else:
                missing_fields.append("learning_goals")
                suggestions.append("Share your learning goals (e.g., 'I want to travel to Japan')")
            
            if profile.previous_knowledge:
                pk = profile.previous_knowledge
                if pk.get("experience_level") or pk.get("years_studying") is not None:
                    completed_fields += 1
                else:
                    missing_fields.append("previous_knowledge")
                    suggestions.append("Tell us about your previous experience with the language")
            
            if profile.learning_experiences:
                le = profile.learning_experiences
                if le.get("preferred_methods") or le.get("learning_style"):
                    completed_fields += 1
                else:
                    missing_fields.append("learning_experiences")
                    suggestions.append("Share your preferred learning methods and style")
            
            if profile.usage_context:
                uc = profile.usage_context
                if uc.get("contexts") or uc.get("specific_situations"):
                    completed_fields += 1
                else:
                    missing_fields.append("usage_context")
                    suggestions.append("Describe where and when you'll use the language")
            
            # Additional notes are optional, so don't count against completion
            if profile.additional_notes:
                completed_fields += 0.5  # Bonus for additional notes
            
            completion_percentage = completed_fields / total_fields
            
            # Generate suggestions if profile is incomplete
            if not status_data["completed"] and completion_percentage < 0.8:
                if not suggestions:
                    suggestions = [
                        "Complete your profile to get a personalized learning path",
                        "Share your learning goals and preferences for better recommendations"
                    ]
    except Exception:
        # If user_profiles table doesn't exist, assume no profile data
        has_profile_data = False
        missing_fields = ["profile_data"]
        suggestions = ["Start building your profile to unlock personalized features"]
    
    # #region agent log
    perf_end = time.time()
    try:
        with open("/home/benedikt/.cursor/debug.log", "a") as f:
            f.write(json.dumps({
                "sessionId": "debug-session",
                "runId": "perf1",
                "hypothesisId": "P7",
                "location": "profile.py:get_profile_status",
                "message": "Profile status endpoint completed",
                "data": {"total_duration_ms": (perf_end - perf_start) * 1000},
                "timestamp": int(time.time() * 1000)
            }) + "\n")
    except: pass
    # #endregion
    
    return ProfileStatusResponse(
        profile_completed=status_data["completed"],
        profile_skipped=status_data["skipped"],
        profile_completed_at=profile_completed_at,
        has_profile_data=has_profile_data,
        completion_percentage=completion_percentage if has_profile_data else None,
        missing_fields=missing_fields,
        suggestions=suggestions
    )


@router.get("/data", response_model=ProfileDataResponse)
async def get_profile_data(
    db: AsyncSession = Depends(get_postgresql_session),
    current_user: User = Depends(get_current_user)
):
    """Get user's profile data."""
    try:
        result = await db.execute(
            select(UserProfile).where(UserProfile.user_id == current_user.id)
        )
        profile = result.scalar_one_or_none()
    except Exception as e:
        # If user_profiles table doesn't exist, treat as "no profile yet"
        if "user_profiles" in str(e) and "does not exist" in str(e).lower():
            profile = None
        else:
            raise
    
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found"
        )
    
    return ProfileDataResponse(
        user_id=profile.user_id,
        learning_goals=profile.learning_goals or [],
        previous_knowledge=profile.previous_knowledge or {},
        learning_experiences=profile.learning_experiences or {},
        usage_context=profile.usage_context or {},
        additional_notes=profile.additional_notes,
        extraction_response=profile.extraction_response,
        profile_building_conversation_id=profile.profile_building_conversation_id,
        created_at=profile.created_at,
        updated_at=profile.updated_at
    )


@router.post("/extract")
async def extract_profile_data(
    request: Dict[str, Any],
    db: AsyncSession = Depends(get_postgresql_session),
    current_user: User = Depends(get_current_user)
):
    """Extract profile data from conversation without saving it."""
    try:
        conversation_id = request.get("conversation_id")
        if not conversation_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="conversation_id is required"
            )
        
        # Convert to UUID if string
        if isinstance(conversation_id, str):
            try:
                conversation_id = uuid.UUID(conversation_id)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid conversation_id format"
                )
        
        # Get conversation messages
        session = await ConversationService.get_session(
            db, conversation_id, current_user.id
        )
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation session not found"
            )
        
        messages = await ConversationService.list_messages(
            db, conversation_id, limit=1000, ascending=True
        )
        
        if not messages or len(messages) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No messages found in conversation. Please have a conversation first before extracting profile data."
            )
        
        message_list = [
            {"role": m.role, "content": m.content}
            for m in messages
        ]
        
        # Extract profile data
        try:
            profile_data, extraction_response = await profile_building_service.extract_profile_data(message_list)
        except ValueError as e:
            # JSON parsing errors
            import structlog
            logger = structlog.get_logger()
            logger.error("profile_extraction_endpoint_json_error", error=str(e), conversation_id=str(conversation_id))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to parse extracted profile data: {str(e)}. Please try again or contact support."
            )
        except Exception as e:
            # Other extraction errors
            import structlog
            logger = structlog.get_logger()
            logger.error("profile_extraction_endpoint_failed", error=str(e), conversation_id=str(conversation_id))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to extract profile data: {str(e)}"
            )
        
        return {
            "profile_data": {
                "learning_goals": profile_data.learning_goals,
                "previous_knowledge": profile_data.previous_knowledge.model_dump() if profile_data.previous_knowledge else {},
                "learning_experiences": profile_data.learning_experiences.model_dump() if profile_data.learning_experiences else {},
                "usage_context": profile_data.usage_context.model_dump() if profile_data.usage_context else {},
                "additional_notes": profile_data.additional_notes,
                "current_level": profile_data.current_level,
            },
            "extraction_response": extraction_response  # Include AI extraction response and assessment
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to extract profile data: {str(e)}"
        )


@router.post("/complete")
async def complete_profile(
    request: ProfileCompleteRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_postgresql_session),
    current_user: User = Depends(get_current_user)
):
    """Mark profile as complete after extracting data from conversation."""
    try:
        # Get conversation messages
        session = await ConversationService.get_session(
            db, request.conversation_id, current_user.id
        )
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation session not found"
            )
        
        messages = await ConversationService.list_messages(
            db, request.conversation_id, limit=1000, ascending=True
        )
        message_list = [
            {"role": m.role, "content": m.content}
            for m in messages
        ]
        
        # Extract profile data (or use provided data)
        extraction_response = None
        if request.profile_data:
            # Convert dict to ProfileData object if needed
            if isinstance(request.profile_data, dict):
                from app.schemas.profile import ProfileData
                profile_data = ProfileData(**request.profile_data)
            else:
                profile_data = request.profile_data
        else:
            profile_data, extraction_response = await profile_building_service.extract_profile_data(message_list)
        
        # Save profile data
        await profile_building_service.save_profile_data(
            db=db,
            user_id=current_user.id,
            profile_data=profile_data,
            conversation_id=request.conversation_id,
            extraction_response=extraction_response
        )
        
        # Mark as complete
        await profile_building_service.mark_profile_complete(db, current_user.id)
        
        # Capture user_id for background task (current_user might not be accessible in background)
        user_id_for_bg = current_user.id
        
        # Generate learning path in background (non-blocking).
        #
        # Reason: this can be slow (Neo4j + path logic) and should not block the
        # user's "Approve & Save" flow. Generate in background so it completes
        # even if it takes longer than a few seconds.
        path_response = None

        async def _generate_path_background() -> None:
            """Background task to generate learning path."""
            from app.db import AsyncSessionLocal, get_neo4j_session
            import structlog
            import traceback
            
            logger = structlog.get_logger()
            logger.info("learning_path_background_task_started", user_id=str(user_id_for_bg))
            
            try:
                async with AsyncSessionLocal() as bg_db:
                    try:
                        async for neo4j_session in get_neo4j_session():
                            try:
                                logger.info("learning_path_background_generating", user_id=str(user_id_for_bg))
                                path_data = await learning_path_service.generate_learning_path(
                                    db=bg_db,
                                    neo4j_session=neo4j_session,
                                    user_id=user_id_for_bg,
                                )
                                logger.info("learning_path_background_saving", user_id=str(user_id_for_bg))
                                saved_path = await learning_path_service.save_learning_path(
                                    db=bg_db,
                                    user_id=user_id_for_bg,
                                    path_data=path_data,
                                )
                                await bg_db.commit()
                                logger.info(
                                    "learning_path_generated_in_background",
                                    user_id=str(user_id_for_bg),
                                    path_id=str(saved_path.id)
                                )
                                break
                            except Exception as bg_err:
                                await bg_db.rollback()
                                error_trace = traceback.format_exc()
                                logger.error(
                                    "learning_path_generation_failed_in_background",
                                    error=str(bg_err),
                                    error_type=type(bg_err).__name__,
                                    traceback=error_trace,
                                    user_id=str(user_id_for_bg)
                                )
                                break
                    except Exception as session_err:
                        error_trace = traceback.format_exc()
                        logger.error(
                            "learning_path_background_db_session_failed",
                            error=str(session_err),
                            error_type=type(session_err).__name__,
                            traceback=error_trace,
                            user_id=str(user_id_for_bg)
                        )
            except Exception as bg_err:
                error_trace = traceback.format_exc()
                logger.error(
                    "learning_path_background_task_failed",
                    error=str(bg_err),
                    error_type=type(bg_err).__name__,
                    traceback=error_trace,
                    user_id=str(user_id_for_bg)
                )
        
        # Try to generate synchronously with a longer timeout (10 seconds)
        # If it times out, fall back to background generation
        async def _generate_path_sync() -> LearningPathResponse | None:
            from app.db import get_neo4j_session

            async for neo4j_session in get_neo4j_session():
                path_data = await learning_path_service.generate_learning_path(
                    db=db,
                    neo4j_session=neo4j_session,
                    user_id=current_user.id,
                )
                saved_path = await learning_path_service.save_learning_path(
                    db=db,
                    user_id=current_user.id,
                    path_data=path_data,
                )
                return LearningPathResponse(
                    id=saved_path.id,
                    user_id=saved_path.user_id,
                    version=saved_path.version,
                    path_name=saved_path.path_name,
                    path_data=saved_path.path_data or {},
                    progress_data=saved_path.progress_data or {},
                    is_active=saved_path.is_active,
                    created_at=saved_path.created_at,
                    updated_at=saved_path.updated_at,
                )

            return None

        try:
            # Try synchronous generation with 10 second timeout
            path_response = await asyncio.wait_for(_generate_path_sync(), timeout=10.0)
        except asyncio.TimeoutError:
            import structlog
            logger = structlog.get_logger()
            logger.info("learning_path_generation_timed_out_using_background", timeout_s=10.0, user_id=str(current_user.id))
            # Schedule background generation
            background_tasks.add_task(_generate_path_background)
        except Exception as path_err:
            # Log but don't fail profile completion, schedule background generation
            import structlog
            logger = structlog.get_logger()
            logger.error("learning_path_generation_failed_using_background", error=str(path_err), user_id=str(current_user.id))
            # Schedule background generation as fallback
            background_tasks.add_task(_generate_path_background)
        
        return {
            "status": "completed",
            "message": "Profile completed successfully",
            "learning_path": path_response.model_dump() if path_response else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to complete profile: {str(e)}"
        )


@router.post("/skip")
async def skip_profile(
    request: ProfileSkipRequest,
    db: AsyncSession = Depends(get_postgresql_session),
    current_user: User = Depends(get_current_user)
):
    """Skip profile building for now."""
    await profile_building_service.mark_profile_skipped(db, current_user.id)
    return {"status": "skipped", "message": "Profile building skipped"}


@router.get("/learning-path", response_model=LearningPathResponse)
async def get_learning_path(
    db: AsyncSession = Depends(get_postgresql_session),
    current_user: User = Depends(get_current_user)
):
    """Get user's active learning path."""
    path = await learning_path_service.get_active_learning_path(db, current_user.id)
    
    if not path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active learning path found"
        )
    
    return LearningPathResponse(
        id=path.id,
        user_id=path.user_id,
        version=path.version,
        path_name=path.path_name,
        path_data=path.path_data or {},
        progress_data=path.progress_data or {},
        is_active=path.is_active,
        created_at=path.created_at,
        updated_at=path.updated_at
    )


@router.get("/learning-path/versions")
async def get_learning_path_versions(
    db: AsyncSession = Depends(get_postgresql_session),
    current_user: User = Depends(get_current_user)
):
    """Get all learning path versions for user."""
    result = await db.execute(
        select(LearningPath)
        .where(LearningPath.user_id == current_user.id)
        .order_by(LearningPath.version.desc())
    )
    paths = result.scalars().all()
    
    return [
        {
            "id": str(p.id),
            "version": p.version,
            "path_name": p.path_name,
            "is_active": p.is_active,
            "created_at": str(p.created_at),
            "updated_at": str(p.updated_at)
        }
        for p in paths
    ]


@router.post("/learning-path/generate")
async def generate_learning_path(
    request: LearningPathGenerateRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_postgresql_session),
    current_user: User = Depends(get_current_user)
):
    """Manually trigger learning path generation."""
    try:
        # Check if path already exists
        existing = await learning_path_service.get_active_learning_path(db, current_user.id)
        if existing and not request.force_regenerate:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Active learning path already exists. Use force_regenerate=true to create new version."
            )
        
        # Run path generation synchronously but with a timeout
        # If it takes too long, we'll return a status message
        from app.db import get_neo4j_session
        import structlog
        logger = structlog.get_logger()
        
        try:
            async for neo4j_session in get_neo4j_session():
                # Generate new path
                path_data = await learning_path_service.generate_learning_path(
                    db=db,
                    neo4j_session=neo4j_session,
                    user_id=current_user.id
                )
                break
            
            # Save path
            new_path = await learning_path_service.save_learning_path(
                db=db,
                user_id=current_user.id,
                path_data=path_data
            )
            
            # Return full path data
            return LearningPathResponse(
                id=new_path.id,
                user_id=new_path.user_id,
                version=new_path.version,
                path_name=new_path.path_name,
                path_data=new_path.path_data or {},
                progress_data=new_path.progress_data or {},
                is_active=new_path.is_active,
                created_at=new_path.created_at,
                updated_at=new_path.updated_at
            )
        except asyncio.TimeoutError:
            logger.warning("Path generation timed out, returning status",
                         user_id=str(current_user.id))
            return {
                "status": "generating",
                "message": "Learning path generation is in progress. Please check back in a moment.",
                "user_id": str(current_user.id)
            }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate learning path: {str(e)}"
        )


@router.post("/learning-path/prelesson-kit")
async def generate_prelesson_kit(
    request: Dict[str, Any],
    db: AsyncSession = Depends(get_postgresql_session),
    current_user: User = Depends(get_current_user)
):
    """
    Generate a pre-lesson kit for a specific CanDo step in the learning path.
    
    Request body: {"can_do_id": "...", "step_id": "..."}
    """
    try:
        can_do_id = request.get("can_do_id")
        step_id = request.get("step_id")
        
        if not can_do_id or not step_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="can_do_id and step_id are required"
            )
        
        # Get active learning path
        path = await learning_path_service.get_active_learning_path(db, current_user.id)
        if not path:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No active learning path found"
            )
        
        # Get user's current level for appropriate kit generation
        user_result = await db.execute(
            select(User).where(User.id == current_user.id)
        )
        user = user_result.scalar_one_or_none()
        learner_level = user.current_level if user else None
        
        # Generate kit
        async for neo4j_session in get_neo4j_session():
            kit = await prelesson_kit_service.generate_kit(
                can_do_id=can_do_id,
                learner_level=learner_level,
                neo4j_session=neo4j_session
            )
            break
        
        # Update learning path with the kit
        path_data = path.path_data or {}
        steps = path_data.get("steps", [])
        
        step_found = False
        for step in steps:
            if step.get("step_id") == step_id:
                step["prelesson_kit"] = kit.model_dump()
                step_found = True
                break
        
        if not step_found:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Step {step_id} not found in learning path"
            )
        
        # Save updated path
        path.path_data = path_data
        path.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(path)
        
        return {
            "status": "ok",
            "step_id": step_id,
            "prelesson_kit": kit.model_dump()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        import structlog
        logger = structlog.get_logger()
        logger.error("failed_to_generate_prelesson_kit", error=str(e), can_do_id=request.get("can_do_id"))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate pre-lesson kit: {str(e)}"
        )


@router.post("/learning-path/update")
async def update_learning_path(
    db: AsyncSession = Depends(get_postgresql_session),
    current_user: User = Depends(get_current_user)
):
    """Update learning path based on progress (creates new version)."""
    try:
        # Get learning analytics (simplified - would come from analytics service)
        analytics = {}  # TODO: Fetch from analytics service
        
        # Get Neo4j session
        from app.db import get_neo4j_session
        async for neo4j_session in get_neo4j_session():
            new_path = await learning_path_service.update_learning_path_based_on_progress(
                db=db,
                neo4j_session=neo4j_session,
                user_id=current_user.id,
                learning_analytics=analytics
            )
            break
        
        if not new_path:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not update learning path"
            )
        
        return {
            "status": "updated",
            "path_id": str(new_path.id),
            "version": new_path.version,
            "path_name": new_path.path_name
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update learning path: {str(e)}"
        )


@router.get("/usage-data/dashboard")
async def get_usage_dashboard(
    db: AsyncSession = Depends(get_postgresql_session),
    current_user: User = Depends(get_current_user)
):
    """Get dashboard data (moved from /learning/dashboard)."""
    from app.api.v1.endpoints.learning import get_dashboard
    result = await get_dashboard(db=db, current_user=current_user)
    return result


@router.get("/usage-data/sessions")
async def get_usage_sessions(
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_postgresql_session),
    current_user: User = Depends(get_current_user)
):
    """Get user's session history."""
    sessions = await ConversationService.list_sessions(
        db, current_user.id, limit=limit, offset=offset
    )
    
    return [
        {
            "id": str(s.id),
            "title": s.title,
            "session_type": s.session_type,
            "language_code": s.language_code,
            "status": s.status,
            "created_at": str(s.created_at),
            "total_messages": s.total_messages or 0
        }
        for s in sessions
    ]


@router.get("/usage-data/analytics")
async def get_usage_analytics(
    days: int = 14,
    db: AsyncSession = Depends(get_postgresql_session),
    current_user: User = Depends(get_current_user)
):
    """Get analytics data (messages/day, sessions/week, etc.)."""
    from app.api.v1.endpoints.analytics import (
        messages_per_day, sessions_per_week
    )
    
    messages_data = await messages_per_day(days=days, db=db, current_user=current_user)
    sessions_data = await sessions_per_week(weeks=days//7 or 1, db=db, current_user=current_user)
    
    return {
        "messages_per_day": messages_data,
        "sessions_per_week": sessions_data
    }


@router.get("/suggestions")
async def get_personalization_suggestions(
    conversation_id: Optional[str] = None,
    db: AsyncSession = Depends(get_postgresql_session),
    current_user: User = Depends(get_current_user)
):
    """Get personalization suggestions based on conversation progress."""
    try:
        suggestions = []
        
        # If conversation_id provided, analyze conversation
        if conversation_id:
            messages = await ConversationService.list_messages(
                db, uuid.UUID(conversation_id), limit=100, ascending=True
            )
            message_list = [
                {"role": m.role, "content": m.content}
                for m in messages
            ]
            
            # Analyze what's been covered
            conversation_text = " ".join([m.get("content", "") for m in message_list])
            
            # Check what's missing
            has_goals = any(keyword in conversation_text.lower() for keyword in ["goal", "want", "achieve", "learn", "purpose"])
            has_experience = any(keyword in conversation_text.lower() for keyword in ["experience", "studied", "know", "familiar", "level"])
            has_methods = any(keyword in conversation_text.lower() for keyword in ["method", "prefer", "style", "way", "how"])
            has_context = any(keyword in conversation_text.lower() for keyword in ["use", "context", "situation", "where", "when"])
            
            # Generate suggestions based on what's missing
            if not has_goals:
                suggestions.append("💡 Example learning goal: 'I want to have basic conversations when traveling'")
                suggestions.append("💡 Example learning goal: 'I want to read Japanese manga or books'")
            
            if not has_experience:
                suggestions.append("💡 Share your experience: Have you studied this language before? What do you already know?")
            
            if not has_methods:
                suggestions.append("💡 Learning method suggestion: Try flashcards for vocabulary retention")
                suggestions.append("💡 Learning method suggestion: Practice with conversation partners")
            
            if not has_context:
                suggestions.append("💡 Usage context: Where do you want to use the language? (travel, work, academic)")
                suggestions.append("💡 Usage context: When do you need to use it? (immediate, short-term, long-term)")
        
        # If no conversation or suggestions generated, provide default suggestions
        if not suggestions:
            suggestions = [
                "💡 Example learning goal: 'I want to have basic conversations when traveling'",
                "💡 Example learning goal: 'I want to read Japanese manga or books'",
                "💡 Learning method suggestion: Try flashcards for vocabulary",
                "💡 Learning method suggestion: Practice with conversation partners",
            ]
        
        return {"suggestions": suggestions[:6]}  # Limit to 6 suggestions
        
    except Exception as e:
        import structlog
        logger = structlog.get_logger()
        logger.error("failed_to_generate_suggestions", error=str(e))
        # Return default suggestions on error
        return {
            "suggestions": [
                "💡 Example learning goal: 'I want to have basic conversations when traveling'",
                "💡 Learning method suggestion: Try flashcards for vocabulary",
            ]
        }

