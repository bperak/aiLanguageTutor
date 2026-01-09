# Production stage prompt builders
from __future__ import annotations

import json
from typing import Any, Dict, Optional, Tuple

from ..models.plan import DomainPlan
from ..models.cards.production import ProductionExerciseItem, ProductionExercisesCard, AIProductionEvaluatorCard
from .constants import STRICT_SYSTEM

# Import _literal_choices and model_schema lazily to avoid circular imports
def _get_literal_choices(model, field_name):
    """Lazy import to avoid circular dependency."""
    from ..generators.utils import _literal_choices
    return _literal_choices(model, field_name)

def _get_model_schema(model):
    """Lazy import to avoid circular dependency."""
    from ..generators.utils import model_schema
    return model_schema(model)


def build_production_exercises_prompt(
    metalanguage: str,
    plan: DomainPlan,
    content_cards: Optional[Dict[str, Any]] = None,
    comprehension_cards: Optional[Dict[str, Any]] = None,
    kit_context: str = "",
    kit_requirements: str = "",
    profile_context: str = "",
) -> Tuple[str, str]:
    """Build prompt for ProductionExercisesCard generation."""
    exercise_types = ", ".join(
        _get_literal_choices(ProductionExerciseItem, "exercise_type")
    )
    # Truncate references to reduce token count and speed up LLM response
    vocab_preview = ""
    if content_cards:
        words = content_cards.get("words")
        if words:
            if hasattr(words, "items") and words.items:
                vocab_preview = (
                    words.items[0].jp.std if hasattr(words.items[0], "jp") else ""
                )
            elif isinstance(words, dict):
                items = words.get("items", [])
                if items:
                    vocab_preview = items[0].get("jp", {}).get("std", "")
        if vocab_preview:
            vocab_preview = f"Vocab: {vocab_preview[:30]}..."
        
        grammar = content_cards.get("grammar_patterns")
        grammar_preview = ""
        if grammar:
            if hasattr(grammar, "patterns") and grammar.patterns:
                grammar_preview = grammar.patterns[0].id if hasattr(grammar.patterns[0], "id") else ""
            elif isinstance(grammar, dict):
                patterns = grammar.get("patterns", [])
                if patterns:
                    grammar_preview = patterns[0].get("id", "")
        if grammar_preview:
            vocab_preview = f"{vocab_preview} Grammar: {grammar_preview[:20]}..." if vocab_preview else f"Grammar: {grammar_preview[:20]}..."

    sys = """You are a Japanese language curriculum expert. Generate production exercises. Return valid JSON only."""
    schema_str = _get_model_schema(ProductionExercisesCard)
    user = f"""TARGET: ProductionExercisesCard

Create 6-8 exercises for: {plan.communicative_function_en} (level {plan.level})
{vocab_preview}
{kit_context}
{profile_context}

JSON SCHEMA (must match exactly):
{schema_str}

CRITICAL RULES:
1. Every item MUST have: id (string like "ex_1"), instructions ({{"en","ja"}})
2. JPText = {{"std": "...", "furigana": "...", "romaji": "...", "translation": {{"en": "..."}}}}
3. exercise_type: {exercise_types}
4. prompt/template/source_sentence: use JPText (not plain strings)
5. sentence_reordering: scrambled_words = string array
6. translation: target_language = string
7. form_focused: grammar_pattern_id = string

PERSONALIZATION:
- If preferred_exercise_types.production are provided in profile, prioritize those exercise types (e.g., translation, sentence building, writing).
- Use grammar_focus_areas from profile to emphasize relevant grammar patterns in exercises.
- Consider user's error_tolerance when designing exercise difficulty and feedback.
- Align exercises with user's learning goals and usage context.

OUTPUT: Valid JSON matching the schema above."""
    return sys, user


