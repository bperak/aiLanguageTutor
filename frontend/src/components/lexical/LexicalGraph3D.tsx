"use client";

import dynamic from "next/dynamic";
import { useEffect, useMemo, useRef, useState } from "react";
import LexicalGraphSidebar from "./LexicalGraphSidebar";
import SpriteText from "three-spritetext";

const ForceGraph3D = dynamic(() => import("react-force-graph-3d"), {
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
  
  // Debug logging for environment variables
  useEffect(() => {
    console.log("Environment check:", {
      NEXT_PUBLIC_API_BASE_URL: process.env.NEXT_PUBLIC_API_BASE_URL,
      apiBase: apiBase,
      NODE_ENV: process.env.NODE_ENV
    });
  }, [apiBase]);

  // Measure container size
  useEffect(() => {
    const updateSize = () => {
      if (containerRef.current) {
        const rect = containerRef.current.getBoundingClientRect();
        setContainerSize({ width: rect.width, height: rect.height });
        // Refit on resize for better visibility
        try {
          graphRef.current?.zoomToFit(500, 100);
        } catch {}
      }
    };

    updateSize();
    window.addEventListener('resize', updateSize);
    return () => window.removeEventListener('resize', updateSize);
  }, []);

  // Notify parent component when node data changes
  useEffect(() => {
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
        const url = `${apiBase}/api/v1/lexical/graph?center=${encodeURIComponent(
          center
        )}&depth=${depth}&searchField=${searchField}`;
        console.log("Loading 3D graph from:", url);
        console.log("API Base URL:", apiBase);
        console.log("Center:", center);
        console.log("Depth:", depth);
        console.log("Search Field:", searchField);
        
        const res = await fetch(url, {
          method: 'GET',
          headers: {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
          },
        });
        
        console.log("Response status:", res.status);
        console.log("Response headers:", Object.fromEntries(res.headers.entries()));
        
        if (!res.ok) {
          const errorText = await res.text();
          console.error("Response error text:", errorText);
          throw new Error(`Failed to load graph: ${res.status} - ${errorText}`);
        }
        
        const json = await res.json();
        console.log("3D Graph data received:", json);
        if (isMounted) {
          setData({ nodes: json.nodes ?? [], links: json.links ?? [] });
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
        console.error("Error loading 3D graph:", e);
        console.error("Error details:", {
          name: e.name,
          message: e.message,
          stack: e.stack,
          cause: e.cause
        });
        if (isMounted) {
          const errorMessage = e?.message || "Failed to load graph";
          setError(`${errorMessage} (API: ${apiBase})`);
        }
      } finally {
        if (isMounted) setLoading(false);
      }
    }
    load();
    return () => {
      isMounted = false;
    };
  }, [apiBase, center, depth, searchField]);





  async function loadNodeDetails(nodeId: string) {
    try {
      const url = `${apiBase}/api/v1/lexical/node/${encodeURIComponent(nodeId)}`;
      console.log("Loading node details from:", url);
      const res = await fetch(url, {
        method: 'GET',
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json',
        },
      });
      if (res.ok) {
        const details = await res.json();
        setSelectedNode(details.node);
        setNeighbors(details.neighbors || []);
      } else {
        console.error("Failed to load node details:", res.status, await res.text());
      }
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
        // Derive appropriate searchField from node id to avoid 404s when ids are hiragana/translation
        const idStr = String(node.id);
        const hiraganaRegex = /^[\u3040-\u309F\s]+$/;
        const japaneseRegex = /[\u4E00-\u9FAF\u30A0-\u30FF]/; // kanji/katakana
        const derivedField: 'kanji' | 'hiragana' | 'translation' =
          hiraganaRegex.test(idStr) ? 'hiragana' : (japaneseRegex.test(idStr) ? 'kanji' : 'translation');
        const url = `${apiBase}/api/v1/lexical/graph?center=${encodeURIComponent(
          idStr
        )}&depth=${depth}&searchField=${derivedField}`;
        console.log("Fetching new 3D graph data centered on:", node.id, "from:", url);
        const res = await fetch(url, {
          method: 'GET',
          headers: {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
          },
        });
        if (!res.ok) {
          const errorText = await res.text();
          throw new Error(`Failed to load graph: ${res.status} - ${errorText}`);
        }
        const json = await res.json();
        console.log("New 3D graph data received:", json);
        
        // Update the graph data to show the new centered node
        setData({ nodes: json.nodes ?? [], links: json.links ?? [] });
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
        console.error("Failed to load new 3D graph:", e);
        setError(e?.message || "Failed to load new graph");
      } finally {
        setLoading(false);
      }
      
      // 3D camera focus using zoomToFit for consistent framing
      try {
        if (graphRef.current) {
          graphRef.current.zoomToFit(500, 100);
        }
      } catch (e) {
        console.warn("3D camera positioning failed:", e);
      }
      
      if (expandOnClick) {
        await expand(node.id as string);
      }
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
      <div ref={containerRef} className="h-full border rounded-lg overflow-hidden relative bg-gray-50">
        {loading && (
          <div className="absolute inset-0 bg-white bg-opacity-75 flex items-center justify-center z-10">
            <div className="text-lg">Loading 3D graph...</div>
          </div>
        )}
        {error && (
          <div className="absolute top-2 left-2 right-2 p-2 text-sm text-red-600 bg-red-50 border border-red-200 rounded z-10">
            Error: {error}
          </div>
        )}
        {!loading && !error && data.nodes.length === 0 && (
          <div className="absolute inset-0 flex items-center justify-center bg-gray-50/80 backdrop-blur-sm z-20">
            <div className="p-6 text-center text-gray-600 bg-white rounded-lg shadow-lg border">
              {!center || center.trim() === '' ? (
                <div>
                  <div className="text-2xl mb-3">🔍</div>
                  <div className="text-lg mb-2 font-medium">Enter a Japanese word to explore</div>
                  <div className="text-sm">Type a kanji, hiragana, or English word to see its 3D lexical network</div>
                </div>
              ) : (
                <div>
                  <div className="text-2xl mb-3">📊</div>
                  <div className="text-lg mb-2 font-medium">No data found</div>
                  <div className="text-sm">Check if the backend API is running at {apiBase}</div>
                </div>
              )}
            </div>
          </div>
        )}
                        {/* Graph Info Overlay - Always show when data exists */}
        {data.nodes.length > 0 && (
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
                  2D
                </button>
                <button 
                  onClick={() => {
                    try {
                      graphRef.current?.zoomToFit(500, 100);
                    } catch (e) {
                      console.warn("3D graph fit failed:", e);
                    }
                  }}
                  className="px-2 py-1 text-xs border border-gray-300 rounded hover:bg-gray-50 transition-colors"
                >
                  Fit
                </button>
                <button 
                  onClick={() => {
                    try {
                      graphRef.current?.zoomToFit(500, 100);
                    } catch (e) {
                      console.warn("3D graph reset failed:", e);
                    }
                  }}
                  className="px-2 py-1 text-xs border border-gray-300 rounded hover:bg-gray-50 transition-colors"
                >
                  Reset
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
          nodeLabel={(n: GraphNode) => generateNodeLabel(n)}
          nodeVal={(n: GraphNode) => {
            // Size based on degree (connections) - enhanced scaling
            const baseSize = n.center ? 8 : 3;
            const degreeSize = Math.min(6, (n.connections || 0) / 3); // More pronounced degree scaling
            return baseSize + degreeSize;
          }}
          nodeThreeObjectExtend={true}
          nodeThreeObject={(node: GraphNode) => {
            try {
              // Use three-spritetext (like in Vasturiano example)
              const sprite = new SpriteText(generateNodeLabel(node));
              
              // Font size based on degree/connections (like 2D)
              const baseFontSize = node.center ? 12 : 10;
              const degreeBonus = Math.min(4, (node.connections || 0) / 3);
              const fontSize = baseFontSize + degreeBonus;
              
              // Colors with enhanced borders for better visibility
              if (node.center) {
                sprite.color = '#dc2626'; // Red for center
                sprite.strokeColor = '#ffffff'; // White border
                sprite.strokeWidth = 0.025; // Slightly thicker border
              } else {
                sprite.color = '#1f2937'; // Dark gray for others
                sprite.strokeColor = '#ffffff'; // White border
                sprite.strokeWidth = 0.02; // Thicker border for better visibility
              }
              
              sprite.textHeight = fontSize;
              sprite.offsetY = -0.1; // Use offsetY to position text closer to node center
              
              // Ensure labels are always rendered in front of nodes
              (sprite as any).renderOrder = 999; // High render order = rendered last (on top)
              (sprite as any).material.depthTest = false; // Disable depth testing = always visible
              
              return sprite;
            } catch (error) {
              console.warn('3D label creation failed:', error);
              return null;
            }
          }}
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
          onNodeClick={handleNodeClick}
          backgroundColor="#ffffff"
          showNavInfo={false}
          enableNodeDrag={true}
          enableNavigationControls={true}
          nodeRelSize={6}
          linkOpacity={0.6}
          linkCurvature={0.1}
          linkDirectionalParticles={1}
          linkDirectionalParticleSpeed={0.004}
          onEngineStop={() => {
            // Auto-center and fit the graph when it finishes loading
            setTimeout(() => {
              if (graphRef.current) {
                try {
                  graphRef.current.zoomToFit(500, 100);
                } catch (e) {
                  console.warn("3D graph auto-fit failed:", e);
                }
              }
            }, 100);
          }}
        />
      </div>

    </div>
  );
}
