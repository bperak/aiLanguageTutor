# Exercise and drill card models
from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field, ConfigDict

from ..base import ImageSpec, JPText, LLMGenSpec

# Note: GuidedStage is also used in interaction.py, but we define it here
# to avoid circular imports. If needed, it can be moved to a shared location.


class GuidedStage(BaseModel):
    model_config = ConfigDict(extra="forbid")
    stage_id: str
    goal_en: str
    expected_patterns: List[str]  # plan.grammar_functions ids
    hints: List[Dict[str, str]]
    learner_turn_schema: Dict[str, Any]
    ai_feedback: Dict[str, Any]


class GuidedDialogueCard(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["GuidedDialogueCard"] = "GuidedDialogueCard"
    mode: Literal["prompted", "mixed"] = "prompted"
    stages: List[GuidedStage]
    gen: Optional[LLMGenSpec] = None


class MatchPair(BaseModel):
    model_config = ConfigDict(extra="forbid")
    left: JPText
    right_options_en: List[str]
    answer_en: str


class MatchExercise(BaseModel):
    model_config = ConfigDict(extra="forbid")
    exercise_type: Literal["match"] = "match"
    id: str
    instructions: Dict[str, str]
    pairs: List[MatchPair]


class FillBlankExercise(BaseModel):
    model_config = ConfigDict(extra="forbid")
    exercise_type: Literal["fill_blank"] = "fill_blank"
    id: str
    item: JPText
    answer_key_en: List[str]


class OrderExercise(BaseModel):
    model_config = ConfigDict(extra="forbid")
    exercise_type: Literal["order"] = "order"
    id: str
    instructions: Dict[str, str]
    segments_ja: List[str]
    correct_order: List[int]


ExerciseItem = Union[MatchExercise, FillBlankExercise, OrderExercise]


class ExercisesCard(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["ExercisesCard"] = "ExercisesCard"
    items: List[ExerciseItem]
    gen: Optional[LLMGenSpec] = None


class CultureCard(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["CultureCard"] = "CultureCard"
    title: Dict[str, str]
    body: Dict[str, str]
    image: Optional[ImageSpec] = None
    gen: Optional[LLMGenSpec] = None


class FormulaicExpressionItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    expression: JPText
    context: Dict[str, str]  # When/where to use this expression
    examples: List[JPText] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    image: Optional[ImageSpec] = None


class FormulaicExpressionsCard(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["FormulaicExpressionsCard"] = "FormulaicExpressionsCard"
    title: Dict[str, str]
    items: List[FormulaicExpressionItem]
    gen: Optional[LLMGenSpec] = None


class SubstitutionSeed(BaseModel):
    model_config = ConfigDict(extra="forbid")
    place: str
    specialty_en: str


class SubstitutionDrill(BaseModel):
    model_config = ConfigDict(extra="forbid")
    drill_type: Literal["substitution"] = "substitution"
    id: str
    pattern_ref: str
    prompt_template: Dict[str, str]
    slots: List[str]
    seed_items: List[SubstitutionSeed]
    ai_support: Dict[str, str]


class PronunciationTarget(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ja: str
    romaji: str


class PronunciationDrill(BaseModel):
    model_config = ConfigDict(extra="forbid")
    drill_type: Literal["pronunciation"] = "pronunciation"
    id: str
    focus: List[PronunciationTarget]
    ai_support: Dict[str, str]


DrillItem = Union[SubstitutionDrill, PronunciationDrill]


class DrillsCard(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["DrillsCard"] = "DrillsCard"
    drills: List[DrillItem]
    gen: Optional[LLMGenSpec] = None

