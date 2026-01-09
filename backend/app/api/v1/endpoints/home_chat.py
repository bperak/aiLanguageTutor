"""
Home chat endpoints for main AI tutor interface.
"""

from typing import Dict, Any, Optional
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, status, Request, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text
import uuid

from app.db import get_postgresql_session
from app.api.v1.endpoints.auth import get_current_user
from app.models.database_models import User, ConversationSession, ConversationMessage, LearningPath
from app.services.conversation_service import ConversationService
from app.services.ai_chat_service import AIChatService
from app.services.profile_building_service import profile_building_service
from app.services.learning_path_service import learning_path_service


def _looks_like_missing_table_error(exc: Exception, table_name: str) -> bool:
    """
    Best-effort detection for missing-table errors across async drivers.

    Args:
        exc: Raised exception.
        table_name: Table name to check for in the error message.

    Returns:
        bool: True if this looks like a "relation does not exist" error.
    """

    msg = str(exc).lower()
    t = table_name.lower()
    return ("does not exist" in msg or "undefinedtableerror" in msg) and t in msg


async def _ensure_learning_paths_table_exists(db: AsyncSession) -> None:
    """
    Ensure `learning_paths` exists.

    Reason: some deployments may have persistent DB volumes where migrations were
    not applied; the home page must not 500 and should be able to save a path.
    """

    import structlog

    logger = structlog.get_logger()
    try:
        await db.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS learning_paths (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    version INTEGER NOT NULL DEFAULT 1,
                    path_name VARCHAR(255) NOT NULL DEFAULT 'Initial Path',
                    path_data JSONB NOT NULL DEFAULT '{}',
                    progress_data JSONB DEFAULT '{}',
                    is_active BOOLEAN DEFAULT TRUE,
                    superseded_by UUID REFERENCES learning_paths(id) ON DELETE SET NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    CONSTRAINT unique_user_active_path UNIQUE (user_id, is_active) DEFERRABLE INITIALLY DEFERRED
                )
                """
            )
        )
        await db.execute(text("CREATE INDEX IF NOT EXISTS idx_learning_paths_user_id ON learning_paths(user_id)"))
        await db.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_learning_paths_user_active ON learning_paths(user_id, is_active) WHERE is_active = TRUE"
            )
        )
        await db.execute(text("CREATE INDEX IF NOT EXISTS idx_learning_paths_created_at ON learning_paths(created_at DESC)"))
        commit = getattr(db, "commit", None)
        if commit:
            await commit()
    except Exception as e:  # noqa: BLE001
        logger.warning("ensure_learning_paths_table_failed", error=str(e), error_type=type(e).__name__)
        # Best-effort: don't fail the home status endpoint because of this.
        try:
            await db.rollback()
        except Exception:
            pass


router = APIRouter()


@router.get("/status")
async def get_home_status(
    db: AsyncSession = Depends(get_postgresql_session),
    current_user: User = Depends(get_current_user)
):
    """Get home page status: greeting, progress, next steps, suggestions."""
    try:
        # Get profile status
        profile_status = await profile_building_service.check_profile_completion(
            db, current_user.id
        )
        
        # Get learning path if profile completed
        learning_path = None
        next_step = None
        next_steps = []  # Next 3 steps for the assistant message
        path_generating = False
        
        if profile_status["completed"]:
            try:
                learning_path = await learning_path_service.get_active_learning_path(db, current_user.id)
            except Exception as lp_err:  # noqa: BLE001
                import structlog

                logger = structlog.get_logger()
                if _looks_like_missing_table_error(lp_err, "learning_paths"):
                    logger.warning(
                        "home_status_learning_paths_missing",
                        error=str(lp_err),
                        error_type=type(lp_err).__name__,
                    )
                    await _ensure_learning_paths_table_exists(db)
                    try:
                        learning_path = await learning_path_service.get_active_learning_path(db, current_user.id)
                    except Exception:
                        learning_path = None
                else:
                    logger.warning(
                        "home_status_learning_path_fetch_failed",
                        error=str(lp_err),
                        error_type=type(lp_err).__name__,
                    )
                    learning_path = None
                # If we failed to fetch, treat as "still generating" so UI doesn't look broken.
                path_generating = True
            
            # Auto-generate path if missing (best-effort with timeout)
            if not learning_path:
                import structlog
                import asyncio
                logger = structlog.get_logger()
                logger.info("auto_generating_learning_path", user_id=str(current_user.id))

                # Avoid initializing Neo4j from this request path.
                # Reason: in some environments (tests, degraded deployments) Neo4j is intentionally
                # not available. Startup already decides whether Neo4j is usable; if the driver is
                # missing, skip auto-generation rather than trying to connect on a user request.
                from app import db as db_module

                if getattr(db_module, "neo4j_driver", None) is None:
                    logger.warning("neo4j_driver_not_initialized_skipping_auto_generation", user_id=str(current_user.id))
                    path_generating = True
                else:
                    async def _generate_path():
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
                            return saved_path
                        return None

                    try:
                        learning_path = await asyncio.wait_for(_generate_path(), timeout=2.5)
                        if learning_path:
                            logger.info("learning_path_auto_generated", user_id=str(current_user.id))
                    except asyncio.TimeoutError:
                        logger.warning(
                            "learning_path_generation_timed_out",
                            timeout_s=2.5,
                            user_id=str(current_user.id),
                        )
                        path_generating = True
                    except Exception as path_err:
                        logger.error(
                            "learning_path_generation_failed",
                            error=str(path_err),
                            user_id=str(current_user.id),
                        )
                        path_generating = True
            
            # Validate learning path has valid CanDo descriptors - force regeneration if invalid
            if learning_path:
                path_data = learning_path.path_data or {}
                steps = path_data.get("steps", [])
                
                # Check if any step has invalid CanDo descriptors
                has_invalid_candos = False
                invalid_cando_ids = []
                if steps:
                    from app.db import get_neo4j_session
                    from app.services.user_path_service import user_path_service
                    
                    try:
                        async for neo4j_session in get_neo4j_session():
                            for step in steps[:5]:  # Check first 5 steps
                                can_do_ids = step.get("can_do_descriptors", [])
                                for can_do_id in can_do_ids:
                                    if can_do_id:
                                        exists = await user_path_service.validate_cando_exists(neo4j_session, can_do_id)
                                        if not exists:
                                            has_invalid_candos = True
                                            invalid_cando_ids.append(can_do_id)
                            break
                    except Exception as val_err:
                        import structlog
                        logger = structlog.get_logger()
                        logger.warning("learning_path_validation_failed", error=str(val_err), user_id=str(current_user.id))
                        # If validation fails, assume path is valid to avoid regeneration loops
                        has_invalid_candos = False
                
                # Regenerate path immediately if invalid CanDo descriptors found
                if has_invalid_candos:
                    import structlog
                    import asyncio
                    from app import db as db_module
                    logger = structlog.get_logger()
                    logger.warning("learning_path_has_invalid_candos_regenerating", 
                                 user_id=str(current_user.id),
                                 invalid_ids=invalid_cando_ids)
                    
                    from app.db import get_neo4j_session
                    if getattr(db_module, "neo4j_driver", None) is not None:
                        try:
                            # Regenerate synchronously - wait for it to complete
                            async for neo4j_session in get_neo4j_session():
                                new_path_data = await learning_path_service.generate_learning_path(
                                    db=db,
                                    neo4j_session=neo4j_session,
                                    user_id=current_user.id,
                                )
                                # Save the new path (this will supersede the old one)
                                learning_path = await learning_path_service.save_learning_path(
                                    db=db,
                                    user_id=current_user.id,
                                    path_data=new_path_data,
                                )
                                logger.info("learning_path_regenerated_after_validation", 
                                          user_id=str(current_user.id),
                                          new_steps=len(new_path_data.steps))
                                # Update path_data and steps from the saved learning_path
                                path_data = learning_path.path_data or {}
                                steps = path_data.get("steps", [])
                                break
                        except Exception as regen_err:
                            logger.error("learning_path_regeneration_failed", 
                                       error=str(regen_err), 
                                       user_id=str(current_user.id))
                            # If regeneration fails, set path_generating so UI shows appropriate state
                            path_generating = True
                            learning_path = None
                    else:
                        path_generating = True
                        learning_path = None
            
            if learning_path:
                progress = learning_path.progress_data or {}
                path_data = learning_path.path_data or {}
                steps = path_data.get("steps", [])
                current_step_id = progress.get("current_step_id")
                
                # Find current step index
                current_idx = 0
                if current_step_id:
                    for i, step in enumerate(steps):
                        if step.get("step_id") == current_step_id:
                            current_idx = i
                            break
                
                # Get next step (current or first if none completed)
                if current_idx < len(steps):
                    next_step = steps[current_idx]
                elif steps:
                    next_step = steps[0]
                    current_idx = 0
                
                # Compute next 3 steps starting from current_idx
                for i in range(current_idx, min(current_idx + 3, len(steps))):
                    step = steps[i]
                    can_do_descriptors = step.get("can_do_descriptors", [])
                    can_do_id = can_do_descriptors[0] if can_do_descriptors else None
                    
                    if can_do_id:
                        next_steps.append({
                            "step_id": step.get("step_id"),
                            "title": step.get("title", "Learning Step"),
                            "can_do_id": can_do_id,
                            "start_endpoint": f"/api/v1/cando/lessons/start?can_do_id={can_do_id}",
                            "compile_endpoint": f"/api/v1/cando/lessons/compile_v2_stream?can_do_id={can_do_id}&user_id={current_user.id}",
                            "description": step.get("description", "")
                        })
        
        # Get recent progress
        from app.api.v1.endpoints.learning import get_dashboard
        try:
            dashboard = await get_dashboard(db=db, current_user=current_user)
        except Exception as dashboard_error:
            import structlog
            logger = structlog.get_logger()
            logger.warning("home_status_dashboard_failed", error=str(dashboard_error))
            # Use default values if dashboard fails
            from app.api.v1.endpoints.learning import DashboardResponse
            dashboard = DashboardResponse(
                user_id=str(current_user.id),
                total_sessions=0,
                total_messages=0,
                last_session_at=None
            )
        
        # Get CanDo sessions info from lesson_sessions table
        from sqlalchemy import text
        cando_sessions = []
        try:
            cando_sessions_result = await db.execute(
                text("""
                    SELECT 
                        can_do_id,
                        phase,
                        completed_count,
                        created_at,
                        updated_at
                    FROM lesson_sessions
                    WHERE expires_at > NOW()
                    AND can_do_id IS NOT NULL
                    ORDER BY updated_at DESC
                    LIMIT 10
                """)
            )
            cando_sessions = [dict(row) for row in cando_sessions_result]
        except Exception as cando_error:
            import structlog
            logger = structlog.get_logger()
            logger.warning("home_status_cando_sessions_failed", error=str(cando_error))
            # Continue with empty list if query fails
            cando_sessions = []
        
        # Get recent lessons (completed or in progress)
        recent_lessons = []
        for sess in cando_sessions:
            recent_lessons.append({
                "can_do_id": sess.get("can_do_id"),
                "phase": sess.get("phase"),
                "completed_count": sess.get("completed_count", 0),
                "last_updated": str(sess.get("updated_at")) if sess.get("updated_at") else None
            })
        
        cando_sessions_info = {
            "total_sessions": len(cando_sessions),
            "recent_lessons": recent_lessons,
            "current_goals": [step.get("can_do_descriptors", []) for step in (path_data.get("steps", [])[:3]) if path_data] if learning_path else []
        }
        
        # Get profile data for AI context
        profile_data_for_ai = None
        if profile_status["completed"]:
            try:
                from app.models.database_models import UserProfile
                profile_result = await db.execute(
                    select(UserProfile).where(UserProfile.user_id == current_user.id)
                )
                profile = profile_result.scalar_one_or_none()
                if profile:
                    profile_data_for_ai = {
                        "learning_goals": profile.learning_goals or [],
                        "experience_level": profile.previous_knowledge.get("experience_level") if profile.previous_knowledge else None,
                        "learning_style": profile.learning_experiences.get("learning_style") if profile.learning_experiences else None
                    }
            except Exception:
                pass
        
        # Build greeting context
        greeting_context = {
            "user_name": current_user.username,
            "profile_completed": profile_status["completed"],
            "profile_data": profile_data_for_ai,  # Include profile data for AI personalization
            "learning_path_info": (
                {
                    "path_name": learning_path.path_name,
                    "current_step": next_step.get("title") if next_step else None,
                    "progress_percentage": (learning_path.progress_data or {}).get("progress_percentage", 0)
                } if learning_path else None
            ),
            "recent_progress": {
                "total_sessions": dashboard.total_sessions,
                "total_messages": dashboard.total_messages,
                "last_session_at": str(dashboard.last_session_at) if dashboard.last_session_at else None
            },
            "cando_sessions_info": cando_sessions_info,
            "next_steps": next_steps,  # Next 3 steps with can_do_id and endpoints
            "path_generating": path_generating  # Indicates if path is being generated
        }
        
        # Generate greeting using AI
        # Path: backend/app/api/v1/endpoints/home_chat.py -> backend/app/prompts/
        base_dir = Path(__file__).parent.parent.parent.parent  # Go from endpoints/ to app/
        prompt_path = base_dir / "prompts" / "home_greeting_prompt.txt"
        prompt_template = None
        try:
            with open(prompt_path, "r", encoding="utf-8") as f:
                prompt_template = f.read()
        except Exception as e:
            import structlog
            logger = structlog.get_logger()
            logger.warning("home_greeting_prompt_file_not_found", path=str(prompt_path), error=str(e))
            # Fallback prompt if file not found
            prompt_template = """Generate a personalized greeting for {user_name}.
