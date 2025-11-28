"use client";

import { useEffect, useMemo, useState } from "react";

type SeedItem = {
  kanji: string;
  hiragana?: string;
  translation?: string;
  pos?: string;
  level?: number;
};

export default function LexicalLessonsPage() {
  const [level, setLevel] = useState(1);
  const [seeds, setSeeds] = useState<SeedItem[]>([]);
  const [selected, setSelected] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [content, setContent] = useState<string>("");
  const [readability, setReadability] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL || "";

  useEffect(() => {
    let isMounted = true;
    async function loadSeeds() {
      try {
        const url = `${apiBase}/api/v1/lexical/lessons/seed?level=${level}&count=12`;
        const res = await fetch(url);
        const json = await res.json();
        if (!res.ok) throw new Error(json?.detail || `Failed to seed (status ${res.status})`);
        if (isMounted) {
          setSeeds(json.items || []);
          setSelected(json.items?.[0]?.kanji || "");
        }
      } catch (e: any) {
        if (isMounted) setError(e?.message || "Failed to load seeds");
      }
    }
    loadSeeds();
    return () => {
      isMounted = false;
    };
  }, [apiBase, level]);

  async function generate() {
    if (!selected) return;
    setLoading(true);
    setError(null);
    setContent("");
    setReadability(null);
    try {
      const url = `${apiBase}/api/v1/lexical/lessons/generate?word=${encodeURIComponent(
        selected
      )}&level=${level}`;
      const res = await fetch(url, { method: "POST" });
      const json = await res.json();
      if (!res.ok) throw new Error(json?.detail || `Failed to generate (status ${res.status})`);
      const contentText = json.content || "";
      setContent(contentText);
      const rd = json.readability || null;
      setReadability(rd);
      // fire-and-forget attempt logging (requires auth; ignore failures)
      try {
        const attemptUrl = `${apiBase}/api/v1/lexical/lessons/attempt`;
        const payload = {
          word: selected,
          level,
          provider: json.ai?.provider,
          model: json.ai?.model,
          readability_score: rd?.score,
          readability_level: rd?.level,
          content_len: contentText.length,
        };
        fetch(attemptUrl, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
          // credentials: include -> if your auth uses cookies; else add Authorization header via your auth store
        }).catch(() => {});
      } catch {}
    } catch (e: any) {
      setError(e?.message || "Generation failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="max-w-5xl mx-auto p-4 space-y-4">
      <h1 className="text-xl font-semibold">Lexical Lessons</h1>
      <div className="flex flex-wrap gap-2 items-center">
        <label className="text-sm">Level</label>
        <select
          className="border px-2 py-1 rounded"
          value={level}
          onChange={(e) => setLevel(Number(e.target.value))}
        >
          <option value={1}>1</option>
          <option value={2}>2</option>
          <option value={3}>3</option>
          <option value={4}>4</option>
          <option value={5}>5</option>
          <option value={6}>6</option>
        </select>
        <label className="text-sm">Word</label>
        <select
          className="border px-2 py-1 rounded min-w-40"
          value={selected}
          onChange={(e) => setSelected(e.target.value)}
        >
          {seeds.map((s) => (
            <option key={s.kanji} value={s.kanji}>
              {s.kanji} {s.hiragana ? `(${s.hiragana})` : ""} — {s.translation || ""}
            </option>
          ))}
        </select>
        <button
          className="ml-auto border px-3 py-1 rounded hover:bg-gray-50"
          onClick={generate}
          disabled={loading || !selected}
        >
          {loading ? "Generating..." : "Generate Lesson"}
        </button>
      </div>
      {error && <div className="text-sm text-red-600">{error}</div>}
      {content && (
        <div className="rounded border p-3 space-y-2">
          <div className="text-sm text-gray-500">Generated Lesson</div>
          <pre className="whitespace-pre-wrap text-sm leading-relaxed">{content}</pre>
          {readability && (
            <div className="text-xs mt-2">
              Readability: {readability.available ? `${readability.level} (${readability.score?.toFixed?.(3)})` : "N/A"}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
