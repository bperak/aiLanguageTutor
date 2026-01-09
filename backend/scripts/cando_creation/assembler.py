# Lesson assembler
from __future__ import annotations

from typing import Any, Dict, Optional

from .models.meta import CanDoMeta, GraphBindings, LessonMeta, LookupSpec, UIPrefs
from .models.plan import DomainPlan
from .models.cards.content import DialogueCard, GrammarPatternsCard, ObjectiveCard, ReadingCard, WordsCard
from .models.cards.comprehension import AIComprehensionTutorCard, ComprehensionExercisesCard
from .models.cards.production import AIProductionEvaluatorCard, ProductionExercisesCard
from .models.cards.interaction import AIScenarioManagerCard, InteractionActivitiesCard, InteractiveDialogueCard
from .models.cards.exercises import CultureCard, DrillsCard, ExercisesCard, FormulaicExpressionsCard, GuidedDialogueCard
from .models.cards.lesson import CardsContainer, Lesson, LessonRoot

def assemble_lesson(

    metalanguage: str,

    cando: Dict[str, Any],

    plan: DomainPlan,

    obj: ObjectiveCard,

    words: WordsCard,

    grammar: GrammarPatternsCard,

    dialog: DialogueCard,

    reading: Optional[ReadingCard] = None,  # Generated in comprehension stage

    guided: Optional[GuidedDialogueCard] = None,  # Generated in production stage

    exercises: Optional[ExercisesCard] = None,

    culture: CultureCard = None,

    drills: Optional[DrillsCard] = None,

    # New stage-organized cards

    formulaic_expressions: Optional[FormulaicExpressionsCard] = None,

    comprehension_exercises: Optional[ComprehensionExercisesCard] = None,

    ai_comprehension_tutor: Optional[AIComprehensionTutorCard] = None,

    production_exercises: Optional[ProductionExercisesCard] = None,

    ai_production_evaluator: Optional[AIProductionEvaluatorCard] = None,

    interactive_dialogue: Optional[InteractiveDialogueCard] = None,

    interaction_activities: Optional[InteractionActivitiesCard] = None,

    ai_scenario_manager: Optional[AIScenarioManagerCard] = None,

    lesson_id: Optional[str] = None,

    graph_words: Optional[LookupSpec] = None,

    graph_patterns: Optional[LookupSpec] = None,

) -> LessonRoot:

    """

    Build a LessonRoot from components. Graph bindings are relation-agnostic.

    Supports both legacy cards and new stage-organized cards.

    """

    lesson_id = lesson_id or f"canDo_{cando['uid']}_v1"

    meta = LessonMeta(

        lesson_id=lesson_id,

        metalanguage=metalanguage,

        can_do=CanDoMeta(

            uid=cando["uid"],

            level=cando["level"],

            primaryTopic_ja=cando["primaryTopic"],

            primaryTopic_en=cando["primaryTopicEn"],

            skillDomain_ja=cando["skillDomain"],

            type_ja=cando["type"],

            description={"en": cando["descriptionEn"], "ja": cando["descriptionJa"]},

            source=cando["source"],

            titleEn=cando.get("titleEn") or None,

            titleJa=cando.get("titleJa") or None,

        ),

    )

    gb = GraphBindings(

        words=graph_words or LookupSpec(),

        grammar_patterns=graph_patterns or LookupSpec(),

    )

    cards = CardsContainer(

        objective=obj,

        words=words,

        grammar_patterns=grammar,

        formulaic_expressions=formulaic_expressions,

        lesson_dialogue=dialog,

        cultural_explanation=culture,

        reading_comprehension=reading,

        comprehension_exercises=comprehension_exercises,

        ai_comprehension_tutor=ai_comprehension_tutor,

        guided_dialogue=guided,

        production_exercises=production_exercises,

        ai_production_evaluator=ai_production_evaluator,

        interactive_dialogue=interactive_dialogue,

        interaction_activities=interaction_activities,

        ai_scenario_manager=ai_scenario_manager,

        # Legacy cards (for backward compatibility)

        exercises=exercises,

        drills_ai=drills,

    )

    root = LessonRoot(

        lesson=Lesson(meta=meta, graph_bindings=gb, ui_prefs=UIPrefs(), cards=cards)

    )

    return root

