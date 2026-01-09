/**
 * TypeScript
type definitions
for LessonRoot structure
 * Mirrors backend Pydantic models from canDo_creation_new.py
 */

export interface JPText {
  /**
   * Preferred v2 format.
   */
  std?: string;
  /**
   * Legacy format still present in some generated content.
   */
  kanji?: string;
  furigana?: string;
  romaji?: string;
  /**
   * Some generators produce a string; others produce {en, ja}.
   * e.g., { en: "...", ja: "..." }
   */
  translation?: Record<string, string> | string;

  /**
   * Legacy/alternate bilingual format used in some places: { en: "...", ja: "..." }
   */
  en?: string;
  ja?: string;
}
export interface ImageSpec {
  prompt: string;
  style?: string;
  size?: string;
  negative_prompt?: string | null;
  seed?: number | null;
  path?: string | null; // Relative path to generated image file
}
export interface LLMGenSpec {
  system: string;
  instruction: string;
  constraints: string[];
  examples?: string | null;
}
export interface CanDoMeta {
  uid: string;
  level: string;
  primaryTopic_ja: string;
  primaryTopic_en: string;
  skillDomain_ja: string;
  type_ja: string;
  description: {
    en: string;
    ja: string;
  };
  source: string;
  titleEn?: string;
  titleJa?: string;
}
export interface LessonMeta {
  generation_status?: {
    content?: string;
    comprehension?: string;
    production?: string;
    interaction?: string;
  };
  errors?: Record<
    string,
    {
      type?: string;
      message?: string;
      retryable?: boolean;
      timestamp?: number;
    }
  >;
  prelesson_kit_available?: boolean;
  prelesson_kit_usage?: {
    words?: {
      used?: string[];
      count?: number;
      total?: number;
      required?: number;
      meets_requirement?: boolean;
    };
    grammar?: {
      used?: string[];
      count?: number;
      total?: number;
      required?: number;
      meets_requirement?: boolean;
    };
    phrases?: {
      used?: string[];
      count?: number;
      total?: number;
      required?: number;
      meets_requirement?: boolean;
    };
    all_requirements_met?: boolean;
    usage_percentage?: number;
  };
  lesson_id: string;
  metalanguage: string;
  can_do: CanDoMeta;
}
export interface LookupSpec {
  by_cypher?: string | null;
  by_keys: string[];
  resolve_label?: string | null;
  resolve_property?: string | null;
}
export interface GraphBindings {
  words: LookupSpec;
  grammar_patterns: LookupSpec;
}
export interface TextLayerPrefs {
  std: boolean;
  furigana: boolean;
  romaji: boolean;
  translation: boolean;
}
export interface UIPrefs {
  text_layers_default: TextLayerPrefs;
}
export interface PlanRole {
  label: string;
  register: string;
}
export interface PlanScenario {
  name: string;
  setting: string;
  roles: PlanRole[];
}
export interface PlanLexBucket {
  name: string;
  items: string[];
}
export interface PlanGrammarFunction {
  id: string;
  label: string;
  pattern_ja: string;
  slots: string[];
  notes_en: string;
}
export interface PlanEvaluation {
  success_criteria: string[];
  discourse_markers: string[];
}
export interface DomainPlan {
  uid: string;
  level: "A1" | "A2" | "B1" | "B2" | "C1" | "C2";
  communicative_function_en: string;
  communicative_function_ja: string;
  scenarios: PlanScenario[];
  lex_buckets: PlanLexBucket[];
  grammar_functions: PlanGrammarFunction[];
  evaluation: PlanEvaluation;
  cultural_themes_en: string[];
  cultural_themes_ja: string[];
}
export interface ObjectiveCard {
  type: "ObjectiveCard";
  title: JPText;
  body: JPText;
  success_criteria: string[];
  outcomes: string[];
  gen?: LLMGenSpec;
}
export interface WordItem {
  id: string;
  neo4j_id?: string | null;
  jp: JPText;
  tags: string[];
  image?: ImageSpec | null;
}
export interface WordsCard {
  type: "WordsCard";
  items: WordItem[];
  ui_layers_override?: TextLayerPrefs | null;
  gen?: LLMGenSpec;
}
export interface PatternExample {
  ja: JPText;
  audio_ref?: string | null;
}
export interface PatternForm {
  ja: JPText;
}
export interface GrammarPatternItem {
  id: string;
  neo4j_id?: string | null;
  classification?: string | null;
  form: PatternForm;
  explanation: JPText;
  slots: string[];
  examples: PatternExample[];
  image?: ImageSpec | null;
}
export interface GrammarPatternsCard {
  type: "GrammarPatternsCard";
  patterns: GrammarPatternItem[];
  gen?: LLMGenSpec;
}
export interface DialogueTurn {
  speaker: string;
  ja: JPText;
  audio_ref?: string | null;
}
export interface DialogueCard {
  type: "DialogueCard";
  title: JPText;
  setting?: string | null;
  characters?: string[] | null;
  turns: DialogueTurn[];
  notes_en?: string | null;
  image?: ImageSpec | null;
  gen?: LLMGenSpec;
}
export interface ComprehensionQA {
  q: JPText;
  a: JPText;
  evidenceSpan?: string | null;
}
export interface ReadingSection {
  title: JPText;
  content: JPText;
  comprehension: ComprehensionQA[];
}
export interface ReadingCard {
  type: "ReadingCard";
  title: Record<string, string>;
  reading: ReadingSection;
  notes_en?: string | null;
  image?: ImageSpec | null;
  gen?: LLMGenSpec | null;
}
export interface GuidedStage {
  stage_id: string;
  goal_en: string;
  expected_patterns: string[];
  hints: JPText[];
  learner_turn_schema: {
    min_words: number;
    max_words: number;
    allow_romaji: boolean;
  };
  ai_feedback: {
    rubric: string[];
    feedback_prompt: string;
  };
}
export interface GuidedDialogueCard {
  type: "GuidedDialogueCard";
  mode: string;
  stages: GuidedStage[];
  gen?: LLMGenSpec;
}
export interface MatchPair {
  left: JPText;
  right_options_en: string[];
  answer_en: string;
}
export interface MatchExercise {
  exercise_type: "match";
  id: string;
  instructions: JPText;
  pairs: MatchPair[];
}
export interface FillBlankExercise {
  exercise_type: "fill_blank";
  id: string;
  item: JPText;
  answer_key_en: string[];
}
export interface OrderExercise {
  exercise_type: "order";
  id: string;
  instructions: JPText;
  segments_ja: string[];
  correct_order: number[];
}
export type Exercise = MatchExercise | FillBlankExercise | OrderExercise;
export interface ExercisesCard {
  type: "ExercisesCard";
  items: Exercise[];
  gen?: LLMGenSpec;
}
export interface CultureCard {
  type: "CultureCard";
  title: JPText;
  body: JPText;
  image?: ImageSpec | null;
  gen?: LLMGenSpec;
}
export interface SubstitutionSeed {
  place: string;
  specialty_en: string;
}
export interface SubstitutionDrill {
  drill_type: "substitution";
  id: string;
  pattern_ref: string;
  prompt_template: {
    template: string;
  };
  slots: string[];
  seed_items: SubstitutionSeed[];
  ai_support: {
    prompt: string;
  };
}
export interface PronunciationTarget {
  ja: string;
  romaji: string;
}
export interface PronunciationDrill {
  drill_type: "pronunciation";
  id: string;
  focus: PronunciationTarget[];
  ai_support: {
    prompt: string;
  };
}
export type Drill = SubstitutionDrill | PronunciationDrill;
export interface DrillsCard {
  type: "DrillsCard";
  drills: Drill[];
  gen?: LLMGenSpec;
}

