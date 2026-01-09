# Content stage prompt builders
from __future__ import annotations

import json
from typing import Any, Dict, List, Tuple

from ..models.plan import DomainPlan
from ..models.cards.content import DialogueCard, ReadingCard
from .constants import STRICT_SYSTEM


def build_objective_prompt(
    metalanguage: str,
    cando_meta: Dict[str, Any],
    plan: DomainPlan,
    kit_context: str = "",
    kit_requirements: str = "",
    profile_context: str = "",
) -> Tuple[str, str]:
    user = f"""TARGET_MODEL: ObjectiveCard

INPUTS:
- metalanguage: {metalanguage}
- can_do: {json.dumps(cando_meta, ensure_ascii=False)}
- plan: {json.dumps(plan.model_dump(), ensure_ascii=False)}

TASK:
Create an ObjectiveCard:
- title: {{"{metalanguage}", "ja"}} succinct.
- body: {{"{metalanguage}", "ja"}} derived from plan.communicative_function_* (learner-facing, A{cando_meta["level"][-1]} terms).
- success_criteria: copy/trim from plan.evaluation.success_criteria (2–5 items).
- outcomes: optional 0–4 finer-grained outcomes.

CONSTRAINTS:
- No extra fields. Strict JSON.
{kit_context}
{kit_requirements}
{profile_context}

CRITICAL OUTPUT REQUIREMENTS:
- Output ONLY the JSON object, NOT wrapped in any other structure
- The JSON must have these exact top-level fields: "type", "title", "body", "success_criteria", "outcomes" (optional)
- "type" must be exactly "ObjectiveCard"
- "title" must be a dict with language codes as keys: {{"{metalanguage}": "...", "ja": "..."}}
- "body" must be a dict with language codes as keys: {{"{metalanguage}": "...", "ja": "..."}}
- "success_criteria" must be a list of strings
- Do NOT wrap the output in {{"ObjectiveCard": ...}}
- Do NOT include any extra fields beyond: type, title, body, success_criteria, outcomes, gen

OUTPUT: ObjectiveCard JSON only.
"""
    return STRICT_SYSTEM, user


def build_words_prompt(
    metalanguage: str,
    plan: DomainPlan,
    kit_context: str = "",
    kit_requirements: str = "",
    profile_context: str = "",
) -> Tuple[str, str]:
    user = f"""TARGET_MODEL: WordsCard

INPUTS:
- metalanguage: {metalanguage}
- plan.lex_buckets: {json.dumps(plan.model_dump(), ensure_ascii=False)}

TASK:
Select 6–12 items total across plan.lex_buckets that best support the function.
For each item:
- Build JPText layers: std (from plan), furigana inline, Hepburn romaji with macrons where applicable,
  translation keyed by "{metalanguage}".
- tags: the source bucket name (e.g., "places","actions","specialties","connectors").
- image: optional flat-icon 1024x1024 prompt describing the concept.

CONSTRAINTS:
- A-level simplicity. Natural readings. No duplicates.
- Strict JSON.
{kit_context}
{kit_requirements}
{profile_context}

PERSONALIZATION:
- If vocabulary_domain_goals are provided in profile, prioritize words from those domains.
- Align word selection with user's learning goals and usage context.
- Consider user's current level when selecting difficulty of vocabulary.

CRITICAL OUTPUT REQUIREMENTS:
- Output ONLY the JSON object, NOT wrapped in any other structure
- The JSON must have these exact top-level fields: "type", "items"
- "type" must be exactly "WordsCard"
- "items" must be an array of WordItem objects
- Do NOT wrap the output in {{"WordsCard": ...}}
- Do NOT include any extra fields beyond: type, items, gen

OUTPUT: WordsCard JSON only.
"""
    return STRICT_SYSTEM, user


