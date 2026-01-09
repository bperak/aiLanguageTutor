# Card generator functions
from __future__ import annotations

from typing import Any, Dict, List, Optional, Type, TypeVar

from pydantic import BaseModel

from ..models.base import LLMGenSpec
from ..models.plan import DomainPlan
from ..models.cards.content import (
    DialogueCard,
    GrammarPatternsCard,
    ObjectiveCard,
    ReadingCard,
    WordsCard,
)
from ..models.cards.comprehension import (
    AIComprehensionTutorCard,
    ComprehensionExercisesCard,
)
from ..models.cards.production import (
    AIProductionEvaluatorCard,
    ProductionExercisesCard,
)
from ..models.cards.interaction import (
    AIScenarioManagerCard,
    InteractionActivitiesCard,
    InteractiveDialogueCard,
)
from ..models.cards.exercises import (
    CultureCard,
    DrillsCard,
    ExercisesCard,
    FormulaicExpressionsCard,
    GuidedDialogueCard,
)
from ..prompts.planner import build_planner_prompt
from ..prompts.content import (
    build_objective_prompt,
    build_words_prompt,
    build_grammar_prompt,
    build_words_prompt_from_dialogue,
    build_grammar_prompt_from_dialogue,
    build_dialogue_prompt,
    build_reading_prompt,
    build_guided_dialogue_prompt,
    build_exercises_prompt,
    build_culture_prompt,
    build_drills_prompt,
    build_formulaic_expressions_prompt,
)
from ..prompts.comprehension import (
    build_comprehension_exercises_prompt,
    build_ai_comprehension_tutor_prompt,
)
from ..prompts.production import (
    build_production_exercises_prompt,
    build_ai_production_evaluator_prompt,
)
from ..prompts.interaction import (
    build_interactive_dialogue_prompt,
    build_interaction_activities_prompt,
    build_ai_scenario_manager_prompt,
)
from .utils import LLMFn, validate_or_repair

T = TypeVar("T", bound=BaseModel)


def _generate_card(
    llm_call: LLMFn,
    card_type: Type[T],
    system_prompt: str,
    user_prompt: str,
    max_repair: int = 2,
) -> T:
    """
    Common pattern for all card generators.
    
    Validates/repairs LLM output and sets the gen spec for traceability.
    
    Args:
        llm_call: Function to call the LLM
        card_type: Pydantic model type for the card
        system_prompt: System prompt used for generation
        user_prompt: User prompt used for generation
        max_repair: Maximum number of repair attempts
        
    Returns:
        Validated card instance with gen spec set
    """
    card = validate_or_repair(llm_call, card_type, system_prompt, user_prompt, max_repair=max_repair)
    card.gen = LLMGenSpec(system=system_prompt, instruction=user_prompt, constraints=[], examples=None)
    return card


def gen_domain_plan(

    llm_call: LLMFn,

    cando: Dict[str, Any],

    metalanguage: str,

    max_repair: int = 2,

    kit_context: str = "",

    kit_requirements: str = "",

    profile_context: str = "",

) -> DomainPlan:
    """Generate a DomainPlan from CanDo metadata.

    Args:
        llm_call: Function to call the LLM
        cando: CanDo metadata dictionary
        metalanguage: Target language code
        max_repair: Maximum number of repair attempts
        kit_context: Optional context from pre-lesson kit
        kit_requirements: Optional requirements from pre-lesson kit
        profile_context: Optional user profile context

    Returns:
        Validated DomainPlan instance
    """

    sys, usr = build_planner_prompt(

        metalanguage,

        cando,

        kit_context=kit_context,

        kit_requirements=kit_requirements,

        profile_context=profile_context,

    )

    return validate_or_repair(llm_call, DomainPlan, sys, usr, max_repair=max_repair)





