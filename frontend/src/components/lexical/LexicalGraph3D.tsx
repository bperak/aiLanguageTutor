"use client";

import dynamic from "next/dynamic";
import { useEffect, useRef, useState } from "react";
import SpriteText from "three-spritetext";
import { apiGet } from "@/lib/api";

const ForceGraph3D = dynamic(() => import("react-force-graph-3d"), {
  ssr: false,
}) as any;

type GraphNode = {
  id: string;
  name?: string;
  kanji?: string;
  hiragana?: string;
  translation?: string;
  level?: number;
  center?: boolean;
  pos?: string;
  domain?: string;
  connections?: number;
};

type GraphLink = {
  source: string;
  target: string;
  weight?: number;
  relation_type?: string;
};

type NodeDetails = {
  kanji: string;
  hiragana: string;
  translation: string;
  level: number;
  pos: string;
  etymology: string;
  connections: number;
};

type NeighborInfo = {
  kanji: string;
  hiragana: string;
  translation: string;
  level: number;
  pos: string;
  domain: string;
  synonym_strength: number;
  relation_type: string;
  mutual_sense: string;
};

type GraphDataResponse = {
  nodes: GraphNode[];
  links: GraphLink[];
  center?: { id: string };
};

type NodeDetailsResponse = {
  node: NodeDetails;
  neighbors: NeighborInfo[];
};