// New stage-organized card types
export interface FormulaicExpressionItem {
  id: string;
  expression: JPText;
  context: Record<string, string>;
  examples: JPText[];
  tags: string[];
  image?: ImageSpec;
}
export interface FormulaicExpressionsCard {
  type: "FormulaicExpressionsCard";
  title: Record<string, string>;
  items: FormulaicExpressionItem[];
  gen?: LLMGenSpec;
}
export interface ComprehensionExerciseItem {
  exercise_type:
    | "reading_qa"
    | "listening"
    | "matching"
    | "ordering"
    | "gap_fill"
    | "information_extraction"
    | "picture_text_matching"
    | "context_inference";
  id: string;
  instructions: Record<string, string>;
  question?: JPText;
  answer?: JPText;
  options?: JPText[];
  correct_answer?: string | number | number[];
  pairs?: any[]; // MatchPair[]
  segments?: string[];
  correct_order?: number[];
  text_passage?: JPText;
  image?: ImageSpec;
  gen?: LLMGenSpec;
}
export interface ComprehensionExercisesCard {
  type: "ComprehensionExercisesCard";
  title: Record<string, string>;
  items: ComprehensionExerciseItem[];
  gen?: LLMGenSpec;
}
export interface AIComprehensionStage {
  stage_id: string;
  goal_en: string;
  question: JPText;
  expected_answer_keywords: string[];
  hints: Array<Record<string, string>>;
  ai_feedback: Record<string, any>;
}
export interface AIComprehensionTutorCard {
  type: "AIComprehensionTutorCard";
  title: Record<string, string>;
  stages: AIComprehensionStage[];
  gen?: LLMGenSpec;
}
export interface ProductionExerciseItem {
  exercise_type:
    | "slot_fill"
    | "transformation"
    | "sentence_construction"
    | "translation"
    | "writing"
    | "role_play_completion"
    | "sentence_completion"
    | "dialogue_completion"
    | "personalization"
    | "sentence_reordering"
    | "form_focused";
  id: string;
  instructions: Record<string, string>;
  prompt?: JPText | string;
  template?: JPText;
  source_sentence?: JPText;
  target_language?: string;
  scrambled_words?: string[];
  grammar_pattern_id?: string;
  expected_elements?: string[];
  rubric?: Record<string, any>;
  gen?: LLMGenSpec;
}
export interface ProductionExercisesCard {
  type: "ProductionExercisesCard";
  title: Record<string, string>;
  items: ProductionExerciseItem[];
  gen?: LLMGenSpec;
}
export interface AIProductionEvaluationStage {
  stage_id: string;
  goal_en: string;
  exercise_type: string;
  expected_patterns: string[];
  rubric: Record<string, any>;
  hints: Array<Record<string, string>>;
  adaptive_difficulty?: Record<string, any>;
}
export interface AIProductionEvaluatorCard {
  type: "AIProductionEvaluatorCard";
  title: Record<string, string>;
  stages: AIProductionEvaluationStage[];
  gen?: LLMGenSpec;
}
export interface InteractiveDialogueCard {
  type: "InteractiveDialogueCard";
  title: Record<string, string>;
  scenarios: Array<Record<string, any>>;
  stages: any[]; // GuidedStage[]
  gen?: LLMGenSpec;
}
export interface InteractionActivityItem {
  activity_type:
    | "conversation_scenario"
    | "information_gap"
    | "negotiation"
    | "collaborative_task"
    | "simulation"
    | "problem_solving"
    | "opinion_exchange"
    | "decision_making"
    | "role_play"
    | "free_conversation";
  id: string;
  title: Record<string, string>;
  instructions: Record<string, string>;
  scenario?: Record<string, any>;
  roles?: string[];
  goals?: string[];
  gen?: LLMGenSpec;
}
export interface InteractionActivitiesCard {
  type: "InteractionActivitiesCard";
  title: Record<string, string>;
  items: InteractionActivityItem[];
  gen?: LLMGenSpec;
}
export interface AIScenarioStage {
  stage_id: string;
  scenario_type: string;
  goal_en: string;
  context: Record<string, string>;
  roles: Array<Record<string, string>>;
  conversation_flow: Array<Record<string, any>>;
  evaluation_criteria: Record<string, any>;
  cultural_notes?: Array<Record<string, string>>;
}
export interface AIScenarioManagerCard {
  type: "AIScenarioManagerCard";
  title: Record<string, string>;
  stages: AIScenarioStage[];
  gen?: LLMGenSpec;
}
export interface CardsContainer {
  // Content stage cards
  objective: ObjectiveCard;
  words: WordsCard;
  grammar_patterns: GrammarPatternsCard;
  formulaic_expressions?: FormulaicExpressionsCard;
  lesson_dialogue: DialogueCard;
  cultural_explanation: CultureCard;
  // Comprehension stage cards
  reading_comprehension: ReadingCard;
  comprehension_exercises?: ComprehensionExercisesCard;
  ai_comprehension_tutor?: AIComprehensionTutorCard;
  // Production stage cards
  guided_dialogue: GuidedDialogueCard;
  production_exercises?: ProductionExercisesCard;
  ai_production_evaluator?: AIProductionEvaluatorCard;
  // Interaction stage cards
  interactive_dialogue?: InteractiveDialogueCard;
  interaction_activities?: InteractionActivitiesCard;
  ai_scenario_manager?: AIScenarioManagerCard;
  // Legacy cards (for backward compatibility)
  exercises?: ExercisesCard;
  drills_ai?: DrillsCard;
}
export interface Lesson {
  meta: LessonMeta;
  graph_bindings: GraphBindings;
  ui_prefs: UIPrefs;
  cards: CardsContainer;
}
export interface LessonRoot {
  lesson: Lesson;
}

// API Response types
export interface CompileLessonV2Response {
  status: string;
  lesson_id: number;
  version: number;
  can_do_id: string;
  message: string;
  duration_sec: number;
}
export interface GuidedTurnResponse {
  status: string;
  ai_response: string;
  transliteration?: string | null;
  translation?: string | null;
  feedback: {
    pattern_matched: boolean;
    word_count: number;
    word_count_ok: boolean;
    goals_met: boolean;
    teaching_direction?: string | null;
  };
  stage_progress: {
    current_stage: number;
    new_stage: number;
    total_stages: number;
    advanced: boolean;
    completed: boolean;
  };
  current_stage_goal: string;
}
export interface FlushGuidedStateResponse {
  status: string;
  session_id: string;
  flushed_at: string;
  message: string;
}
