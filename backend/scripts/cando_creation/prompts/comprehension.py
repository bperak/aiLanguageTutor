# Comprehension stage prompt builders
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Tuple

from ..models.plan import DomainPlan
from ..models.cards.content import ReadingCard
from ..models.cards.comprehension import ComprehensionExerciseItem, AIComprehensionTutorCard
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


def build_comprehension_exercises_prompt(
    metalanguage: str,
    plan: DomainPlan,
    reading: Optional[ReadingCard] = None,
    content_cards: Optional[Dict[str, Any]] = None,
    kit_context: str = "",
    kit_requirements: str = "",
    profile_context: str = "",
) -> Tuple[str, str]:
    """Build prompt for ComprehensionExercisesCard generation."""
    exercise_types = ", ".join(
        _get_literal_choices(ComprehensionExerciseItem, "exercise_type")
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

    reading_preview = ""
    if reading and reading.reading.content.std:
        reading_preview = reading.reading.content.std[:120] + "..."

    sys = """You are a Japanese language curriculum expert. Generate comprehension exercises. Return ONLY valid JSON data matching the schema. Do NOT include schema definitions ($defs)."""
    # Use a clear example structure instead of full schema to avoid confusion
    user = f"""TARGET: ComprehensionExercisesCard

Create 6-8 exercises for: {plan.communicative_function_en} (level {plan.level})
{vocab_preview}
{reading_preview}
{kit_context}
{profile_context}

REQUIRED JSON STRUCTURE (return DATA, not schema):
{{
  "type": "ComprehensionExercisesCard",
  "title": {{"en": "...", "ja": "..."}},
  "items": [
    {{
      "exercise_type": "reading_qa",
      "id": "ex_1",
      "instructions": {{"en": "...", "ja": "..."}},
      "question": {{"std": "...", "furigana": "...", "romaji": "...", "translation": {{"en": "..."}}}},
      "answer": {{"std": "...", "furigana": "...", "romaji": "...", "translation": {{"en": "..."}}}}
    }}
  ]
}}

CRITICAL RULES - READ CAREFULLY:
1. Every item MUST have: id (string like "ex_1"), instructions ({{"en": "...", "ja": "..."}})

2. JPText structure - question and answer MUST be JPText objects, NOT strings:
   CORRECT: {{"std": "質問", "furigana": "しつもん", "romaji": "shitsumon", "translation": {{"en": "question"}}}}
   WRONG: "質問" (string is invalid)
   WRONG: {{"ja": "質問"}} (missing required JPText fields: std, furigana, romaji, translation)

3. exercise_type: {exercise_types} (use exactly these literal values)

4. For matching exercises:
   - pairs = array of {{"left": JPText, "right_options_en": ["option1", "option2"], "answer_en": "correct_option"}}
   - right_options_en MUST be an array of strings (not a single string)
   - answer_en MUST be a string (required field)
   - left MUST be a complete JPText object

5. For ordering exercises:
   - segments = array of strings
   - correct_order = array of integers
   - NO answer field (ordering doesn't use answer)

6. For reading_qa exercises:
   - question = JPText object (required)
   - answer = JPText object (required)
   - NO top-level "ja"/"en" keys in question/answer - only JPText keys (std, furigana, romaji, translation)

7. title must be {{"en": "...", "ja": "..."}} (dict with en/ja keys, NOT a string)

PERSONALIZATION:
- If preferred_exercise_types.comprehension are provided in profile, prioritize those exercise types (e.g., matching, q&a, gap-fill).
- Use cultural_interests from profile to select relevant reading topics and themes for exercises.
- Use reading topic interests from usage_context to create contextually relevant exercises.
- Ensure exercise difficulty matches user's current level and pacing preferences.

OUTPUT: Valid JSON data only. Use "items" (NOT "exercises"). Do NOT include "$defs" or schema definitions."""
    return sys, user


def build_ai_comprehension_tutor_prompt(
    metalanguage: str,
    plan: DomainPlan,
    reading: Optional[ReadingCard] = None,
    kit_context: str = "",
    kit_requirements: str = "",
    profile_context: str = "",
) -> Tuple[str, str]:
    """Build prompt for AIComprehensionTutorCard generation (reuses GuidedDialogue concepts)."""
    reading_ref = ""
    if reading:
        reading_ref = f"""
Reading Passage:
- Title: {reading.reading.title.std if reading.reading.title else 'N/A'}
- Content: {reading.reading.content.std[:300] if reading.reading.content.std else 'N/A'}...
"""

    sys = """You are a Japanese language curriculum expert. Generate an AI comprehension tutor system. Return valid JSON only."""
    schema_str = _get_model_schema(AIComprehensionTutorCard)
    user = f"""TARGET_MODEL: AIComprehensionTutorCard

INPUTS:
- metalanguage: {metalanguage}
- communicative_function: {plan.communicative_function_en}
- success_criteria: {json.dumps(plan.evaluation.success_criteria, ensure_ascii=False)}
{reading_ref}
{kit_context}
{kit_requirements}
{profile_context}

JSON SCHEMA (must match exactly):
{schema_str}

CRITICAL RULES - READ CAREFULLY:
1. question field MUST be a JPText object, NOT a string:
   CORRECT: {{"std": "質問", "furigana": "しつもん", "romaji": "shitsumon", "translation": {{"en": "question"}}}}
   WRONG: "質問" (string is invalid)
   WRONG: {{"ja": "質問"}} (missing required JPText fields)

2. hints must be an array of objects, each with "en" and "ja" keys:
   CORRECT: [{{"en": "Hint 1", "ja": "ヒント1"}}, {{"en": "Hint 2", "ja": "ヒント2"}}]
   WRONG: {{"en": "Hint", "ja": "ヒント"}} (single object, not array)
   WRONG: ["Hint 1", "Hint 2"] (strings, not objects)

3. stage_id must be unique string identifier (e.g., "stage_1", "stage_2")

4. goal_en must be a string describing the comprehension goal

5. title must be {{"en": "...", "ja": "..."}} (dict with en/ja keys)

EXAMPLE STRUCTURE:
{{
  "type": "AIComprehensionTutorCard",
  "title": {{"en": "Reading Comprehension", "ja": "読解"}},
  "stages": [
    {{
      "stage_id": "stage_1",
      "goal_en": "Understand main idea",
      "question": {{"std": "本文の主な内容は何ですか？", "furigana": "ほんぶんのしゅないようはなんですか？", "romaji": "honbun no shunaiyou wa nan desu ka?", "translation": {{"en": "What is the main content of the text?"}}}},
      "expected_answer_keywords": ["main", "idea", "content"],
      "hints": [{{"en": "Look at the first paragraph", "ja": "最初の段落を見てください"}}],
      "ai_feedback": {{"rubric": "Check if answer mentions main idea"}}
    }}
  ]
}}

Keep prompts concise and level-appropriate for {plan.level}
{kit_requirements}

PERSONALIZATION:
- Use preferred_exercise_types.comprehension from profile to guide question types and formats.
- Use cultural_interests from profile to select relevant reading topics and themes.
- Ensure question difficulty matches user's current level and pacing preferences.
- Consider user's learning style when crafting hints and feedback.

OUTPUT: Valid JSON matching the schema above. Every question field MUST be a complete JPText object."""
    return sys, user