Profile completed: {profile_completed}
Learning path: {learning_path_info}
Recent progress: {recent_progress}"""
        
        # Format next_steps for prompt
        next_steps_text = ""
        if next_steps:
            next_steps_text = "\n".join([
                f"{i+1}. {step['title']} - Start: `{step['start_endpoint']}`"
                for i, step in enumerate(next_steps)
            ])
        else:
            next_steps_text = "No steps available yet."
        
        # Format profile data for prompt
        profile_data_text = ""
        if greeting_context["profile_data"]:
            pd = greeting_context["profile_data"]
            profile_data_text = f"""
Profile Data:
- Learning Goals: {', '.join(pd.get('learning_goals', [])) if pd.get('learning_goals') else 'Not specified'}
- Experience Level: {pd.get('experience_level', 'Not specified')}
- Learning Style: {pd.get('learning_style', 'Not specified')}
"""
        else:
            profile_data_text = "\nProfile Data: Not completed yet - guide user to complete profile at /profile/build"
        
        # Format prompt with all variables
        try:
            formatted_prompt = prompt_template.format(
                user_name=greeting_context["user_name"],
                is_new_user=str(greeting_context["is_new_user"]),
                profile_completed=str(profile_status["completed"]),
                profile_data=profile_data_text,
                learning_path_info=str(greeting_context["learning_path_info"]),
                recent_progress=str(greeting_context["recent_progress"]),
                cando_sessions_info=str(cando_sessions_info),
                next_steps=next_steps_text,
                path_generating=str(path_generating)
            )
        except KeyError as e:
            # Fallback if prompt template doesn't have all placeholders
            import structlog
            logger = structlog.get_logger()
            logger.warning("prompt_template_missing_placeholder", placeholder=str(e))
            # Use a safer approach: replace placeholders manually to avoid KeyError
            formatted_prompt = prompt_template
            # Replace all known placeholders
            replacements = {
                "{user_name}": greeting_context["user_name"],
                "{is_new_user}": str(greeting_context.get("is_new_user", False)),
                "{profile_completed}": str(profile_status["completed"]),
                "{profile_data}": profile_data_text,
                "{learning_path_info}": str(greeting_context["learning_path_info"]),
                "{recent_progress}": str(greeting_context["recent_progress"]),
                "{cando_sessions_info}": str(cando_sessions_info),
                "{next_steps}": next_steps_text,
                "{path_generating}": str(path_generating)
            }
            for placeholder, value in replacements.items():
                formatted_prompt = formatted_prompt.replace(placeholder, value)
        
        # Use user's native language (meta-language) for greeting, default to English.
        # Reason: the production `users` table may not have a `native_language` column
        # (see `app/models/database_models.py::User`), so guard attribute access.
        native_lang = getattr(current_user, "native_language", None) or "en"
        system_prompt_text = f"""You are a friendly AI language tutor. Generate a warm, personalized greeting.

