"""
Pydantic schemas for Script API endpoints.
"""

from typing import List, Literal, Optional
from pydantic import BaseModel, Field


class ScriptItemResponse(BaseModel):
    """Response model for script items."""
    id: str = Field(..., description="Unique identifier for the script item")
    script_type: Literal["hiragana", "katakana"] = Field(..., description="Type of script")
    kana: str = Field(..., description="The kana character(s)")
    romaji: str = Field(..., description="Canonical romaji representation")
    romaji_aliases: List[str] = Field(default_factory=list, description="Accepted romaji variants")
    tags: List[str] = Field(default_factory=list, description="Tags (gojuon, dakuten, combo, etc.)")
    group: Optional[str] = Field(None, description="Optional grouping label")


class ScriptPracticeCheckRequest(BaseModel):
    """Request model for checking script practice answers."""
    item_id: str = Field(..., description="Script item ID")
    mode: Literal["kana_to_romaji", "romaji_to_kana", "mcq"] = Field(..., description="Practice mode")
    user_answer: str = Field(..., description="User's answer")
    choices: Optional[List[str]] = Field(None, description="Multiple choice options (for mcq validation)")


class ScriptPracticeCheckResponse(BaseModel):
    """Response model for script practice check."""
    item_id: str = Field(..., description="Script item ID")
    mode: str = Field(..., description="Practice mode used")
    is_correct: bool = Field(..., description="Whether the answer is correct")
    expected_answer: str = Field(..., description="Canonical expected answer")
    accepted_answers: List[str] = Field(..., description="All accepted answer variants")
    feedback: str = Field(..., description="Learner-friendly feedback message")


class ScriptProgressSummaryResponse(BaseModel):
    """Response model for script progress summary."""
    total_attempts: int = Field(..., description="Total practice attempts")
    correct_rate: float = Field(..., description="Overall correct rate (0.0-1.0)")
    items_practiced: int = Field(..., description="Number of unique items practiced")
    mastered_items: int = Field(..., description="Number of mastered items (last 3 attempts correct)")


class ScriptItemProgressResponse(BaseModel):
    """Response model for individual script item progress."""
    item_id: str = Field(..., description="Script item ID")
    last_attempted: Optional[str] = Field(None, description="ISO timestamp of last attempt")
    attempts: int = Field(..., description="Total number of attempts")
    correct_rate: float = Field(..., description="Correct rate for this item (0.0-1.0)")
    mastery_level: int = Field(..., ge=1, le=5, description="Mastery level (1-5)")

