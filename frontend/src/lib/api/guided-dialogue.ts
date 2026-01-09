/**
 * API client for guided dialogue interactions
 */

import type {
  FlushGuidedStateResponse,
  GuidedTurnResponse,
} from "@/types/lesson-root";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface SendGuidedTurnParams {
  session_id: string;
  stage_idx: number;
  learner_input: string;
}

export interface GetGuidedInitialMessageParams {
  session_id: string;
  stage_idx: number;
}

export interface GuidedInitialMessageResponse {
  status: string;
  message: string;
  transliteration?: string | null;
  translation?: string | null;
  feedback?: string;
  grammar_focus?: string;
  hints?: string[];
}

/**
 * Send a learner turn in guided dialogue and get AI feedback
 */
export async function sendGuidedTurn(
  params: SendGuidedTurnParams
): Promise<GuidedTurnResponse> {
  const response = await fetch(`${API_BASE}/api/v1/cando/lessons/guided/turn`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    credentials: "include",
    body: JSON.stringify(params),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({
      detail: "Unknown error",
    }));
    throw new Error(
      error.detail || `Failed to send guided turn: ${response.statusText}`
    );
  }

  return response.json();
}

/**
 * Get initial AI greeting message for guided dialogue with full meta structure
 */
export async function getGuidedInitialMessage(
  params: GetGuidedInitialMessageParams
): Promise<GuidedInitialMessageResponse> {
  try {
    const response = await fetch(
      `${API_BASE}/api/v1/cando/lessons/guided/initial-message`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        credentials: "include",
        body: JSON.stringify(params),
      }
    );

    if (!response.ok) {
      let errorDetail = "Unknown error";
      try {
        const error = await response.json();
        errorDetail =
          error.detail ||
          error.message ||
          `HTTP ${response.status}: ${response.statusText}`;
      } catch {
        errorDetail = `HTTP ${response.status}: ${response.statusText}`;
      }

      // Log but don't throw for 404/400 errors - these are expected in some cases
      if (response.status === 404 || response.status === 400) {
        console.warn(
          "Initial message endpoint returned error (non-critical):",
          errorDetail
        );
        // Return a default response instead of throwing
        return {
          status: "error",
          message: "こんにちは！よろしくお願いします。",
          translation: "Hello! Nice to meet you.",
          feedback:
            "Let's start practicing. Use the hints above to guide your response.",
        };
      }

      console.error("API Error:", errorDetail, "Status:", response.status);
      throw new Error(errorDetail);
    }

    return response.json();
  } catch (error) {
    // Only log network errors, not expected API errors
    if (error instanceof TypeError && error.message === "Failed to fetch") {
      console.warn(
        "Network error fetching initial message (backend may be unavailable):",
        error.message
      );
      // Return default response for network errors
      return {
        status: "error",
        message: "こんにちは！よろしくお願いします。",
        translation: "Hello! Nice to meet you.",
        feedback:
          "Let's start practicing. Use the hints above to guide your response.",
      };
    }

    // Re-throw other errors
    throw error;
  }
}

/**
 * Flush/reset guided dialogue state for a session
 */
export async function flushGuidedState(
  sessionId: string
): Promise<FlushGuidedStateResponse> {
  const response = await fetch(
    `${API_BASE}/api/v1/cando/lessons/guided/flush?session_id=${encodeURIComponent(
      sessionId
    )}`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      credentials: "include",
    }
  );

  if (!response.ok) {
    const error = await response.json().catch(() => ({
      detail: "Unknown error",
    }));
    throw new Error(
      error.detail || `Failed to flush guided state: ${response.statusText}`
    );
  }

  return response.json();
}