IMPORTANT: You MUST generate your response in the learner's native language (meta-language), which is {native_lang}. 
Do NOT use the target language (Japanese) for this greeting. The greeting should be in {native_lang} so the learner can understand it clearly.
Be conversational, warm, and encouraging in {native_lang}."""
        
        # Generate greeting with error handling
        greeting = "Hello! Welcome back to your learning journey."
        try:
            ai_service = AIChatService()
            greeting_response = await ai_service.generate_reply(
                provider="openai",
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt_text},
                    {"role": "user", "content": formatted_prompt}
                ],
                temperature=0.7
            )
            greeting = greeting_response.get("content", greeting)
        except Exception as ai_error:
            import structlog
            logger = structlog.get_logger()
            logger.warning(
                "home_greeting_ai_failed",
                error=str(ai_error),
                error_type=type(ai_error).__name__,
                user_id=str(current_user.id)
            )
            # Use fallback greeting if AI generation fails
            greeting = f"Hello {greeting_context['user_name']}! Welcome back to your learning journey."
        
        # Get profile data summary if completed
        profile_summary = None
        if profile_status["completed"]:
            try:
                from app.models.database_models import UserProfile
                profile_result = await db.execute(
                    select(UserProfile).where(UserProfile.user_id == current_user.id)
                )
                profile = profile_result.scalar_one_or_none()
                if profile:
                    profile_summary = {
                        "learning_goals": profile.learning_goals or [],
                        "previous_knowledge": {
                            "experience_level": profile.previous_knowledge.get("experience_level") if profile.previous_knowledge else None
                        } if profile.previous_knowledge else {},
                        "learning_experiences": {
                            "learning_style": profile.learning_experiences.get("learning_style") if profile.learning_experiences else None,
                            "preferred_methods": profile.learning_experiences.get("preferred_methods", []) if profile.learning_experiences else []
                        } if profile.learning_experiences else {}
                    }
            except Exception:
                # If profile fetch fails, continue without summary
                pass
        
        # Build learning path info for frontend
        learning_path_info = None
        if learning_path:
            learning_path_info = {
                "path_id": str(learning_path.id),
                "path_name": learning_path.path_name,
                "version": learning_path.version,
                "total_steps": len(steps),
                "current_step": next_step.get("title") if next_step else None,
                "progress_percentage": (learning_path.progress_data or {}).get("progress_percentage", 0),
                "steps": steps[:10],  # Include first 10 steps for preview
                "has_path": True
            }
        elif path_generating:
            learning_path_info = {
                "has_path": False,
                "generating": True
            }
        else:
            learning_path_info = {
                "has_path": False,
                "generating": False
            }
        
        return {
            "greeting": greeting,
            "profile_completed": profile_status["completed"],
            "profile_skipped": profile_status.get("skipped", False),
            "profile_summary": profile_summary,  # Profile data for display in Home UI
            "progress_summary": {
                "total_sessions": dashboard.total_sessions,
                "total_messages": dashboard.total_messages,
                "last_session_at": str(dashboard.last_session_at) if dashboard.last_session_at else None
            },
            "next_learning_step": next_step,
            "next_steps": next_steps,  # Next 3 steps with can_do_id and endpoints
            "learning_path_info": learning_path_info,  # Full learning path info for display
            "path_generating": path_generating,
            "recent_lessons": recent_lessons,
            "suggestions": [
                "Complete your next learning step",
                "Review previous lessons",
                "Start a new CanDo session"
            ]  # TODO: Generate with AI based on context
        }
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        import structlog
        import traceback
        logger = structlog.get_logger()
        error_trace = traceback.format_exc()
        logger.error(
            "home_status_failed",
            error=str(e),
            error_type=type(e).__name__,
            traceback=error_trace
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get home status: {str(e)}"
        )


@router.get("/sessions")
async def list_home_sessions(
    db: AsyncSession = Depends(get_postgresql_session),
    current_user: User = Depends(get_current_user)
):
    """List user's home chat sessions."""
    # Get sessions with title starting with "home" or session_type = "home"
    sessions = await ConversationService.list_sessions(
        db, current_user.id, limit=50, offset=0
    )
    
    home_sessions = [
        s for s in sessions
        if (s.title and "home" in s.title.lower()) or s.session_type == "home"
    ]
    
    return [
        {
            "id": str(s.id),
            "title": s.title or "Home",
            "created_at": str(s.created_at),
            "total_messages": s.total_messages or 0
        }
        for s in home_sessions
    ]


