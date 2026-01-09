# Stage generator functions
from __future__ import annotations

import asyncio
from typing import Any, Callable, Dict, Optional

from ..models.plan import DomainPlan
from ..models.cards.content import ReadingCard
from .utils import LLMFn
from .cards import (
    gen_objective_card,
    gen_words_card,
    gen_grammar_card,
    gen_formulaic_expressions_card,
    gen_dialogue_card,
    gen_culture_card,
    gen_comprehension_exercises_card,
    gen_ai_comprehension_tutor_card,
    gen_guided_dialogue_card,
    gen_production_exercises_card,
    gen_ai_production_evaluator_card,
    gen_interactive_dialogue_card,
    gen_interaction_activities_card,
    gen_ai_scenario_manager_card,
)

async def gen_content_stage(

    llm_call_main: LLMFn,

    llm_call_fast: LLMFn,

    metalanguage: str,

    cando_input: Dict[str, Any],

    plan: DomainPlan,

    max_repair: int = 2,

    kit_context: str = "",

    kit_requirements: str = "",

    profile_context: str = "",

    progress_callback: Optional[Callable[[str, int], None]] = None,

) -> Dict[str, Any]:

    """

    Generate Content stage cards: Objective, Vocabulary, Grammar, Formulaic Expressions, Dialogue, Culture.

    These can be generated in parallel (except objective which depends on plan).

    """

    # Objective depends on plan, so generate it first

    if progress_callback:

        progress_callback("Objective", 10)

    obj = await asyncio.to_thread(

        gen_objective_card,

        llm_call_main,

        metalanguage,

        {

            "uid": cando_input["uid"],

            "level": cando_input["level"],

            "primaryTopic_ja": cando_input["primaryTopic"],

            "primaryTopic_en": cando_input["primaryTopicEn"],

            "skillDomain_ja": cando_input["skillDomain"],

            "type_ja": cando_input["type"],

            "description": {

                "en": cando_input["descriptionEn"],

                "ja": cando_input["descriptionJa"],

            },

            "source": cando_input["source"],

        },

        plan,

        kit_context=kit_context,

        kit_requirements=kit_requirements,

        profile_context=profile_context,

    )

    if progress_callback:

        progress_callback("Objective", 100)



    # Generate remaining content cards in parallel

    if progress_callback:

        progress_callback("Vocabulary", 0)

    words_task = asyncio.to_thread(

        gen_words_card,

        llm_call_fast,

        metalanguage,

        plan,

        max_repair=max_repair,

        kit_context=kit_context,

        kit_requirements=kit_requirements,

        profile_context=profile_context,

    )

    if progress_callback:

        progress_callback("Grammar", 0)

    grammar_task = asyncio.to_thread(

        gen_grammar_card,

        llm_call_fast,

        metalanguage,

        plan,

        max_repair=max_repair,

        kit_context=kit_context,

        kit_requirements=kit_requirements,

        profile_context=profile_context,

    )

    if progress_callback:

        progress_callback("Formulaic Expressions", 0)

    formulaic_task = asyncio.to_thread(

        gen_formulaic_expressions_card,

        llm_call_fast,

        metalanguage,

        plan,

        max_repair=max_repair,

        kit_context=kit_context,

        kit_requirements=kit_requirements,

        profile_context=profile_context,

    )

    if progress_callback:

        progress_callback("Dialogue", 0)

    dialogue_task = asyncio.to_thread(

        gen_dialogue_card,

        llm_call_main,

        metalanguage,

        plan,

        max_repair=max_repair,

        kit_context=kit_context,

        kit_requirements=kit_requirements,

        profile_context=profile_context,

    )

    if progress_callback:

        progress_callback("Culture", 0)

    culture_task = asyncio.to_thread(

        gen_culture_card,

        llm_call_fast,

        metalanguage,

        plan,

        max_repair=max_repair,

        kit_context=kit_context,

        kit_requirements=kit_requirements,

        profile_context=profile_context,

    )



    words, grammar, formulaic, dialogue, culture = await asyncio.gather(

        words_task, grammar_task, formulaic_task, dialogue_task, culture_task

    )

    

    # Mark all parallel cards as complete

    if progress_callback:

        for card_name in ["Vocabulary", "Grammar", "Formulaic Expressions", "Dialogue", "Culture"]:

            progress_callback(card_name, 100)



    return {

        "objective": obj,

        "words": words,

        "grammar_patterns": grammar,

        "formulaic_expressions": formulaic,

        "lesson_dialogue": dialogue,

        "cultural_explanation": culture,

    }





