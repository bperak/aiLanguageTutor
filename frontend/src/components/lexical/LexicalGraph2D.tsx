"use client";

import dynamic from "next/dynamic";
import { useEffect, useRef, useState } from "react";
import LexicalGraphSidebar from "./LexicalGraphSidebar";
import { apiGet } from "@/lib/api";

const ForceGraph2D = dynamic(() => import("react-force-graph-2d"), {
  ssr: false,
}) as any;

type GraphNode = {
  id: string;
  name?: string;
  hiragana?: string;
  translation?: string;
  level?: number;
  center?: boolean;
  pos?: string;
  domain?: string;
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
  center?: {
    id: string;
  };
};

type NodeDetailsResponse = {
  node: NodeDetails;
  neighbors: NeighborInfo[];
};

export default function LexicalGraph2D({
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
  labelTypes?: {
    kanji: boolean;
    hiragana: boolean;
    translation: boolean;
  };
  expandOnClick?: boolean;
  onCenterChange?: (center: string) => void;
  onDepthChange?: (depth: number) => void;
  onSearch?: () => void;
  onToggle3D?: () => void;
  onNodeDataChange?: (nodeData: { selectedNode: NodeDetails | null; neighbors: NeighborInfo[] }) => void;
}) {
  const graphRef = useRef<any>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [data, setData] = useState<{ nodes: GraphNode[]; links: GraphLink[] }>({
    nodes: [],
    links: [],
  });

  // Function to generate label text based on selected label types
  const generateNodeLabel = (node: GraphNode): string => {
    const parts: string[] = [];
    
    if (labelTypes.kanji && node.name) {
      parts.push(node.name);
    }
    
    if (labelTypes.hiragana && node.hiragana) {
      parts.push(node.hiragana);
    }
    
    if (labelTypes.translation && node.translation) {
      parts.push(node.translation);
    }
    
    
    // If no labels are selected, fallback to kanji or id
    if (parts.length === 0) {
      return node.name || node.id;
    }
    
    return parts.join(' | ');
  };
  const [loaded, setLoaded] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedNode, setSelectedNode] = useState<NodeDetails | null>(null);
  const [neighbors, setNeighbors] = useState<NeighborInfo[]>([]);
  const [searchInfo, setSearchInfo] = useState({
    totalNodes: 0,
    totalLinks: 0,
    searchTerm: "",
    searchField: "kanji"
  });
  const [currentCenter, setCurrentCenter] = useState(center);
  const [containerSize, setContainerSize] = useState({ width: 800, height: 600 });

  const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

  // Sanitize server data to avoid force-graph null source/target crashes
  function sanitizeGraphData(input: { nodes?: GraphNode[]; links?: GraphLink[] }): { nodes: GraphNode[]; links: GraphLink[] } {
    const rawNodes = input.nodes ?? [];
    const rawLinks = input.links ?? [];

    const idSet = new Set<string>();
    const nodes: GraphNode[] = [];
    for (const n of rawNodes) {
      const id = (n?.id || "").trim();
      if (!id) continue;
      if (idSet.has(id)) continue;
      idSet.add(id);
      nodes.push(n);
    }

    const links: GraphLink[] = [];
    for (const l of rawLinks) {
      const src = (l as any)?.source?.toString().trim();
      const tgt = (l as any)?.target?.toString().trim();
      if (!src || !tgt) continue;
      if (!idSet.has(src) || !idSet.has(tgt)) continue;
      if (src === tgt) continue;
      // Coerce weight
      const weight = (l as any).weight;
      let cleanWeight: number | undefined = undefined;
      if (typeof weight === 'number') cleanWeight = weight;
      else if (weight != null) {
        const parsed = Number(weight);
        cleanWeight = Number.isFinite(parsed) ? parsed : 1;
      }
      links.push({ ...(l as any), weight: cleanWeight });
    }

    return { nodes, links };
  }

  // Helper: consistently fit graph to screen with sensible padding
  const fitToScreen = (padding: number = 80, duration: number = 500) => {
    try {
      if (graphRef.current) {
        graphRef.current.zoomToFit(duration, padding);
      }
    } catch (e) {
      console.warn("2D graph fit failed:", e);
    }
  };

  // Measure container size
  useEffect(() => {
    const updateSize = () => {
      if (containerRef.current) {
        const rect = containerRef.current.getBoundingClientRect();
        setContainerSize({ width: rect.width, height: rect.height });
        // Re-fit on size changes for better visibility
        fitToScreen();
      }
    };

    updateSize();
    window.addEventListener('resize', updateSize);
    return () => window.removeEventListener('resize', updateSize);
  }, []);

  // Notify parent component when node data changes
  useEffect(() => {
    console.log("LexicalGraph2D: Node data changed", { selectedNode, neighbors });
    onNodeDataChange?.({ selectedNode, neighbors });
  }, [selectedNode, neighbors, onNodeDataChange]);

  useEffect(() => {
    let isMounted = true;
    async function load() {
      // Don't make API call if center is empty
      if (!center || center.trim() === '') {
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
        console.log("Fetching graph data from:", url);
        const json = await apiGet<GraphDataResponse>(url);
        console.log("Graph data received:", json);
        const sanitized = sanitizeGraphData(json);
        if (isMounted) {
          setData(sanitized);
          setLoaded(new Set([json.center?.id || center]));
          
          // Update current center
          setCurrentCenter(json.center?.id || center);
          
          // Update search info
          setSearchInfo({
            totalNodes: json.nodes?.length || 0,
            totalLinks: json.links?.length || 0,
            searchTerm: center,
            searchField: searchField
          });
          
          // Load details for center node
          if (json.center?.id) {
            await loadNodeDetails(json.center.id);
          }
        }
      } catch (e: any) {
        if (isMounted) setError(e?.message || "Failed to load graph");
      } finally {
        if (isMounted) setLoading(false);
      }
    }
    load();
    return () => {
      isMounted = false;
    };
  }, [apiBase, center, depth]);

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

  async function expand(nodeId: string) {
    if (!nodeId || nodeId.trim() === '') {
      return;
    }
    try {
      setLoaded(new Set([...Array.from(loaded), nodeId]));
    } catch {}
  }

  const handleNodeClick = async (node: any) => {
    if (node?.id && node.id.trim() !== '') {
      // Update parent component's center state
      onCenterChange?.(node.id);
      
      // Load node details for the sidebar
      await loadNodeDetails(node.id as string);
      
      // Fetch new graph data centered on this node
      try {
        setLoading(true);
        setError(null);
        // Derive the appropriate searchField from the node id to avoid 404s
        const idStr = String(node.id);
        const hiraganaRegex = /^[\u3040-\u309F\s]+$/;
        const japaneseRegex = /[\u4E00-\u9FAF\u30A0-\u30FF]/; // kanji/katakana
        const derivedField: 'kanji' | 'hiragana' | 'translation' =
          hiraganaRegex.test(idStr) ? 'hiragana' : (japaneseRegex.test(idStr) ? 'kanji' : 'translation');

        const tryOrder = Array.from(new Set<'kanji' | 'hiragana' | 'translation'>([
          derivedField,
          'kanji',
          'hiragana',
          'translation',
        ]));

        let json: GraphDataResponse | null = null;
        let lastError: any = null;
        for (const field of tryOrder) {
          const url = `/api/v1/lexical/graph?center=${encodeURIComponent(idStr)}&depth=${depth}&searchField=${field}`;
          console.log("Fetching new graph data centered on:", node.id, "from:", url);
          try {
            json = await apiGet<GraphDataResponse>(url);
            break;
          } catch (e: any) {
            lastError = e;
            // Only continue fallback on 404; rethrow other errors
            if (e?.response?.status !== 404) {
              throw e;
            }
          }
        }

        if (!json) {
          throw lastError || new Error('Failed to load graph for clicked node');
        }

        console.log("New graph data received:", json);
        const sanitized = sanitizeGraphData(json);
        
        // Update the graph data to show the new centered node
        setData(sanitized);
        setLoaded(new Set([json.center?.id || node.id]));
        
        // Update current center for the overlay
        setCurrentCenter(node.id);
        
        // Update search info
        setSearchInfo({
          totalNodes: json.nodes?.length || 0,
          totalLinks: json.links?.length || 0,
          searchTerm: node.id,
          searchField: derivedField
        });
        
        // Load details for the new center node
        if (json.center?.id) {
          await loadNodeDetails(json.center.id);
        }
      } catch (e: any) {
        console.error("Failed to load new graph:", e);
        setError(e?.message || "Failed to load new graph");
      } finally {
        setLoading(false);
      }
      
      if (expandOnClick) {
        await expand(node.id as string);
      }

      // After changing center, re-fit for optimal view
      setTimeout(() => fitToScreen(), 0);
    }
  };

  return (
    <div className="h-full w-full">
      {/* Mobile Node Details - Collapsible panel */}
      <div className="lg:hidden bg-white border rounded-lg">
        <details className="group">
          <summary className="flex items-center justify-between p-3 cursor-pointer hover:bg-gray-50">
            <span className="font-semibold text-sm">
              {selectedNode ? `Selected: ${selectedNode.kanji}` : 'Click a node to see details'}
            </span>
            <svg className="w-4 h-4 transition-transform group-open:rotate-180" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </summary>
          <div className="p-3 border-t space-y-3">
            {selectedNode ? (
              <>
                <div>
                  <div className="text-xl font-bold text-red-600">{selectedNode.kanji}</div>
                  <div className="text-gray-600">{selectedNode.hiragana}</div>
                  <div className="text-gray-800 font-medium">{selectedNode.translation}</div>
                </div>
                <div className="text-xs text-gray-600">
                  <div className="flex items-center gap-3">
                    <span><span className="font-medium">POS:</span> {selectedNode.pos || '-'}</span>
                    <span><span className="font-medium">Level:</span> {selectedNode.level || '-'}</span>
                    <span><span className="font-medium">Connections:</span> {selectedNode.connections || 0}</span>
                  </div>
                  {selectedNode.etymology && (
                    <div className="mt-1">
                      <span className="font-medium">Etymology:</span> {selectedNode.etymology}
                    </div>
                  )}
                </div>
              </>
            ) : (
              <div className="text-gray-500 text-sm">No node selected</div>
            )}
          </div>
        </details>
      </div>



      {/* Main Graph Area */}
      <div ref={containerRef} className="h-full border rounded-lg overflow-hidden relative">
        {loading && (
          <div className="absolute inset-0 bg-white bg-opacity-75 flex items-center justify-center z-10">
            <div className="text-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-2"></div>
              <div className="text-sm text-gray-600">Loading new graph...</div>
            </div>
          </div>
        )}
        {error && (
          <div className="p-2 text-sm text-red-600">Error: {error}</div>
        )}
        {!loading && !error && data.nodes.length === 0 && (
          <div className="p-4 text-center text-gray-500">
            {!center || center.trim() === '' ? (
              <div>
                <div className="text-lg mb-2">🔍 Enter a Japanese word to explore</div>
                <div className="text-sm">Type a kanji, hiragana, or English word to see its lexical network</div>
              </div>
            ) : (
              <div>
                <div className="text-lg mb-2">No data found</div>
                <div className="text-sm">Check if the backend API is running at {apiBase}</div>
              </div>
            )}
          </div>
        )}
        {!loading && !error && data.nodes.length > 0 && (
          <div className="absolute top-2 left-2 right-2 p-2 bg-white/20 backdrop-blur-sm border border-gray-200 rounded shadow-sm z-30">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3 text-xs text-gray-600">
                <span>Search node: <span className="text-red-600 font-medium">{currentCenter}</span></span>
                <span>Nodes: {data.nodes.length}</span>
                <span>Links: {data.links.length}</span>
                <select
                  className="px-2 py-1 text-xs border border-gray-300 rounded focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
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
                  className="px-2 py-1 text-xs border border-gray-300 rounded hover:bg-gray-50 transition-colors"
                >
                  3D
                </button>
                <button 
                  onClick={() => fitToScreen()}
                  className="px-2 py-1 text-xs border border-gray-300 rounded hover:bg-gray-50 transition-colors"
                >
                  Fit
                </button>
                <button 
                  onClick={() => fitToScreen()}
                  className="px-2 py-1 text-xs border border-gray-300 rounded hover:bg-gray-50 transition-colors"
                >
                  Reset
                </button>
              </div>
            </div>
          </div>
        )}
        <ForceGraph2D
          ref={graphRef}
          graphData={data}
          width={containerSize.width}
          height={containerSize.height}
          nodeLabel={(n: GraphNode) =>
            `${n.name || n.id}${n.hiragana ? ` (${n.hiragana})` : ""}${
              n.translation ? ` — ${n.translation}` : ""
            }`
          }
          nodeAutoColorBy={(n: GraphNode) => {
            if (colorBy === "pos") return (n as any).pos || "";
            if (colorBy === "domain") return (n as any).domain || "";
            return `${n.level ?? 0}`;
          }}

          nodeColor={(n: GraphNode) => {
            // Make center node red, selected node orange, others default
            if (n.center) return "#dc2626"; // red-600
            if (selectedNode && n.id === selectedNode.kanji) return "#ea580c"; // orange-600
            return undefined; // use auto color
          }}
          linkWidth={(l: any) => {
            // Link width based on weight - more weight = more visible
            const weight = l.weight || 1;
            return Math.max(0.5, Math.min(4, weight / 2)); // Scale weight to reasonable width
          }}
          linkColor={(l: any) => {
            // Link color based on weight - more weight = more opaque
            const weight = l.weight || 1;
            const alpha = Math.max(0.3, Math.min(0.9, weight / 10)); // Scale weight to opacity
            return `rgba(60,120,255,${alpha})`;
          }}
          linkDirectionalParticles={1}
          linkDirectionalParticleSpeed={0.004}
          onNodeClick={handleNodeClick}
          nodeCanvasObject={(node: any, ctx: any, globalScale: any) => {
            // Keep nodes small but enhance degree-based sizing
            const baseSize = node.center ? 4 : 2;
            const degreeSize = Math.min(3, (node.connections || 0) / 4); // Subtle degree scaling
            const size = baseSize + degreeSize;
            const color = node.color || '#3b82f6';
            
            ctx.beginPath();
            ctx.arc(node.x, node.y, size, 0, 2 * Math.PI);
            ctx.fillStyle = color;
            ctx.fill();
            
            // Draw border
            ctx.strokeStyle = '#1f2937';
            ctx.lineWidth = 1;
            ctx.stroke();
            
            // Draw label with size based on degree/weighted degree
            const label = generateNodeLabel(node);
            if (label) {
              // Font size based on degree/connections
              const baseFontSize = node.center ? 8 : 6;
              const degreeBonus = Math.min(4, (node.connections || 0) / 3); // Scale degree to font size
              const fontSize = baseFontSize + degreeBonus;
              
              ctx.font = `${fontSize}px Arial`;
              ctx.textAlign = 'center';
              ctx.textBaseline = 'middle';
              
              // Measure text for background
              const textWidth = ctx.measureText(label).width;
              const textHeight = fontSize;
              const padding = 2; // Padding for rounded look
              const radius = 3; // Rounded corners
              
              // Create rounded background that feels integrated
              const bgX = node.x - textWidth/2 - padding;
              const bgY = node.y - textHeight/2 - padding;
              const bgWidth = textWidth + padding * 2;
              const bgHeight = textHeight + padding * 2;
              
              // Draw rounded rectangle background manually (for compatibility)
              ctx.beginPath();
              ctx.moveTo(bgX + radius, bgY);
              ctx.lineTo(bgX + bgWidth - radius, bgY);
              ctx.quadraticCurveTo(bgX + bgWidth, bgY, bgX + bgWidth, bgY + radius);
              ctx.lineTo(bgX + bgWidth, bgY + bgHeight - radius);
              ctx.quadraticCurveTo(bgX + bgWidth, bgY + bgHeight, bgX + bgWidth - radius, bgY + bgHeight);
              ctx.lineTo(bgX + radius, bgY + bgHeight);
              ctx.quadraticCurveTo(bgX, bgY + bgHeight, bgX, bgY + bgHeight - radius);
              ctx.lineTo(bgX, bgY + radius);
              ctx.quadraticCurveTo(bgX, bgY, bgX + radius, bgY);
              ctx.closePath();
              
              // Fill with enhanced background for better visibility
              ctx.fillStyle = 'rgba(255, 255, 255, 0.85)';
              ctx.fill();
              
              // Add slightly more visible border for better integration
              ctx.strokeStyle = 'rgba(0, 0, 0, 0.15)';
              ctx.lineWidth = 0.8;
              ctx.stroke();
              
              // Draw text ON the node (centered)
              ctx.fillStyle = node.center ? '#dc2626' : '#1f2937';
              ctx.fillText(label, node.x, node.y);
            }
          }}
          onEngineStop={() => {
            // Auto-center and fit the graph when it finishes loading
            setTimeout(() => {
              fitToScreen();
            }, 100);
          }}
        />
      </div>

    </div>
  );
}
