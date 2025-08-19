"""
Conversation analytics endpoints (MVP): summary stats per user.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.auth import get_current_user
from app.db import get_postgresql_session
from app.models.database_models import ConversationMessage, ConversationSession, User


router = APIRouter()


class ConversationSummary(BaseModel):
    total_sessions: int
    total_messages: int
    avg_messages_per_session: float
    last_message_at: Optional[datetime]


@router.get("/summary", response_model=ConversationSummary)
async def get_conversation_summary(
    db: AsyncSession = Depends(get_postgresql_session),
    current_user: User = Depends(get_current_user),
) -> ConversationSummary:
    # Total sessions for user
    total_sessions_q = select(func.count()).select_from(ConversationSession).where(
        ConversationSession.user_id == current_user.id
    )
    total_sessions = (await db.execute(total_sessions_q)).scalar_one() or 0

    # Total messages for user's sessions
    total_messages_q = (
        select(func.count())
        .select_from(ConversationMessage)
        .join(ConversationSession, ConversationMessage.session_id == ConversationSession.id)
        .where(ConversationSession.user_id == current_user.id)
    )
    total_messages = (await db.execute(total_messages_q)).scalar_one() or 0

    # Last message timestamp
    last_message_q = (
        select(func.max(ConversationMessage.created_at))
        .join(ConversationSession, ConversationMessage.session_id == ConversationSession.id)
        .where(ConversationSession.user_id == current_user.id)
    )
    last_message_at = (await db.execute(last_message_q)).scalar_one()

    avg = float(total_messages) / float(total_sessions) if total_sessions else 0.0
    return ConversationSummary(
        total_sessions=int(total_sessions),
        total_messages=int(total_messages),
        avg_messages_per_session=round(avg, 2),
        last_message_at=last_message_at,
    )


@router.get("/messages_per_day")
async def messages_per_day(
    days: int = 14,
    db: AsyncSession = Depends(get_postgresql_session),
    current_user: User = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    """Return message counts per day for the past N days (UTC)."""
    day_bucket = func.date_trunc("day", ConversationMessage.created_at).label("day")
    q = (
        select(day_bucket, func.count())
        .select_from(ConversationMessage)
        .join(ConversationSession, ConversationMessage.session_id == ConversationSession.id)
        .where(ConversationSession.user_id == current_user.id)
        .group_by(day_bucket)
        .order_by(day_bucket.desc())
        .limit(days)
    )
    rows = (await db.execute(q)).all()
    rows = list(reversed(rows))
    return [{"date": r[0].date().isoformat(), "count": int(r[1])} for r in rows]


@router.get("/sessions_per_week")
async def sessions_per_week(
    weeks: int = 8,
    db: AsyncSession = Depends(get_postgresql_session),
    current_user: User = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    """Return session counts per week for the past N weeks (UTC)."""
    week_bucket = func.date_trunc("week", ConversationSession.created_at).label("week")
    q = (
        select(week_bucket, func.count())
        .select_from(ConversationSession)
        .where(ConversationSession.user_id == current_user.id)
        .group_by(week_bucket)
        .order_by(week_bucket.desc())
        .limit(weeks)
    )
    rows = (await db.execute(q)).all()
    rows = list(reversed(rows))
    return [{"week": r[0].date().isoformat(), "count": int(r[1])} for r in rows]