def build_grammar_prompt(
    metalanguage: str,
    plan: DomainPlan,
    kit_context: str = "",
    kit_requirements: str = "",
    profile_context: str = "",
) -> Tuple[str, str]:
    user = f"""TARGET_MODEL: GrammarPatternsCard

INPUTS:
- metalanguage: {metalanguage}
- plan.grammar_functions: {json.dumps(plan.model_dump(), ensure_ascii=False)}

TASK:
Choose 2–4 grammar_functions from the plan that are core for achieving the CanDo.
For each chosen function:
- id: reuse the plan function id.
- form.ja: JPText layers where std == pattern_ja; add furigana and romaji; translation in "{metalanguage}".
- explanation: Dict[str, str] - MUST be a dictionary with language codes as keys, like {{"{metalanguage}": "1–2 sentences explaining the pattern"}}. NEVER a plain string.
- slots: copy from the plan function.
- examples: 1–2 A-level examples with full JPText and ≤12 words each.
- image: optional diagram 1280x720.

CONSTRAINTS:
- Respect the level; avoid advanced structures.
- Strict JSON.
- Return ONLY the GrammarPatternsCard structure with "type" and "patterns" fields.
- Do NOT include "metalanguage" or "plan" fields in the response.
{kit_context}
{kit_requirements}
{profile_context}

PERSONALIZATION:
- If grammar_focus_areas are provided in profile, prioritize grammar patterns that align with those focus areas.
- If grammar_progression_goals are provided, ensure selected patterns support those goals.
- Consider user's grammar challenges when crafting explanations and examples.

OUTPUT: GrammarPatternsCard JSON only. The response must be a valid GrammarPatternsCard with:
- type: "GrammarPatternsCard"
- patterns: List of GrammarPatternItem objects
- NO other fields
"""
    return STRICT_SYSTEM, user


def build_words_prompt_from_dialogue(
    metalanguage: str,
    plan: DomainPlan,
    dialog: DialogueCard,
    reading: ReadingCard,
    extracted_words: List[Dict[str, Any]],
    kit_context: str = "",
    kit_requirements: str = "",
    profile_context: str = "",
) -> Tuple[str, str]:
    """Build prompt for WordsCard generation using words extracted from dialogue AND reading."""
    # Format extracted words for prompt
    extracted_words_summary = []
    for w in extracted_words[:20]:  # Limit to top 20
        orth = w.get("orth") or w.get("standard_orthography") or w.get("text") or ""
        pos = w.get("pos") or w.get("pos_primary") or ""
        translation = w.get("translation") or ""
        if orth:
            extracted_words_summary.append(
                {"text": orth, "pos": pos, "translation": translation}
            )

    # Extract reading context
    reading_title = ""
    if reading and reading.reading and reading.reading.title:
        reading_title = (
            reading.reading.title.std
            if hasattr(reading.reading.title, "std")
            else str(reading.reading.title)
        )

    user = f"""TARGET_MODEL: WordsCard

INPUTS:
- metalanguage: {metalanguage}
- plan: {json.dumps(plan.model_dump(), ensure_ascii=False)}
- dialogue: {json.dumps({"setting": dialog.setting, "turns_count": len(dialog.turns)}, ensure_ascii=False)}
- reading: {json.dumps({"title": reading_title, "has_content": bool(reading and reading.reading)}, ensure_ascii=False)}
- extracted_words_from_dialogue_and_reading: {json.dumps(extracted_words_summary, ensure_ascii=False)}

TASK:
Create a WordsCard focusing on words that actually appear in the dialogue AND reading text above.
Select 6–12 items from the extracted_words_from_dialogue_and_reading that are most important for understanding both the dialogue and reading.
Prioritize words that appear in the reading text (which elaborates and extends the dialogue), but also include key words from the dialogue.
For each item:
- Build JPText layers: std (from extracted word text), furigana inline, Hepburn romaji with macrons,
  translation keyed by "{metalanguage}" (use extracted translation if available).
- tags: infer from context (e.g., "places","actions","specialties","connectors","verbs","nouns").
- image: optional flat-icon 1024x1024 prompt describing the concept.

CONSTRAINTS:
- Prioritize words that appear in the reading text (extended narrative), then dialogue.
- A-level simplicity. Natural readings. No duplicates.
- If extracted words are insufficient, you may select relevant items from plan.lex_buckets.
{kit_context}
{kit_requirements}
{profile_context}

PERSONALIZATION:
- If vocabulary_domain_goals are provided in profile, prioritize words from those domains when selecting from extracted words.
- Align word selection with user's learning goals and usage context.
- Consider user's current level when selecting difficulty of vocabulary.

- Strict JSON.

OUTPUT: WordsCard JSON only.
"""
    return STRICT_SYSTEM, user


