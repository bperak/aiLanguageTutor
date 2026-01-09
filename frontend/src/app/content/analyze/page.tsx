"use client";

import { useState } from "react";
import { apiPost } from "@/lib/api";
import { Button } from "@/components/ui/button";

type AnalysisItem = {
  kind: string;
  value: string;
  confidence?: number;
};

export default function AnalyzeContentPage() {
  const [text, setText] = useState("");
  const [loading, setLoading] = useState(false);
  const [items, setItems] = useState<AnalysisItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function runAnalysis() {
    if (!text.trim()) return;
    setLoading(true);
    setError(null);

    try {
      const res = await apiPost<{ items: AnalysisItem[] }>(
        "/api/v1/content/analyze",
        {
          text,
          source: { title: "User submission", language: "ja" },
        }
      );
      setItems(res.items || []);
    } catch (e) {
      setError("Analysis failed. Check backend logs.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="max-w-3xl mx-auto p-6">
      <h1 className="text-2xl font-semibold mb-3">Analyze Content</h1>
      <p className="text-sm text-muted-foreground mb-4">
        Paste Japanese text to extract vocabulary/grammar with AI and graph
        context.
      </p>
      <textarea
        className="w-full border rounded p-3 h-40 mb-3"
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="Paste text..."
      />
      <div className="flex gap-2">
        <Button onClick={runAnalysis} disabled={loading}>
          {loading ? "Analyzing..." : "Analyze"}
        </Button>
        <Button
          variant="ghost"
          onClick={() => {
            setText("");
            setItems(null);
            setError(null);
          }}
        >
          Clear
        </Button>
      </div>
      {error && <p className="text-sm text-destructive mt-3">{error}</p>}
      {items && (
        <div className="mt-4">
          <h2 className="text-lg font-semibold mb-2">Results</h2>
          <ul className="list-disc pl-5 space-y-1">
            {items.map((it, idx) => (
              <li key={idx} className="text-sm">
                {it.kind}: {it.value}{" "}
                {typeof it.confidence === "number" ? `(${it.confidence})` : ""}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