export default function LexicalGraph3D({
  center,
  depth = 1,
  colorBy = "domain",
  searchField = "kanji",
  labelTypes = { kanji: true, hiragana: false, translation: false },
  expandOnClick = true,
  onCenterChange,
  onDepthChange,
  onSearch,
  onToggle3D,
  onNodeDataChange,
}: {
  center: string;
  depth?: number;
  colorBy?: "domain" | "pos" | "level";
  searchField?: "kanji" | "hiragana" | "translation";
  labelTypes?: { kanji: boolean; hiragana: boolean; translation: boolean };
  expandOnClick?: boolean;
  onCenterChange?: (center: string) => void;
  onDepthChange?: (depth: number) => void;
  onSearch?: () => void;
  onToggle3D?: () => void;
  onNodeDataChange?: (nodeData: {
    selectedNode: NodeDetails | null;
    neighbors: NeighborInfo[];
  }) => void;
}) {
  const graphRef = useRef<any>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [data, setData] = useState<{ nodes: GraphNode[]; links: GraphLink[] }>({
    nodes: [],
    links: [],
  });
  const [isDark, setIsDark] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedNode, setSelectedNode] = useState<NodeDetails | null>(null);
  const [neighbors, setNeighbors] = useState<NeighborInfo[]>([]);
  const [currentCenter, setCurrentCenter] = useState(center);
  const [containerSize, setContainerSize] = useState({ width: 800, height: 600 });

  // Track dark mode
  useEffect(() => {
    const root = document.documentElement;
    const updateTheme = () => setIsDark(root.classList.contains("dark"));
    updateTheme();
    const observer = new MutationObserver(updateTheme);
    observer.observe(root, { attributes: true, attributeFilter: ["class"] });
    return () => observer.disconnect();
  }, []);

  const generateNodeLabel = (node: GraphNode): string => {
    const parts: string[] = [];
    const kanjiValue = node.kanji || node.name;
    if (labelTypes.kanji && kanjiValue) parts.push(kanjiValue);
    if (labelTypes.hiragana && node.hiragana) parts.push(node.hiragana);
    if (labelTypes.translation && node.translation) parts.push(node.translation);
    if (parts.length === 0) return kanjiValue || node.id;
    return parts.join(" | ");
  };

  function sanitizeGraphData(input: {
    nodes?: GraphNode[];
    links?: GraphLink[];
  }): { nodes: GraphNode[]; links: GraphLink[] } {
    const rawNodes = input.nodes ?? [];
    const rawLinks = input.links ?? [];
    const idSet = new Set<string>();
    const nodes: GraphNode[] = [];

    for (const n of rawNodes) {
      const id = (n?.id || "").trim();
      if (!id || idSet.has(id)) continue;
      idSet.add(id);
      nodes.push({
        ...n,
        name: n.kanji || n.name || id,
        kanji: n.kanji || n.name || id,
      });
    }

    const links: GraphLink[] = [];
    for (const l of rawLinks) {
      const src = (l as any)?.source?.toString().trim();
      const tgt = (l as any)?.target?.toString().trim();
      if (!src || !tgt || !idSet.has(src) || !idSet.has(tgt) || src === tgt)
        continue;
      const weight =
        typeof l.weight === "number" ? l.weight : Number(l.weight) || 1;
      links.push({ ...l, weight });
    }

    return { nodes, links };
  }

  const fitToScreen = (duration: number = 500) => {
    try {
      graphRef.current?.zoomToFit(duration, 80);
    } catch (e) {
      console.warn("3D graph fit failed:", e);
    }
  };

  // Measure container size
  useEffect(() => {
    const updateSize = () => {
      if (containerRef.current) {
        const rect = containerRef.current.getBoundingClientRect();
        setContainerSize({ width: rect.width, height: rect.height });
        fitToScreen();
      }
    };
    updateSize();
    window.addEventListener("resize", updateSize);
    return () => window.removeEventListener("resize", updateSize);
  }, []);

  // Notify parent component when node data changes
  useEffect(() => {
    onNodeDataChange?.({ selectedNode, neighbors });
  }, [selectedNode, neighbors, onNodeDataChange]);

  // Load graph data
  useEffect(() => {
    let isMounted = true;
    async function load() {
      if (!center || center.trim() === "") {
        if (isMounted) {
          setLoading(false);
          setError(null);
          setData({ nodes: [], links: [] });
        }
        return;
      }

      setLoading(true);
      setError(null);
      try {
        const url = `/api/v1/lexical/graph?center=${encodeURIComponent(
          center
        )}&depth=${depth}&searchField=${searchField}`;
        const json = await apiGet<GraphDataResponse>(url);
        const sanitized = sanitizeGraphData(json);
        if (isMounted) {
          setData(sanitized);
          setCurrentCenter(json.center?.id || center);
          if (json.center?.id) {
            await loadNodeDetails(json.center.id);
          }
        }
      } catch (e: any) {
        if (isMounted) {
          // Reason: Handle timeout and 524 errors gracefully with user-friendly messages
          if (e?.code === "ECONNABORTED" || e?.message?.includes("timeout") || e?.response?.status === 524) {
            setError("Request timed out. The graph query is taking too long. Try a different word or reduce the depth.");
          } else if (e?.response?.status === 503) {
            setError("Service temporarily unavailable. Please try again in a moment.");
          } else {
            setError(e?.message || "Failed to load graph");
          }
        }
      } finally {
        if (isMounted) setLoading(false);
      }
    }
    load();
    return () => {
      isMounted = false;
    };
  }, [center, depth, searchField]);

  async function loadNodeDetails(nodeId: string) {
    try {
      const url = `/api/v1/lexical/node/${encodeURIComponent(nodeId)}`;
      const details = await apiGet<NodeDetailsResponse>(url);
      setSelectedNode(details.node);
      setNeighbors(details.neighbors || []);
    } catch (e) {
      console.error("Failed to load node details:", e);
    }
  }

  const handleNodeClick = async (node: any) => {
    if (!node?.id || node.id.trim() === "") return;
    onCenterChange?.(node.id);
    await loadNodeDetails(node.id);
    setTimeout(() => fitToScreen(), 0);
  };

  return (
    <div className="h-full w-full">
      <div
        ref={containerRef}
        className="h-full border rounded-lg overflow-hidden relative"
      >
        {loading && (
          <div className="absolute inset-0 bg-background/75 flex items-center justify-center z-10">
            <div className="text-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto mb-2"></div>
              <div className="text-sm text-muted-foreground">
                Loading new graph...
              </div>
            </div>
          </div>
        )}
        {error && (
          <div className="p-2 text-sm text-red-600">Error: {error}</div>
        )}
        {!loading && !error && data.nodes.length === 0 && (
          <div className="p-4 text-center text-muted-foreground">
            {!center || center.trim() === "" ? (
              <div>
                <div className="text-lg mb-2">
                  🔍 Enter a Japanese word to explore
                </div>
                <div className="text-sm">
                  Type a kanji, hiragana, or English word to see its lexical
                  network
                </div>
              </div>
            ) : (
              <div>
                <div className="text-lg mb-2">No data found</div>
                <div className="text-sm">
                  Try another word or check your connection.
                </div>
              </div>
            )}
          </div>
        )}
        {!loading && !error && data.nodes.length > 0 && (
          <div className="absolute top-2 left-2 right-2 p-2 bg-background/60 backdrop-blur-sm border border-border rounded shadow-sm z-30">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3 text-xs text-muted-foreground">
                <span>
                  Search node:{" "}
                  <span className="text-red-600 font-medium">
                    {currentCenter}
                  </span>
                </span>
                <span>Nodes: {data.nodes.length}</span>
                <span>Links: {data.links.length}</span>
                <select
                  className="px-2 py-1 text-xs border border-input bg-background text-foreground rounded"
                  value={depth}
                  onChange={(e) => onDepthChange?.(Number(e.target.value))}
                >
                  <option value={1}>Depth: 1</option>
                  <option value={2}>Depth: 2</option>
                </select>
              </div>
              <div className="flex items-center gap-1">
                <button
                  onClick={onToggle3D}
                  className="px-2 py-1 text-xs border border-input rounded hover:bg-accent"
                >
                  2D
                </button>
                <button
                  onClick={() => fitToScreen()}
                  className="px-2 py-1 text-xs border border-input rounded hover:bg-accent"
                >
                  Fit
                </button>
              </div>
            </div>
          </div>
        )}
        <ForceGraph3D
          ref={graphRef}
          graphData={data}
          width={containerSize.width}
          height={containerSize.height}
          backgroundColor={isDark ? "#1a1a2e" : "#f8fafc"}
          nodeLabel={(n: GraphNode) =>
            `${n.kanji || n.name || n.id}${
              n.hiragana ? ` (${n.hiragana})` : ""
            }${n.translation ? ` — ${n.translation}` : ""}`
          }
          nodeAutoColorBy={(n: GraphNode) => {
            if (colorBy === "pos") return n.pos || "";
            if (colorBy === "domain") return n.domain || "";
            return `${n.level ?? 0}`;
          }}
          nodeColor={(n: GraphNode) => {
            if (n.center) return "#dc2626";
            if (selectedNode && n.id === selectedNode.kanji) return "#ea580c";
            return undefined;
          }}
          nodeThreeObject={(node: any) => {
            const label = generateNodeLabel(node);
            const sprite = new SpriteText(label);
            sprite.color = node.center ? "#dc2626" : isDark ? "#e2e8f0" : "#1f2937";
            sprite.textHeight = node.center ? 6 : 4;
            sprite.fontWeight = node.center ? "bold" : "normal";
            return sprite;
          }}
          linkWidth={(l: any) => Math.max(0.3, Math.min(3, (l.weight || 1) / 3))}
          linkColor={(l: any) => {
            const alpha = Math.max(0.3, Math.min(0.9, (l.weight || 1) / 10));
            return `rgba(60,120,255,${alpha})`;
          }}
          linkDirectionalParticles={1}
          linkDirectionalParticleSpeed={0.004}
          onNodeClick={handleNodeClick}
          onEngineStop={() => {
            setTimeout(() => fitToScreen(), 100);
          }}
        />
      </div>
    </div>
  );
}
