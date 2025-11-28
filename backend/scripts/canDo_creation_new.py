# lesson_pipeline.py
# Pydantic v2 full pipeline: CanDo -> DomainPlan -> Cards -> LessonRoot
from __future__ import annotations

import json
from typing import Any, Callable, Dict, List, Literal, Optional, Protocol, Tuple, Type, TypeVar, Union

from pydantic import BaseModel, Field, ValidationError, ConfigDict

# ======================================================================================
#                                P Y D A N T I C   M O D E L S
# ======================================================================================

# ----------------- Shared -----------------

class JPText(BaseModel):
    model_config = ConfigDict(extra="forbid")
    std: str
    furigana: str
    romaji: str
    translation: Dict[str, str]  # {"en": "..."} where key == metalanguage code


class ImageSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    prompt: str
    style: Literal["flat-icon", "scene-illustration", "diagram", "infographic", "photo"]
    size: Literal["1024x1024", "1280x720", "1280x768", "2048x2048"]
    negative_prompt: Optional[str] = None
    seed: Optional[int] = None
    path: Optional[str] = None  # Relative path to generated image file


class LLMGenSpec(BaseModel):
    """Carry the exact prompts used to generate a card for traceability/repro."""
    model_config = ConfigDict(extra="forbid")
    system: str
    instruction: str
    constraints: List[str] = Field(default_factory=list)
    examples: Optional[str] = None


# ----------------- Meta & Graph -----------------

class CanDoMeta(BaseModel):
    model_config = ConfigDict(extra="forbid")
    uid: str
    level: Literal["A1", "A2", "B1", "B2", "C1", "C2"]
    primaryTopic_ja: str
    primaryTopic_en: str
    skillDomain_ja: str
    type_ja: str
    description: Dict[str, str]  # {"en": "...", "ja": "..."}
    source: str  # from Neo4j CanDoDescriptor.source
    titleEn: Optional[str] = None  # AI-generated title in English
    titleJa: Optional[str] = None  # AI-generated title in Japanese


class LessonMeta(BaseModel):
    model_config = ConfigDict(extra="forbid")
    lesson_id: str
    metalanguage: Literal["en", "hr", "ja", "de", "fr", "it", "es"]
    can_do: CanDoMeta  # Injected directly from Neo4j CanDoDescriptor + metalanguage


class LookupSpec(BaseModel):
    """
    Relation-agnostic binding:
      - by_cypher: provide explicit Cypher (optional)
      - by_keys: business keys to resolve later (optional)
      - resolve_label / resolve_property: optional hints to build Cypher outside LLM
    """
    model_config = ConfigDict(extra="forbid")
    by_cypher: Optional[str] = None
    by_keys: List[str] = Field(default_factory=list)
    resolve_label: Optional[str] = None
    resolve_property: Optional[str] = None


class GraphBindings(BaseModel):
    model_config = ConfigDict(extra="forbid")
    words: LookupSpec = Field(default_factory=LookupSpec)
    grammar_patterns: LookupSpec = Field(default_factory=LookupSpec)


class TextLayerPrefs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    std: bool = True
    furigana: bool = True
    romaji: bool = False
    translation: bool = True


class UIPrefs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text_layers_default: TextLayerPrefs = Field(default_factory=TextLayerPrefs)


# ----------------- Planner (DomainPlan) -----------------

class PlanRole(BaseModel):
    model_config = ConfigDict(extra="forbid")
    label: str               # free label, e.g., "Guide", "Friend", "Clerk"
    register: Literal["plain", "polite", "neutral"] = "polite"


