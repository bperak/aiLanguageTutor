const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface ProductionEvaluatorParams {
  session_id: string;
  can_do_id: string;
  stage_idx: number;
  learner_input: string;
}

export interface ProductionEvaluatorResponse {
  status: string;
  ai_response: string;
  transliteration?: string | null;
  translation?: string | null;
  feedback: {
    teaching_direction?: string;
    rubric_scores: {
      pattern_correctness?: number;
      fluency?: number;
      content_relevance?: number;
    };
  };
  stage_progress: {
    current_stage: number;
    total_stages: number;
  };
}

export async function evaluateProduction(
  params: ProductionEvaluatorParams
): Promise<ProductionEvaluatorResponse> {
  const response = await fetch(
    `${API_BASE}/api/v1/cando/lessons/production/ai-evaluator/evaluate`,
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
      error.detail || `Failed to evaluate production: ${response.statusText}`
    );
  }

  return response.json();
}
