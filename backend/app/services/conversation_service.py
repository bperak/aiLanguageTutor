"""
Conversation service for session and message management.
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from fastapi import HTTPException
import structlog
import uuid
import asyncio

from app.models.database_models import ConversationSession, ConversationMessage
from app.services.embedding_service import EmbeddingService

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
        generate_embedding: bool = True,
    ) -> ConversationMessage:
        try:
            # Lightweight loop guard: if last user content matches the previous user message, mark content slightly to avoid infinite repetition downstream
            final_content = content
            if role == "user":
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
                        final_content = (content or "") + "\n[note: user repeated the same phrase]"
                except Exception:
                    pass
            
            message = ConversationMessage(
                session_id=session_id,
                role=role,
                content=final_content,
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

            await db.commit()
            await db.refresh(message)
            
            # Note: Embedding generation moved to endpoint level using BackgroundTasks
            # to avoid session closure issues. See conversations.py endpoint.
            
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

    @staticmethod
    async def search_similar_past_conversations(
        db: AsyncSession,
        user_id: uuid.UUID,
        query_embedding: List[float],
        current_session_id: Optional[uuid.UUID] = None,
        limit: int = 5,
        session_type: Optional[str] = None,
        days_back: Optional[int] = 30
    ) -> List[Dict[str, Any]]:
        """
        Search for similar past conversations using vector similarity.
        
        Args:
            db: Database session
            user_id: User ID to filter conversations
            query_embedding: Embedding vector of the query
            current_session_id: Exclude current session from results
            limit: Maximum number of results
            session_type: Filter by session type (e.g., 'home', 'chat')
            days_back: Only search messages from last N days
            
        Returns:
            List of similar messages with similarity scores
        """
        try:
            # Build query with filters
            where_clauses = [
                "s.user_id = :user_id",
                "m.content_embedding IS NOT NULL",
                "m.role = 'user'"  # Only search user messages for context
            ]
            params = {
                'user_id': user_id,
                'query_embedding': query_embedding,
                'limit': limit
            }
            
            if current_session_id:
                where_clauses.append("m.session_id != :current_session_id")
                params['current_session_id'] = current_session_id
            
            if session_type:
                where_clauses.append("s.session_type = :session_type")
                params['session_type'] = session_type
            
            if days_back:
                where_clauses.append("m.created_at > NOW() - INTERVAL ':days_back days'")
                params['days_back'] = days_back
            
            where_clause = " AND ".join(where_clauses)
            
            sql = f"""
            SELECT 
                m.id,
                m.session_id,
                m.content,
                m.role,
                m.created_at,
                s.title as session_title,
                s.session_type,
                1 - (m.content_embedding <=> :query_embedding) as similarity
            FROM conversation_messages m
            JOIN conversation_sessions s ON m.session_id = s.id
            WHERE {where_clause}
            ORDER BY m.content_embedding <=> :query_embedding
            LIMIT :limit
            """
            
            result = await db.execute(text(sql), params)
            rows = result.fetchall()
            
            return [
                {
                    'message_id': str(row.id),
                    'session_id': str(row.session_id),
                    'content': row.content,
                    'role': row.role,
                    'created_at': str(row.created_at),
                    'session_title': row.session_title,
                    'session_type': row.session_type,
                    'similarity': float(row.similarity)
                }
                for row in rows
            ]
        except Exception as e:
            logger.error("Failed to search similar conversations", error=str(e))
            return []

    @staticmethod
    async def hybrid_search_past_conversations(
        db: AsyncSession,
        user_id: uuid.UUID,
        query_text: str,
        query_embedding: List[float],
        current_session_id: Optional[uuid.UUID] = None,
        limit: int = 5,
        session_type: Optional[str] = None,
        days_back: Optional[int] = 30
    ) -> List[Dict[str, Any]]:
        """
        Hybrid search combining vector similarity and full-text search.
        Uses reciprocal rank fusion to merge results.
        
        Args:
            db: Database session
            user_id: User ID to filter conversations
            query_text: Text query for full-text search
            query_embedding: Embedding vector for vector search
            current_session_id: Exclude current session from results
            limit: Maximum number of results
            session_type: Filter by session type
            days_back: Only search messages from last N days
            
        Returns:
            List of similar messages with combined scores
        """
        try:
            # Build common filters
            common_filters = ["s.user_id = :user_id", "m.role = 'user'"]
            params = {
                'user_id': user_id,
                'query_text': query_text,
                'query_embedding': query_embedding,
                'limit': limit
            }
            
            if current_session_id:
                common_filters.append("m.session_id != :current_session_id")
                params['current_session_id'] = current_session_id
            
            if session_type:
                common_filters.append("s.session_type = :session_type")
                params['session_type'] = session_type
            
            if days_back:
                common_filters.append("m.created_at > NOW() - INTERVAL ':days_back days'")
                params['days_back'] = days_back
            
            common_where = " AND ".join(common_filters)
            
            # Hybrid search with reciprocal rank fusion
            sql = f"""
            WITH vector_search AS (
                SELECT 
                    m.id,
                    m.session_id,
                    m.content,
                    m.role,
                    m.created_at,
                    s.title as session_title,
                    s.session_type,
                    ROW_NUMBER() OVER (ORDER BY m.content_embedding <=> :query_embedding) as v_rank
                FROM conversation_messages m
                JOIN conversation_sessions s ON m.session_id = s.id
                WHERE {common_where}
                AND m.content_embedding IS NOT NULL
                ORDER BY m.content_embedding <=> :query_embedding
                LIMIT :limit
            ),
            text_search AS (
                SELECT 
                    m.id,
                    m.session_id,
                    m.content,
                    m.role,
                    m.created_at,
                    s.title as session_title,
                    s.session_type,
                    ROW_NUMBER() OVER (ORDER BY ts_rank_cd(m.textsearch, plainto_tsquery('english', :query_text)) DESC) as t_rank
                FROM conversation_messages m
                JOIN conversation_sessions s ON m.session_id = s.id
                WHERE {common_where}
                AND m.textsearch @@ plainto_tsquery('english', :query_text)
                ORDER BY ts_rank_cd(m.textsearch, plainto_tsquery('english', :query_text)) DESC
                LIMIT :limit
            )
            SELECT 
                COALESCE(v.id, t.id) as id,
                COALESCE(v.session_id, t.session_id) as session_id,
                COALESCE(v.content, t.content) as content,
                COALESCE(v.role, t.role) as role,
                COALESCE(v.created_at, t.created_at) as created_at,
                COALESCE(v.session_title, t.session_title) as session_title,
                COALESCE(v.session_type, t.session_type) as session_type,
                1.0 / (60 + COALESCE(v.v_rank, 1000)) + 1.0 / (60 + COALESCE(t.t_rank, 1000)) as score
            FROM vector_search v
            FULL OUTER JOIN text_search t ON v.id = t.id
            ORDER BY score DESC
            LIMIT :limit
            """
            
            result = await db.execute(text(sql), params)
            rows = result.fetchall()
            
            return [
                {
                    'message_id': str(row.id),
                    'session_id': str(row.session_id),
                    'content': row.content,
                    'role': row.role,
                    'created_at': str(row.created_at),
                    'session_title': row.session_title,
                    'session_type': row.session_type,
                    'score': float(row.score)
                }
                for row in rows
            ]
        except Exception as e:
            logger.error("Failed to hybrid search conversations", error=str(e))
            # Fallback to vector search only
            return await ConversationService.search_similar_past_conversations(
                db, user_id, query_embedding, current_session_id, limit, session_type, days_back
            )

    @staticmethod
    async def build_user_conversation_profile(
        db: AsyncSession,
        user_id: uuid.UUID,
        days_back: int = 90
    ) -> Dict[str, Any]:
        """
        Build a user conversation profile from their message embeddings.
        This creates an average embedding vector to represent their learning patterns.
        
        Args:
            db: Database session
            user_id: User ID
            days_back: Only consider messages from last N days
            
        Returns:
            Profile dict with average embedding, topics, patterns, etc.
        """
        try:
            # Get all user messages with embeddings
            result = await db.execute(
                text("""
                SELECT 
                    m.content_embedding,
                    m.content,
                    m.created_at,
                    s.session_type,
                    s.title as session_title
                FROM conversation_messages m
                JOIN conversation_sessions s ON m.session_id = s.id
                WHERE s.user_id = :user_id
                AND m.role = 'user'
                AND m.content_embedding IS NOT NULL
                AND m.created_at > NOW() - INTERVAL ':days_back days'
                ORDER BY m.created_at DESC
                LIMIT 100
                """),
                {
                    'user_id': user_id,
                    'days_back': days_back
                }
            )
            
            rows = result.fetchall()
            if not rows:
                return {
                    'has_profile': False,
                    'message_count': 0,
                    'topics': [],
                    'session_types': []
                }
            
            # Calculate average embedding (simple mean)
            # Note: This requires pgvector extension for vector operations
            avg_result = await db.execute(
                text("""
                SELECT AVG(m.content_embedding) as avg_embedding
                FROM conversation_messages m
                JOIN conversation_sessions s ON m.session_id = s.id
                WHERE s.user_id = :user_id
                AND m.role = 'user'
                AND m.content_embedding IS NOT NULL
                AND m.created_at > NOW() - INTERVAL ':days_back days'
                """),
                {
                    'user_id': user_id,
                    'days_back': days_back
                }
            )
            
            avg_embedding_row = avg_result.fetchone()
            avg_embedding = avg_embedding_row.avg_embedding if avg_embedding_row else None
            
            # Extract topics and session types
            session_types = list(set([row.session_type for row in rows if row.session_type]))
            topics = [row.session_title for row in rows if row.session_title]
            unique_topics = list(set(topics))[:10]  # Top 10 unique topics
            
            # Get recent conversation patterns
            recent_messages = [row.content for row in rows[:20]]
            
            return {
                'has_profile': True,
                'message_count': len(rows),
                'avg_embedding': avg_embedding,
                'session_types': session_types,
                'topics': unique_topics,
                'recent_patterns': recent_messages[:5],  # Sample of recent messages
                'days_analyzed': days_back
            }
        except Exception as e:
            logger.error("Failed to build user conversation profile", error=str(e))
            return {
                'has_profile': False,
                'error': str(e)
            }

    @staticmethod
    async def find_similar_users_by_profile(
        db: AsyncSession,
        user_id: uuid.UUID,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Find users with similar conversation profiles using embedding similarity.
        This can be used for collaborative learning or finding study partners.
        
        Args:
            db: Database session
            user_id: User ID to find similar users for
            limit: Maximum number of similar users
            
        Returns:
            List of similar users with similarity scores
        """
        try:
            # Get current user's profile
            profile = await ConversationService.build_user_conversation_profile(db, user_id)
            if not profile.get('has_profile') or not profile.get('avg_embedding'):
                return []
            
            # Find users with similar average embeddings
            # This is a simplified approach - in production, you'd want to store
            # user profiles in a separate table with indexed embeddings
            result = await db.execute(
                text("""
                WITH user_avg_embeddings AS (
                    SELECT 
                        s.user_id,
                        AVG(m.content_embedding) as avg_embedding,
                        COUNT(*) as message_count
                    FROM conversation_messages m
                    JOIN conversation_sessions s ON m.session_id = s.id
                    WHERE m.role = 'user'
                    AND m.content_embedding IS NOT NULL
                    AND m.created_at > NOW() - INTERVAL '90 days'
                    GROUP BY s.user_id
                    HAVING COUNT(*) >= 10  -- Minimum messages for meaningful profile
                )
                SELECT 
                    user_id,
                    message_count,
                    1 - (avg_embedding <=> :query_embedding) as similarity
                FROM user_avg_embeddings
                WHERE user_id != :user_id
                ORDER BY avg_embedding <=> :query_embedding
                LIMIT :limit
                """),
                {
                    'user_id': user_id,
                    'query_embedding': profile['avg_embedding'],
                    'limit': limit
                }
            )
            
            rows = result.fetchall()
            return [
                {
                    'user_id': str(row.user_id),
                    'similarity': float(row.similarity),
                    'message_count': row.message_count
                }
                for row in rows
            ]
        except Exception as e:
            logger.error("Failed to find similar users", error=str(e))
            return []


