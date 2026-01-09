"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import React from "react";

// Types
interface ModelInfo {
  model_key: string;
  provider: string;
  display_name: string;
  input_cost_per_1k: number;
  output_cost_per_1k: number;
  max_tokens: number;
  supports_json_mode: boolean;
  recommended_for: string[];
}

interface NetworkStats {
  total_words: number;
  total_relations: number;
  lexical_relations: Record<string, number>;
  relations_by_pos: Record<string, Record<string, number>>;
  all_relations_by_type: Record<string, number>;
  relations_by_category: Record<string, number>;
  pos_distribution: Record<string, number>;
  difficulty_distribution: Record<string, number>;
  avg_relations_per_word: number;
  words_without_relations: number;
  most_connected_words: Array<Record<string, unknown>>;
  relations_by_type: Record<string, number>;
}

interface RelationSample {
  source: string;
  source_pos?: string;
  target: string;
  target_pos?: string;
  rel_type: string;
  rel_category?: string;
  weight?: number | null;
  confidence?: number | null;
  is_symmetric?: boolean | null;
  domain_tags?: string[] | null;
  domain_weights?: number[] | null;
  context_tags?: string[] | null;
  context_weights?: number[] | null;
  register_source?: string | null;
  register_target?: string | null;
  formality_difference?: string | null;
  raw_orth?: string | null;
  raw_reading?: string | null;
  resolution?: string | null;
  res_conf?: number | null;
  ai_provider?: string | null;
  ai_model?: string | null;
  ai_temperature?: number | null;
  created_utc?: string | null;
  updated_utc?: string | null;
  edge_properties?: Record<string, unknown>;
}

interface WordProcessingResult {
  word: string;
  relations_created: number;
  relations_updated: number;
  targets_found: number;
  targets_resolved: number;
  error?: string;
  timestamp: string;
}

interface Job {
  id: string;
  status: string;
  job_type: string;
  progress: number;
  created_at: string;
  started_at?: string;
  completed_at?: string;
  source_words?: string[];
  config?: {
    source?: string;
    pos_filter?: string;
    max_relations?: number;
    max_words?: number;
    relation_types?: string[];
  };
  result?: {
    processed?: number;
    relations_created?: number;
    relations_updated?: number;
    errors?: number;
    total_tokens_input?: number;
    total_tokens_output?: number;
    total_cost_usd?: number;
    avg_latency_ms?: number;
    models_used?: Record<string, number>;
    total_targets_attempted?: number;
    total_targets_resolved?: number;
    total_targets_dropped_not_found?: number;
    total_targets_dropped_ambiguous?: number;
    resolution_rate?: number;
  };
  current_word?: string;
  current_word_index?: number;
  total_words?: number;
  recent_results?: WordProcessingResult[];
}

const API_BASE = "/api/v1/lexical-network";

// Get auth token from localStorage
function getAuthToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("token");
}

