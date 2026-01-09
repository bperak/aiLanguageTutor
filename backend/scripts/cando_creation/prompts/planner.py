# Planner prompt builder
from __future__ import annotations

from typing import Any, Dict, Tuple

from .constants import STRICT_SYSTEM


def build_planner_prompt(
    metalanguage: str,
    cando: Dict[str, Any],
    kit_context: str = "",
    kit_requirements: str = "",
    profile_context: str = "",
) -> Tuple[str, str]:
    """Planner prompt: CanDo -> DomainPlan (no hardcoded domain content)."""
    user = f"""TARGET_MODEL: DomainPlan

CONTEXT:
- metalanguage: {metalanguage}
- CanDoDescriptor:
  uid: {cando["uid"]}
  level: {cando["level"]}
  primaryTopic_ja: {cando["primaryTopic"]}
  primaryTopic_en: {cando["primaryTopicEn"]}
  skillDomain_ja: {cando["skillDomain"]}
  type_ja: {cando["type"]}
  description.en: {cando["descriptionEn"]}
  description.ja: {cando["descriptionJa"]}
  source: {cando["source"]}

TASK:
Derive a DomainPlan solely from the CanDoDescriptor (no preset phrases).
1) communicative_function_*: restate the CanDo as a concise function in en/ja.
2) scenarios: 1–2 plausible contexts consistent with type_ja and skillDomain_ja. Create roles with labels you invent (e.g., ガイド/友人 or their English forms), and pick register appropriate to level {cando["level"]}.
3) lex_buckets: 3–5 buckets relevant to THIS CanDo. Each 6–14 JP surface forms (std only).
4) grammar_functions: 2–5 functions (id, label, pattern_ja, slots, notes_en) that enable THIS function at level {cando["level"]}. Do not assume any domain beyond what the CanDo implies.
5) evaluation: 2–5 success_criteria and 2–5 discourse_markers aligned with the function.
6) cultural_themes_*: 2–5 short bullets in en and ja for pragmatic/cultural awareness.

CONSTRAINTS:
- JP items must be natural for the stated level.
- No furigana/romaji in the plan.
- Do not invent Neo4j ids or relations.
{kit_context}
{kit_requirements}
{profile_context}

PERSONALIZATION:
- Consider user profile context when selecting scenarios, vocabulary, and cultural themes.
- Use register_preferences from profile to select appropriate register for scenarios (plain/polite/neutral).
- Use cultural_interests from profile to select relevant cultural themes.
- Use scenario_details from profile to create specific, relevant scenarios.
- Use grammar_focus_areas from profile to emphasize relevant grammar functions.
- Align content with user's learning goals and usage context.
- Ensure difficulty matches user's current level.
- If path-level structures (vocabulary_domain_goals, grammar_progression_goals) are provided, incorporate them into the plan.

OUTPUT: DomainPlan JSON only.
"""
    return STRICT_SYSTEM, user

