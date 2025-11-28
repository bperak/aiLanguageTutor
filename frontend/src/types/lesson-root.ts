/**
 * TypeScript type definitions for LessonRoot structure
 * Mirrors backend Pydantic models from canDo_creation_new.py
 */

export interface JPText {
  std: string
  furigana: string
  romaji: string
  translation: Record<string, string> // e.g., { en: "...", ja: "..." }
}

export interface ImageSpec {
  prompt: string
  style?: string
  size?: string
  negative_prompt?: string | null
  seed?: number | null
  path?: string | null  // Relative path to generated image file
}

export interface LLMGenSpec {
  system: string
  instruction: string
  constraints: string[]
  examples?: string | null
}

export interface CanDoMeta {
  uid: string
  level: string
  primaryTopic_ja: string
  primaryTopic_en: string
  skillDomain_ja: string
  type_ja: string
  description: {
    en: string
    ja: string
  }
  source: string
  titleEn?: string
  titleJa?: string
}

export interface LessonMeta {
  lesson_id: string
  metalanguage: string
  can_do: CanDoMeta
}

export interface LookupSpec {
  by_cypher?: string | null
  by_keys: string[]
  resolve_label?: string | null
  resolve_property?: string | null
}

export interface GraphBindings {
  words: LookupSpec
  grammar_patterns: LookupSpec
}

export interface TextLayerPrefs {
  std: boolean
  furigana: boolean
  romaji: boolean
  translation: boolean
}

export interface UIPrefs {
  text_layers_default: TextLayerPrefs
}

export interface PlanRole {
  label: string
  register: string
}

export interface PlanScenario {
  name: string
  setting: string
  roles: PlanRole[]
}

export interface PlanLexBucket {
  name: string
  items: string[]
}

export interface PlanGrammarFunction {
  id: string
  label: string
  pattern_ja: string
  slots: string[]
  notes_en: string
}

export interface PlanEvaluation {
  success_criteria: string[]
  discourse_markers: string[]
}

export interface DomainPlan {
  uid: string
  level: "A1" | "A2" | "B1" | "B2" | "C1" | "C2"
  communicative_function_en: string
  communicative_function_ja: string
  scenarios: PlanScenario[]
  lex_buckets: PlanLexBucket[]
  grammar_functions: PlanGrammarFunction[]
  evaluation: PlanEvaluation
  cultural_themes_en: string[]
  cultural_themes_ja: string[]
}

export interface ObjectiveCard {
  type: "ObjectiveCard"
  title: JPText
  body: JPText
  success_criteria: string[]
  outcomes: string[]
  gen?: LLMGenSpec
}

export interface WordItem {
  id: string
  neo4j_id?: string | null
  jp: JPText
  tags: string[]
  image?: ImageSpec | null
}

export interface WordsCard {
  type: "WordsCard"
  items: WordItem[]
  ui_layers_override?: TextLayerPrefs | null
  gen?: LLMGenSpec
}

export interface PatternExample {
  ja: JPText
  audio_ref?: string | null
}

export interface PatternForm {
  ja: JPText
}

export interface GrammarPatternItem {
  id: string
  neo4j_id?: string | null
  classification?: string | null
  form: PatternForm
  explanation: JPText
  slots: string[]
  examples: PatternExample[]
  image?: ImageSpec | null
}

export interface GrammarPatternsCard {
  type: "GrammarPatternsCard"
  patterns: GrammarPatternItem[]
  gen?: LLMGenSpec
}

export interface DialogueTurn {
  speaker: string
  ja: JPText
  audio_ref?: string | null
}

export interface DialogueCard {
  type: "DialogueCard"
  title: JPText
  setting?: string | null
  characters?: string[] | null
  turns: DialogueTurn[]
  notes_en?: string | null
  image?: ImageSpec | null
  gen?: LLMGenSpec
}

export interface ComprehensionQA {
  q: JapaneseText
  a: JapaneseText
  evidenceSpan?: string | null
}

export interface ReadingSection {
  title: JapaneseText
  content: JapaneseText
  comprehension: ComprehensionQA[]
}

export interface ReadingCard {
  type: "ReadingCard"
  title: Record<string, string>
  reading: ReadingSection
  notes_en?: string | null
  image?: ImageSpec | null
  gen?: LLMGenSpec | null
}

export interface GuidedStage {
  stage_id: string
  goal_en: string
  expected_patterns: string[]
  hints: JPText[]
  learner_turn_schema: {
    min_words: number
    max_words: number
    allow_romaji: boolean
  }
  ai_feedback: {
    rubric: string[]
    feedback_prompt: string
  }
}

export interface GuidedDialogueCard {
  type: "GuidedDialogueCard"
  mode: string
  stages: GuidedStage[]
  gen?: LLMGenSpec
}

export interface MatchPair {
  left: JPText
  right_options_en: string[]
  answer_en: string
}

export interface MatchExercise {
  exercise_type: "match"
  id: string
  instructions: JPText
  pairs: MatchPair[]
}

export interface FillBlankExercise {
  exercise_type: "fill_blank"
  id: string
  item: JPText
  answer_key_en: string[]
}

export interface OrderExercise {
  exercise_type: "order"
  id: string
  instructions: JPText
  segments_ja: string[]
  correct_order: number[]
}

export type Exercise = MatchExercise | FillBlankExercise | OrderExercise

export interface ExercisesCard {
  type: "ExercisesCard"
  items: Exercise[]
  gen?: LLMGenSpec
}

export interface CultureCard {
  type: "CultureCard"
  title: JPText
  body: JPText
  image?: ImageSpec | null
  gen?: LLMGenSpec
}

export interface SubstitutionSeed {
  place: string
  specialty_en: string
}

export interface SubstitutionDrill {
  drill_type: "substitution"
  id: string
  pattern_ref: string
  prompt_template: {
    template: string
  }
  slots: string[]
  seed_items: SubstitutionSeed[]
  ai_support: {
    prompt: string
  }
}

export interface PronunciationTarget {
  ja: string
  romaji: string
}

export interface PronunciationDrill {
  drill_type: "pronunciation"
  id: string
  focus: PronunciationTarget[]
  ai_support: {
    prompt: string
  }
}

export type Drill = SubstitutionDrill | PronunciationDrill

export interface DrillsCard {
  type: "DrillsCard"
  drills: Drill[]
  gen?: LLMGenSpec
}

export interface CardsContainer {
  objective: ObjectiveCard
  words: WordsCard
  grammar_patterns: GrammarPatternsCard
  lesson_dialogue: DialogueCard
  reading_comprehension: ReadingCard
  guided_dialogue: GuidedDialogueCard
  exercises: ExercisesCard
  cultural_explanation: CultureCard
  drills_ai: DrillsCard
}

export interface Lesson {
  meta: LessonMeta
  graph_bindings: GraphBindings
  ui_prefs: UIPrefs
  cards: CardsContainer
}

export interface LessonRoot {
  lesson: Lesson
}

// API Response types

export interface CompileLessonV2Response {
  status: string
  lesson_id: number
  version: number
  can_do_id: string
  message: string
  duration_sec: number
}

export interface GuidedTurnResponse {
  status: string
  ai_response: string
  transliteration?: string | null
  translation?: string | null
  feedback: {
    pattern_matched: boolean
    word_count: number
    word_count_ok: boolean
    goals_met: boolean
    teaching_direction?: string | null
  }
  stage_progress: {
    current_stage: number
    new_stage: number
    total_stages: number
    advanced: boolean
    completed: boolean
  }
  current_stage_goal: string
}

export interface FlushGuidedStateResponse {
  status: string
  session_id: string
  flushed_at: string
  message: string
}