// API helpers with authentication
async function apiGet<T>(url: string): Promise<T> {
  const token = getAuthToken();
  const headers: Record<string, string> = {
    Accept: "application/json",
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const res = await fetch(url, { headers });
  if (!res.ok) throw new Error(`API Error: ${res.status}`);
  return res.json();
}

async function apiPost<T>(url: string, data?: unknown): Promise<T> {
  const token = getAuthToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const res = await fetch(url, {
    method: "POST",
    headers,
    body: data ? JSON.stringify(data) : undefined,
  });
  if (!res.ok) throw new Error(`API Error: ${res.status}`);
  return res.json();
}

// Relation types per POS
const POS_RELATION_TYPES: Record<string, string[]> = {
  名詞: ["SYNONYM", "ANTONYM", "HYPERNYM", "HYPONYM", "MERONYM", "HOLONYM"],
  形容詞: [
    "SYNONYM",
    "NEAR_SYNONYM",
    "GRADABLE_ANTONYM",
    "SCALAR_INTENSITY",
    "REGISTER_VARIANT",
  ],
  形容動詞: [
    "SYNONYM",
    "NEAR_SYNONYM",
    "GRADABLE_ANTONYM",
    "SCALAR_INTENSITY",
    "REGISTER_VARIANT",
  ],
  動詞: [
    "SYNONYM",
    "ANTONYM",
    "CONVERSE",
    "TROPONYM",
    "CAUSATIVE_PAIR",
    "ASPECT_PAIR",
  ],
  副詞: [
    "SYNONYM",
    "ANTONYM",
    "INTENSITY_SCALE",
    "TEMPORAL_PAIR",
    "REGISTER_VARIANT",
  ],
};

export default function LexicalNetworkAdminPage() {
  const [activeTab, setActiveTab] = useState<
    "overview" | "relations" | "jobs" | "build" | "import"
  >("overview");
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [stats, setStats] = useState<NetworkStats | null>(null);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState({
    models: true,
    stats: true,
    jobs: true,
  });
  const [error, setError] = useState<string | null>(null);

  // Fetch models
  useEffect(() => {
    apiGet<ModelInfo[]>(`${API_BASE}/models`)
      .then(setModels)
      .catch((e) => setError(e.message))
      .finally(() => setLoading((l) => ({ ...l, models: false })));
  }, []);

  // Fetch stats with refresh
  const fetchStats = useCallback(() => {
    apiGet<NetworkStats>(`${API_BASE}/stats`)
      .then(setStats)
      .catch(() => {})
      .finally(() => setLoading((l) => ({ ...l, stats: false })));
  }, []);

  useEffect(() => {
    fetchStats();
    const interval = setInterval(fetchStats, 30000);
    return () => clearInterval(interval);
  }, [fetchStats]);

  // Fetch jobs with refresh
  const fetchJobs = useCallback(() => {
    apiGet<Job[]>(`${API_BASE}/jobs`)
      .then(setJobs)
      .catch(() => setJobs([]))
      .finally(() => setLoading((l) => ({ ...l, jobs: false })));
  }, []);

  const hasRunningJob = jobs.some((j) => j.status === "running");

  useEffect(() => {
    fetchJobs();
    const interval = setInterval(fetchJobs, hasRunningJob ? 2000 : 5000);
    return () => clearInterval(interval);
  }, [fetchJobs, hasRunningJob]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-background via-muted to-background text-foreground p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-4xl font-bold bg-gradient-to-r from-cyan-400 to-blue-500 bg-clip-text text-transparent">
            Lexical Network Generator
          </h1>
          <p className="text-muted-foreground mt-2">
            AI-Powered Japanese Lexical Relations Builder
          </p>
        </div>

        {error && (
          <div className="bg-red-900/50 border border-red-500 rounded-lg p-4 mb-6">
            <p className="text-red-300">{error}</p>
          </div>
        )}

        {/* Tabs */}
        <div className="flex space-x-1 bg-card/80 p-1 rounded-xl mb-8">
          {[
            { id: "overview", label: "Overview", icon: "📊" },
            { id: "relations", label: "Relations", icon: "🔎" },
            { id: "jobs", label: "Jobs", icon: "⚙️" },
            { id: "build", label: "Build Relations", icon: "🔗" },
            { id: "import", label: "Import", icon: "📥" },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as typeof activeTab)}
              className={`flex-1 py-3 px-4 rounded-lg font-medium transition-all ${
                activeTab === tab.id
                  ? "bg-gradient-to-r from-cyan-500 to-blue-600 text-foreground shadow-lg"
                  : "text-muted-foreground hover:text-foreground hover:bg-muted/60"
              }`}
            >
              <span className="mr-2">{tab.icon}</span>
              {tab.label}
            </button>
          ))}
        </div>

        {/* Content */}
        {activeTab === "overview" && (
          <OverviewContent models={models} stats={stats} loading={loading} />
        )}
        {activeTab === "relations" && <RelationsContent stats={stats} />}
        {activeTab === "jobs" && (
          <JobsContent
            jobs={jobs}
            loading={loading.jobs}
            onRefresh={fetchJobs}
          />
        )}
        {activeTab === "build" && (
          <BuildContent
            models={models}
            loading={loading.models}
            onJobCreated={fetchJobs}
          />
        )}
        {activeTab === "import" && <ImportContent />}
      </div>
    </div>
  );
}