def gen_objective_card(

    llm_call: LLMFn,

    metalanguage: str,

    cando_meta: Dict[str, Any],

    plan: DomainPlan,

    max_repair: int = 2,

    kit_context: str = "",

    kit_requirements: str = "",

    profile_context: str = "",

) -> ObjectiveCard:
    """Generate an ObjectiveCard for the lesson.

    Args:
        llm_call: Function to call the LLM
        metalanguage: Target language code
        cando_meta: CanDo metadata dictionary
        plan: DomainPlan for the lesson
        max_repair: Maximum number of repair attempts
        kit_context: Optional context from pre-lesson kit
        kit_requirements: Optional requirements from pre-lesson kit
        profile_context: Optional user profile context for personalization

    Returns:
        Validated ObjectiveCard instance
    """

    sys, usr = build_objective_prompt(

        metalanguage,

        cando_meta,

        plan,

        kit_context=kit_context,

        kit_requirements=kit_requirements,

        profile_context=profile_context,

    )

    return _generate_card(llm_call, ObjectiveCard, sys, usr, max_repair=max_repair)





def gen_words_card(

    llm_call: LLMFn,

    metalanguage: str,

    plan: DomainPlan,

    max_repair: int = 2,

    kit_context: str = "",

    kit_requirements: str = "",

    profile_context: str = "",

) -> WordsCard:
    """Generate a WordsCard with vocabulary for the lesson.

    Args:
        llm_call: Function to call the LLM
        metalanguage: Target language code
        plan: DomainPlan for the lesson
        max_repair: Maximum number of repair attempts
        kit_context: Optional context from pre-lesson kit
        kit_requirements: Optional requirements from pre-lesson kit
        profile_context: Optional user profile context for personalization

    Returns:
        Validated WordsCard instance
    """

    sys, usr = build_words_prompt(

        metalanguage, plan, kit_context=kit_context, kit_requirements=kit_requirements, profile_context=profile_context

    )

    return _generate_card(llm_call, WordsCard, sys, usr, max_repair=max_repair)





def gen_grammar_card(

    llm_call: LLMFn,

    metalanguage: str,

    plan: DomainPlan,

    max_repair: int = 2,

    kit_context: str = "",

    kit_requirements: str = "",

    profile_context: str = "",

) -> GrammarPatternsCard:
    """Generate a GrammarPatternsCard with grammar patterns for the lesson.

    Args:
        llm_call: Function to call the LLM
        metalanguage: Target language code
        plan: DomainPlan for the lesson
        max_repair: Maximum number of repair attempts
        kit_context: Optional context from pre-lesson kit
        kit_requirements: Optional requirements from pre-lesson kit
        profile_context: Optional user profile context for personalization

    Returns:
        Validated GrammarPatternsCard instance
    """

    sys, usr = build_grammar_prompt(

        metalanguage, plan, kit_context=kit_context, kit_requirements=kit_requirements, profile_context=profile_context

    )

    return _generate_card(llm_call, GrammarPatternsCard, sys, usr, max_repair=max_repair)





def gen_words_card_from_extracted(

    llm_call: LLMFn,

    metalanguage: str,

    plan: DomainPlan,

    dialog: DialogueCard,

    reading: ReadingCard,

    extracted_words: List[Dict[str, Any]],

    max_repair: int = 2,

    kit_context: str = "",

    kit_requirements: str = "",

) -> WordsCard:
    """Generate WordsCard from words extracted from dialogue AND reading.

    Args:
        llm_call: Function to call the LLM
        metalanguage: Target language code
        plan: DomainPlan for the lesson
        dialog: DialogueCard to extract words from
        reading: ReadingCard to extract words from
        extracted_words: List of extracted word dictionaries
        max_repair: Maximum number of repair attempts
        kit_context: Optional context from pre-lesson kit
        kit_requirements: Optional requirements from pre-lesson kit

    Returns:
        Validated WordsCard instance
    """

    sys, usr = build_words_prompt_from_dialogue(

        metalanguage,

        plan,

        dialog,

        reading,

        extracted_words,

        kit_context=kit_context,

        kit_requirements=kit_requirements,

    )

    return _generate_card(llm_call, WordsCard, sys, usr, max_repair=max_repair)





