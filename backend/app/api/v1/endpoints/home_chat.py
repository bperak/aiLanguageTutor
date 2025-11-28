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
        if profile_status["completed"]:
            learning_path = await learning_path_service.get_active_learning_path(db, current_user.id)
            if learning_path:
                progress = learning_path.progress_data or {}
                path_data = learning_path.path_data or {}
                steps = path_data.get("steps", [])
                current_step_id = progress.get("current_step_id")
                
                if current_step_id:
                    next_step = next(
                        (s for s in steps if s.get("step_id") == current_step_id),
                        None
                    )
                elif steps:
                    next_step = steps[0]
        
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
        
        # Build greeting context
        greeting_context = {
            "user_name": current_user.full_name or current_user.username,
            "profile_completed": profile_status["completed"],
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
            "cando_sessions_info": cando_sessions_info
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
        
        formatted_prompt = prompt_template.format(
            user_name=greeting_context["user_name"],
            profile_completed=str(profile_status["completed"]),
            learning_path_info=str(greeting_context["learning_path_info"]),
            recent_progress=str(greeting_context["recent_progress"]),
            cando_sessions_info=str(cando_sessions_info)
        )
        
        # Use user's native language (meta-language) for greeting, default to English
        native_lang = current_user.native_language or "en"
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
        
        return {
            "greeting": greeting,
            "profile_completed": profile_status["completed"],
            "progress_summary": {
                "total_sessions": dashboard.total_sessions,
                "total_messages": dashboard.total_messages,
                "last_session_at": str(dashboard.last_session_at) if dashboard.last_session_at else None
            },
            "next_learning_step": next_step,
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
        system_prompt = """You are a friendly AI language tutor GUIDE and COACH. Your role is to guide users to learning endpoints, not teach directly.

Learning happens via dedicated endpoints:
- CanDo lessons: /api/v1/cando/lessons/start?can_do_id=JF:21
- Guided dialogue: /api/v1/cando/lessons/guided/turn
- Lexical lessons: /api/v1/lexical/lessons/activate?can_do_id=JF:21

Give clear, actionable instructions. Direct users to endpoints. Acknowledge their progress."""
    
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
        current_step = None
        progress = {}
        learning_path = None
        try:
            learning_path = await learning_path_service.get_active_learning_path(db, current_user.id)
            if learning_path:
                progress = learning_path.progress_data or {}
                path_data = learning_path.path_data or {}
                steps = path_data.get("steps", [])
                current_step_id = progress.get("current_step_id")
                if current_step_id:
                    current_step = next((s for s in steps if s.get("step_id") == current_step_id), None)
        except Exception as e:
            import structlog
            logger = structlog.get_logger()
            logger.warning("Failed to fetch learning path", error=str(e))
            await db.rollback()
        
        # Enhance system prompt with latest progress
        enhanced_system_prompt = session.system_prompt or ""
        if recent_lessons or current_step:
            progress_context = f"""
**LATEST USER PROGRESS (update this context in your response):**
- Recent lessons: {recent_lessons}
- Current learning step: {current_step.get('title') if current_step else 'None'}
- Progress: {progress.get('progress_percentage', 0) if learning_path else 0}%

Acknowledge these achievements and guide them to next steps.
"""
            enhanced_system_prompt = enhanced_system_prompt + progress_context
        
        # Refresh session to get latest message count (handles race condition)
        try:
            await db.refresh(session)
        except Exception:
            pass  # Ignore if refresh fails
        
        # Get message history and prepare for streaming
        # Use enhanced system prompt directly instead of modifying session object
        # Ensure we can see the latest messages (handle potential race condition with just-sent messages)
        import asyncio
        from sqlalchemy import select, func
        
        # Get expected message count from session to detect if we're missing the latest message
        session_msg_count = session.total_messages or 0
        
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
                if history:
                    user_messages = [m for m in history if m.role == "user"]
                    if user_messages:
                        # If session says we have messages but got fewer, might be a race condition
                        if len(history) >= session_msg_count or session_msg_count == 0:
                            break  # We have the expected messages
                
                if attempt < max_retries - 1:
                    await asyncio.sleep(0.1) # Small delay to ensure message is committed and visible
        except Exception as history_error:
            logger.error("failed_to_get_message_history", session_id=session_id, error=str(history_error))
            await db.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to get message history: {str(history_error)}")
        
        history_payload = [{"role": m.role, "content": m.content or ""} for m in history]
        
        # Ensure we have at least one user message to respond to
        user_messages = [m for m in history_payload if m.get("role") == "user"]
        if not user_messages:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No user messages found in session to respond to"
            )
        
        # Build session metadata
        session_meta = {
            "language_code": session.language_code,
            "current_level": getattr(current_user, "current_level", None),
            "learning_goals": getattr(current_user, "learning_goals", None),
            "topic": session.title,
        }
        corrections_memory = [
            f"Corrected '{m.content}'" for m in history if m.role == "assistant" and "correct" in (m.content or "").lower()
        ][-5:]
        
        # Extract session values before streaming
        system_prompt_to_use = enhanced_system_prompt  # Use enhanced prompt directly
        ai_provider = session.ai_provider or "openai"
        ai_model = session.ai_model or "gpt-4o-mini"
        
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
        
        # Background task to persist message
        async def persist_message_after_stream():
            if not full_text_container:
                return
            from app.db import AsyncSessionLocal
            async with AsyncSessionLocal() as new_db:
                try:
                    full_text = full_text_container[0]
                    if full_text.strip():
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
                except Exception as e:
                    import structlog
                    logger = structlog.get_logger()
                    logger.error("Failed to persist message after stream", error=str(e), session_id=session_id)
                    await new_db.rollback()
        
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

