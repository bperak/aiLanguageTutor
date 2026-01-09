/**
 * AI Conversation Practice API Client
 * Handles dynamic dialogue-based grammar pattern practice
 */

import { apiGet, apiPost } from "../api";

// Types
export interface ConversationContext {
  value: string;
  label: string;
  description: string;
}

export interface DialogueTurn {
  speaker: "ai" | "user";
  message: string;
  transliteration?: string; // Romanized version
  translation?: string; // English translation
  feedback?: string;
  user_feedback?: string; // Feedback about user's input
  grammar_focus?: string;
  corrections?: string[];
  hints?: string[];
}

export interface ConversationScenario {
  scenario_id: string;
  pattern_id: string;
  pattern: string;
  context: string;
  situation: string;
  learning_objective: string;
  ai_character: string;
  user_role: string;
  difficulty_level: string;
  initial_dialogue: DialogueTurn[];
}

export interface ConversationScenarioRequest {
  pattern_id: string;
  context: string;
  difficulty_level?: string;
  provider?: string;
  custom_scenario?: string;
}

export interface ConversationTurnRequest {
  scenario_id: string;
  user_message: string;
  provider?: string;
}

// API Functions

/**
 * Get available conversation contexts
 */
export async function getConversationContexts(): Promise<ConversationContext[]> {
  return await apiGet<ConversationContext[]>(
    "/api/v1/grammar/conversation/contexts"
  );
}

/**
 * Start a new AI conversation practice session
 */
export async function startConversationPractice(
  request: ConversationScenarioRequest
): Promise<ConversationScenario> {
  return await apiPost<ConversationScenario>(
    "/api/v1/grammar/conversation/start",
    {
      pattern_id: request.pattern_id,
      context: request.context,
      difficulty_level: request.difficulty_level || "intermediate",
      provider: request.provider || "openai",
      custom_scenario: request.custom_scenario,
    }
  );
}

/**
 * Continue conversation with user input
 */
export async function sendConversationMessage(
  request: ConversationTurnRequest
): Promise<DialogueTurn> {
  return await apiPost<DialogueTurn>("/api/v1/grammar/conversation/turn", {
    scenario_id: request.scenario_id,
    user_message: request.user_message,
    provider: request.provider || "openai",
  });
}

/**
 * Helper function to format dialogue for display
 */
export function formatDialogueHistory(turns: DialogueTurn[]): string {
  return turns
    .map((turn) => `${turn.speaker === "ai" ? "AI" : "You"}: ${turn.message}`)
    .join("\n\n");
}

/**
 * Extract feedback from a dialogue turn
 */
export function extractFeedback(turn: DialogueTurn): {
  hasCorrections: boolean;
  hasHints: boolean;
  feedback: string;
} {
  return {
    hasCorrections: Boolean(turn.corrections && turn.corrections.length > 0),
    hasHints: Boolean(turn.hints && turn.hints.length > 0),
    feedback: [
      turn.feedback,
      turn.corrections?.length
        ? `Corrections: ${turn.corrections.join(", ")}`
        : "",
      turn.hints?.length ? `Hints: ${turn.hints.join(", ")}` : "",
    ]
      .filter(Boolean)
      .join("\n\n"),
  };
}
