"""
Conversation endpoints: create/list/get sessions, add messages.
"""

from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_postgresql_session
from app.core.config import settings
from app.services.knowledge_search_service import KnowledgeSearchService, SearchMode, SearchFilters
from app.api.v1.endpoints.auth import get_current_user
from app.models.database_models import User
from app.services.conversation_service import ConversationService
from app.services.ai_chat_service import AIChatService

router = APIRouter()


@router.post("/sessions")
async def create_session(
    payload: Dict[str, Any],
    db: AsyncSession = Depends(get_postgresql_session),
    current_user: User = Depends(get_current_user),
):
    session = await ConversationService.create_session(
        db=db,
        user_id=current_user.id,
        language_code=payload.get("language_code", "ja"),
        ai_provider=payload.get("ai_provider", "openai"),
        ai_model=payload.get("ai_model", "gpt-4o-mini"),
        title=payload.get("title"),
        session_type=payload.get("session_type", "chat"),
        system_prompt=payload.get("system_prompt"),
        conversation_context=payload.get("conversation_context", {}),
    )
    return {"id": str(session.id), "status": session.status, "created_at": str(session.created_at)}


@router.get("/sessions")
async def list_sessions(
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_postgresql_session),
    current_user: User = Depends(get_current_user),
):
    sessions = await ConversationService.list_sessions(db, current_user.id, limit, offset)
    return [
        {
            "id": str(s.id),
            "title": s.title,
            "status": s.status,
            "created_at": str(s.created_at),
            "language_code": s.language_code,
            "total_messages": s.total_messages or 0,
            "user_messages": s.user_messages or 0,
            "ai_messages": s.ai_messages or 0,
        }
        for s in sessions
    ]


