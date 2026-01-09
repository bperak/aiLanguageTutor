# Interaction stage prompt builders
from __future__ import annotations

import json
from typing import Any, Dict, Optional, Tuple

from ..models.plan import DomainPlan
from ..models.cards.interaction import InteractionActivityItem
from .constants import STRICT_SYSTEM

# Import _literal_choices lazily to avoid circular imports
def _get_literal_choices(model, field_name):
    """Lazy import to avoid circular dependency."""
    from ..generators.utils import _literal_choices
    return _literal_choices(model, field_name)


def build_interactive_dialogue_prompt(
    metalanguage: str,
    plan: DomainPlan,
    content_cards: Optional[Dict[str, Any]] = None,
    comprehension_cards: Optional[Dict[str, Any]] = None,
    production_cards: Optional[Dict[str, Any]] = None,
    kit_context: str = "",
    kit_requirements: str = "",
    profile_context: str = "",
) -> Tuple[str, str]:
    """Build prompt for InteractiveDialogueCard generation."""
    sys = """You are a Japanese language curriculum expert. Generate an interactive dialogue system for real conversation practice."""
    user = f"""TARGET_MODEL: InteractiveDialogueCard

INPUTS:
- metalanguage: {metalanguage}
- communicative_function: {plan.communicative_function_en}
- scenarios: {[s.name for s in plan.scenarios]}
- success_criteria: {json.dumps(plan.evaluation.success_criteria, ensure_ascii=False)}
{kit_context}
{kit_requirements}
{profile_context}

TASK: Create an InteractiveDialogueCard for conversation practice.

REQUIRED FIELDS:
- type: "InteractiveDialogueCard"
- title: {{"en": "...", "ja": "..."}}
- scenarios: Array of conversation scenarios
- stages: Array of GuidedStage objects

CONSTRAINTS:
- AI acts as conversation partner with structured feedback
- Feedback format: CONVERSATIONAL_RESPONSE, TRANSLITERATION, TRANSLATION, TEACHING_DIRECTION
{kit_requirements}

PERSONALIZATION:
- Use interaction_preferences from profile to guide dialogue style (e.g., structured vs free conversation, role-play preferences).
- Use register_preferences from profile to select appropriate register (plain/polite/neutral) for dialogue scenarios.
- Use scenario_details from profile to create specific, relevant dialogue scenarios aligned with user's usage context.
- Use cultural_background from profile to ensure culturally appropriate dialogue content.
- Align scenarios with user's learning goals and usage context.

OUTPUT: InteractiveDialogueCard JSON only."""
    return sys, user


def build_interaction_activities_prompt(
    metalanguage: str,
    plan: DomainPlan,
    kit_context: str = "",
    kit_requirements: str = "",
    profile_context: str = "",
) -> Tuple[str, str]:
    """Build prompt for InteractionActivitiesCard generation."""
    activity_types = ", ".join(
        _get_literal_choices(InteractionActivityItem, "activity_type")
    )
    sys = """You are a Japanese language curriculum expert. Generate diverse interaction activities for real-world scenario practice."""
    user = f"""TARGET_MODEL: InteractionActivitiesCard

INPUTS:
- metalanguage: {metalanguage}
- plan.communicative_function_en: {plan.communicative_function_en}
- plan.scenarios: {[s.name for s in plan.scenarios]}
- plan.level: {plan.level}
{kit_context}
{kit_requirements}
{profile_context}

TASK: Create an InteractionActivitiesCard with 8-12 diverse interaction activities.

REQUIRED FIELDS:
- type: "InteractionActivitiesCard"
- title: {{"en": "...", "ja": "..."}}
- items: Array of activity objects

TYPE & SCHEMA GUARDRAILS:
- activity_type choices (use exactly these literals): {activity_types}
- Use field name activity_type (not "type")
- Only include keys that match the chosen activity_type; omit unrelated fields

TYPE FIELDS:
- All activities: id (string), title ({{"en": "...", "ja": "..."}}), instructions ({{"en": "...", "ja": "..."}})
- conversation_scenario / role_play / negotiation / collaborative_task / simulation / problem_solving / opinion_exchange / decision_making: scenario (dict with context), roles (List[str]), goals (List[str]) as needed
- information_gap / free_conversation: clear goals and context; roles optional

CONSTRAINTS:
- Keep scenarios practical, leveled to {plan.level}, and tied to {plan.communicative_function_en}
{kit_requirements}

PERSONALIZATION:
- Use interaction_preferences from profile to guide activity types (e.g., structured vs free conversation, role-play preferences).
- Use register_preferences from profile to select appropriate register (plain/polite/neutral) for activity scenarios.
- Use scenario_details from profile to create specific, relevant activity scenarios aligned with user's usage context.
- Use cultural_background from profile to ensure culturally appropriate activity content.
- Align activities with user's learning goals and usage context.

OUTPUT: InteractionActivitiesCard JSON only."""
    return sys, user


def build_ai_scenario_manager_prompt(
    metalanguage: str,
    plan: DomainPlan,
    kit_context: str = "",
    kit_requirements: str = "",
    profile_context: str = "",
) -> Tuple[str, str]:
    """Build prompt for AIScenarioManagerCard generation."""
    sys = """You are a Japanese language curriculum expert. Generate an AI scenario manager system for role-play scenarios and conversation flow management."""
    user = f"""TARGET_MODEL: AIScenarioManagerCard

INPUTS:
- metalanguage: {metalanguage}
- plan.communicative_function_en: {plan.communicative_function_en}
- plan.scenarios: {[s.name for s in plan.scenarios]}
- plan.evaluation.success_criteria: {plan.evaluation.success_criteria}
{kit_context}
{kit_requirements}
{profile_context}

TASK: Create an AIScenarioManagerCard with 3-5 stages for role-play scenarios.

REQUIRED FIELDS:
- type: "AIScenarioManagerCard"
- title: {{"en": "...", "ja": "..."}}
- stages: Array of AIScenarioStage objects

EACH STAGE:
- stage_id: unique identifier
- scenario_type: type of scenario (restaurant, shop, travel, etc.)
- goal_en: interaction goal
- context: {{"en": "...", "ja": "..."}}
- roles: Array of role definitions ({{"name": "...", "description": "..."}})
- conversation_flow: Expected conversation flow structure
- evaluation_criteria: How to evaluate interaction quality
- cultural_notes: Optional cultural context (optional)

CONSTRAINTS:
- AI manages scenario progression and provides feedback
{kit_requirements}

PERSONALIZATION:
- Use interaction_preferences from profile to guide scenario style and structure.
- Use register_preferences from profile to select appropriate register (plain/polite/neutral) for scenarios.
- Use scenario_details from profile to create specific, relevant scenarios aligned with user's usage context.
- Use cultural_background from profile to ensure culturally appropriate scenario content and cultural notes.
- Align scenarios with user's learning goals and usage context.

OUTPUT: AIScenarioManagerCard JSON only."""
    return sys, user

