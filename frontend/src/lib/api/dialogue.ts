export type DialogueTurnPayload = {
  speaker: string;
  japanese: any;
  notes?: string;
};

function getDialogueApiBaseUrl(): string {
  /**
   * Prefer same-origin proxy routes in the browser (`/api/v1/...`) so requests go through
   * Next.js' backend proxy route (fast, internal Docker networking).
   *
   * On the server (Node/SSR), call the backend directly via `BACKEND_URL`.
   */
  if (typeof window !== "undefined") return "";
  return process.env.BACKEND_URL || "http://backend:8000";
}

export async function extendDialogue(payload: {
  can_do_id: string;
  setting: string;
  dialogue_turns?: DialogueTurnPayload[];
  characters?: string[];
  vocabulary?: string[];
  grammar_patterns?: string[];
  num_turns?: number;
}): Promise<any> {
  const base = getDialogueApiBaseUrl();
  // Send dialogue_turns as empty array if none provided (backend expects list)
  const body: any = {
    can_do_id: payload.can_do_id,
    setting: payload.setting || "",
    dialogue_turns: payload.dialogue_turns || [],
    characters: payload.characters,
    vocabulary: payload.vocabulary,
    grammar_patterns: payload.grammar_patterns,
    num_turns: payload.num_turns,
  };
  const res = await fetch(`${base}/api/v1/cando/dialogue/extend`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`extend_failed: ${res.status}`);
  return res.json();
}

export async function newDialogue(payload: {
  can_do_id: string;
  seed_setting?: string;
  vocabulary?: string[];
  grammar_patterns?: string[];
  num_turns?: number;
  characters?: string[];
}): Promise<any> {
  const base = getDialogueApiBaseUrl();
  const res = await fetch(`${base}/api/v1/cando/dialogue/new`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`new_failed: ${res.status}`);
  return res.json();
}

export async function storeDialogue(payload: {
  can_do_id: string;
  dialogue_card: any;
}): Promise<any> {
  const base = getDialogueApiBaseUrl();
  const res = await fetch(`${base}/api/v1/cando/dialogue/store`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`store_failed: ${res.status}`);
  return res.json();
}
