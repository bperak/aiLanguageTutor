# Production stage card models
from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field, ConfigDict

from ..base import JPText, LLMGenSpec


class ProductionExerciseItem(BaseModel):
    """Enhanced exercise item for production stage"""

    model_config = ConfigDict(extra="forbid")
    exercise_type: Literal[
        "slot_fill",
        "transformation",
        "sentence_construction",
        "translation",
        "writing",
        "role_play_completion",
        "sentence_completion",
        "dialogue_completion",
        "personalization",
        "sentence_reordering",
        "form_focused",
    ]
    id: str
    instructions: Dict[str, str]
    # Type-specific fields
    prompt: Optional[Union[JPText, str]] = (
        None  # For sentence_construction, writing, etc.
    )
    template: Optional[JPText] = None  # For slot_fill, transformation
    source_sentence: Optional[JPText] = None  # For transformation, sentence_completion
    target_language: Optional[str] = None  # For translation
    scrambled_words: Optional[List[str]] = None  # For sentence_reordering
    grammar_pattern_id: Optional[str] = None  # For form_focused
    expected_elements: Optional[List[str]] = (
        None  # Expected vocabulary/grammar in response
    )
    rubric: Optional[Dict[str, Any]] = None  # Evaluation rubric
    gen: Optional[LLMGenSpec] = None


class ProductionExercisesCard(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["ProductionExercisesCard"] = "ProductionExercisesCard"
    title: Dict[str, str]
    items: List[ProductionExerciseItem]
    gen: Optional[LLMGenSpec] = None


class AIProductionEvaluationStage(BaseModel):
    """Stage for AI production evaluator"""

    model_config = ConfigDict(extra="forbid")
    stage_id: str
    goal_en: str
    exercise_type: str
    expected_patterns: List[str]  # Grammar patterns or vocabulary expected
    rubric: Dict[str, Any]  # pattern_correctness, fluency, content_relevance
    hints: List[Dict[str, str]]
    adaptive_difficulty: Optional[Dict[str, Any]] = None


class AIProductionEvaluatorCard(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["AIProductionEvaluatorCard"] = "AIProductionEvaluatorCard"
    title: Dict[str, str]
    stages: List[AIProductionEvaluationStage]
    gen: Optional[LLMGenSpec] = None