def build_grammar_prompt_from_dialogue(
    metalanguage: str,
    plan: DomainPlan,
    dialog: DialogueCard,
    reading: ReadingCard,
    extracted_grammar: List[Dict[str, Any]],
    kit_context: str = "",
    kit_requirements: str = "",
    profile_context: str = "",
) -> Tuple[str, str]:
    """Build prompt for GrammarPatternsCard generation using patterns extracted from dialogue AND reading."""
    # Format extracted grammar for prompt
    extracted_grammar_summary = []
    for g in extracted_grammar[:10]:  # Limit to top 10
        pattern = g.get("pattern") or ""
        classification = g.get("classification") or ""
        gid = g.get("id") or ""
        if pattern:
            extracted_grammar_summary.append(
                {"id": gid, "pattern": pattern, "classification": classification}
            )

    # Extract reading context
    reading_title = ""
    if reading and reading.reading and reading.reading.title:
        reading_title = (
            reading.reading.title.std
            if hasattr(reading.reading.title, "std")
            else str(reading.reading.title)
        )

    user = f"""TARGET_MODEL: GrammarPatternsCard

INPUTS:
- metalanguage: {metalanguage}
- plan: {json.dumps(plan.model_dump(), ensure_ascii=False)}
- dialogue: {json.dumps({"setting": dialog.setting, "turns_count": len(dialog.turns)}, ensure_ascii=False)}
- reading: {json.dumps({"title": reading_title, "has_content": bool(reading and reading.reading)}, ensure_ascii=False)}
- extracted_grammar_from_dialogue_and_reading: {json.dumps(extracted_grammar_summary, ensure_ascii=False)}

TASK:
Create a GrammarPatternsCard focusing on grammar patterns that actually appear in the dialogue AND reading text above.
Choose 2–4 patterns from extracted_grammar_from_dialogue_and_reading that are core for both the dialogue and reading.
Prioritize patterns that appear in the reading text (which elaborates and extends the dialogue), but also include key patterns from the dialogue.
If a pattern matches a plan.grammar_functions id, reuse that function's details.
For each pattern:
- id: use extracted id if available, otherwise create new id based on pattern.
- form.ja: JPText layers where std == pattern; add furigana and romaji; translation in "{metalanguage}".
- explanation: Dict[str, str] - MUST be a dictionary with language codes as keys, like {{"{metalanguage}": "1–2 sentences explaining how it's used in the dialogue and reading"}}. NEVER a plain string.
- slots: infer from pattern structure or copy from matching plan function if available.
- examples: 1–2 A-level examples from the reading or dialogue, with full JPText and ≤12 words each.
- image: optional diagram 1280x720.

CONSTRAINTS:
- Prioritize patterns that appear in the reading text (extended narrative), then dialogue.
- Respect the level; avoid advanced structures.
- CRITICAL: All explanation fields must be Dict[str, str] like {{"{metalanguage}": "text"}}, NEVER plain strings
- If extracted patterns are insufficient, you may select relevant items from plan.grammar_functions.
{kit_context}
{kit_requirements}
{profile_context}

PERSONALIZATION:
- If grammar_focus_areas are provided in profile, prioritize grammar patterns that align with those focus areas.
- If grammar_progression_goals are provided, ensure selected patterns support those goals.
- Consider user's grammar challenges when crafting explanations and examples.

- Strict JSON.

OUTPUT: GrammarPatternsCard JSON only.
"""
    return STRICT_SYSTEM, user


def build_dialogue_prompt(
    metalanguage: str,
    plan: DomainPlan,
    kit_context: str = "",
    kit_requirements: str = "",
    profile_context: str = "",
) -> Tuple[str, str]:
    user = f"""TARGET_MODEL: DialogueCard

INPUTS:
- metalanguage: {metalanguage}
- scenario: {json.dumps(plan.scenarios[0].model_dump(), ensure_ascii=False)}
- grammar_ids: {json.dumps([g.id for g in plan.grammar_functions], ensure_ascii=False)}
- vocabulary: {json.dumps([it for b in plan.lex_buckets for it in b.items], ensure_ascii=False)}
{kit_context}
{profile_context}

TASK: Create a DialogueCard with 8-10 turns using the first scenario.

REQUIRED FIELDS:
- type: "DialogueCard"
- title: {{"en": "...", "ja": "..."}}
- turns: List[DialogueTurn] (use "turns", NOT "dialogue")
- setting: Optional string describing the scene
- characters: Optional array of speaker names

CONSTRAINTS:
- Each turn: JPText with std, furigana, romaji, translation (translation is Dict[str, str], NOT string)
- Use at least 2 grammar function ids from the list
- Prefer vocabulary from the provided list (≥60% of content words)
- ≤12 words per turn, appropriate register for scenario roles
- Use scenario role labels for "speaker" field
{kit_requirements}

PERSONALIZATION:
- Use register_preferences from profile to select appropriate register (plain/polite/neutral) for dialogue turns.
- Use scenario_details from profile to create specific, relevant dialogue scenarios.
- Align dialogue content with user's usage context (e.g., work, travel, academic).
- Consider user's cultural background for culturally appropriate dialogue content.

OUTPUT: DialogueCard JSON only."""
    return STRICT_SYSTEM, user


