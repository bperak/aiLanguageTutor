"""
Conversation service for session and message management.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException
import structlog
import uuid

from app.models.database_models import ConversationSession, ConversationMessage

logger = structlog.get_logger()


class ConversationService:
    """Service for managing conversation sessions and messages."""

    @staticmethod
    async def create_session(
        db: AsyncSession,
        user_id: uuid.UUID,
        language_code: str,
        ai_provider: str,
        ai_model: str,
        title: Optional[str] = None,
        session_type: str = "chat",
        system_prompt: Optional[str] = None,
        conversation_context: Optional[Dict[str, Any]] = None,
    ) -> ConversationSession:
        try:
            session = ConversationSession(
                user_id=user_id,
                title=title,
                language_code=language_code or "ja",
                session_type=session_type or "chat",
                status="active",
                ai_provider=ai_provider,
                ai_model=ai_model,
                system_prompt=system_prompt,
                conversation_context=conversation_context or {},
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                total_messages=0,
                user_messages=0,
                ai_messages=0,
                session_duration_seconds=0,
            )

            db.add(session)
            await db.commit()
            await db.refresh(session)

            return session
        except Exception as e:
            await db.rollback()
            logger.error("Failed to create session", error=str(e))
            raise HTTPException(status_code=500, detail="Failed to create session")

    @staticmethod
    async def list_sessions(
        db: AsyncSession, user_id: uuid.UUID, limit: int = 20, offset: int = 0
    ) -> List[ConversationSession]:
        result = await db.execute(
            select(ConversationSession)
            .where(ConversationSession.user_id == user_id)
            .order_by(ConversationSession.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return result.scalars().all()

    @staticmethod
    async def get_session(
        db: AsyncSession, session_id: uuid.UUID, user_id: uuid.UUID
    ) -> Optional[ConversationSession]:
        result = await db.execute(
            select(ConversationSession).where(
                (ConversationSession.id == session_id)
                & (ConversationSession.user_id == user_id)
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def update_session_title(
        db: AsyncSession, session_id: uuid.UUID, user_id: uuid.UUID, title: str
    ) -> ConversationSession:
        """Update a session title for the given user."""
        try:
            session = await ConversationService.get_session(db, session_id, user_id)
            if session is None:
                raise HTTPException(status_code=404, detail="Session not found")
            session.title = title
            session.updated_at = datetime.utcnow()
            await db.commit()
            await db.refresh(session)
            return session
        except HTTPException:
            raise
        except Exception as e:
            await db.rollback()
            logger.error("Failed to update session title", error=str(e))
            raise HTTPException(status_code=500, detail="Failed to update session")

    @staticmethod
    async def add_message(
        db: AsyncSession,
        session_id: uuid.UUID,
        role: str,
        content: str,
        message_order: int,
        content_type: str = "text",
        ai_provider: Optional[str] = None,
        ai_model: Optional[str] = None,
    ) -> ConversationMessage:
        try:
            message = ConversationMessage(
                session_id=session_id,
                role=role,
                content=content,
                content_type=content_type,
                ai_provider=ai_provider,
                ai_model=ai_model,
                message_order=message_order,
                created_at=datetime.utcnow(),
            )
            db.add(message)
            # Update session counters
            session = await db.get(ConversationSession, session_id)
            if session:
                session.total_messages = (session.total_messages or 0) + 1
                if role == "user":
                    session.user_messages = (session.user_messages or 0) + 1
                elif role == "assistant":
                    session.ai_messages = (session.ai_messages or 0) + 1
                session.updated_at = datetime.utcnow()
                # Lightweight loop guard: if last user content matches the previous user message, mark content slightly to avoid infinite repetition downstream
                try:
                    recent = await db.execute(
                        select(ConversationMessage).where(ConversationMessage.session_id == session_id).order_by(ConversationMessage.message_order.desc()).limit(2)
                    )
                    recent_msgs = list(recent.scalars())
                    if (
                        len(recent_msgs) >= 2
                        and recent_msgs[0].role == "user"
                        and recent_msgs[1].role == "user"
                        and (recent_msgs[0].content or "").strip().lower() == (recent_msgs[1].content or "").strip().lower()
                    ):
                        # Reason: helps the tutor detect repetition patterns
                        message.content = (message.content or "") + "\n[note: user repeated the same phrase]"
                except Exception:
                    pass

            await db.commit()
            await db.refresh(message)
            return message
        except Exception as e:
            await db.rollback()
            logger.error("Failed to add message", error=str(e))
            raise HTTPException(status_code=500, detail="Failed to add message")

    @staticmethod
    async def list_messages(
        db: AsyncSession,
        session_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0,
        ascending: bool = True,
    ) -> List[ConversationMessage]:
        from sqlalchemy import select

        order_clause = (
            ConversationMessage.message_order.asc()
            if ascending
            else ConversationMessage.message_order.desc()
        )
        result = await db.execute(
            select(ConversationMessage)
            .where(ConversationMessage.session_id == session_id)
            .order_by(order_clause)
            .limit(limit)
            .offset(offset)
        )
        return result.scalars().all()


