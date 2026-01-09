"use client";

import { useState } from "react";
import { apiGet } from "@/lib/api";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

type Result = {
  id?: string;
  label?: string;
  score?: number;
  snippet?: string;
};

export default function KnowledgeSearchPage() {
  const [q, setQ] = useState("");
  const [items, setItems] = useState<Result[] | null>(null);
  const [loading, setLoading] = useState(false);

  async function search() {
    if (!q.trim()) return;
    setLoading(true);
    try {
      const res = await apiGet<{ results: Result[] }>(
        `/api/v1/knowledge/search?q=${encodeURIComponent(q)}&max_results=10`
      );
      setItems(res.results || []);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="max-w-3xl mx-auto p-6">
      <h1 className="text-2xl font-semibold mb-3">Knowledge Search</h1>
      <div className="flex items-center gap-2 mb-3">
        <Input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search grammar/vocabulary..."
        />
        <Button onClick={search} disabled={loading}>
          {loading ? "Searching..." : "Search"}
        </Button>
      </div>
      {items && (
        <ul className="space-y-2">
          {items.map((it, i) => (
            <li key={i} className="border rounded p-3">
              <div className="text-sm font-medium">{it.label || it.id}</div>
              {typeof it.score === "number" && (
                <div className="text-xs text-muted-foreground">
                  Score: {it.score.toFixed(2)}
                </div>
              )}
              {it.snippet && <div className="text-xs mt-1">{it.snippet}</div>}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