def gen_grammar_card_from_extracted(

    llm_call: LLMFn,

    metalanguage: str,

    plan: DomainPlan,

    dialog: DialogueCard,

    reading: ReadingCard,

    extracted_grammar: List[Dict[str, Any]],

    max_repair: int = 2,

    kit_context: str = "",

    kit_requirements: str = "",

) -> GrammarPatternsCard:
    """Generate GrammarPatternsCard from grammar patterns extracted from dialogue AND reading.

    Args:
        llm_call: Function to call the LLM
        metalanguage: Target language code
        plan: DomainPlan for the lesson
        dialog: DialogueCard to extract grammar from
        reading: ReadingCard to extract grammar from
        extracted_grammar: List of extracted grammar pattern dictionaries
        max_repair: Maximum number of repair attempts
        kit_context: Optional context from pre-lesson kit
        kit_requirements: Optional requirements from pre-lesson kit

    Returns:
        Validated GrammarPatternsCard instance
    """

    sys, usr = build_grammar_prompt_from_dialogue(

        metalanguage,

        plan,

        dialog,

        reading,

        extracted_grammar,

        kit_context=kit_context,

        kit_requirements=kit_requirements,

    )

    return _generate_card(llm_call, GrammarPatternsCard, sys, usr, max_repair=max_repair)





def gen_dialogue_card(

    llm_call: LLMFn,

    metalanguage: str,

    plan: DomainPlan,

    max_repair: int = 2,

    kit_context: str = "",

    kit_requirements: str = "",

    profile_context: str = "",

) -> DialogueCard:
    """Generate a DialogueCard with lesson dialogue.

    Args:
        llm_call: Function to call the LLM
        metalanguage: Target language code
        plan: DomainPlan for the lesson
        max_repair: Maximum number of repair attempts
        kit_context: Optional context from pre-lesson kit
        kit_requirements: Optional requirements from pre-lesson kit
        profile_context: Optional user profile context for personalization

    Returns:
        Validated DialogueCard instance
    """

    sys, usr = build_dialogue_prompt(

        metalanguage, plan, kit_context=kit_context, kit_requirements=kit_requirements, profile_context=profile_context

    )

    return _generate_card(llm_call, DialogueCard, sys, usr, max_repair=max_repair)





def gen_reading_card(

    llm_call: LLMFn,

    metalanguage: str,

    cando: Dict[str, Any],

    plan: DomainPlan,

    dialog: DialogueCard,

    max_repair: int = 2,

    kit_context: str = "",

    kit_requirements: str = "",

    profile_context: str = "",

) -> ReadingCard:
    """Generate ReadingCard focused on CanDo domain elaboration.

    Args:
        llm_call: Function to call the LLM
        metalanguage: Target language code
        cando: CanDo metadata dictionary
        plan: DomainPlan for the lesson
        dialog: DialogueCard for context
        max_repair: Maximum number of repair attempts
        kit_context: Optional context from pre-lesson kit
        kit_requirements: Optional requirements from pre-lesson kit
        profile_context: Optional user profile context for personalization

    Returns:
        Validated ReadingCard instance
    """

    sys, usr = build_reading_prompt(

        metalanguage,

        cando,

        plan,

        dialog,

        kit_context=kit_context,

        kit_requirements=kit_requirements,

        profile_context=profile_context,

    )

    return _generate_card(llm_call, ReadingCard, sys, usr, max_repair=max_repair)





def gen_guided_dialogue_card(

    llm_call: LLMFn, metalanguage: str, plan: DomainPlan, max_repair: int = 2

) -> GuidedDialogueCard:
    """Generate a GuidedDialogueCard with scaffolded dialogue stages.

    Args:
        llm_call: Function to call the LLM
        metalanguage: Target language code
        plan: DomainPlan for the lesson
        max_repair: Maximum number of repair attempts

    Returns:
        Validated GuidedDialogueCard instance
    """

    sys, usr = build_guided_dialogue_prompt(metalanguage, plan)

    return _generate_card(llm_call, GuidedDialogueCard, sys, usr, max_repair=max_repair)