def build_ai_production_evaluator_prompt(
    metalanguage: str,
    plan: DomainPlan,
    content_cards: Optional[Dict[str, Any]] = None,
    kit_context: str = "",
    kit_requirements: str = "",
    profile_context: str = "",
) -> Tuple[str, str]:
    """Build prompt for AIProductionEvaluatorCard generation."""
    content_ref = ""
    if content_cards:
        # Handle GrammarPatternsCard - can be Pydantic model or dict
        grammar = content_cards.get("grammar_patterns")
        grammar_list = []
        if grammar:
            if hasattr(grammar, "patterns"):
                # Pydantic model
                patterns = grammar.patterns[:5] if grammar.patterns else []
                grammar_list = [p.id for p in patterns if hasattr(p, "id")]
            elif isinstance(grammar, dict):
                # Dict
                patterns = grammar.get("patterns", [])[:5]
                grammar_list = [
                    p.get("id", "") for p in patterns if isinstance(p, dict)
                ]

        content_ref = f"""
Content Stage Reference:
- Grammar patterns: {', '.join(grammar_list) if grammar_list else 'N/A'}
"""

    sys = """You are a Japanese language curriculum expert. Generate an AI production evaluator system with stages, rubric evaluation, and adaptive difficulty (reuses GuidedDialogue concepts)."""
    schema_str = _get_model_schema(AIProductionEvaluatorCard)
    user = f"""TARGET_MODEL: AIProductionEvaluatorCard

INPUTS:
- metalanguage: {metalanguage}
- plan.communicative_function_en: {plan.communicative_function_en}
- plan.evaluation.success_criteria: {plan.evaluation.success_criteria}
- plan.grammar_functions: {[gf.id for gf in plan.grammar_functions[:5]]}
{content_ref}
{kit_context}
{kit_requirements}
{profile_context}

JSON SCHEMA (must match exactly):
{schema_str}

CRITICAL RULES - READ CAREFULLY:
1. hints must be an array of objects, each with "en" and "ja" keys:
   CORRECT: [{{"en": "Hint 1", "ja": "ヒント1"}}, {{"en": "Hint 2", "ja": "ヒント2"}}]
   WRONG: {{"en": "Hint", "ja": "ヒント"}} (single object, not array)
   WRONG: ["Hint 1", "Hint 2"] (strings, not objects)

2. title must be {{"en": "...", "ja": "..."}} (dict with en/ja keys, NOT a string)

3. stage_id must be unique string identifier (e.g., "stage_1", "stage_2")

4. goal_en must be a string describing the production goal

5. rubric must be a dict with keys like "pattern_correctness", "fluency", "content_relevance"

EXAMPLE STRUCTURE:
{{
  "type": "AIProductionEvaluatorCard",
  "title": {{"en": "Production Evaluation", "ja": "産出評価"}},
  "stages": [
    {{
      "stage_id": "stage_1",
      "goal_en": "Produce grammatically correct sentences",
      "exercise_type": "sentence_construction",
      "expected_patterns": ["pattern_1", "pattern_2"],
      "rubric": {{"pattern_correctness": "...", "fluency": "...", "content_relevance": "..."}},
      "hints": [{{"en": "Use the grammar pattern", "ja": "文法パターンを使ってください"}}]
    }}
  ]
}}

CONSTRAINTS:
- AI evaluates learner output using rubric
- Feedback format: CONVERSATIONAL_RESPONSE, TRANSLITERATION, TRANSLATION, TEACHING_DIRECTION
- Keep prompts concise and level-appropriate for {plan.level}
{kit_requirements}

PERSONALIZATION:
- Use feedback_preferences from profile to guide feedback style (e.g., encouraging, detailed, concise).
- Use error_tolerance from profile to adjust feedback strictness and error correction approach.
- Use grammar_focus_areas from profile to emphasize relevant grammar patterns in evaluation.
- Consider user's learning style when crafting hints and feedback messages.

OUTPUT: Valid JSON matching the schema above."""
    return sys, user

