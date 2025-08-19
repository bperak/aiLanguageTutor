"""
Learning endpoints (MVP): personalized dashboard summary.
"""

from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.auth import get_current_user
from app.db import get_postgresql_session
from app.models.database_models import ConversationMessage, ConversationSession, User
from app.schemas.user import (
    DiagnosticQuizQuestion,
    DiagnosticQuizResponse,
    DiagnosticQuizResult,
)


router = APIRouter()


class DashboardResponse(BaseModel):
    """Minimal personalized dashboard summary."""

    user_id: str
    total_sessions: int
    total_messages: int
    last_session_at: Optional[datetime]


@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard(
    db: AsyncSession = Depends(get_postgresql_session),
    current_user: User = Depends(get_current_user),
) -> DashboardResponse:
    # Total sessions
    sessions_q = select(func.count()).select_from(ConversationSession).where(
        ConversationSession.user_id == current_user.id
    )
    total_sessions = (await db.execute(sessions_q)).scalar_one() or 0

    # Total messages (by joining sessions for safety)
    msgs_q = (
        select(func.count())
        .select_from(ConversationMessage)
        .join(ConversationSession, ConversationMessage.session_id == ConversationSession.id)
        .where(ConversationSession.user_id == current_user.id)
    )
    total_messages = (await db.execute(msgs_q)).scalar_one() or 0

    # Last session created_at
    last_q = (
        select(func.max(ConversationSession.created_at))
        .where(ConversationSession.user_id == current_user.id)
        .limit(1)
    )
    last_session_at = (await db.execute(last_q)).scalar_one()

    return DashboardResponse(
        user_id=str(current_user.id),
        total_sessions=int(total_sessions),
        total_messages=int(total_messages),
        last_session_at=last_session_at,
    )


# --- Onboarding Diagnostic Quiz (MVP) ---

_QUIZ_BANK: List[DiagnosticQuizQuestion] = [
    DiagnosticQuizQuestion(
        id="q1",
        type="multiple_choice",
        question="What is the reading of 日?",
        options=["にち", "ひ", "じつ", "に"],
        correct_answer="ひ",
        difficulty_level="beginner",
        skill_area="vocabulary",
    ),
    DiagnosticQuizQuestion(
        id="q2",
        type="translation",
        question="Translate to Japanese: 'Good morning'",
        options=None,
        correct_answer="おはよう",
        difficulty_level="beginner",
        skill_area="vocabulary",
    ),
    DiagnosticQuizQuestion(
        id="q3",
        type="multiple_choice",
        question="Choose the correct particle: 私___学生です。",
        options=["が", "は", "を", "に"],
        correct_answer="は",
        difficulty_level="beginner",
        skill_area="grammar",
    ),
]


@router.get("/diagnostic/quiz", response_model=List[DiagnosticQuizQuestion])
async def get_diagnostic_quiz() -> List[DiagnosticQuizQuestion]:
    return _QUIZ_BANK


@router.post("/diagnostic/grade", response_model=DiagnosticQuizResult)
async def grade_diagnostic_quiz(
    responses: List[DiagnosticQuizResponse],
    current_user: User = Depends(get_current_user),
) -> DiagnosticQuizResult:
    # Map id -> correct answer
    answer_key = {q.id: q.correct_answer for q in _QUIZ_BANK}
    correct = 0
    for r in responses:
        if answer_key.get(r.question_id) == r.user_answer:
            correct += 1
    total = max(1, len(_QUIZ_BANK))
    score = correct / total
    # Minimal level estimation
    assessed_level = "beginner" if score < 0.7 else "beginner+"
    confidence = round(0.5 + 0.5 * score, 2)
    return DiagnosticQuizResult(
        user_id=current_user.id,
        assessed_level=assessed_level,
        confidence_score=confidence,
        skill_breakdown={"vocabulary": score, "grammar": score},
        recommendations=["Start with basic particles", "Practice greetings"],
        suggested_learning_path=["hiragana", "basic particles", "common phrases"],
        completed_at=datetime.utcnow(),
    )


