/**
 * Grammar Progress API Client
 * ===========================
 *
 * API client functions for grammar pattern progress tracking and SRS integration
 */

import { apiGet, apiPost } from "../api";

// Types matching backend schemas
export interface PatternProgressRequest {
  pattern_id: string;
  grade: "again" | "hard" | "good" | "easy";
  study_time_seconds?: number;
  confidence_self_reported?: number;
}

export interface PatternProgress {
  pattern_id: string;
  pattern_name: string;
  mastery_level: number;
  last_studied?: string;
  next_review_date?: string;
  is_completed: boolean;
  study_count: number;
  ease_factor: number;
  interval_days: number;
}

export interface LearningPathStats {
  total_patterns: number;
  completed_patterns: number;
  average_mastery: number;
  estimated_completion_days: number;
  total_study_time_minutes: number;
}

export interface UserProgressSummary {
  total_patterns_studied: number;
  total_patterns_mastered: number;
  current_streak_days: number;
  weekly_study_minutes: number;
  average_mastery_level: number;
  patterns_due_today: number;
  patterns_overdue: number;
}

/**
 * Record a study session for a grammar pattern
 */
export const recordPatternStudy = async (
  progressData: PatternProgressRequest
): Promise<PatternProgress> => {
  return apiPost<PatternProgress>(
    "/api/v1/grammar/progress/study",
    progressData
  );
};

/**
 * Get user's progress for specific grammar patterns
 */
export const getUserPatternProgress = async (
  params: {
    pattern_ids?: string[];
    include_completed?: boolean;
    limit?: number;
  } = {}
): Promise<PatternProgress[]> => {
  const searchParams = new URLSearchParams();
  if (params.pattern_ids?.length) {
    params.pattern_ids.forEach((id) => searchParams.append("pattern_ids", id));
  }
  if (params.include_completed !== undefined) {
    searchParams.set("include_completed", params.include_completed.toString());
  }
  if (params.limit) {
    searchParams.set("limit", params.limit.toString());
  }
  const query = searchParams.toString();
  const url = `/api/v1/grammar/progress/patterns${query ? "?" + query : ""}`;
  return apiGet<PatternProgress[]>(url);
};

/**
 * Get patterns that are due for review
 */
export const getPatternsDueForReview = async (
  params: {
    include_overdue?: boolean;
    limit?: number;
  } = {}
): Promise<PatternProgress[]> => {
  const searchParams = new URLSearchParams();
  if (params.include_overdue !== undefined) {
    searchParams.set("include_overdue", params.include_overdue.toString());
  }
  if (params.limit) {
    searchParams.set("limit", params.limit.toString());
  }
  const query = searchParams.toString();
  const url = `/api/v1/grammar/progress/due${query ? "?" + query : ""}`;
  return apiGet<PatternProgress[]>(url);
};

/**
 * Get comprehensive user progress summary
 */
export const getUserProgressSummary = async (): Promise<UserProgressSummary> => {
  return apiGet<UserProgressSummary>("/api/v1/grammar/progress/summary");
};

/**
 * Get statistics for a specific learning path
 */
export const getLearningPathStats = async (
  patternIds: string[]
): Promise<LearningPathStats> => {
  const searchParams = new URLSearchParams();
  patternIds.forEach((id) => searchParams.append("pattern_ids", id));
  const query = searchParams.toString();
  const url = `/api/v1/grammar/progress/learning-path-stats?${query}`;
  return apiGet<LearningPathStats>(url);
};

/**
 * Schedule SRS review using the SRS service
 */
export const scheduleSRSReview = async (params: {
  item_id: string;
  last_interval_days: number;
  grade: "again" | "hard" | "good" | "easy";
}): Promise<{
  item_id: string;
  next_interval_days: number;
  next_review_at: string;
}> => {
  return apiPost("/api/v1/srs/schedule", params);
};

/**
 * Combined function to record study and update SRS
 */
export const recordStudyWithSRS = async (
  patternId: string,
  grade: "again" | "hard" | "good" | "easy",
  studyTimeSeconds?: number,
  confidence?: number
): Promise<PatternProgress> => {
  try {
    // Record the study session (which handles SRS internally)
    const progress = await recordPatternStudy({
      pattern_id: patternId,
      grade,
      study_time_seconds: studyTimeSeconds,
      confidence_self_reported: confidence,
    });
    return progress;
  } catch (error) {
    console.error("Error recording study session:", error);
    throw error;
  }
};

/**
 * Utility function to get SRS data for pattern cards
 */
export const getPatternSRSData = (progress: PatternProgress) => {
  return {
    mastery_level: progress.mastery_level,
    next_review_date: progress.next_review_date || "",
    interval_days: progress.interval_days,
    ease_factor: progress.ease_factor,
    last_studied: progress.last_studied,
  };
};

/**
 * Check if a pattern needs review today
 */
export const isPatternDueForReview = (progress: PatternProgress): boolean => {
  if (!progress.next_review_date) return false;
  const today = new Date().toISOString().split("T")[0];
  return progress.next_review_date <= today;
};

/**
 * Get days until next review
 */
export const getDaysUntilReview = (progress: PatternProgress): number => {
  if (!progress.next_review_date) return 0;
  const today = new Date();
  const reviewDate = new Date(progress.next_review_date);
  const diffTime = reviewDate.getTime() - today.getTime();
  const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
  return diffDays;
};

// === GRAMMAR EVIDENCE TRACKING ===

export interface EvidenceRecordRequest {
  pattern_id: string;
  stage: "presentation" | "comprehension" | "production" | "interaction";
  interaction_type: string;
  is_correct?: boolean;
  user_response?: string;
  attempts_count?: number;
  hint_used?: boolean;
  response_time_seconds?: number;
  confidence_self_reported?: number;
  rubric_scores?: {
    pattern_used?: boolean;
    form_accurate?: boolean;
    meaning_matches?: boolean;
  };
  error_tags?: string[];
  stage_specific_data?: Record<string, any>;
}

export interface EvidenceRecordResponse {
  interaction_id: string;
  pattern_id: string;
  stage: string;
  mastery_level: number;
  next_review_date?: string;
  message: string;
}

export interface EvidenceSummary {
  pattern_id: string;
  pattern_name: string;
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

/**
 * Record evidence of grammar learning from any stage
 */
export const recordGrammarEvidence = async (
  evidence: EvidenceRecordRequest
): Promise<EvidenceRecordResponse> => {
  return apiPost<EvidenceRecordResponse>(
    "/api/v1/grammar/evidence/record",
    evidence
  );
};

/**
 * Get evidence summary for a grammar pattern
 */
export const getGrammarEvidenceSummary = async (
  patternId: string,
  limit: number = 10
): Promise<EvidenceSummary> => {
  return apiGet<EvidenceSummary>(
    `/api/v1/grammar/evidence/summary?pattern_id=${encodeURIComponent(
      patternId
    )}&limit=${limit}`
  );
};