async def gen_comprehension_stage(

    llm_call_main: LLMFn,

    llm_call_fast: LLMFn,

    metalanguage: str,

    plan: DomainPlan,

    content_cards: Dict[str, Any],

    reading: Optional[ReadingCard] = None,

    max_repair: int = 2,

    kit_context: str = "",

    kit_requirements: str = "",

    profile_context: str = "",

) -> Dict[str, Any]:

    """

    Generate Comprehension stage cards: Reading (if not provided), Comprehension Exercises, AI Comprehension Tutor.

    These can be generated in parallel after Content stage.

    """

    import asyncio



    # If reading not provided, generate it (should be done before this stage typically)

    if reading is None:

        # Reading needs dialogue, so it should be generated separately

        raise ValueError("Reading card must be generated before comprehension stage")



    # Generate comprehension exercises and AI tutor in parallel

    exercises_task = asyncio.to_thread(

        gen_comprehension_exercises_card,

        llm_call_fast,

        metalanguage,

        plan,

        reading=reading,

        content_cards=content_cards,

        max_repair=max_repair,

        kit_context=kit_context,

        kit_requirements=kit_requirements,

        profile_context=profile_context,

    )

    tutor_task = asyncio.to_thread(

        gen_ai_comprehension_tutor_card,

        llm_call_fast,

        metalanguage,

        plan,

        reading=reading,

        max_repair=max_repair,

        kit_context=kit_context,

        kit_requirements=kit_requirements,

        profile_context=profile_context,

    )



    exercises, tutor = await asyncio.gather(exercises_task, tutor_task)



    return {

        "reading_comprehension": reading,

        "comprehension_exercises": exercises,

        "ai_comprehension_tutor": tutor,

    }





async def gen_production_stage(

    llm_call_main: LLMFn,

    llm_call_fast: LLMFn,

    metalanguage: str,

    plan: DomainPlan,

    content_cards: Dict[str, Any],

    comprehension_cards: Optional[Dict[str, Any]] = None,

    max_repair: int = 2,

    kit_context: str = "",

    kit_requirements: str = "",

    profile_context: str = "",

) -> Dict[str, Any]:

    """

    Generate Production stage cards: Guided Dialogue, Production Exercises, AI Production Evaluator.

    These can be generated in parallel after Comprehension stage.

    """

    import asyncio



    # Generate production cards in parallel

    guided_task = asyncio.to_thread(

        gen_guided_dialogue_card,

        llm_call_fast,

        metalanguage,

        plan,

        max_repair=max_repair,

    )

    exercises_task = asyncio.to_thread(

        gen_production_exercises_card,

        llm_call_fast,

        metalanguage,

        plan,

        content_cards=content_cards,

        comprehension_cards=comprehension_cards,

        max_repair=max_repair,

        kit_context=kit_context,

        kit_requirements=kit_requirements,

        profile_context=profile_context,

    )

    evaluator_task = asyncio.to_thread(

        gen_ai_production_evaluator_card,

        llm_call_fast,

        metalanguage,

        plan,

        content_cards=content_cards,

        max_repair=max_repair,

        kit_context=kit_context,

        kit_requirements=kit_requirements,

        profile_context=profile_context,

    )



    guided, exercises, evaluator = await asyncio.gather(

        guided_task, exercises_task, evaluator_task

    )



    return {

        "guided_dialogue": guided,

        "production_exercises": exercises,

        "ai_production_evaluator": evaluator,

    }





async def gen_interaction_stage(

    llm_call_main: LLMFn,

    llm_call_fast: LLMFn,

    metalanguage: str,

    plan: DomainPlan,

    content_cards: Dict[str, Any],

    comprehension_cards: Optional[Dict[str, Any]] = None,

    production_cards: Optional[Dict[str, Any]] = None,

    max_repair: int = 2,

    kit_context: str = "",

    kit_requirements: str = "",

    profile_context: str = "",

) -> Dict[str, Any]:

    """

    Generate Interaction stage cards: Interactive Dialogue, Interaction Activities, AI Scenario Manager.

    These can be generated in parallel after Production stage.

    """

    import asyncio



    # Generate interaction cards in parallel

    dialogue_task = asyncio.to_thread(

        gen_interactive_dialogue_card,

        llm_call_fast,

        metalanguage,

        plan,

        content_cards=content_cards,

        comprehension_cards=comprehension_cards,

        production_cards=production_cards,

        max_repair=max_repair,

        kit_context=kit_context,

        kit_requirements=kit_requirements,

        profile_context=profile_context,

    )

    activities_task = asyncio.to_thread(

        gen_interaction_activities_card,

        llm_call_fast,

        metalanguage,

        plan,

        max_repair=max_repair,

        kit_context=kit_context,

        kit_requirements=kit_requirements,

        profile_context=profile_context,

    )

    scenario_task = asyncio.to_thread(

        gen_ai_scenario_manager_card,

        llm_call_fast,

        metalanguage,

        plan,

        max_repair=max_repair,

        kit_context=kit_context,

        kit_requirements=kit_requirements,

        profile_context=profile_context,

    )



    dialogue, activities, scenario = await asyncio.gather(

        dialogue_task, activities_task, scenario_task

    )



    return {

        "interactive_dialogue": dialogue,

        "interaction_activities": activities,

        "ai_scenario_manager": scenario,

    }





# assemble_lesson is in assembler.py, not here







# Stage generator functions - no main block needed