@router.get("/sessions/{session_id}")
async def get_session(
    session_id: str,
    db: AsyncSession = Depends(get_postgresql_session),
    current_user: User = Depends(get_current_user),
):
    session = await ConversationService.get_session(db, session_id, current_user.id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return {
        "id": str(session.id),
        "title": session.title,
        "status": session.status,
        "created_at": str(session.created_at),
        "language_code": session.language_code,
        "ai_provider": session.ai_provider,
        "ai_model": session.ai_model,
    }


@router.put("/sessions/{session_id}")
async def update_session(
    session_id: str,
    payload: Dict[str, Any],
    db: AsyncSession = Depends(get_postgresql_session),
    current_user: User = Depends(get_current_user),
):
    """Update session metadata (currently only title)."""
    title = payload.get("title")
    if title is None or not isinstance(title, str):
        raise HTTPException(status_code=400, detail="'title' is required")
    session = await ConversationService.update_session_title(db, session_id, current_user.id, title)
    return {"id": str(session.id), "title": session.title}


@router.post("/sessions/{session_id}/messages")
async def add_message(
    session_id: str,
    payload: Dict[str, Any],
    db: AsyncSession = Depends(get_postgresql_session),
    current_user: User = Depends(get_current_user),
):
    # Determine next order (simple approach)
    from sqlalchemy import select, func
    from app.models.database_models import ConversationMessage

    result = await db.execute(
        select(func.coalesce(func.max(ConversationMessage.message_order), 0)).where(
            ConversationMessage.session_id == session_id
        )
    )
    next_order = (result.scalar() or 0) + 1

    # Save user message
    message = await ConversationService.add_message(
        db=db,
        session_id=session_id,
        role=payload.get("role", "user"),
        content=payload.get("content", ""),
        content_type=payload.get("content_type", "text"),
        ai_provider=payload.get("ai_provider"),
        ai_model=payload.get("ai_model"),
        message_order=next_order,
    )

    # Generate assistant reply using configured provider/model on the session
    session = await ConversationService.get_session(db, session_id, current_user.id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Build short context: last N messages
    history = await ConversationService.list_messages(db, session_id, limit=40, offset=0, ascending=True)
    history_payload = [{"role": m.role, "content": m.content} for m in history]
    # Build session metadata and light corrections memory
    session_meta = {
        "language_code": session.language_code,
        "current_level": getattr(current_user, "current_level", None),
        "learning_goals": getattr(current_user, "learning_goals", None),
        "topic": session.title,
    }
    corrections_memory = [
        f"Corrected '{m.content}'" for m in history if m.role == "assistant" and "correct" in (m.content or "").lower()
    ][-5:]
    # Knowledge term seeds: use last user message content
    last_user = next((m for m in reversed(history) if m.role == "user"), None)
    knowledge_terms = [last_user.content] if last_user else []

    # Stream-first architecture: do not generate here to avoid double replies.
    assistant_payload = None

    return {
        "user_message": {"id": str(message.id), "order": message.message_order, "created_at": str(message.created_at)},
        "assistant_message": assistant_payload,
    }


@router.get("/sessions/{session_id}/messages")
async def list_messages(
    session_id: str,
    limit: int = 50,
    offset: int = 0,
    ascending: bool = True,
    db: AsyncSession = Depends(get_postgresql_session),
    current_user: User = Depends(get_current_user),
):
    # Ensure the session belongs to the user
    session = await ConversationService.get_session(db, session_id, current_user.id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    messages = await ConversationService.list_messages(
        db=db, session_id=session_id, limit=limit, offset=offset, ascending=ascending
    )
    return [
        {
            "id": str(m.id),
            "role": m.role,
            "content": m.content,
            "order": m.message_order,
            "created_at": str(m.created_at),
        }
        for m in messages
    ]


@router.get("/search")
async def search_messages(
    q: str,
    limit: int = 50,
    db: AsyncSession = Depends(get_postgresql_session),
    current_user: User = Depends(get_current_user),
):
    """Simple message text search across user's sessions (ILIKE)."""
    from sqlalchemy import select
    from app.models.database_models import ConversationMessage, ConversationSession

    stmt = (
        select(ConversationMessage, ConversationSession)
        .join(ConversationSession, ConversationMessage.session_id == ConversationSession.id)
        .where(ConversationSession.user_id == current_user.id)
        .where(ConversationMessage.content.ilike(f"%{q}%"))
        .order_by(ConversationMessage.created_at.desc())
        .limit(limit)
    )
    rows = (await db.execute(stmt)).all()
    results = []
    for m, s in rows:
        results.append({
            "message_id": str(m.id),
            "session_id": str(s.id),
            "session_title": s.title,
            "role": m.role,
            "content": m.content,
            "created_at": str(m.created_at),
        })
    return {"items": results}


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str,
    db: AsyncSession = Depends(get_postgresql_session),
    current_user: User = Depends(get_current_user),
):
    from sqlalchemy import delete
    from app.models.database_models import ConversationSession

    session = await ConversationService.get_session(db, session_id, current_user.id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    # Delete cascades to messages via FK
    await db.execute(delete(ConversationSession).where(ConversationSession.id == session_id))
    await db.commit()
    return {"status": "deleted"}

@router.get("/sessions/{session_id}/stream")
async def stream_assistant_reply(
    session_id: str,
    db: AsyncSession = Depends(get_postgresql_session),
    neo4j_session=None,
    current_user: User = Depends(get_current_user),
    request: Request = None,
):
    """Stream an assistant reply for the current session via Server-Sent Events (SSE).

    Returns text/event-stream with data: <delta chunk> lines and a final [DONE].
    """
    session = await ConversationService.get_session(db, session_id, current_user.id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    history = await ConversationService.list_messages(db, session_id, limit=40, offset=0, ascending=True)
    history_payload = [{"role": m.role, "content": m.content} for m in history]
    # Build session metadata and light corrections memory for streaming as well
    session_meta = {
        "language_code": session.language_code,
        "current_level": getattr(current_user, "current_level", None),
        "learning_goals": getattr(current_user, "learning_goals", None),
        "topic": session.title,
    }
    corrections_memory = [
        f"Corrected '{m.content}'" for m in history if m.role == "assistant" and "correct" in (m.content or "").lower()
    ][-5:]
    # Knowledge terms via KG
    knowledge_terms: list[str] = []
    last_user = next((m for m in reversed(history) if m.role == "user"), None)
    if last_user and neo4j_session:
        try:
            ks = KnowledgeSearchService()
            results = await ks.search(
                query=last_user.content,
                mode=SearchMode.HYBRID,
                filters=SearchFilters(max_results=5),
                neo4j_session=neo4j_session,
                postgresql_session=db,
            )
            for r in results.results[:5]:
                name = getattr(r, "term", None) or getattr(r, "text", None) or getattr(r, "label", None)
                if name:
                    knowledge_terms.append(str(name))
        except Exception:
            knowledge_terms = [last_user.content]
    elif last_user:
        knowledge_terms = [last_user.content]

    # Determine next order for assistant message to persist after stream
    from sqlalchemy import select, func
    from app.models.database_models import ConversationMessage

    result = await db.execute(
        select(func.coalesce(func.max(ConversationMessage.message_order), 0)).where(
            ConversationMessage.session_id == session_id
        )
    )
    next_order = (result.scalar() or 0) + 1

    async def event_generator():  # type: ignore[no-any-unimported]
        ai = AIChatService()
        full_text: str = ""
        try:
            async for chunk in ai.stream_reply(
                provider=session.ai_provider or "openai",
                model=session.ai_model or "gpt-4o-mini",
                messages=history_payload,
                system_prompt=session.system_prompt,
                session_metadata=session_meta,
                corrections_memory=corrections_memory,
                knowledge_terms=knowledge_terms,
            ):
                full_text += chunk
                # SSE requires flushing; ensure CORS headers are set by ASGI stack
                yield f"data: {chunk}\n\n"
        except Exception:
            # Signal error to client
            yield "event: error\ndata: streaming_failed\n\n"
        else:
            # Persist assistant message if we have any content and it's not a duplicate
            if full_text.strip():
                from sqlalchemy import select
                from app.models.database_models import ConversationMessage
                # Check for an identical last assistant message to avoid duplicates
                last_assistant_q = (
                    select(ConversationMessage)
                    .where(
                        (ConversationMessage.session_id == session_id)
                        & (ConversationMessage.role == "assistant")
                    )
                    .order_by(ConversationMessage.message_order.desc())
                    .limit(1)
                )
                last_assistant = (await db.execute(last_assistant_q)).scalars().first()
                if not last_assistant or (last_assistant.content or "").strip() != full_text.strip():
                    _assistant = await ConversationService.add_message(
                        db=db,
                        session_id=session_id,
                        role="assistant",
                        content=full_text,
                        content_type="text",
                        ai_provider=session.ai_provider,
                        ai_model=session.ai_model,
                        message_order=next_order,
                    )
            yield "data: [DONE]\n\n"

    response = StreamingResponse(event_generator(), media_type="text/event-stream")
    # Add CORS headers for SSE explicitly (echo allowed origin)
    origin = request.headers.get("origin") if request else None
    if origin and (origin in settings.CORS_ORIGINS):
        response.headers["Access-Control-Allow-Origin"] = origin
    response.headers["Access-Control-Allow-Credentials"] = "true"
    response.headers["Cache-Control"] = "no-cache"
    return response

