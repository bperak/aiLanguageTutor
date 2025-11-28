"use client";

import { useState, useEffect } from "react";
import LexicalGraph3D from "@/components/lexical/LexicalGraph3D";
import LexicalGraph2D from "@/components/lexical/LexicalGraph2D";
import WordInfoPanel from "@/components/lexical/WordInfoPanel";

export default function LexicalGraphPage() {
  const [center, setCenter] = useState("日本");
  const [depth, setDepth] = useState(1);
  const [mode3d, setMode3d] = useState(false);
  const [colorBy, setColorBy] = useState<"domain" | "pos" | "level">("domain");
  const [searchFields, setSearchFields] = useState<{
    kanji: boolean;
    hiragana: boolean;
    translation: boolean;
  }>({
    kanji: true,
    hiragana: true,
    translation: true,
  });
  const [showSearchFieldDropdown, setShowSearchFieldDropdown] = useState(false);
  const [exactMatch, setExactMatch] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [labelTypes, setLabelTypes] = useState<{
    kanji: boolean;
    hiragana: boolean;
    translation: boolean;
  }>({
    kanji: true,
    hiragana: false,
    translation: false,
  });
  const [showLabelDropdown, setShowLabelDropdown] = useState(false);
  const [activeTab, setActiveTab] = useState<"graph" | "description" | "lesson">("graph");
  const [graphNodeData, setGraphNodeData] = useState<{
    selectedNode: any | null;
    neighbors: any[];
  }>({ selectedNode: null, neighbors: [] });

  // Helper function to detect the appropriate search field based on input content
  const detectSearchField = (input: string): "kanji" | "hiragana" | "translation" => {
    if (!input.trim()) {
      // Empty input - return first enabled field
      if (searchFields.kanji) return "kanji";
      if (searchFields.hiragana) return "hiragana";
      if (searchFields.translation) return "translation";
      return "kanji";
    }

    const trimmedInput = input.trim();
    
    // If input contains only hiragana characters (ひらがな)
    const hiraganaRegex = /^[\u3040-\u309F\s]+$/;
    if (hiraganaRegex.test(trimmedInput) && searchFields.hiragana) {
      console.log("Detected hiragana input:", trimmedInput);
      return "hiragana";
    }
    
    // If input contains kanji or katakana characters (漢字・カタカナ)
    const japaneseRegex = /[\u4E00-\u9FAF\u30A0-\u30FF]/;
    if (japaneseRegex.test(trimmedInput) && searchFields.kanji) {
      console.log("Detected Japanese (kanji/katakana) input:", trimmedInput);
      return "kanji";
    }
    
    // If input contains only English letters (likely translation)
    const englishRegex = /^[a-zA-Z\s\-']+$/;
    if (englishRegex.test(trimmedInput) && searchFields.translation) {
      console.log("Detected English translation input:", trimmedInput);
      return "translation";
    }
    
    // Fallback to first enabled field
    console.log("Using fallback search field for input:", trimmedInput);
    if (searchFields.kanji) return "kanji";
    if (searchFields.hiragana) return "hiragana";
    if (searchFields.translation) return "translation";
    return "kanji"; // final fallback
  };

  // Click outside handler for dropdowns
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      const target = event.target as Element;
      if (!target.closest('.dropdown-container')) {
        setShowSearchFieldDropdown(false);
        setShowLabelDropdown(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  return (
    <div className="max-w-7xl mx-auto p-2 sm:p-4 space-y-3 sm:space-y-4">
      {/* Title Row with Search and Settings */}
      <div className="flex flex-col sm:flex-row sm:items-center gap-3">
        <h1 className="text-xl sm:text-2xl font-bold text-gray-800">Lexical Graph</h1>
        
        {/* Search Input */}
        <div className="flex items-center gap-2">
          <div className="relative">
            <input
              className="px-3 py-1.5 text-sm border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500 min-w-[200px]"
              value={center}
              onChange={(e) => setCenter(e.target.value)}
              placeholder="Enter kanji/hiragana/translation"
            />
            {/* Search field indicator */}
            {center && (
              <div className="absolute -bottom-5 left-0 text-xs text-gray-500">
                Searching in: {detectSearchField(center)}
              </div>
            )}
            {/* Search fields indicator */}
            <div className="absolute -top-1 -right-1 flex gap-1">
              {Object.entries(searchFields)
                .filter(([_, enabled]) => enabled)
                .map(([key, _]) => {
                  const isActive = detectSearchField(center) === key;
                  return (
                    <span
                      key={key}
                      className={`inline-flex items-center px-1.5 py-0.5 rounded-full text-xs font-medium ${
                        isActive 
                          ? 'bg-green-100 text-green-800 border border-green-300' 
                          : 'bg-blue-100 text-blue-800'
                      }`}
                      title={`${key.charAt(0).toUpperCase() + key.slice(1)} ${isActive ? '(active)' : ''}`}
                    >
                      {key.charAt(0).toUpperCase()}
                    </span>
                  );
                })}
            </div>
          </div>
          <button
            onClick={() => {
              // Trigger search by updating state
              setCenter(center);
            }}
            className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
          >
            Search
          </button>
        </div>
        
        {/* Settings Button */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowSettings(!showSettings)}
            className="px-3 py-1.5 text-sm border border-gray-300 rounded-md hover:bg-gray-50 focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
          >
            ⚙️ Settings
          </button>
        </div>
      </div>
      

      {/* Settings Panel (Collapsible) */}
      {showSettings && (
        <div className="bg-gray-50 border rounded-lg p-3 sm:p-4 relative z-50">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 items-start">
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Color by:</label>
              <select
                className="w-full border px-2 py-1.5 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm"
                value={colorBy}
                onChange={(e) => setColorBy(e.target.value as any)}
              >
                <option value="domain">Domain</option>
                <option value="pos">POS</option>
                <option value="level">Level</option>
              </select>
            </div>
            
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Search Fields:</label>
              <div className="relative dropdown-container">
                <button
                  type="button"
                  onClick={() => setShowSearchFieldDropdown(!showSearchFieldDropdown)}
                  className="w-full border px-2 py-1.5 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm bg-white text-left flex items-center justify-between"
                >
                  <span>
                    {Object.entries(searchFields)
                      .filter(([_, enabled]) => enabled)
                      .map(([key, _]) => {
                        const labels = { kanji: 'Kanji', hiragana: 'Hiragana', translation: 'Translation' };
                        return labels[key as keyof typeof labels];
                      })
                      .join(', ') || 'Select search fields...'}
                  </span>
                  <span className="text-gray-400">▼</span>
                </button>
                {showSearchFieldDropdown && (
                  <div className="absolute top-full left-0 right-0 mt-1 bg-white border border-gray-300 rounded-md shadow-lg z-[60]">
                    <div className="p-2 space-y-1">
                      {[
                        { key: 'kanji', label: 'Kanji' },
                        { key: 'hiragana', label: 'Hiragana' },
                        { key: 'translation', label: 'Translation' }
                      ].map(({ key, label }) => (
                        <label key={key} className="flex items-center space-x-2 text-sm cursor-pointer hover:bg-gray-50 p-1 rounded">
                          <input
                            type="checkbox"
                            checked={searchFields[key as keyof typeof searchFields]}
                            onChange={(e) => {
                              setSearchFields(prev => ({
                                ...prev,
                                [key]: e.target.checked
                              }));
                            }}
                            className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                          />
                          <span>{label}</span>
                        </label>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
            
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Node Labels:</label>
              <div className="relative dropdown-container">
                <button
                  type="button"
                  onClick={() => setShowLabelDropdown(!showLabelDropdown)}
                  className="w-full border px-2 py-1.5 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm bg-white text-left flex items-center justify-between"
                >
                  <span>
                    {Object.entries(labelTypes)
                      .filter(([_, enabled]) => enabled)
                      .map(([key, _]) => {
                        const labels = { kanji: 'Kanji', hiragana: 'Hiragana', translation: 'Translation' };
                        return labels[key as keyof typeof labels];
                      })
                      .join(', ') || 'Select label types...'}
                  </span>
                  <span className="text-gray-400">▼</span>
                </button>
                {showLabelDropdown && (
                  <div className="absolute top-full left-0 right-0 mt-1 bg-white border border-gray-300 rounded-md shadow-lg z-[60]">
                    <div className="p-2 space-y-1">
                      {[
                        { key: 'kanji', label: 'Kanji' },
                        { key: 'hiragana', label: 'Hiragana' },
                        { key: 'translation', label: 'Translation' }
                      ].map(({ key, label }) => (
                        <label key={key} className="flex items-center space-x-2 text-sm cursor-pointer hover:bg-gray-50 p-1 rounded">
                          <input
                            type="checkbox"
                            checked={labelTypes[key as keyof typeof labelTypes]}
                            onChange={(e) => {
                              setLabelTypes(prev => ({
                                ...prev,
                                [key]: e.target.checked
                              }));
                            }}
                            className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                          />
                          <span>{label}</span>
                        </label>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
            
            <div className="flex items-center justify-between">
              <div className="flex items-center">
                <input
                  type="checkbox"
                  id="exact-match"
                  checked={exactMatch}
                  onChange={(e) => setExactMatch(e.target.checked)}
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <label htmlFor="exact-match" className="ml-2 text-xs font-medium text-gray-700">
                  Exact Match
                </label>
              </div>
              <button
                onClick={() => setShowSettings(false)}
                className="px-3 py-1.5 text-sm text-gray-600 hover:text-gray-800"
              >
                ✕ Close
              </button>
            </div>
          </div>
        </div>
      )}
      
      
      {/* Main Content Area with Global Tabs */}
      <div className="flex h-[70vh] gap-4 w-full overflow-hidden">
        {/* Left Sidebar - Global Tabs */}
        <div className="w-16 bg-gray-50 border rounded-lg flex flex-col">
                  {[
          { id: "graph" as const, label: "Graph" },
          { id: "description" as const, label: "Info" },
          { id: "lesson" as const, label: "Lesson" },
        ].map((tab) => (
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
              <span className="writing-vertical-rl">
                {tab.label}
              </span>
            </button>
          ))}
        </div>

        {/* Main Content Area */}
        <div className="flex-1 bg-white border rounded-lg shadow-sm overflow-hidden">
          {activeTab === "graph" && (
            mode3d ? (
              <LexicalGraph3D 
                center={center} 
                depth={depth} 
                colorBy={colorBy} 
                searchField={detectSearchField(center)}
                labelTypes={labelTypes}
                expandOnClick 
                onCenterChange={setCenter}
                onDepthChange={(newDepth) => {
                  console.log("Depth changed to:", newDepth);
                  setDepth(newDepth);
                }}
                onSearch={() => {
                  // Trigger search by updating state
                  setCenter(center);
                }}
                onToggle3D={() => {
                  console.log("Switching to 2D mode");
                  setMode3d(false);
                }}
                onNodeDataChange={setGraphNodeData}
              />
            ) : (
              <LexicalGraph2D 
                center={center} 
                depth={depth} 
                colorBy={colorBy} 
                searchField={detectSearchField(center)}
                labelTypes={labelTypes}
                expandOnClick 
                onCenterChange={setCenter}
                onDepthChange={(newDepth) => {
                  console.log("Depth changed to:", newDepth);
                  setDepth(newDepth);
                }}
                onSearch={() => {
                  // Trigger search by updating state
                  setCenter(center);
                }}
                onToggle3D={() => {
                  console.log("Switching to 3D mode");
                  setMode3d(true);
                }}
                onNodeDataChange={setGraphNodeData}
              />
            )
          )}

                                          {activeTab === "description" && (
            <div className="h-full p-6 overflow-y-auto">
              <WordInfoPanel 
                selectedNode={graphNodeData.selectedNode ? {
                  kanji: graphNodeData.selectedNode.kanji,
                  hiragana: graphNodeData.selectedNode.hiragana,
                  translation: graphNodeData.selectedNode.translation,
                  pos: graphNodeData.selectedNode.pos,
                  level: graphNodeData.selectedNode.level,
                  connections: graphNodeData.selectedNode.connections,
                  etymology: graphNodeData.selectedNode.etymology
                } : null} 
              />
            </div>
          )}

          {activeTab === "lesson" && (
            <div className="h-full p-6 overflow-y-auto">
              <h2 className="text-2xl font-bold mb-4">AI Language Lesson</h2>
              <div className="space-y-6">
                <div className="bg-gradient-to-r from-blue-50 to-purple-50 p-4 rounded-lg">
                  <h3 className="text-xl font-semibold mb-2">Learning: {center}</h3>
                  <p className="text-gray-600">Interactive AI-powered lesson content</p>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="bg-yellow-50 p-4 rounded-lg">
                    <h4 className="font-semibold mb-2">Study Points</h4>
                    <ul className="text-sm space-y-1">
                      <li>• Understanding the kanji components</li>
                      <li>• Related vocabulary and synonyms</li>
                      <li>• Cultural context and usage</li>
                    </ul>
                  </div>
                  <div className="bg-pink-50 p-4 rounded-lg">
                    <h4 className="font-semibold mb-2">Practice Exercises</h4>
                    <p className="text-sm text-gray-600">Interactive exercises and quizzes</p>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Right Sidebar - Context Content */}
        <div className="w-80 bg-white border rounded-lg shadow-sm">
          {activeTab === "graph" && (
            <div className="h-full p-4 overflow-y-auto">
              <h3 className="font-semibold text-lg mb-4">Selected Node</h3>
              {graphNodeData.selectedNode ? (
                <div className="space-y-4">
                  <div className="bg-gray-50 p-3 rounded">
                    <div className="text-2xl font-bold text-red-600 mb-1">{graphNodeData.selectedNode.kanji}</div>
                    <div className="text-gray-600 mb-1">{graphNodeData.selectedNode.hiragana}</div>
                    <div className="text-gray-800 font-medium mb-2">{graphNodeData.selectedNode.translation}</div>
                    <div className="text-xs text-gray-600">
                      <div className="flex items-center gap-4">
                        <span><span className="font-medium">POS:</span> {graphNodeData.selectedNode.pos || '-'}</span>
                        <span><span className="font-medium">Level:</span> {graphNodeData.selectedNode.level || '-'}</span>
                        <span><span className="font-medium">Connections:</span> {graphNodeData.selectedNode.connections || 0}</span>
                      </div>
                      {graphNodeData.selectedNode.etymology && (
                        <div className="mt-1">
                          <span className="font-medium">Etymology:</span> {graphNodeData.selectedNode.etymology}
                        </div>
                      )}
                    </div>
                  </div>
                  
                  <div className="bg-blue-50 p-3 rounded">
                    <h4 className="font-medium mb-3">Neighbors (Synonyms)</h4>
                    <div className="space-y-2 max-h-60 overflow-y-auto">
                      {graphNodeData.neighbors.map((neighbor, index) => (
                        <button
                          key={index}
                          onClick={() => setCenter(neighbor.kanji)}
                          className="w-full p-2 border rounded text-sm text-left hover:bg-blue-100 hover:border-blue-300 transition-colors"
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
              ) : (
                <div className="text-gray-500 text-center py-8">
                  Click a node to see details
                </div>
              )}
            </div>
          )}

                                {activeTab === "description" && (
                        <div className="h-full p-4 overflow-y-auto">
                          <h3 className="font-semibold text-lg mb-4">Additional Information</h3>
              <div className="space-y-4">
                <div className="bg-gray-50 p-3 rounded">
                  <h4 className="font-medium mb-2">Etymology</h4>
                  <p className="text-sm text-gray-600">Word origin and history</p>
                </div>
                <div className="bg-green-50 p-3 rounded">
                  <h4 className="font-medium mb-2">Related Words</h4>
                  <p className="text-sm text-gray-600">Synonyms, antonyms, and related terms</p>
                </div>
                <div className="bg-blue-50 p-3 rounded">
                  <h4 className="font-medium mb-2">Cultural Notes</h4>
                  <p className="text-sm text-gray-600">Cultural context and usage</p>
                </div>
              </div>
            </div>
          )}

          {activeTab === "lesson" && (
            <div className="h-full p-4 overflow-y-auto">
              <h3 className="font-semibold text-lg mb-4">AI Chat Assistant</h3>
              <div className="space-y-4">
                <div className="bg-gray-100 p-3 rounded">
                  <div className="font-medium mb-1">AI Tutor:</div>
                  <div className="text-sm">Hello! I'm here to help you learn about "{center}". What would you like to know?</div>
                </div>
                <div className="space-y-2">
                  <input 
                    type="text" 
                    placeholder="Ask a question..." 
                    className="w-full px-3 py-2 text-sm border rounded focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  />
                  <button className="w-full px-3 py-2 text-sm bg-blue-600 text-white rounded hover:bg-blue-700">
                    Send Message
                  </button>
                </div>
                <div className="bg-yellow-50 p-3 rounded">
                  <h4 className="font-medium mb-2">Quick Actions</h4>
                  <div className="space-y-1">
                    <button className="w-full text-left text-sm text-blue-600 hover:underline">Explain pronunciation</button>
                    <button className="w-full text-left text-sm text-blue-600 hover:underline">Show usage examples</button>
                    <button className="w-full text-left text-sm text-blue-600 hover:underline">Create practice quiz</button>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
      
      <p className="text-xs text-gray-500 text-center">
        Powered by react-force-graph (2D/3D). Data from Neo4j lexical network.
      </p>
    </div>
  );
}