class PlanScenario(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    setting: str             # e.g., "outdoors", "classroom"
    roles: List[PlanRole]


class PlanLexBucket(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str                # e.g., "places", "specialties", "actions", "connectors"
    items: List[str]         # JP surface forms (std only). No furigana/romaji here.


class PlanGrammarFunction(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str                  # stable id for cross-refs, e.g., "gf_001"
    label: str               # e.g., "fame/reason", "existence/location"
    pattern_ja: str          # JP skeleton (std), e.g., "XはYで有名です"
    slots: List[str]         # e.g., ["X:place", "Y:feature"]
    notes_en: Optional[str] = None


class PlanEvaluation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    success_criteria: List[str]
    discourse_markers: List[str]  # e.g., ["まず","次に","最後に"] or others per function


class DomainPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")
    uid: str
    level: Literal["A1", "A2", "B1", "B2", "C1", "C2"]
    communicative_function_en: str
    communicative_function_ja: str
    scenarios: List[PlanScenario]
    lex_buckets: List[PlanLexBucket]
    grammar_functions: List[PlanGrammarFunction]
    evaluation: PlanEvaluation
    cultural_themes_en: List[str]
    cultural_themes_ja: List[str]


# ----------------- Cards -----------------

class ObjectiveCard(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["ObjectiveCard"] = "ObjectiveCard"
    title: Dict[str, str]
    body: Dict[str, str]
    success_criteria: List[str]
    outcomes: List[str] = Field(default_factory=list)
    gen: Optional[LLMGenSpec] = None


class WordItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    neo4j_id: Optional[str] = None
    jp: JPText
    tags: List[str] = Field(default_factory=list)
    image: Optional[ImageSpec] = None


class WordsCard(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["WordsCard"] = "WordsCard"
    items: List[WordItem]
    ui_layers_override: Optional[TextLayerPrefs] = None
    gen: Optional[LLMGenSpec] = None


class PatternExample(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ja: JPText
    audio_ref: Optional[str] = None


class PatternForm(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ja: JPText


class GrammarPatternItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str                   # MUST match a DomainPlan.grammar_functions[i].id
    neo4j_id: Optional[str] = None
    form: PatternForm
    explanation: Dict[str, str]
    slots: List[str]
    examples: List[PatternExample]
    image: Optional[ImageSpec] = None


class GrammarPatternsCard(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["GrammarPatternsCard"] = "GrammarPatternsCard"
    patterns: List[GrammarPatternItem]
    gen: Optional[LLMGenSpec] = None


class DialogueTurn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    speaker: str             # free label from plan.scenarios[*].roles
    ja: JPText
    audio_ref: Optional[str] = None


class DialogueCard(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["DialogueCard"] = "DialogueCard"
    title: Dict[str, str]
    setting: Optional[str] = None  # Contextual opening paragraph for the dialogue scene
    characters: Optional[List[str]] = None  # Optional list of character names
    turns: List[DialogueTurn]
    notes_en: Optional[str] = None
    image: Optional[ImageSpec] = None
    gen: Optional[LLMGenSpec] = None


class ComprehensionQA(BaseModel):
    model_config = ConfigDict(extra="forbid")
    q: JPText  # Question in Japanese
    a: JPText  # Answer in Japanese
    evidenceSpan: Optional[str] = None  # Text span in reading that supports answer


class ReadingSection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: JPText  # Title of the reading passage
    content: JPText  # Full reading text (200+ words)
    comprehension: List[ComprehensionQA]  # 5-7 comprehension questions


class ReadingCard(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["ReadingCard"] = "ReadingCard"
    title: Dict[str, str]  # Multilingual title
    reading: ReadingSection  # Contains title, content (JPText), comprehension (List[ComprehensionQA])
    notes_en: Optional[str] = None
    image: Optional[ImageSpec] = None
    gen: Optional[LLMGenSpec] = None


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


class CardsContainer(BaseModel):
    model_config = ConfigDict(extra="forbid")
    objective: ObjectiveCard
    words: WordsCard
    grammar_patterns: GrammarPatternsCard
    lesson_dialogue: DialogueCard
    reading_comprehension: ReadingCard
    guided_dialogue: GuidedDialogueCard
    exercises: ExercisesCard
    cultural_explanation: CultureCard
    drills_ai: DrillsCard


class Lesson(BaseModel):
    model_config = ConfigDict(extra="forbid")
    meta: LessonMeta
    graph_bindings: GraphBindings = Field(default_factory=GraphBindings)
    ui_prefs: UIPrefs = Field(default_factory=UIPrefs)
    cards: CardsContainer


class LessonRoot(BaseModel):
    model_config = ConfigDict(extra="forbid")
    lesson: Lesson


# ======================================================================================
#                           J S O N   S C H E M A   +   U T I L S
# ======================================================================================

def model_schema(model: Type[BaseModel]) -> str:
    """JSON Schema string for a Pydantic model."""
    return json.dumps(model.model_json_schema(), ensure_ascii=False, indent=2)


def extract_first_json_block(text: str) -> str:
    """
    If a model returns extra prose, extract the first valid JSON object by brace matching.
    Falls back to original text if parsing fails.
    """
    start = text.find("{")
    if start == -1:
        return text
    depth = 0
    for i, ch in enumerate(text[start:], start=start):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start:i+1]
    return text


T = TypeVar("T", bound=BaseModel)


def validate_or_repair(
    llm_call: Callable[[str, str], str],
    target_model: Type[T],
    system_prompt: str,
    user_prompt: str,
    max_repair: int = 2,
) -> T:
    """
    Call LLM, enforce STRICT JSON, validate against Pydantic model, repair if needed.
    """
    raw = llm_call(system_prompt, user_prompt)
    raw = extract_first_json_block(raw)

    for attempt in range(max_repair + 1):
        try:
            return target_model.model_validate_json(raw)
        except ValidationError as e:
            if attempt >= max_repair:
                raise
            # Ask model to repair using the schema and the error list
            schema_str = model_schema(target_model)
            repair_user = (
                "You returned JSON that failed validation.\n"
                "SCHEMA:\n" + schema_str + "\n\n"
                "JSON_WITH_ERRORS:\n" + raw + "\n\n"
                "ERRORS:\n" + json.dumps(e.errors(), ensure_ascii=False, indent=2) + "\n\n"
                "Return a corrected JSON that fully validates. Output STRICT JSON only."
            )
            raw = llm_call(system_prompt, repair_user)
            raw = extract_first_json_block(raw)

    # Should never reach
    return target_model.model_validate_json(raw)


# ======================================================================================
#                            L L M   A D A P T E R   I N T E R F A C E
# ======================================================================================

class LLMFn(Protocol):
    def __call__(self, system: str, user: str) -> str: ...


# ======================================================================================
#                         P R O M P T   B U I L D E R S   ( N O   H A R D C O D E S )
# ======================================================================================

STRICT_SYSTEM = (
    "You output a SINGLE JSON object that must validate the target Pydantic model. "
    "Return STRICT JSON only. No Markdown, no comments, no explanations."
)

def build_planner_prompt(metalanguage: str, cando: Dict[str, Any]) -> Tuple[str, str]:
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

OUTPUT: DomainPlan JSON only.
"""
    return STRICT_SYSTEM, user


def build_objective_prompt(metalanguage: str, cando_meta: Dict[str, Any], plan: DomainPlan) -> Tuple[str, str]:
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
"""
    return STRICT_SYSTEM, user


def build_words_prompt(metalanguage: str, plan: DomainPlan) -> Tuple[str, str]:
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

OUTPUT: WordsCard JSON only.
"""
    return STRICT_SYSTEM, user


def build_grammar_prompt(metalanguage: str, plan: DomainPlan) -> Tuple[str, str]:
    user = f"""TARGET_MODEL: GrammarPatternsCard

INPUTS:
- metalanguage: {metalanguage}
- plan.grammar_functions: {json.dumps(plan.model_dump(), ensure_ascii=False)}

TASK:
Choose 2–4 grammar_functions from the plan that are core for achieving the CanDo.
For each chosen function:
- id: reuse the plan function id.
- form.ja: JPText layers where std == pattern_ja; add furigana and romaji; translation in "{metalanguage}".
- explanation: {{"{metalanguage}": "..."}}, 1–2 sentences.
- slots: copy from the plan function.
- examples: 1–2 A-level examples with full JPText and ≤12 words each.
- image: optional diagram 1280x720.

CONSTRAINTS:
- Respect the level; avoid advanced structures.
- Strict JSON.

OUTPUT: GrammarPatternsCard JSON only.
"""
    return STRICT_SYSTEM, user


def build_words_prompt_from_dialogue(
    metalanguage: str, 
    plan: DomainPlan, 
    dialog: DialogueCard,
    reading: ReadingCard,
    extracted_words: List[Dict[str, Any]]
) -> Tuple[str, str]:
    """Build prompt for WordsCard generation using words extracted from dialogue AND reading."""
    # Format extracted words for prompt
    extracted_words_summary = []
    for w in extracted_words[:20]:  # Limit to top 20
        orth = w.get("orth") or w.get("standard_orthography") or w.get("text") or ""
        pos = w.get("pos") or w.get("pos_primary") or ""
        translation = w.get("translation") or ""
        if orth:
            extracted_words_summary.append({"text": orth, "pos": pos, "translation": translation})
    
    # Extract reading context
    reading_title = ""
    if reading and reading.reading and reading.reading.title:
        reading_title = reading.reading.title.std if hasattr(reading.reading.title, 'std') else str(reading.reading.title)
    
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
- Strict JSON.

OUTPUT: WordsCard JSON only.
"""
    return STRICT_SYSTEM, user


def build_grammar_prompt_from_dialogue(
    metalanguage: str, 
    plan: DomainPlan, 
    dialog: DialogueCard,
    reading: ReadingCard,
    extracted_grammar: List[Dict[str, Any]]
) -> Tuple[str, str]:
    """Build prompt for GrammarPatternsCard generation using patterns extracted from dialogue AND reading."""
    # Format extracted grammar for prompt
    extracted_grammar_summary = []
    for g in extracted_grammar[:10]:  # Limit to top 10
        pattern = g.get("pattern") or ""
        classification = g.get("classification") or ""
        gid = g.get("id") or ""
        if pattern:
            extracted_grammar_summary.append({
                "id": gid,
                "pattern": pattern,
                "classification": classification
            })
    
    # Extract reading context
    reading_title = ""
    if reading and reading.reading and reading.reading.title:
        reading_title = reading.reading.title.std if hasattr(reading.reading.title, 'std') else str(reading.reading.title)
    
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
- explanation: {{"{metalanguage}": "..."}}, 1–2 sentences explaining how it's used in the dialogue and reading.
- slots: infer from pattern structure or copy from matching plan function if available.
- examples: 1–2 A-level examples from the reading or dialogue, with full JPText and ≤12 words each.
- image: optional diagram 1280x720.

CONSTRAINTS:
- Prioritize patterns that appear in the reading text (extended narrative), then dialogue.
- Respect the level; avoid advanced structures.
- If extracted patterns are insufficient, you may select relevant items from plan.grammar_functions.
- Strict JSON.

OUTPUT: GrammarPatternsCard JSON only.
"""
    return STRICT_SYSTEM, user


def build_dialogue_prompt(metalanguage: str, plan: DomainPlan) -> Tuple[str, str]:
    user = f"""TARGET_MODEL: DialogueCard

INPUTS:
- metalanguage: {metalanguage}
- plan.scenarios[0]: {json.dumps(plan.scenarios[0].model_dump(), ensure_ascii=False)}
- plan.grammar_functions (ids available): {json.dumps([g.id for g in plan.grammar_functions], ensure_ascii=False)}
 - plan.lex_items (preferred vocabulary): {json.dumps([it for b in plan.lex_buckets for it in b.items], ensure_ascii=False)}

TASK:
Create a DialogueCard with 8–10 turns in the first scenario. Use the scenario roles' labels for "speaker".
START with a contextual opening "setting" field: one paragraph describing the scene (place, people, motives, context) before the dialogue begins.
Include a "characters" array listing the speaker names if there are 2 or more participants.
Each turn provides JPText layers (std, furigana, romaji, translation["{metalanguage}"]).
Grammar alignment: naturally use at least 2 of the selected grammar function ids across the dialogue.
Vocabulary alignment: prefer content words from plan.lex_items (target ≥60% of nouns/verbs from this list); allow at most 2 new content words total.
Add a one-line notes_en, and optionally a scene-illustration 1280x768.

CONSTRAINTS:
- ≤12 words per turn. A-level tone/register per scenario role register. Keep continuity across turns (light back-and-forth).
- Strict JSON.

OUTPUT: DialogueCard JSON only.
"""
    return STRICT_SYSTEM, user


def build_reading_prompt(metalanguage: str, cando: Dict[str, Any], plan: DomainPlan, dialog: DialogueCard) -> Tuple[str, str]:
    """Build prompt for ReadingCard generation that extends dialogue with CanDo domain elements."""
    # Extract full dialogue for reference
    dialogue_context = {
        "setting": dialog.setting,
        "characters": dialog.characters,
        "turns": [{"speaker": t.speaker, "text": t.ja.std} for t in dialog.turns]  # All turns for context
    }
    
    user = f"""TARGET_MODEL: ReadingCard

INPUTS:
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
- plan.lex_buckets: Vocabulary buckets relevant to this CanDo domain
- plan.grammar_functions: Grammar patterns relevant to this CanDo
- dialogue: {json.dumps(dialogue_context, ensure_ascii=False)}

TASK:
Create a ReadingCard with an elaborate narrative text that:
1. ELABORATES the dialogue - continues/expands on the dialogue story with more narrative detail
2. EXTENDS with CanDo domain elements - introduces additional scenarios, options, or related topics from the CanDo domain that weren't in the dialogue
3. Contains at least 200 words of Japanese text
4. Uses vocabulary from plan.lex_buckets and grammar from plan.grammar_functions
5. Includes 5-7 comprehension questions that test understanding of the narrative and extended domain elements

The reading should:
- Continue where the dialogue left off or elaborate on what happened during/after the dialogue
- Add related elements from the CanDo domain (e.g., if CanDo is about family and dialogue mentions parents, add siblings, grandparents, cousins, etc.)
- Expand on scenarios relevant to primaryTopic that weren't covered in the dialogue
- Show additional applications of the communicative function from different angles
- Provide more context and narrative around the dialogue situation

Examples of extension:
- If CanDo is about family and dialogue talks about parents → extend to siblings, grandparents, extended family
- If CanDo is about shopping and dialogue shows buying food → extend to buying clothes, electronics, asking for sizes/colors
- If CanDo is about directions and dialogue asks for a location → extend to giving directions, landmarks, transportation options

Structure:
- title: {{"{metalanguage}", "ja"}} - Brief title for the reading
- reading.title: JPText - Title of the reading passage (full JPText with std/furigana/romaji/translation)
- reading.content: JPText - Elaboration and extension of dialogue (minimum 200 words, std/furigana/romaji/translation)
- reading.comprehension: Array of {{q: JPText, a: JPText, evidenceSpan?: string}} - Exactly 5-7 questions

Questions should actively test:
- Understanding of the dialogue narrative extension (what happened in the extended story)
- Comprehension of the additional CanDo domain elements introduced (siblings, other scenarios, etc.)
- How the extended elements relate to the primaryTopic
- Key vocabulary and grammar patterns from the extended narrative
- Inferences about the extended scenarios and their connection to the CanDo function

Each comprehension question should have:
- q: Full JPText (question in Japanese with translation)
- a: Full JPText (answer in Japanese with translation)
- evidenceSpan: Optional string indicating text span that supports the answer

CONSTRAINTS:
- Minimum 200 words in reading.content.std
- Exactly 5-7 comprehension questions (not more, not less)
- Questions and answers must be full JPText format (std, furigana, romaji, translation)
- Keep level-appropriate (same level as CanDo, typically A-level)
- Start from/elaborate the dialogue, but extend with more domain elements
- Use vocabulary from plan.lex_buckets and grammar from plan.grammar_functions
- Ground the extension in the CanDo domain (primaryTopic, skillDomain)
- Strict JSON.

OUTPUT: ReadingCard JSON only.
"""
    return STRICT_SYSTEM, user


def build_guided_dialogue_prompt(metalanguage: str, plan: DomainPlan) -> Tuple[str, str]:
    user = f"""TARGET_MODEL: GuidedDialogueCard

INPUTS:
- metalanguage: {metalanguage}
- plan.grammar_functions (ids): {json.dumps([g.id for g in plan.grammar_functions], ensure_ascii=False)}
- plan.evaluation.success_criteria: {json.dumps(plan.evaluation.success_criteria, ensure_ascii=False)}

TASK:
Create 1–3 scaffold stages moving the learner towards the success_criteria.
Each stage:
- stage_id
- goal_en (align with one success criterion)
- expected_patterns: choose relevant grammar function ids from plan
- 1–2 bilingual hints ({{"{metalanguage}","ja"}})
- learner_turn_schema: {{"min_words":4,"max_words":12,"allow_romaji":false}}
- ai_feedback: rubric ["pattern_correctness","fluency_{plan.level.lower()}","content_relevance"] and a one-line feedback prompt.

CONSTRAINTS:
- Strict JSON.

OUTPUT: GuidedDialogueCard JSON only.
"""
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


def build_culture_prompt(metalanguage: str, plan: DomainPlan) -> Tuple[str, str]:
    user = f"""TARGET_MODEL: CultureCard

INPUTS:
- metalanguage: {metalanguage}
- plan.cultural_themes_* and plan.communicative_function_*:
  en: {json.dumps(plan.cultural_themes_en, ensure_ascii=False)}
  ja: {json.dumps(plan.cultural_themes_ja, ensure_ascii=False)}

TASK:
Write a CultureCard (title/body in {{"{metalanguage}","ja"}}) summarizing 2–4 key pragmatic/cultural themes relevant to the communicative function.
Optional infographic image 1280x720 (style "infographic").

CONSTRAINTS:
- Strict JSON.

OUTPUT: CultureCard JSON only.
"""
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

OUTPUT: DrillsCard JSON only.
"""
    return STRICT_SYSTEM, user


# ======================================================================================
#                           G E N E R A T I O N   F U N C T I O N S
# ======================================================================================

def gen_domain_plan(llm_call: LLMFn, cando: Dict[str, Any], metalanguage: str, max_repair: int = 2) -> DomainPlan:
    sys, usr = build_planner_prompt(metalanguage, cando)
    return validate_or_repair(llm_call, DomainPlan, sys, usr, max_repair=max_repair)


def gen_objective_card(llm_call: LLMFn, metalanguage: str, cando_meta: Dict[str, Any], plan: DomainPlan, max_repair: int = 2) -> ObjectiveCard:
    sys, usr = build_objective_prompt(metalanguage, cando_meta, plan)
    card = validate_or_repair(llm_call, ObjectiveCard, sys, usr, max_repair=max_repair)
    card.gen = LLMGenSpec(system=sys, instruction=usr, constraints=[], examples=None)
    return card


def gen_words_card(llm_call: LLMFn, metalanguage: str, plan: DomainPlan, max_repair: int = 2) -> WordsCard:
    sys, usr = build_words_prompt(metalanguage, plan)
    card = validate_or_repair(llm_call, WordsCard, sys, usr, max_repair=max_repair)
    card.gen = LLMGenSpec(system=sys, instruction=usr, constraints=[], examples=None)
    return card


def gen_grammar_card(llm_call: LLMFn, metalanguage: str, plan: DomainPlan, max_repair: int = 2) -> GrammarPatternsCard:
    sys, usr = build_grammar_prompt(metalanguage, plan)
    card = validate_or_repair(llm_call, GrammarPatternsCard, sys, usr, max_repair=max_repair)
    card.gen = LLMGenSpec(system=sys, instruction=usr, constraints=[], examples=None)
    return card


def gen_words_card_from_extracted(
    llm_call: LLMFn, 
    metalanguage: str, 
    plan: DomainPlan, 
    dialog: DialogueCard,
    reading: ReadingCard,
    extracted_words: List[Dict[str, Any]], 
    max_repair: int = 2
) -> WordsCard:
    """Generate WordsCard from words extracted from dialogue AND reading."""
    sys, usr = build_words_prompt_from_dialogue(metalanguage, plan, dialog, reading, extracted_words)
    card = validate_or_repair(llm_call, WordsCard, sys, usr, max_repair=max_repair)
    card.gen = LLMGenSpec(system=sys, instruction=usr, constraints=[], examples=None)
    return card


def gen_grammar_card_from_extracted(
    llm_call: LLMFn, 
    metalanguage: str, 
    plan: DomainPlan, 
    dialog: DialogueCard,
    reading: ReadingCard,
    extracted_grammar: List[Dict[str, Any]], 
    max_repair: int = 2
) -> GrammarPatternsCard:
    """Generate GrammarPatternsCard from grammar patterns extracted from dialogue AND reading."""
    sys, usr = build_grammar_prompt_from_dialogue(metalanguage, plan, dialog, reading, extracted_grammar)
    card = validate_or_repair(llm_call, GrammarPatternsCard, sys, usr, max_repair=max_repair)
    card.gen = LLMGenSpec(system=sys, instruction=usr, constraints=[], examples=None)
    return card


def gen_dialogue_card(llm_call: LLMFn, metalanguage: str, plan: DomainPlan, max_repair: int = 2) -> DialogueCard:
    sys, usr = build_dialogue_prompt(metalanguage, plan)
    card = validate_or_repair(llm_call, DialogueCard, sys, usr, max_repair=max_repair)
    card.gen = LLMGenSpec(system=sys, instruction=usr, constraints=[], examples=None)
    return card


def gen_reading_card(llm_call: LLMFn, metalanguage: str, cando: Dict[str, Any], plan: DomainPlan, dialog: DialogueCard, max_repair: int = 2) -> ReadingCard:
    """Generate ReadingCard focused on CanDo domain elaboration."""
    sys, usr = build_reading_prompt(metalanguage, cando, plan, dialog)
    card = validate_or_repair(llm_call, ReadingCard, sys, usr, max_repair=max_repair)
    card.gen = LLMGenSpec(system=sys, instruction=usr, constraints=[], examples=None)
    return card


def gen_guided_dialogue_card(llm_call: LLMFn, metalanguage: str, plan: DomainPlan, max_repair: int = 2) -> GuidedDialogueCard:
    sys, usr = build_guided_dialogue_prompt(metalanguage, plan)
    card = validate_or_repair(llm_call, GuidedDialogueCard, sys, usr, max_repair=max_repair)
    card.gen = LLMGenSpec(system=sys, instruction=usr, constraints=[], examples=None)
    return card


def gen_exercises_card(llm_call: LLMFn, metalanguage: str, plan: DomainPlan, max_repair: int = 2) -> ExercisesCard:
    sys, usr = build_exercises_prompt(metalanguage, plan)
    card = validate_or_repair(llm_call, ExercisesCard, sys, usr, max_repair=max_repair)
    card.gen = LLMGenSpec(system=sys, instruction=usr, constraints=[], examples=None)
    return card


def gen_culture_card(llm_call: LLMFn, metalanguage: str, plan: DomainPlan, max_repair: int = 2) -> CultureCard:
    sys, usr = build_culture_prompt(metalanguage, plan)
    card = validate_or_repair(llm_call, CultureCard, sys, usr, max_repair=max_repair)
    card.gen = LLMGenSpec(system=sys, instruction=usr, constraints=[], examples=None)
    return card


def gen_drills_card(llm_call: LLMFn, metalanguage: str, plan: DomainPlan, max_repair: int = 2) -> DrillsCard:
    sys, usr = build_drills_prompt(metalanguage, plan)
    card = validate_or_repair(llm_call, DrillsCard, sys, usr, max_repair=max_repair)
    card.gen = LLMGenSpec(system=sys, instruction=usr, constraints=[], examples=None)
    return card


# ======================================================================================
#                               A S S E M B L Y   H E L P E R S
# ======================================================================================

def assemble_lesson(
    metalanguage: str,
    cando: Dict[str, Any],
    plan: DomainPlan,
    obj: ObjectiveCard,
    words: WordsCard,
    grammar: GrammarPatternsCard,
    dialog: DialogueCard,
    reading: ReadingCard,
    guided: GuidedDialogueCard,
    exercises: ExercisesCard,
    culture: CultureCard,
    drills: DrillsCard,
    lesson_id: Optional[str] = None,
    graph_words: Optional[LookupSpec] = None,
    graph_patterns: Optional[LookupSpec] = None,
) -> LessonRoot:
    """
    Build a LessonRoot from components. Graph bindings are relation-agnostic.
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
        lesson_dialogue=dialog,
        reading_comprehension=reading,
        guided_dialogue=guided,
        exercises=exercises,
        cultural_explanation=culture,
        drills_ai=drills,
    )
    root = LessonRoot(lesson=Lesson(meta=meta, graph_bindings=gb, ui_prefs=UIPrefs(), cards=cards))
    return root


# ======================================================================================
#                                      E X A M P L E
# ======================================================================================

if __name__ == "__main__":
    # ---- Example LLM adapter (placeholder) ----
    # Replace with your own connector (OpenAI, local model, etc.)
    def dummy_llm(system: str, user: str) -> str:
        # This dummy raises to remind you to wire a real LLM.
        raise RuntimeError("Plug in your LLM adapter here. Received prompts are too long to mock sensibly.")

    # Example CanDoDescriptor input (fill from Neo4j)
    cando_input = {
        "uid": "JFまるごと:14",
        "level": "A2",
        "primaryTopic": "旅行と交通",
        "primaryTopicEn": "Travel and Transportation",
        "skillDomain": "産出",
        "type": "活動",
        "descriptionEn": "Can introduce in short, simple terms famous sights, local specialties and other features when giving a friend a tour of one's hometown or other familiar cities.",
        "descriptionJa": "友人に自分の出身地など、よく知っている町を案内するとき、名所や名物などを短い簡単な言葉で紹介することができる。",
        "source": "JFまるごと"
    }
    metalanguage = "en"

    # Outline of usage:
    # plan = gen_domain_plan(dummy_llm, cando_input, metalanguage)
    # obj = gen_objective_card(dummy_llm, metalanguage, {**cando_input, "description": {"en": cando_input["descriptionEn"], "ja": cando_input["descriptionJa"]}}, plan)
    # words = gen_words_card(dummy_llm, metalanguage, plan)
    # grammar = gen_grammar_card(dummy_llm, metalanguage, plan)
    # dialog = gen_dialogue_card(dummy_llm, metalanguage, plan)
    # guided = gen_guided_dialogue_card(dummy_llm, metalanguage, plan)
    # exercises = gen_exercises_card(dummy_llm, metalanguage, plan)
    # culture = gen_culture_card(dummy_llm, metalanguage, plan)
    # drills = gen_drills_card(dummy_llm, metalanguage, plan)
    # lesson = assemble_lesson(metalanguage, cando_input, plan, obj, words, grammar, dialog, guided, exercises, culture, drills)
    # print(lesson.model_dump_json(ensure_ascii=False, indent=2))
    pass

# Rebuild all models to resolve forward references
JPText.model_rebuild()
ImageSpec.model_rebuild()
LLMGenSpec.model_rebuild()
CanDoMeta.model_rebuild()
LessonMeta.model_rebuild()
LookupSpec.model_rebuild()
GraphBindings.model_rebuild()
TextLayerPrefs.model_rebuild()
UIPrefs.model_rebuild()
PlanRole.model_rebuild()
PlanScenario.model_rebuild()
PlanLexBucket.model_rebuild()
PlanGrammarFunction.model_rebuild()
PlanEvaluation.model_rebuild()
DomainPlan.model_rebuild()
ObjectiveCard.model_rebuild()
WordItem.model_rebuild()
WordsCard.model_rebuild()
PatternExample.model_rebuild()
PatternForm.model_rebuild()
GrammarPatternItem.model_rebuild()
GrammarPatternsCard.model_rebuild()
DialogueTurn.model_rebuild()
DialogueCard.model_rebuild()
ComprehensionQA.model_rebuild()
ReadingSection.model_rebuild()
ReadingCard.model_rebuild()
GuidedStage.model_rebuild()
GuidedDialogueCard.model_rebuild()
MatchPair.model_rebuild()
MatchExercise.model_rebuild()
FillBlankExercise.model_rebuild()
OrderExercise.model_rebuild()
ExercisesCard.model_rebuild()
CultureCard.model_rebuild()
SubstitutionSeed.model_rebuild()
SubstitutionDrill.model_rebuild()
PronunciationTarget.model_rebuild()
PronunciationDrill.model_rebuild()
DrillsCard.model_rebuild()
CardsContainer.model_rebuild()
Lesson.model_rebuild()
LessonRoot.model_rebuild()
