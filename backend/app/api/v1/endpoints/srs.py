"""
Minimal SRS endpoints (Phase 2): schedule next review based on a simple rule.
"""

from datetime import datetime, timedelta
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, Field


router = APIRouter()


class SRSRequest(BaseModel):
    item_id: str = Field(min_length=1)
    last_interval_days: int = Field(ge=0, default=0)
    grade: Literal["again", "hard", "good", "easy"]


class SRSResponse(BaseModel):
    item_id: str
    next_interval_days: int
    next_review_at: datetime


@router.post("/schedule", response_model=SRSResponse)
async def schedule_review(req: SRSRequest) -> SRSResponse:
    # Very simple scheduling rule to unblock UI integration:
    mapping = {"again": 0, "hard": max(1, req.last_interval_days), "good": max(1, req.last_interval_days * 2 or 1), "easy": max(2, int(req.last_interval_days * 2.5) or 2)}
    next_days = mapping.get(req.grade, 1)
    return SRSResponse(
        item_id=req.item_id,
        next_interval_days=next_days,
        next_review_at=datetime.utcnow() + timedelta(days=next_days),
    )


