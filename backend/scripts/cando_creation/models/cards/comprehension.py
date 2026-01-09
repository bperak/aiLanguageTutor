# Comprehension stage card models
from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field, ConfigDict

from ..base import ImageSpec, JPText, LLMGenSpec
from .exercises import MatchPair


class ComprehensionExerciseItem(BaseModel):
    """Enhanced exercise item for comprehension stage with multiple types"""

    model_config = ConfigDict(extra="forbid")
    exercise_type: Literal[
        "reading_qa",
        "listening",
        "matching",
        "ordering",
        "gap_fill",
        "information_extraction",
        "picture_text_matching",
        "context_inference",
    ]
    id: str
    instructions: Dict[str, str]
    # Type-specific fields (use Optional based on exercise_type)
    question: Optional[JPText] = None  # For reading_qa, context_inference
    answer: Optional[JPText] = None  # For reading_qa
    options: Optional[List[JPText]] = None  # For gap_fill, reading_qa (multiple choice)
    correct_answer: Optional[Union[str, int, List[int]]] = None  # Answer key
    pairs: Optional[List[MatchPair]] = None  # For matching
    segments: Optional[List[str]] = None  # For ordering
    correct_order: Optional[List[int]] = None  # For ordering
    text_passage: Optional[JPText] = (
        None  # For information_extraction, context_inference
    )
    image: Optional[ImageSpec] = None  # For picture_text_matching
    gen: Optional[LLMGenSpec] = None


class ComprehensionExercisesCard(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["ComprehensionExercisesCard"] = "ComprehensionExercisesCard"
    title: Dict[str, str]
    items: List[ComprehensionExerciseItem]
    gen: Optional[LLMGenSpec] = None


class AIComprehensionStage(BaseModel):
    """Stage for AI comprehension tutor (similar to GuidedStage)"""

    model_config = ConfigDict(extra="forbid")
    stage_id: str
    goal_en: str
    question: JPText
    expected_answer_keywords: List[str]  # Keywords that should appear in answer
    hints: List[Dict[str, str]]
    ai_feedback: Dict[str, Any]  # Rubric and feedback structure


class AIComprehensionTutorCard(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["AIComprehensionTutorCard"] = "AIComprehensionTutorCard"
    title: Dict[str, str]
    stages: List[AIComprehensionStage]
    gen: Optional[LLMGenSpec] = None

