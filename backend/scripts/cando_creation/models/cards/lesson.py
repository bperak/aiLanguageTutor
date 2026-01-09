# Lesson container models
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, ConfigDict

from ..meta import GraphBindings, LessonMeta, UIPrefs
from .content import (
    DialogueCard,
    GrammarPatternsCard,
    ObjectiveCard,
    ReadingCard,
    WordsCard,
)
from .comprehension import (
    AIComprehensionTutorCard,
    ComprehensionExercisesCard,
)
from .exercises import (
    CultureCard,
    DrillsCard,
    ExercisesCard,
    FormulaicExpressionsCard,
    GuidedDialogueCard,
)
from .interaction import (
    AIScenarioManagerCard,
    InteractionActivitiesCard,
    InteractiveDialogueCard,
)
from .production import (
    AIProductionEvaluatorCard,
    ProductionExercisesCard,
)


class CardsContainer(BaseModel):
    model_config = ConfigDict(extra="forbid")
    # Content stage cards
    objective: ObjectiveCard
    words: WordsCard
    grammar_patterns: GrammarPatternsCard
    formulaic_expressions: Optional[FormulaicExpressionsCard] = None
    lesson_dialogue: DialogueCard
    cultural_explanation: CultureCard
    # Comprehension stage cards
    reading_comprehension: Optional[ReadingCard] = (
        None  # Generated in comprehension stage
    )
    comprehension_exercises: Optional[ComprehensionExercisesCard] = None
    ai_comprehension_tutor: Optional[AIComprehensionTutorCard] = None
    # Production stage cards
    guided_dialogue: Optional[GuidedDialogueCard] = (
        None  # Generated in production stage
    )
    production_exercises: Optional[ProductionExercisesCard] = None
    ai_production_evaluator: Optional[AIProductionEvaluatorCard] = None
    # Interaction stage cards
    interactive_dialogue: Optional[InteractiveDialogueCard] = None
    interaction_activities: Optional[InteractionActivitiesCard] = None
    ai_scenario_manager: Optional[AIScenarioManagerCard] = None
    # Legacy cards (kept for backward compatibility)
    exercises: Optional[ExercisesCard] = (
        None  # Legacy - use comprehension_exercises or production_exercises
    )
    drills_ai: Optional[DrillsCard] = None


class Lesson(BaseModel):
    model_config = ConfigDict(extra="forbid")
    meta: LessonMeta
    graph_bindings: GraphBindings = Field(default_factory=GraphBindings)
    ui_prefs: UIPrefs = Field(default_factory=UIPrefs)
    cards: CardsContainer


class LessonRoot(BaseModel):
    model_config = ConfigDict(extra="forbid")
    lesson: Lesson