def gen_exercises_card(

    llm_call: LLMFn, metalanguage: str, plan: DomainPlan, max_repair: int = 2

) -> ExercisesCard:
    """Generate an ExercisesCard with exercises for the lesson.

    Args:
        llm_call: Function to call the LLM
        metalanguage: Target language code
        plan: DomainPlan for the lesson
        max_repair: Maximum number of repair attempts

    Returns:
        Validated ExercisesCard instance
    """

    sys, usr = build_exercises_prompt(metalanguage, plan)

    return _generate_card(llm_call, ExercisesCard, sys, usr, max_repair=max_repair)





def gen_culture_card(

    llm_call: LLMFn,

    metalanguage: str,

    plan: DomainPlan,

    max_repair: int = 2,

    kit_context: str = "",

    kit_requirements: str = "",

    profile_context: str = "",

) -> CultureCard:
    """Generate a CultureCard with cultural explanations.

    Args:
        llm_call: Function to call the LLM
        metalanguage: Target language code
        plan: DomainPlan for the lesson
        max_repair: Maximum number of repair attempts
        kit_context: Optional context from pre-lesson kit
        kit_requirements: Optional requirements from pre-lesson kit
        profile_context: Optional user profile context for personalization

    Returns:
        Validated CultureCard instance
    """

    sys, usr = build_culture_prompt(

        metalanguage, plan, kit_context=kit_context, kit_requirements=kit_requirements, profile_context=profile_context

    )

    return _generate_card(llm_call, CultureCard, sys, usr, max_repair=max_repair)





def gen_drills_card(

    llm_call: LLMFn, metalanguage: str, plan: DomainPlan, max_repair: int = 2

) -> DrillsCard:
    """Generate a DrillsCard with pronunciation and substitution drills.

    Args:
        llm_call: Function to call the LLM
        metalanguage: Target language code
        plan: DomainPlan for the lesson
        max_repair: Maximum number of repair attempts

    Returns:
        Validated DrillsCard instance
    """

    sys, usr = build_drills_prompt(metalanguage, plan)

    return _generate_card(llm_call, DrillsCard, sys, usr, max_repair=max_repair)





# ======================================================================================

#                    N E W   C A R D   G E N E R A T I O N   F U N C T I O N S

# ======================================================================================





def gen_formulaic_expressions_card(

    llm_call: LLMFn,

    metalanguage: str,

    plan: DomainPlan,

    max_repair: int = 2,

    kit_context: str = "",

    kit_requirements: str = "",

    profile_context: str = "",

) -> FormulaicExpressionsCard:
    """Generate a FormulaicExpressionsCard with fixed expressions.

    Args:
        llm_call: Function to call the LLM
        metalanguage: Target language code
        plan: DomainPlan for the lesson
        max_repair: Maximum number of repair attempts
        kit_context: Optional context from pre-lesson kit
        kit_requirements: Optional requirements from pre-lesson kit
        profile_context: Optional user profile context for personalization

    Returns:
        Validated FormulaicExpressionsCard instance
    """

    sys, usr = build_formulaic_expressions_prompt(

        metalanguage, plan, kit_context=kit_context, kit_requirements=kit_requirements, profile_context=profile_context

    )

    return _generate_card(llm_call, FormulaicExpressionsCard, sys, usr, max_repair=max_repair)





def gen_comprehension_exercises_card(

    llm_call: LLMFn,

    metalanguage: str,

    plan: DomainPlan,

    reading: Optional[ReadingCard] = None,

    content_cards: Optional[Dict[str, Any]] = None,

    max_repair: int = 2,

    kit_context: str = "",

    kit_requirements: str = "",

    profile_context: str = "",

) -> ComprehensionExercisesCard:
    """Generate a ComprehensionExercisesCard with comprehension exercises.

    Args:
        llm_call: Function to call the LLM
        metalanguage: Target language code
        plan: DomainPlan for the lesson
        reading: Optional ReadingCard for context
        content_cards: Optional content stage cards for context
        max_repair: Maximum number of repair attempts
        kit_context: Optional context from pre-lesson kit
        kit_requirements: Optional requirements from pre-lesson kit
        profile_context: Optional user profile context for personalization

    Returns:
        Validated ComprehensionExercisesCard instance
    """

    sys, usr = build_comprehension_exercises_prompt(

        metalanguage,

        plan,

        reading=reading,

        content_cards=content_cards,

        kit_context=kit_context,

        kit_requirements=kit_requirements,

        profile_context=profile_context,

    )

    return _generate_card(llm_call, ComprehensionExercisesCard, sys, usr, max_repair=max_repair)