// Overview Tab
function OverviewContent({
  models,
  stats,
  loading,
}: {
  models: ModelInfo[];
  stats: NetworkStats | null;
  loading: { models: boolean; stats: boolean };
}) {
  const totalAllRelations = Object.values(
    stats?.all_relations_by_type || {}
  ).reduce((a, b) => a + b, 0);

  return (
    <div className="space-y-6">
      {/* Primary Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <StatCard
          title="Total Words"
          value={stats?.total_words?.toLocaleString() ?? 0}
          loading={loading.stats}
          icon="📚"
          color="cyan"
        />
        <StatCard
          title="Lexical Relations"
          value={stats?.total_relations?.toLocaleString() ?? 0}
          loading={loading.stats}
          icon="🔗"
          color="blue"
        />
        <StatCard
          title="All Relations"
          value={totalAllRelations.toLocaleString()}
          loading={loading.stats}
          icon="🌐"
          color="green"
        />
        <StatCard
          title="Words Need Relations"
          value={stats?.words_without_relations?.toLocaleString() ?? 0}
          loading={loading.stats}
          icon="⚠️"
          color="amber"
        />
      </div>

      {/* AI Models */}
      <div className="bg-card/80 rounded-xl p-6 border border-border">
        <h2 className="text-xl font-semibold mb-4 text-cyan-400">
          🤖 Available AI Models
        </h2>
        {loading.models ? (
          <div className="text-muted-foreground animate-pulse">
            Loading models...
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {models.map((model) => (
              <div
                key={model.model_key}
                className="bg-muted/60 rounded-lg p-4 border border-border hover:border-cyan-500/50 transition-colors"
              >
                <div className="flex items-center justify-between mb-3">
                  <h3 className="font-semibold text-foreground">
                    {model.display_name}
                  </h3>
                  <span
                    className={`text-xs px-2 py-1 rounded-full ${
                      model.provider === "openai"
                        ? "bg-green-900/50 text-green-400"
                        : model.provider === "gemini"
                          ? "bg-blue-900/50 text-blue-400"
                          : "bg-purple-900/50 text-purple-400"
                    }`}
                  >
                    {model.provider}
                  </span>
                </div>
                <div className="text-sm text-muted-foreground space-y-1">
                  <div>
                    💰 ${model.input_cost_per_1k}/1K in • $
                    {model.output_cost_per_1k}/1K out
                  </div>
                  <div>📏 Max: {model.max_tokens.toLocaleString()} tokens</div>
                  <div>{model.supports_json_mode ? "✅" : "❌"} JSON mode</div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// Relations Tab
function RelationsContent({ stats }: { stats: NetworkStats | null }) {
  const [relations, setRelations] = useState<RelationSample[]>([]);
  const [loading, setLoading] = useState(false);
  const [filterSource, setFilterSource] = useState("");

  const fetchRelations = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      params.set("limit", "50");
      if (filterSource.trim()) params.set("source", filterSource.trim());
      const data = await apiGet<RelationSample[]>(
        `${API_BASE}/relations/sample?${params.toString()}`
      );
      setRelations(data || []);
    } catch (e) {
      console.error(e);
      setRelations([]);
    } finally {
      setLoading(false);
    }
  }, [filterSource]);

  useEffect(() => {
    fetchRelations();
  }, [fetchRelations]);

  return (
    <div className="space-y-6">
      <div className="bg-card/80 rounded-xl p-6 border border-border">
        <div className="flex flex-wrap gap-3 items-end mb-4">
          <div className="flex flex-col gap-1">
            <label className="text-xs text-muted-foreground">Source Word</label>
            <input
              className="bg-muted/70 border border-border rounded px-3 py-2 text-sm text-foreground min-w-[220px]"
              placeholder="e.g., 美しい"
              value={filterSource}
              onChange={(e) => setFilterSource(e.target.value)}
            />
          </div>
          <button
            onClick={fetchRelations}
            className="text-foreground bg-cyan-600/80 hover:bg-cyan-600 px-3 py-2 rounded text-sm"
            disabled={loading}
          >
            {loading ? "Loading..." : "Search"}
          </button>
        </div>

        {relations.length === 0 ? (
          <div className="text-muted-foreground text-sm">No relations found.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border">
                  <th className="text-left py-2 px-3 text-muted-foreground">
                    Source
                  </th>
                  <th className="text-left py-2 px-3 text-muted-foreground">
                    Relation
                  </th>
                  <th className="text-left py-2 px-3 text-muted-foreground">
                    Target
                  </th>
                </tr>
              </thead>
              <tbody>
                {relations.map((r, idx) => (
                  <tr
                    key={idx}
                    className="border-b border-border/60 hover:bg-muted/50"
                  >
                    <td className="py-2 px-3 text-foreground">{r.source}</td>
                    <td className="py-2 px-3 text-cyan-300">{r.rel_type}</td>
                    <td className="py-2 px-3 text-foreground">{r.target}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

// Jobs Tab
function JobsContent({
  jobs,
  loading,
  onRefresh,
}: {
  jobs: Job[];
  loading: boolean;
  onRefresh: () => void;
}) {
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  const handleAction = async (jobId: string, action: "start" | "cancel") => {
    setActionLoading(jobId);
    try {
      await apiPost(`${API_BASE}/jobs/${jobId}/${action}`);
      onRefresh();
    } catch (e) {
      alert(`Error: ${e}`);
    } finally {
      setActionLoading(null);
    }
  };

  return (
    <div className="bg-card/80 rounded-xl p-6 border border-border">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold text-cyan-400">Background Jobs</h2>
        <button
          onClick={onRefresh}
          className="text-muted-foreground hover:text-foreground transition-colors"
        >
          🔄 Refresh
        </button>
      </div>

      {loading ? (
        <div className="text-muted-foreground animate-pulse">
          Loading jobs...
        </div>
      ) : jobs.length === 0 ? (
        <div className="text-center py-12 text-muted-foreground">
          <div className="text-4xl mb-4">📭</div>
          <p>No jobs yet. Create one in the Build tab.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {jobs.map((job) => (
            <div
              key={job.id}
              className="bg-muted/60 rounded-lg p-4 border border-border"
            >
              <div className="flex items-center justify-between mb-3">
                <div>
                  <div className="font-semibold text-foreground">
                    {job.job_type}
                  </div>
                  <div className="text-sm text-muted-foreground">
                    ID: {job.id.slice(0, 8)}...
                  </div>
                </div>
                <span
                  className={`px-3 py-1 rounded-full text-sm font-medium ${
                    job.status === "completed"
                      ? "bg-green-900/50 text-green-400"
                      : job.status === "running"
                        ? "bg-blue-900/50 text-blue-400"
                        : job.status === "failed"
                          ? "bg-red-900/50 text-red-400"
                          : "bg-muted text-muted-foreground"
                  }`}
                >
                  {job.status}
                </span>
              </div>

              {job.status === "running" && (
                <div className="mb-3 p-4 bg-card/80 rounded-lg border border-blue-500/30">
                  <div className="flex items-center gap-3 mb-3">
                    <div className="flex-1">
                      <div className="w-full bg-muted rounded-full h-2">
                        <div
                          className="bg-gradient-to-r from-cyan-500 to-blue-600 h-2 rounded-full transition-all"
                          style={{ width: `${(job.progress || 0) * 100}%` }}
                        />
                      </div>
                    </div>
                    <div className="text-sm text-cyan-400 font-semibold">
                      {((job.progress || 0) * 100).toFixed(1)}%
                    </div>
                  </div>
                  {job.current_word && (
                    <div className="text-sm text-muted-foreground">
                      Processing: <span className="text-foreground">{job.current_word}</span>
                    </div>
                  )}
                </div>
              )}

              <div className="flex gap-2">
                {job.status === "pending" && (
                  <button
                    onClick={() => handleAction(job.id, "start")}
                    disabled={actionLoading === job.id}
                    className="px-4 py-2 bg-gradient-to-r from-cyan-500 to-blue-600 text-foreground rounded-lg hover:opacity-90 text-sm disabled:opacity-50"
                  >
                    {actionLoading === job.id ? "..." : "▶ Start"}
                  </button>
                )}
                {["pending", "running"].includes(job.status) && (
                  <button
                    onClick={() => handleAction(job.id, "cancel")}
                    disabled={actionLoading === job.id}
                    className="px-4 py-2 bg-red-900/50 text-red-400 rounded-lg hover:bg-red-900 text-sm disabled:opacity-50"
                  >
                    {actionLoading === job.id ? "..." : "⏹ Cancel"}
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// Build Tab
function BuildContent({
  models,
  loading,
  onJobCreated,
}: {
  models: ModelInfo[];
  loading: boolean;
  onJobCreated: () => void;
}) {
  const [sourceMode, setSourceMode] = useState<"database" | "word_list">(
    "database"
  );
  const [posFilter, setPosFilter] = useState<string | null>(null);
  const [wordList, setWordList] = useState("");
  const [selectedModel, setSelectedModel] = useState("gpt-4o-mini");
  const [relationTypes, setRelationTypes] = useState<string[]>(["SYNONYM"]);
  const [maxWords, setMaxWords] = useState(50);
  const [creating, setCreating] = useState(false);

  const availableRelations = posFilter
    ? POS_RELATION_TYPES[posFilter] || ["SYNONYM"]
    : Array.from(
        new Set([
          ...(POS_RELATION_TYPES["名詞"] || []),
          ...(POS_RELATION_TYPES["形容詞"] || []),
          ...(POS_RELATION_TYPES["動詞"] || []),
          ...(POS_RELATION_TYPES["副詞"] || []),
        ])
      ).sort();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreating(true);
    try {
      const config: any = {
        job_type: "relation_building",
        source: sourceMode,
        relation_types: relationTypes,
        model: selectedModel,
        max_words: maxWords,
      };
      if (sourceMode === "word_list") {
        config.word_list = wordList
          .split(/[,\n]/)
          .map((w) => w.trim())
          .filter(Boolean);
      } else {
        if (posFilter) config.pos_filter = posFilter;
      }
      await apiPost(`${API_BASE}/jobs`, config);
      alert("✅ Job created successfully!");
      onJobCreated();
    } catch (e) {
      alert(`❌ Error: ${e}`);
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="bg-card/80 rounded-xl p-6 border border-border">
      <h2 className="text-xl font-semibold mb-6 text-cyan-400">
        Build Lexical Relations
      </h2>
      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Source Mode Selection */}
        <div>
          <label className="block text-sm font-medium text-foreground mb-3">
            Source Mode
          </label>
          <div className="grid grid-cols-2 gap-4">
            <label
              className={`flex items-center justify-center gap-3 p-4 rounded-lg border cursor-pointer transition-all ${
                sourceMode === "database"
                  ? "border-cyan-500 bg-cyan-500/10 text-cyan-400"
                  : "border-border hover:border-border text-muted-foreground"
              }`}
            >
              <input
                type="radio"
                checked={sourceMode === "database"}
                onChange={() => setSourceMode("database")}
                className="sr-only"
              />
              <span className="text-2xl">🗄️</span>
              <div>
                <div className="font-medium">Database Filter</div>
                <div className="text-xs opacity-70">Filter words from Neo4j</div>
              </div>
            </label>
            <label
              className={`flex items-center justify-center gap-3 p-4 rounded-lg border cursor-pointer transition-all ${
                sourceMode === "word_list"
                  ? "border-cyan-500 bg-cyan-500/10 text-cyan-400"
                  : "border-border hover:border-border text-muted-foreground"
              }`}
            >
              <input
                type="radio"
                checked={sourceMode === "word_list"}
                onChange={() => setSourceMode("word_list")}
                className="sr-only"
              />
              <span className="text-2xl">📝</span>
              <div>
                <div className="font-medium">Word List</div>
                <div className="text-xs opacity-70">Manual word input</div>
              </div>
            </label>
          </div>
        </div>

        {/* Database Filter Options */}
        {sourceMode === "database" && (
          <div className="p-4 bg-muted/60 rounded-lg border border-border">
            <label className="block text-xs text-muted-foreground mb-2">
              Part of Speech
            </label>
            <select
              value={posFilter || ""}
              onChange={(e) => setPosFilter(e.target.value || null)}
              className="w-full bg-background border border-border rounded-lg px-4 py-2 text-foreground text-sm focus:border-cyan-500 focus:outline-none"
            >
              <option value="">All POS (任意)</option>
              <option value="名詞">名詞 (Noun)</option>
              <option value="形容詞">形容詞 (i-Adjective)</option>
              <option value="形容動詞">形容動詞 (na-Adjective)</option>
              <option value="動詞">動詞 (Verb)</option>
              <option value="副詞">副詞 (Adverb)</option>
            </select>
          </div>
        )}

        {/* Word List Input */}
        {sourceMode === "word_list" && (
          <div className="p-4 bg-muted/60 rounded-lg border border-border">
            <label className="block text-sm font-medium text-foreground mb-2">
              Word List
            </label>
            <textarea
              value={wordList}
              onChange={(e) => setWordList(e.target.value)}
              className="w-full bg-background border border-border rounded-lg px-4 py-3 text-foreground focus:border-cyan-500 focus:outline-none font-mono text-sm"
              rows={5}
              placeholder="美しい, 綺麗, 大きい, 小さい"
            />
          </div>
        )}

        {/* Max Words */}
        <div>
          <label className="block text-sm font-medium text-foreground mb-2">
            Max Words to Process: {maxWords}
          </label>
          <input
            type="range"
            min="1"
            max="500"
            value={maxWords}
            onChange={(e) => setMaxWords(parseInt(e.target.value))}
            className="w-full h-2 bg-muted rounded-lg appearance-none cursor-pointer accent-cyan-500"
          />
        </div>

        {/* AI Model */}
        <div>
          <label className="block text-sm font-medium text-foreground mb-2">
            AI Model
          </label>
          {loading ? (
            <div className="text-muted-foreground">Loading models...</div>
          ) : (
            <select
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
              className="w-full bg-background border border-border rounded-lg px-4 py-3 text-foreground focus:border-cyan-500 focus:outline-none"
            >
              {models.map((model) => (
                <option key={model.model_key} value={model.model_key}>
                  {model.display_name} ({model.provider})
                </option>
              ))}
            </select>
          )}
        </div>

        {/* Relation Types */}
        <div>
          <label className="block text-sm font-medium text-foreground mb-3">
            Relation Types to Generate
          </label>
          <div className="flex flex-wrap gap-2">
            {availableRelations.map((type) => (
              <label
                key={type}
                className={`px-3 py-2 rounded-lg border cursor-pointer transition-all text-sm ${
                  relationTypes.includes(type)
                    ? "border-cyan-500 bg-cyan-500/10 text-cyan-400"
                    : "border-border text-muted-foreground hover:border-border"
                }`}
              >
                <input
                  type="checkbox"
                  checked={relationTypes.includes(type)}
                  onChange={(e) => {
                    if (e.target.checked) {
                      setRelationTypes([...relationTypes, type]);
                    } else {
                      setRelationTypes(relationTypes.filter((t) => t !== type));
                    }
                  }}
                  className="sr-only"
                />
                {type.replace(/_/g, " ")}
              </label>
            ))}
          </div>
        </div>

        {/* Submit */}
        <button
          type="submit"
          disabled={
            creating ||
            relationTypes.length === 0 ||
            (sourceMode === "word_list" && !wordList.trim())
          }
          className="w-full py-4 bg-gradient-to-r from-cyan-500 to-blue-600 text-foreground font-semibold rounded-lg hover:opacity-90 disabled:opacity-50 transition-all"
        >
          {creating ? "Creating Job..." : "🚀 Create Relation Building Job"}
        </button>
      </form>
    </div>
  );
}

// Import Tab
function ImportContent() {
  const [importing, setImporting] = useState<string | null>(null);

  const handleImport = async (dict: "lee" | "matsushita") => {
    setImporting(dict);
    try {
      await apiPost(`${API_BASE}/import/${dict}-dict`);
      alert(
        `✅ ${dict === "lee" ? "Lee" : "Matsushita"} dictionary import started!`
      );
    } catch (e) {
      alert(`❌ Import not available: ${e}`);
    } finally {
      setImporting(null);
    }
  };

  return (
    <div className="space-y-6">
      <div className="bg-card/80 rounded-xl p-6 border border-border">
        <h2 className="text-xl font-semibold mb-4 text-cyan-400">
          Import Dictionaries
        </h2>
        <p className="text-muted-foreground mb-6">
          Import vocabulary from external dictionary sources to enrich the
          lexical network.
        </p>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="bg-muted/60 rounded-lg p-6 border border-border">
            <h3 className="font-semibold text-foreground mb-2">
              📕 Lee Dictionary
            </h3>
            <p className="text-sm text-muted-foreground mb-4">
              分類語彙表 - Comprehensive Japanese vocabulary with semantic
              categories
            </p>
            <button
              onClick={() => handleImport("lee")}
              disabled={importing !== null}
              className="w-full py-3 bg-gradient-to-r from-cyan-500 to-blue-600 text-foreground rounded-lg hover:opacity-90 disabled:opacity-50"
            >
              {importing === "lee" ? "Importing..." : "Import Lee Dict"}
            </button>
          </div>

          <div className="bg-muted/60 rounded-lg p-6 border border-border">
            <h3 className="font-semibold text-foreground mb-2">
              📗 Matsushita Dictionary
            </h3>
            <p className="text-sm text-muted-foreground mb-4">
              Japanese vocabulary with frequency and difficulty levels
            </p>
            <button
              onClick={() => handleImport("matsushita")}
              disabled={importing !== null}
              className="w-full py-3 bg-gradient-to-r from-cyan-500 to-blue-600 text-foreground rounded-lg hover:opacity-90 disabled:opacity-50"
            >
              {importing === "matsushita"
                ? "Importing..."
                : "Import Matsushita Dict"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// Stat Card Component
function StatCard({
  title,
  value,
  loading,
  icon,
  color,
}: {
  title: string;
  value: string | number;
  loading: boolean;
  icon: string;
  color: "cyan" | "blue" | "green" | "amber";
}) {
  const colorClasses = {
    cyan: "from-cyan-500/20 to-cyan-600/10 border-cyan-500/30",
    blue: "from-blue-500/20 to-blue-600/10 border-blue-500/30",
    green: "from-green-500/20 to-green-600/10 border-green-500/30",
    amber: "from-amber-500/20 to-amber-600/10 border-amber-500/30",
  };

  return (
    <div
      className={`bg-gradient-to-br ${colorClasses[color]} border rounded-xl p-6`}
    >
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-muted-foreground">{title}</p>
          <p className="text-3xl font-bold text-foreground mt-1">
            {loading ? <span className="animate-pulse">...</span> : value}
          </p>
        </div>
        <div className="text-4xl opacity-50">{icon}</div>
      </div>
    </div>
  );
}
