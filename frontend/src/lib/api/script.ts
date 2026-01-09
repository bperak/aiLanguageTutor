/**
 * API functions for Script learning feature.
 */

import { apiGet, apiPost } from "../api";

export interface ScriptItem {
  id: string;
  script_type: "hiragana" | "katakana";
  kana: string;
  romaji: string;
  romaji_aliases: string[];
  tags: string[];
  group?: string;
}

export interface ScriptPracticeCheckRequest {
  item_id: string;
  mode: "kana_to_romaji" | "romaji_to_kana" | "mcq";
  user_answer: string;
  choices?: string[];
}

export interface ScriptPracticeCheckResponse {
  item_id: string;
  mode: string;
  is_correct: boolean;
  expected_answer: string;
  accepted_answers: string[];
  feedback: string;
}

export interface ScriptProgressSummary {
  total_attempts: number;
  correct_rate: number;
  items_practiced: number;
  mastered_items: number;
}

export interface ScriptItemProgress {
  item_id: string;
  last_attempted: string | null;
  attempts: number;
  correct_rate: number;
  mastery_level: number;
}

/**
 * Get script items with optional filtering.
 */
export async function getScriptItems(params?: {
  script_type?: "hiragana" | "katakana";
  tags?: string[];
  search?: string;
  limit?: number;
  offset?: number;
}): Promise<ScriptItem[]> {
  const queryParams = new URLSearchParams();
  if (params?.script_type) {
    queryParams.append("script_type", params.script_type);
  }
  if (params?.tags) {
    params.tags.forEach((tag) => queryParams.append("tags", tag));
  }
  if (params?.search) queryParams.append("search", params.search);
  if (params?.limit) queryParams.append("limit", String(params.limit));
  if (params?.offset) queryParams.append("offset", String(params.offset));
  return apiGet<ScriptItem[]>(`/api/v1/script/items?${queryParams.toString()}`);
}

/**
 * Get a specific script item by ID.
 */
export async function getScriptItem(itemId: string): Promise<ScriptItem> {
  return apiGet<ScriptItem>(
    `/api/v1/script/items/${encodeURIComponent(itemId)}`
  );
}

/**
 * Check a script practice answer.
 */
export async function checkScriptAnswer(
  request: ScriptPracticeCheckRequest
): Promise<ScriptPracticeCheckResponse> {
  return apiPost<ScriptPracticeCheckResponse>(
    "/api/v1/script/practice/check",
    request
  );
}

/**
 * Get script progress summary.
 */
export async function getScriptProgressSummary(
  script_type?: "hiragana" | "katakana"
): Promise<ScriptProgressSummary> {
  const queryParams = new URLSearchParams();
  if (script_type) queryParams.append("script_type", script_type);
  return apiGet<ScriptProgressSummary>(
    `/api/v1/script/progress/summary?${queryParams.toString()}`
  );
}

/**
 * Get progress for individual script items.
 */
export async function getScriptItemProgress(params?: {
  script_type?: "hiragana" | "katakana";
  limit?: number;
  offset?: number;
}): Promise<ScriptItemProgress[]> {
  const queryParams = new URLSearchParams();
  if (params?.script_type) {
    queryParams.append("script_type", params.script_type);
  }
  if (params?.limit) queryParams.append("limit", String(params.limit));
  if (params?.offset) queryParams.append("offset", String(params.offset));
  return apiGet<ScriptItemProgress[]>(
    `/api/v1/script/progress/items?${queryParams.toString()}`
  );
}
