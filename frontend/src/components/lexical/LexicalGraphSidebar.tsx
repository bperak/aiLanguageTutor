"use client";

import { useState } from "react";
import WordInfoPanel from "./WordInfoPanel";

interface NodeDetails {
  kanji: string;
  hiragana: string;
  translation: string;
  pos?: string;
  level?: string | number;
  connections?: number;
  etymology?: string;
}

interface NeighborInfo {
  kanji: string;
  hiragana: string;
  translation: string;
  synonym_strength: number;
  pos: string;
  level: string | number;
  relation_type: string;
  mutual_sense: string;
}

interface LexicalGraphSidebarProps {
  selectedNode: NodeDetails | null;
  neighbors: NeighborInfo[];
  onNodeClick: (nodeId: string) => void;
}

export default function LexicalGraphSidebar({
  selectedNode,
  neighbors,
  onNodeClick,
}: LexicalGraphSidebarProps) {
  const [activeTab, setActiveTab] = useState<"graph" | "description" | "lesson">("graph");

  const tabs = [
    { id: "graph" as const, label: "Graph", icon: "📊" },
    { id: "description" as const, label: "Description", icon: "📖" },
    { id: "lesson" as const, label: "Lesson", icon: "🎓" },
  ];

  return (
    <div className="hidden lg:flex w-80 bg-white border rounded-lg overflow-hidden">
      {/* Vertical Tabs */}
      <div className="w-16 bg-gray-50 border-r flex flex-col">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex flex-col items-center justify-center p-3 text-xs font-medium transition-colors ${
              activeTab === tab.id
                ? "bg-blue-100 text-blue-700 border-r-2 border-blue-500"
                : "text-gray-600 hover:bg-gray-100"
            }`}
            title={tab.label}
          >
            <span className="text-lg mb-1">{tab.icon}</span>
            <span className="writing-vertical-rl">
              {tab.label}
            </span>
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div className="flex-1 p-4 overflow-y-auto">
        {activeTab === "graph" && (
          <div className="space-y-4">
            <h3 className="font-semibold text-lg mb-4">Selected Node</h3>
            {selectedNode ? (
              <div className="space-y-3">
                <div>
                  <div className="text-2xl font-bold text-red-600">{selectedNode.kanji}</div>
                  <div className="text-gray-600">{selectedNode.hiragana}</div>
                  <div className="text-gray-800 font-medium">{selectedNode.translation}</div>
                </div>
                <div className="text-xs text-gray-600">
                  <div className="flex items-center gap-4">
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
              </div>
            ) : (
              <div className="text-gray-500">Click a node to see details</div>
            )}
            
            <div className="mt-6">
              <h4 className="font-semibold mb-3">Neighbors (Synonyms)</h4>
              <div className="space-y-2 max-h-60 overflow-y-auto">
                {neighbors.map((neighbor, index) => (
                  <button
                    key={index}
                    onClick={() => onNodeClick(neighbor.kanji)}
                    className="w-full p-2 border rounded text-sm text-left hover:bg-blue-50 hover:border-blue-300 transition-colors"
                  >
                    <div className="font-medium">{neighbor.kanji}</div>
                    <div className="text-gray-600">{neighbor.hiragana}</div>
                    <div className="text-gray-800">{neighbor.translation}</div>
                    <div className="text-xs text-gray-500">
                      Synonym: {neighbor.synonym_strength.toFixed(2)} | 
                      POS: {neighbor.pos} | 
                      Level: {neighbor.level}
                    </div>
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {activeTab === "description" && (
          <WordInfoPanel selectedNode={selectedNode} />
        )}

        {activeTab === "lesson" && (
          <div className="space-y-4">
            <h3 className="font-semibold text-lg mb-4">AI Lesson</h3>
            {selectedNode ? (
              <div className="space-y-4">
                <div className="bg-gradient-to-r from-blue-50 to-purple-50 p-4 rounded-lg">
                  <h4 className="font-medium text-lg mb-2">Learning: {selectedNode.kanji}</h4>
                  <div className="text-gray-600 mb-3">{selectedNode.hiragana} - {selectedNode.translation}</div>
                  
                  <div className="space-y-3">
                    <div className="bg-white p-3 rounded border">
                      <h5 className="font-medium mb-2">📚 Study Points</h5>
                      <ul className="text-sm space-y-1">
                        <li>• Understanding the kanji components</li>
                        <li>• Related vocabulary and synonyms</li>
                        <li>• Cultural context and usage</li>
                      </ul>
                    </div>
                    
                    <div className="bg-white p-3 rounded border">
                      <h5 className="font-medium mb-2">💬 Interactive Chat</h5>
                      <div className="text-sm text-gray-600 mb-2">
                        Ask questions about this word or practice using it in sentences.
                      </div>
                      <div className="space-y-2">
                        <div className="bg-gray-100 p-2 rounded text-sm">
                          <div className="font-medium">AI Tutor:</div>
                          <div>Hello! I'm here to help you learn about "{selectedNode.kanji}". What would you like to know?</div>
                        </div>
                        <div className="flex gap-2">
                          <input 
                            type="text" 
                            placeholder="Ask a question..." 
                            className="flex-1 px-2 py-1 text-sm border rounded"
                          />
                          <button className="px-3 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700">
                            Send
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              <div className="text-gray-500 text-center py-8">
                Select a node to start an AI lesson
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