@router.post("/sessions")
async def create_home_session(
    payload: Dict[str, Any],
    db: AsyncSession = Depends(get_postgresql_session),
    current_user: User = Depends(get_current_user)
):
    """Create a new home chat session."""
    session_name = payload.get("session_name", "home")
    greeting = payload.get("greeting")
    user_actions = payload.get("user_actions", {})
    
    # Load home greeting prompt
    # Path: backend/app/api/v1/endpoints/home_chat.py -> backend/app/prompts/
    base_dir = Path(__file__).parent.parent.parent.parent  # Go from endpoints/ to app/
    prompt_path = base_dir / "prompts" / "home_greeting_prompt.txt"
    system_prompt = None
    try:
        with open(prompt_path, "r", encoding="utf-8") as f:
            system_prompt = f.read()
    except Exception:
        # Enhanced system prompt with profile context
        system_prompt = """You are a friendly AI language tutor GUIDE and COACH. Your role is to have natural conversations with learners while guiding them to appropriate learning activities.

**Your Capabilities:**
- Have natural, conversational interactions with learners
- Answer questions about their learning journey, progress, and goals
- Provide encouragement and motivation
- Guide users to learning endpoints when appropriate:
  - CanDo lessons: /api/v1/cando/lessons/start?can_do_id=JF:21
  - Guided dialogue: /api/v1/cando/lessons/guided/turn
  - Lexical lessons: /api/v1/lexical/lessons/activate?can_do_id=JF:21

**Your Approach:**
- Be conversational and helpful - you can discuss their learning goals, answer questions, and provide guidance
- When users want to practice or learn, direct them to appropriate endpoints
- Acknowledge their progress and celebrate achievements
- Be encouraging and supportive
- Use the profile context and user actions to personalize your responses"""
    
    # Add user actions context to system prompt
    if user_actions:
        user_actions_str = f"""
**User Actions Context:**
- Recent lessons: {user_actions.get('recent_lessons', [])}
- Progress: {user_actions.get('progress', {})}
- Next step: {user_actions.get('next_step', {})}

Use this information to personalize your guidance and acknowledge achievements.
"""
        system_prompt = system_prompt + user_actions_str
    
    # Add profile context if available
    try:
        from app.models.database_models import UserProfile
        profile_result = await db.execute(
            select(UserProfile).where(UserProfile.user_id == current_user.id)
        )
        profile = profile_result.scalar_one_or_none()
        if profile:
            profile_context = f"""
**User Profile Context (use this to personalize conversations):**
- Learning Goals: {', '.join(profile.learning_goals or [])}
- Experience Level: {profile.previous_knowledge.get('experience_level', 'Not specified') if profile.previous_knowledge else 'Not specified'}
- Learning Style: {profile.learning_experiences.get('learning_style', 'Not specified') if profile.learning_experiences else 'Not specified'}

Use this profile information to have more personalized and relevant conversations. Reference their goals and preferences when appropriate.
"""
            system_prompt = system_prompt + profile_context
    except Exception:
        pass  # Continue without profile context if unavailable
    
    # If greeting provided, prepend it to system prompt as context
    if greeting:
        system_prompt = f"""Previous greeting context (for reference):
{greeting}

---

{system_prompt}"""
    
    # Build conversation context with user actions
    conversation_context = {
        "home_session": True,
        "greeting": greeting,
        "user_actions": user_actions
    }
    
    session = await ConversationService.create_session(
        db=db,
        user_id=current_user.id,
        language_code=payload.get("language_code", current_user.target_languages[0] if current_user.target_languages else "ja"),
        ai_provider=payload.get("ai_provider", current_user.preferred_ai_provider or "openai"),
        ai_model=payload.get("ai_model", "gpt-4o-mini"),
        title=f"Home: {session_name}",
        session_type="home",
        system_prompt=system_prompt,
        conversation_context=conversation_context
    )
    
    # If greeting provided, save it as the first assistant message
    if greeting:
        await ConversationService.add_message(
            db=db,
            session_id=session.id,
            role="assistant",
            content=greeting,
            content_type="text",
            message_order=1
        )
    
    return {
        "id": str(session.id),
        "title": session.title,
        "status": session.status,
        "created_at": str(session.created_at)
    }