def build_reading_prompt(
    metalanguage: str,
    cando: Dict[str, Any],
    plan: DomainPlan,
    dialog: DialogueCard,
    kit_context: str = "",
    kit_requirements: str = "",
    profile_context: str = "",
) -> Tuple[str, str]:
    """Build prompt for ReadingCard generation that extends dialogue with CanDo domain elements."""
    dialogue_context = {
        "setting": dialog.setting,
        "characters": dialog.characters,
        "turns": [{"speaker": t.speaker, "text": t.ja.std} for t in dialog.turns],
    }

    user = f"""TARGET_MODEL: ReadingCard

INPUTS:
- metalanguage: {metalanguage}
- can_do: {cando["uid"]} ({cando["level"]}) - {cando.get("primaryTopicEn", cando.get("primaryTopic", "Unknown"))}
- dialogue: {json.dumps(dialogue_context, ensure_ascii=False)}
- vocabulary: from plan.lex_buckets
- grammar: from plan.grammar_functions
{kit_context}

TASK: Create a ReadingCard that extends the dialogue for comprehension practice.

REQUIRED FIELDS:
- type: "ReadingCard"
- title: {{"en": "...", "ja": "..."}} (simple dict, NOT JPText)
- reading.title: JPText (std, furigana, romaji, translation as Dict[str, str])
- reading.content: JPText (140-220 Japanese words, extends dialogue)
- reading.comprehension: Array of {{q: JPText, a: JPText, evidenceSpan?: string}} (5-7 questions)

CRITICAL: All JPText.translation fields MUST be Dict[str, str], NEVER strings!
Example of CORRECT format:
  "translation": {{"{metalanguage}": "Translation text here"}}
  
Example of WRONG format (DO NOT USE):
  "translation": "Translation text here"  ❌ WRONG - this is a string, not a dict!

Every JPText object (reading.title, reading.content, comprehension[].q, comprehension[].a) must have:
  "translation": {{"{metalanguage}": "..."}}  ✅ CORRECT

CONSTRAINTS:
- Extend dialogue with 1-2 new domain elements (same topic, different angle)
- Use vocabulary/grammar from plan
- All translation fields must be Dict[str, str] with language code keys, NOT strings
- Optional notes_en with "PRODUCTION:" and "INTERACTION:" sections
{kit_requirements}
{profile_context}

PERSONALIZATION:
- Use cultural_interests from profile to select relevant reading topics and themes.
- Use scenario_details from profile to create specific, relevant reading scenarios.
- Align reading content with user's learning goals and usage context.
- Consider user's cultural background for culturally appropriate reading content.
- Ensure reading difficulty matches user's current level.

OUTPUT: ReadingCard JSON only."""
    return STRICT_SYSTEM, user


def build_guided_dialogue_prompt(
    metalanguage: str, plan: DomainPlan
) -> Tuple[str, str]:
    user = f"""TARGET_MODEL: GuidedDialogueCard

INPUTS:
- metalanguage: {metalanguage}
- grammar_ids: {json.dumps([g.id for g in plan.grammar_functions], ensure_ascii=False)}
- success_criteria: {json.dumps(plan.evaluation.success_criteria, ensure_ascii=False)}

TASK: Create a GuidedDialogueCard with 1-3 scaffold stages.

REQUIRED FIELDS:
- type: "GuidedDialogueCard"
- title: {{"en": "...", "ja": "..."}}
- stages: Array of stage objects

EACH STAGE:
- stage_id: unique identifier
- goal_en: aligned with one success criterion
- expected_patterns: relevant grammar function ids
- hints: 1-2 bilingual hints ({{"{metalanguage}": "...", "ja": "..."}})
- learner_turn_schema: {{"min_words": 4, "max_words": 12, "allow_romaji": false}}
- ai_feedback: rubric with pattern_correctness, fluency, content_relevance

OUTPUT: GuidedDialogueCard JSON only."""
    return STRICT_SYSTEM, user


def build_exercises_prompt(metalanguage: str, plan: DomainPlan) -> Tuple[str, str]:
    user = f"""TARGET_MODEL: ExercisesCard

INPUTS:
- metalanguage: {metalanguage}
- plan.lex_buckets: {json.dumps(plan.model_dump(), ensure_ascii=False)}
- plan.grammar_functions (ids & patterns available): {json.dumps([{ "id": g.id, "pattern_ja": g.pattern_ja } for g in plan.grammar_functions], ensure_ascii=False)}
- plan.evaluation.discourse_markers: {json.dumps(plan.evaluation.discourse_markers, ensure_ascii=False)}

TASK:
Create 2–4 exercises:
1) "match" (3–6 pairs) using lexemes from plan.lex_buckets; answers in "{metalanguage}".
2) "fill_blank" using one grammar function; provide 3–6 acceptable answers in "{metalanguage}".
3) optionally "order" (3 segments) if discourse markers exist.

Use JPText for any Japanese stems.

CONSTRAINTS:
- A-level difficulty. Strict JSON.

OUTPUT: ExercisesCard JSON only.
"""
    return STRICT_SYSTEM, user


