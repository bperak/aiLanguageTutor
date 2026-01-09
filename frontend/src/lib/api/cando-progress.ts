/**
 * CanDo Progress API Client
 * ==========================
 *
 * API client functions for CanDo lesson progress tracking and evidence recording
 */

import { apiGet, apiPost } from "../api";

// Types matching backend schemas
export interface CanDoEvidenceRecordRequest {
  can_do_id: string;
  stage: "content" | "comprehension" | "production" | "interaction";
  interaction_type: string;
  is_correct?: boolean;
  user_response?: string;
  attempts_count?: number;
  hint_used?: boolean;
  response_time_seconds?: number;
  confidence_self_reported?: number;
  rubric_scores?: Record<string, any>;
  error_tags?: string[];
  stage_specific_data?: Record<string, any>;
}

export interface CanDoEvidenceRecordResponse {
  interaction_id: string;
  can_do_id: string;
  stage: string;
  mastery_level: number;
  next_review_date?: string;
  message: string;
}

export interface CanDoEvidenceSummary {
  can_do_id: string;
  can_do_title: string;
  total_attempts: number;
  attempts_by_stage: Record<string, number>;
  correct_rate: number;
  mastery_level: number;
  last_attempted?: string;
  next_review_date?: string;
  common_error_tags: string[];
  best_example?: {
    user_response: string;
    stage?: string;
    created_at?: string;
  };
  recent_attempts: Array<{
    stage: string;
    is_correct: boolean;
    user_response?: string;
    created_at?: string;
    rubric_scores?: Record<string, any>;
  }>;
}

export interface CanDoProgress {
  can_do_id: string;
  session_id?: string;
  stages: {
    content?: {
      completed: boolean;
      mastery_level: number;
      last_attempted?: string;
    };
    comprehension?: {
      completed: boolean;
      mastery_level: number;
      last_attempted?: string;
    };
    production?: {
      completed: boolean;
      mastery_level: number;
      last_attempted?: string;
    };
    interaction?: {
      completed: boolean;
      mastery_level: number;
      last_attempted?: string;
    };
  };
  next_recommended_stage?: string;
  all_complete: boolean;
}

export interface CanDoRecommendations {
  next_lesson?: {
    can_do_id: string;
    title: string;
    level?: string;
    topic?: string;
    reason: string;
    mastery_level?: number;
  };
  review_items: Array<{
    can_do_id: string;
    mastery_level: number;
    last_attempted?: string;
  }>;
  focus_areas: Array<{
    stage: string;
    practice_count: number;
  }>;
  common_errors: string[];
  total_lessons_studied: number;
  total_attempts: number;
}

/**
 * Record evidence from a CanDo lesson stage
 */
export const recordCanDoEvidence = async (
  canDoId: string,
  evidence: Omit<CanDoEvidenceRecordRequest, "can_do_id">
): Promise<CanDoEvidenceRecordResponse> => {
  return apiPost<CanDoEvidenceRecordResponse>(
    `/api/v1/cando/lessons/${encodeURIComponent(canDoId)}/evidence/record`,
    { ...evidence, can_do_id: canDoId }
  );
};

/**
 * Get evidence summary for a CanDo lesson
 */
export const getCanDoEvidenceSummary = async (
  canDoId: string,
  limit: number = 10
): Promise<CanDoEvidenceSummary> => {
  return apiGet<CanDoEvidenceSummary>(
    `/api/v1/cando/lessons/${encodeURIComponent(canDoId)}/evidence/summary?limit=${limit}`
  );
};

/**
 * Get stage progress for a CanDo lesson
 */
export const getCanDoProgress = async (
  canDoId: string,
  sessionId?: string
): Promise<CanDoProgress> => {
  const params = sessionId
    ? `?session_id=${encodeURIComponent(sessionId)}`
    : "";
  return apiGet<CanDoProgress>(
    `/api/v1/cando/lessons/${encodeURIComponent(canDoId)}/progress${params}`
  );
};

/**
 * Mark a stage as complete
 */
export const markStageComplete = async (
  canDoId: string,
  stage: "content" | "comprehension" | "production" | "interaction",
  sessionId?: string,
  masteryLevel?: number
): Promise<{
  can_do_id: string;
  session_id?: string;
  stage: string;
  completed: boolean;
  mastery_level: number;
  next_recommended_stage?: string;
  updated_progress: CanDoProgress["stages"];
}> => {
  const params = new URLSearchParams();
  if (sessionId) params.set("session_id", sessionId);
  if (masteryLevel) params.set("mastery_level", masteryLevel.toString());
  const query = params.toString();
  return apiPost(
    `/api/v1/cando/lessons/${encodeURIComponent(canDoId)}/stages/${stage}/complete${query ? "?" + query : ""}`,
    {}
  );
};

/**
 * Get adaptive recommendations
 */
export const getCanDoRecommendations = async (
  limit: number = 5
): Promise<CanDoRecommendations> => {
  return apiGet<CanDoRecommendations>(
    `/api/v1/cando/recommendations?limit=${limit}`
  );
};
