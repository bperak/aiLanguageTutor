const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface ComprehensionTutorTurnParams {
  session_id: string;
  can_do_id: string;
  stage_idx: number;
  learner_input: string;
}

export interface ComprehensionTutorTurnResponse {
  status: string;
  ai_response: string;
  transliteration?: string | null;
  translation?: string | null;
  feedback: {
    comprehension_score: number;
    keywords_found: string[];
    teaching_direction?: string;
  };
  stage_progress: {
    current_stage: number;
    total_stages: number;
  };
}

export async function sendComprehensionTutorTurn(
  params: ComprehensionTutorTurnParams
): Promise<ComprehensionTutorTurnResponse> {
  const response = await fetch(
    `${API_BASE}/api/v1/cando/lessons/comprehension/ai-tutor/turn`,
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
    const error = await response.json().catch(() => ({
      detail: "Unknown error",
    }));
    throw new Error(
      error.detail ||
        `Failed to send comprehension tutor turn: ${response.statusText}`
    );
  }

  return response.json();
}