def build_culture_prompt(
    metalanguage: str,
    plan: DomainPlan,
    kit_context: str = "",
    kit_requirements: str = "",
    profile_context: str = "",
) -> Tuple[str, str]:
    user = f"""TARGET_MODEL: CultureCard

INPUTS:
- metalanguage: {metalanguage}
- cultural_themes_en: {json.dumps(plan.cultural_themes_en, ensure_ascii=False)}
- cultural_themes_ja: {json.dumps(plan.cultural_themes_ja, ensure_ascii=False)}
{kit_context}
{profile_context}

TASK: Create a CultureCard summarizing 2-4 key cultural/pragmatic themes.

REQUIRED FIELDS:
- type: "CultureCard"
- title: {{"en": "...", "ja": "..."}}
- body: {{"en": "string", "ja": "string"}} (both must be strings, NOT lists)

CONSTRAINTS:
- body.en and body.ja must be plain strings
- Optional image: ImageSpec (1280x720, style "infographic")
{kit_requirements}

PERSONALIZATION:
- Use cultural_interests from profile to prioritize relevant cultural themes.
- Consider user's cultural_background when explaining cultural concepts.
- Align cultural content with user's learning goals and usage context.

OUTPUT: CultureCard JSON only."""
    return STRICT_SYSTEM, user


def build_drills_prompt(metalanguage: str, plan: DomainPlan) -> Tuple[str, str]:
    user = f"""TARGET_MODEL: DrillsCard

INPUTS:
- metalanguage: {metalanguage}
- plan.grammar_functions (ids & slots): {json.dumps([{ "id": g.id, "slots": g.slots } for g in plan.grammar_functions], ensure_ascii=False)}
- plan.lex_buckets (for seed items): {json.dumps([b.model_dump() for b in plan.lex_buckets], ensure_ascii=False)}

TASK:
Create 2 drills:
- substitution: choose one grammar function id for pattern_ref; set slots per that function; add 2–6 seed_items from lex_buckets (simple nouns).
- pronunciation: 2–4 targets from high-frequency lexemes or pattern chunks (provide "ja" and "romaji").

Include ai_support prompts.

CONSTRAINTS:
- Strict JSON.

CRITICAL OUTPUT REQUIREMENTS:
- Output ONLY the JSON object, NOT wrapped in any other structure
- The JSON must have these exact top-level fields: "type", "items"
- "type" must be exactly "DrillsCard"
- "items" must be an array of DrillItem objects (SubstitutionDrill or PronunciationDrill)
- Do NOT wrap the output in {{"DrillsCard": ...}}
- Do NOT include any extra fields beyond: type, items, gen

OUTPUT: DrillsCard JSON only.
"""
    return STRICT_SYSTEM, user


def build_formulaic_expressions_prompt(
    metalanguage: str,
    plan: DomainPlan,
    kit_context: str = "",
    kit_requirements: str = "",
    profile_context: str = "",
) -> Tuple[str, str]:
    """Build prompt for FormulaicExpressionsCard generation."""
    sys = """You are a Japanese language curriculum expert. Generate formulaic expressions appropriate for the communicative function and level."""
    user = f"""TARGET_MODEL: FormulaicExpressionsCard

INPUTS:
- metalanguage: {metalanguage}
- communicative_function: {plan.communicative_function_en} / {plan.communicative_function_ja}
- level: {plan.level}
{kit_context}
{kit_requirements}

TASK: Create a FormulaicExpressionsCard with 5-8 fixed expressions for this communicative function.

REQUIRED FIELDS:
- type: "FormulaicExpressionsCard"
- title: {{"en": "...", "ja": "..."}}
- items: Array of expression objects (each with JPText, context, examples)

CONSTRAINTS:
- Expressions must be fixed phrases appropriate for level {plan.level}
- Each expression: JPText, context info, 1-2 example sentences
{kit_requirements}
{profile_context}

PERSONALIZATION:
- Use formulaic_expression_goals from profile to prioritize relevant expression contexts.
- Use register_preferences from profile to select appropriate register for expressions.
- Align expressions with user's usage context and learning goals.

OUTPUT: FormulaicExpressionsCard JSON only."""
    return sys, user