@router.get("/sessions/{session_id}")
async def get_home_session(
    session_id: str,
    db: AsyncSession = Depends(get_postgresql_session),
    current_user: User = Depends(get_current_user)
):
    """Get specific home chat session details."""
    session = await ConversationService.get_session(db, uuid.UUID(session_id), current_user.id)
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    return {
        "id": str(session.id),
        "title": session.title,
        "session_type": session.session_type,
        "status": session.status,
        "created_at": str(session.created_at),
        "total_messages": session.total_messages or 0
    }


@router.post("/sessions/{session_id}/messages")
async def send_home_message(
    session_id: str,
    payload: Dict[str, Any],
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_postgresql_session),
    current_user: User = Depends(get_current_user)
):
    """Send message to home chat session (reuses conversation endpoint logic)."""
    try:
        # Use ConversationService directly
        from app.services.conversation_service import ConversationService
        from sqlalchemy import select, func
        from app.models.database_models import ConversationMessage
        
        # Verify session exists and belongs to user
        session = await ConversationService.get_session(
            db, uuid.UUID(session_id), current_user.id
        )
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
        
        # Determine next order
        result = await db.execute(
            select(func.coalesce(func.max(ConversationMessage.message_order), 0)).where(
                ConversationMessage.session_id == uuid.UUID(session_id)
            )
        )
        next_order = (result.scalar() or 0) + 1
        
        # Save user message
        message = await ConversationService.add_message(
            db=db,
            session_id=uuid.UUID(session_id),
            role=payload.get("role", "user"),
            content=payload.get("content", ""),
            content_type=payload.get("content_type", "text"),
            ai_provider=payload.get("ai_provider"),
            ai_model=payload.get("ai_model"),
            message_order=next_order,
            generate_embedding=False,  # We'll handle this in background task
        )
        
        # Generate embedding in background for user messages
        if message.role == "user" and message.content and message.content.strip():
            async def generate_embedding_background():
                """Background task to generate and store embedding."""
                from app.db import AsyncSessionLocal
                from app.services.embedding_service import EmbeddingService
                async with AsyncSessionLocal() as new_db:
                    try:
                        embedding_service = EmbeddingService()
                        await embedding_service.generate_and_store_message_embedding(
                            message_id=str(message.id),
                            content=message.content,
                            postgresql_session=new_db,
                            provider="openai"
                        )
                    except Exception as e:
                        import structlog
                        logger = structlog.get_logger()
                        logger.warning("Failed to generate embedding in background", 
                                     message_id=str(message.id),
                                     error=str(e))
            
            background_tasks.add_task(generate_embedding_background)
        
        # Return message info (AI reply will be streamed separately)
        return {
            "user_message": {"id": str(message.id), "order": message.message_order, "created_at": str(message.created_at)},
            "assistant_message": None  # Use streaming endpoint for AI reply
        }
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        import structlog
        logger = structlog.get_logger()
        logger.error("send_home_message_failed", error=str(e), session_id=session_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send message: {str(e)}"
        )