def gen_ai_comprehension_tutor_card(

    llm_call: LLMFn,

    metalanguage: str,

    plan: DomainPlan,

    reading: Optional[ReadingCard] = None,

    max_repair: int = 2,

    kit_context: str = "",

    kit_requirements: str = "",

    profile_context: str = "",

) -> AIComprehensionTutorCard:
    """Generate an AIComprehensionTutorCard with AI-guided comprehension stages.

    Args:
        llm_call: Function to call the LLM
        metalanguage: Target language code
        plan: DomainPlan for the lesson
        reading: Optional ReadingCard for context
        max_repair: Maximum number of repair attempts
        kit_context: Optional context from pre-lesson kit
        kit_requirements: Optional requirements from pre-lesson kit
        profile_context: Optional user profile context for personalization

    Returns:
        Validated AIComprehensionTutorCard instance
    """

    sys, usr = build_ai_comprehension_tutor_prompt(

        metalanguage,

        plan,

        reading=reading,

        kit_context=kit_context,

        kit_requirements=kit_requirements,

        profile_context=profile_context,

    )

    return _generate_card(llm_call, AIComprehensionTutorCard, sys, usr, max_repair=max_repair)





def gen_production_exercises_card(

    llm_call: LLMFn,

    metalanguage: str,

    plan: DomainPlan,

    content_cards: Optional[Dict[str, Any]] = None,

    comprehension_cards: Optional[Dict[str, Any]] = None,

    max_repair: int = 2,

    kit_context: str = "",

    kit_requirements: str = "",

    profile_context: str = "",

) -> ProductionExercisesCard:
    """Generate a ProductionExercisesCard with production exercises.

    Args:
        llm_call: Function to call the LLM
        metalanguage: Target language code
        plan: DomainPlan for the lesson
        content_cards: Optional content stage cards for context
        comprehension_cards: Optional comprehension stage cards for context
        max_repair: Maximum number of repair attempts
        kit_context: Optional context from pre-lesson kit
        kit_requirements: Optional requirements from pre-lesson kit
        profile_context: Optional user profile context for personalization

    Returns:
        Validated ProductionExercisesCard instance
    """

    sys, usr = build_production_exercises_prompt(

        metalanguage,

        plan,

        content_cards=content_cards,

        comprehension_cards=comprehension_cards,

        kit_context=kit_context,

        kit_requirements=kit_requirements,

        profile_context=profile_context,

    )

    return _generate_card(llm_call, ProductionExercisesCard, sys, usr, max_repair=max_repair)





def gen_ai_production_evaluator_card(

    llm_call: LLMFn,

    metalanguage: str,

    plan: DomainPlan,

    content_cards: Optional[Dict[str, Any]] = None,

    max_repair: int = 2,

    kit_context: str = "",

    kit_requirements: str = "",

    profile_context: str = "",

) -> AIProductionEvaluatorCard:
    """Generate an AIProductionEvaluatorCard with AI-guided production evaluation.

    Args:
        llm_call: Function to call the LLM
        metalanguage: Target language code
        plan: DomainPlan for the lesson
        content_cards: Optional content stage cards for context
        max_repair: Maximum number of repair attempts
        kit_context: Optional context from pre-lesson kit
        kit_requirements: Optional requirements from pre-lesson kit
        profile_context: Optional user profile context for personalization

    Returns:
        Validated AIProductionEvaluatorCard instance
    """

    sys, usr = build_ai_production_evaluator_prompt(

        metalanguage,

        plan,

        content_cards=content_cards,

        kit_context=kit_context,

        kit_requirements=kit_requirements,

        profile_context=profile_context,

    )

    return _generate_card(llm_call, AIProductionEvaluatorCard, sys, usr, max_repair=max_repair)