@router.get("/sessions/{session_id}/stream")
async def stream_home_reply(
    session_id: str,
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_postgresql_session),
    current_user: User = Depends(get_current_user)
):
    """Stream assistant reply for home chat session with real-time progress tracking."""
    from app.services.conversation_service import ConversationService
    from sqlalchemy import text
    import structlog
    import traceback
    
    logger = structlog.get_logger()
    
    try:
        # Validate session_id format
        try:
            session_uuid = uuid.UUID(session_id)
        except ValueError:
            logger.error("invalid_session_id_format", session_id=session_id)
            raise HTTPException(status_code=400, detail="Invalid session ID format")
        
        # Fetch latest user progress before generating reply
        try:
            session = await ConversationService.get_session(db, session_uuid, current_user.id)
        except Exception as session_error:
            logger.error("failed_to_fetch_session", session_id=session_id, error=str(session_error))
            await db.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to fetch session: {str(session_error)}")
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # CRITICAL: Extract ALL session and user attributes as simple types IMMEDIATELY after fetch
        # This prevents lazy loading issues when the session is expired later
        session_msg_count = int(session.total_messages or 0)
        session_language_code = str(session.language_code) if session.language_code else "ja"
        session_title = str(session.title) if session.title else "Home"
        session_ai_provider = str(session.ai_provider) if session.ai_provider else "openai"
        session_ai_model = str(session.ai_model) if session.ai_model else "gpt-4o-mini"
        session_system_prompt_raw = session.system_prompt
        session_system_prompt = str(session_system_prompt_raw) if session_system_prompt_raw else ""
        
        # Extract current_user attributes immediately (including id to avoid any ORM access)
        user_id_uuid = current_user.id  # Extract ID immediately as UUID
        user_current_level = str(getattr(current_user, "current_level", "")) if getattr(current_user, "current_level", None) else None
        user_learning_goals_raw = getattr(current_user, "learning_goals", []) or []
        user_learning_goals = [str(g) for g in user_learning_goals_raw if g]
        
        # Get recent lesson progress (with error handling)
        recent_lessons = []
        try:
            cando_sessions_result = await db.execute(
                text("""
                    SELECT 
                        can_do_id,
                        phase,
                        completed_count,
                        updated_at
                    FROM lesson_sessions
                    WHERE expires_at > NOW()
                    AND can_do_id IS NOT NULL
                    ORDER BY updated_at DESC
                    LIMIT 5
                """)
            )
            recent_lessons = [dict(row) for row in cando_sessions_result]
        except Exception as e:
            import structlog
            logger = structlog.get_logger()
            logger.warning("Failed to fetch recent lessons", error=str(e))
            await db.rollback()
        
        # Get learning path progress (with error handling)
        # Use already-extracted user_id_uuid to avoid ORM access
        current_step = None
        progress = {}
        learning_path_data = None
        try:
            # Fetch learning path - ensure we're in proper async context
            learning_path_obj = await learning_path_service.get_active_learning_path(db, user_id_uuid)
            if learning_path_obj:
                # Extract all data as simple Python types immediately
                learning_path_data = {
                    "id": str(learning_path_obj.id),
                    "path_name": str(learning_path_obj.path_name) if learning_path_obj.path_name else None,
                    "progress_data": dict(learning_path_obj.progress_data) if learning_path_obj.progress_data else {},
                    "path_data": dict(learning_path_obj.path_data) if learning_path_obj.path_data else {}
                }
                progress = learning_path_data.get("progress_data", {})
                path_data = learning_path_data.get("path_data", {})
                steps = list(path_data.get("steps", []))
                current_step_id = progress.get("current_step_id")
                if current_step_id and steps:
                    for s in steps:
                        step_dict = dict(s) if isinstance(s, dict) else {}
                        if step_dict.get("step_id") == current_step_id:
                            current_step = step_dict
                            break
        except Exception as e:
            import structlog
            logger = structlog.get_logger()
            logger.warning("Failed to fetch learning path - continuing without it", error=str(e), error_type=type(e).__name__)
            # Continue without learning path - it's not critical for streaming
            current_step = None
            progress = {}
            learning_path_data = None
        
        # CRITICAL: Extract ALL ORM attributes as simple types BEFORE any operations
        # Use already-extracted session system prompt
        enhanced_system_prompt = session_system_prompt
        
        # Extract profile data as simple types BEFORE using it
        profile_learning_goals = []
        profile_experience_level = "Not specified"
        profile_learning_style = "Not specified"
        
        # Add profile context if available (for existing sessions that might not have it)
        try:
            from app.models.database_models import UserProfile
            profile_result = await db.execute(
                select(UserProfile).where(UserProfile.user_id == user_id_uuid)  # Use already-extracted user_id
            )
            profile = profile_result.scalar_one_or_none()
            if profile:
                # Extract ALL profile attributes as simple types immediately
                profile_learning_goals = list(profile.learning_goals or [])
                profile_previous_knowledge = dict(profile.previous_knowledge or {})
                profile_learning_experiences = dict(profile.learning_experiences or {})
                profile_experience_level = str(profile_previous_knowledge.get('experience_level', 'Not specified'))
                profile_learning_style = str(profile_learning_experiences.get('learning_style', 'Not specified'))
                
                if "{profile_data}" not in enhanced_system_prompt:
                    profile_context = f"""
**User Profile Context (use this to personalize conversations):**
- Learning Goals: {', '.join(profile_learning_goals)}
- Experience Level: {profile_experience_level}
- Learning Style: {profile_learning_style}

Use this profile information to have more personalized and relevant conversations. Reference their goals and preferences when appropriate. You can discuss their learning goals, answer questions about their progress, and provide guidance.
"""
                    enhanced_system_prompt = enhanced_system_prompt + profile_context
        except Exception as profile_err:
            import structlog
            logger = structlog.get_logger()
            logger.warning("Failed to add profile context to stream", error=str(profile_err))
        
        # Add progress context
        if recent_lessons or current_step:
            progress_pct = progress.get('progress_percentage', 0) if progress else 0
            current_step_title = current_step.get('title') if current_step and isinstance(current_step, dict) else 'None'
            progress_context = f"""
**LATEST USER PROGRESS (update this context in your response):**
- Recent lessons: {recent_lessons}
- Current learning step: {current_step_title}
- Progress: {progress_pct}%

Acknowledge these achievements and guide them to next steps.
"""
            enhanced_system_prompt = enhanced_system_prompt + progress_context
        
        # Ensure the prompt is conversational (for existing sessions with old prompts)
        if "conversational" not in enhanced_system_prompt.lower() and "discuss" not in enhanced_system_prompt.lower():
            conversational_note = """
**IMPORTANT: You are a conversational AI tutor. You can:
- Have natural conversations with learners
- Answer questions about their learning journey, progress, and goals
- Provide encouragement and motivation
- Discuss their learning goals and preferences
- Guide them to learning endpoints when they want to practice
"""
            enhanced_system_prompt = enhanced_system_prompt + conversational_note
        
        # All database operations must complete before the generator starts
        # Session values already extracted above - no need to extract again
        # Commit any pending changes to ensure clean state before generator
        try:
            await db.commit()
        except Exception:
            pass  # Ignore if commit fails (might already be committed)
        
        # Get message history and prepare for streaming
        # Use enhanced system prompt directly instead of modifying session object
        # Ensure we can see the latest messages (handle potential race condition with just-sent messages)
        import asyncio
        from sqlalchemy import select, func
        
        # session_msg_count already extracted above as simple type
        
        history = []
        try:
            max_retries = 5
            for attempt in range(max_retries):
                try:
                    history = await ConversationService.list_messages(db, session_uuid, limit=40, offset=0, ascending=True)
                except Exception as msg_error:
                    logger.warning("failed_to_list_messages", attempt=attempt, error=str(msg_error))
                    if attempt < max_retries - 1:
                        await asyncio.sleep(0.1)
                        continue
                    else:
                        raise
                
                # Check if we have messages and at least one user message
                # Extract roles immediately to avoid ORM access
                if history:
                    user_message_count = 0
                    for m in history:
                        role = str(m.role) if m.role else ""
                        if role == "user":
                            user_message_count += 1
                    if user_message_count > 0:
                        # If session says we have messages but got fewer, might be a race condition
                        if len(history) >= session_msg_count or session_msg_count == 0:
                            break  # We have the expected messages
                
                if attempt < max_retries - 1:
                    await asyncio.sleep(0.1) # Small delay to ensure message is committed and visible
        except Exception as history_error:
            logger.error("failed_to_get_message_history", session_id=session_id, error=str(history_error))
            await db.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to get message history: {str(history_error)}")
        
        # CRITICAL: Extract ALL values from ORM objects as simple types BEFORE generator
        # This prevents greenlet errors when DB session is closed
        history_payload = []
        for m in history:
            # Extract all attributes as simple types immediately
            role = str(m.role) if m.role else "user"
            content = str(m.content) if m.content else ""
            history_payload.append({"role": role, "content": content})
        
        # Ensure we have at least one user message to respond to
        user_messages = [m for m in history_payload if m.get("role") == "user"]
        if not user_messages:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No user messages found in session to respond to"
            )
        
        # Build session metadata (use already-extracted values to avoid lazy loading)
        session_meta = {
            "language_code": session_language_code,
            "current_level": user_current_level,  # Use already-extracted value
            "learning_goals": user_learning_goals,  # Use already-extracted value
            "topic": session_title,
        }
        
        # Extract corrections from history (convert to strings to avoid lazy loading)
        # Use history_payload instead of history to avoid ORM access
        corrections_memory = []
        for m in history_payload:
            if m.get("role") == "assistant" and m.get("content") and "correct" in (m.get("content") or "").lower():
                corrections_memory.append(f"Corrected '{m.get('content')}'")
        corrections_memory = corrections_memory[-5:]
        
        # Extract session values before streaming (all as simple types)
        # Use already-extracted values to avoid accessing ORM object after commit
        system_prompt_to_use = str(enhanced_system_prompt)  # Ensure it's a string
        ai_provider = session_ai_provider  # Use already-extracted value
        ai_model = session_ai_model  # Use already-extracted value
        
        # Determine next order for assistant message
        from sqlalchemy import select, func
        try:
            result = await db.execute(
                select(func.coalesce(func.max(ConversationMessage.message_order), 0)).where(
                    ConversationMessage.session_id == session_uuid
                )
            )
            next_order = (result.scalar() or 0) + 1
        except Exception as order_error:
            logger.warning("failed_to_get_next_order", error=str(order_error))
            await db.rollback()
            try:
                result = await db.execute(
                    select(func.coalesce(func.max(ConversationMessage.message_order), 0)).where(
                        ConversationMessage.session_id == session_uuid
                    )
                )
                next_order = (result.scalar() or 0) + 1
            except Exception:
                # Fallback to 1 if we can't determine order
                next_order = 1
        
        # Store full_text outside generator to persist after streaming
        full_text_container: list[str] = []
        streaming_error: list[Exception] = []
        
        # Create streaming generator using enhanced prompt
        async def event_generator():
            ai = AIChatService()
            full_text: str = ""
            try:
                async for chunk in ai.stream_reply(
                    provider=ai_provider,
                    model=ai_model,
                    messages=history_payload,
                    system_prompt=system_prompt_to_use,  # Use enhanced prompt here
                    session_metadata=session_meta,
                    corrections_memory=corrections_memory,
                    knowledge_terms=[],
                    past_conversation_context=[],
                ):
                    full_text += chunk
                    yield f"data: {chunk}\n\n"
                
                # Store full text for persistence
                full_text_container.append(full_text)
                yield "data: [DONE]\n\n"
            except Exception as e:
                streaming_error.append(e)
                import structlog
                logger = structlog.get_logger()
                logger.error("streaming_failed", error=str(e), error_type=type(e).__name__, session_id=session_id)
                yield "event: error\ndata: streaming_failed\n\n"
        
        # Persist message after streaming
        # Use background_tasks which FastAPI handles properly with async context
        async def persist_message_after_stream():
            if not full_text_container:
                return
            try:
                full_text = full_text_container[0]
                if full_text.strip():
                    from app.db import AsyncSessionLocal
                    # Use context manager to ensure proper session lifecycle
                    async with AsyncSessionLocal() as new_db:
                        try:
                            await ConversationService.add_message(
                                db=new_db,
                                session_id=uuid.UUID(session_id),
                                role="assistant",
                                content=full_text,
                                content_type="text",
                                ai_provider=ai_provider,
                                ai_model=ai_model,
                                message_order=next_order,
                            )
                            await new_db.commit()
                        except Exception:
                            await new_db.rollback()
                            raise
            except Exception as e:
                import structlog
                logger = structlog.get_logger()
                logger.error("Failed to persist message after stream", error=str(e), session_id=session_id, error_type=type(e).__name__)
        
        background_tasks.add_task(persist_message_after_stream)
        
        # Create streaming response with CORS headers
        from app.core.config import settings
        response = StreamingResponse(event_generator(), media_type="text/event-stream")
        origin = request.headers.get("origin") if request else None
        if settings.DEBUG:
            response.headers["Access-Control-Allow-Origin"] = origin or "*"
        elif origin and (origin in settings.CORS_ORIGINS):
            response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        response.headers["Cache-Control"] = "no-cache"
        return response
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        error_trace = traceback.format_exc()
        logger.error(
            "stream_home_reply_failed",
            error=str(e),
            error_type=type(e).__name__,
            session_id=session_id,
            traceback=error_trace
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to stream reply: {str(e)}"
        )