def gen_interactive_dialogue_card(

    llm_call: LLMFn,

    metalanguage: str,

    plan: DomainPlan,

    content_cards: Optional[Dict[str, Any]] = None,

    comprehension_cards: Optional[Dict[str, Any]] = None,

    production_cards: Optional[Dict[str, Any]] = None,

    max_repair: int = 2,

    kit_context: str = "",

    kit_requirements: str = "",

    profile_context: str = "",

) -> InteractiveDialogueCard:
    """Generate an InteractiveDialogueCard for real conversation practice.

    Args:
        llm_call: Function to call the LLM
        metalanguage: Target language code
        plan: DomainPlan for the lesson
        content_cards: Optional content stage cards for context
        comprehension_cards: Optional comprehension stage cards for context
        production_cards: Optional production stage cards for context
        max_repair: Maximum number of repair attempts
        kit_context: Optional context from pre-lesson kit
        kit_requirements: Optional requirements from pre-lesson kit
        profile_context: Optional user profile context for personalization

    Returns:
        Validated InteractiveDialogueCard instance
    """

    sys, usr = build_interactive_dialogue_prompt(

        metalanguage,

        plan,

        content_cards=content_cards,

        comprehension_cards=comprehension_cards,

        production_cards=production_cards,

        kit_context=kit_context,

        kit_requirements=kit_requirements,

        profile_context=profile_context,

    )

    return _generate_card(llm_call, InteractiveDialogueCard, sys, usr, max_repair=max_repair)





def gen_interaction_activities_card(

    llm_call: LLMFn,

    metalanguage: str,

    plan: DomainPlan,

    max_repair: int = 2,

    kit_context: str = "",

    kit_requirements: str = "",

    profile_context: str = "",

) -> InteractionActivitiesCard:
    """Generate an InteractionActivitiesCard with diverse interaction activities.

    Args:
        llm_call: Function to call the LLM
        metalanguage: Target language code
        plan: DomainPlan for the lesson
        max_repair: Maximum number of repair attempts
        kit_context: Optional context from pre-lesson kit
        kit_requirements: Optional requirements from pre-lesson kit
        profile_context: Optional user profile context for personalization

    Returns:
        Validated InteractionActivitiesCard instance
    """

    sys, usr = build_interaction_activities_prompt(

        metalanguage, plan, kit_context=kit_context, kit_requirements=kit_requirements, profile_context=profile_context

    )

    return _generate_card(llm_call, InteractionActivitiesCard, sys, usr, max_repair=max_repair)





def gen_ai_scenario_manager_card(

    llm_call: LLMFn,

    metalanguage: str,

    plan: DomainPlan,

    max_repair: int = 2,

    kit_context: str = "",

    kit_requirements: str = "",

    profile_context: str = "",

) -> AIScenarioManagerCard:
    """Generate an AIScenarioManagerCard with AI-managed role-play scenarios.

    Args:
        llm_call: Function to call the LLM
        metalanguage: Target language code
        plan: DomainPlan for the lesson
        max_repair: Maximum number of repair attempts
        kit_context: Optional context from pre-lesson kit
        kit_requirements: Optional requirements from pre-lesson kit
        profile_context: Optional user profile context for personalization

    Returns:
        Validated AIScenarioManagerCard instance
    """

    sys, usr = build_ai_scenario_manager_prompt(

        metalanguage, plan, kit_context=kit_context, kit_requirements=kit_requirements, profile_context=profile_context

    )

    return _generate_card(llm_call, AIScenarioManagerCard, sys, usr, max_repair=max_repair)





# ======================================================================================

#                    S T A G E - S P E C I F I C   G E N E R A T I O N

# ======================================================================================





