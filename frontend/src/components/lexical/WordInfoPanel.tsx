"use client";

import React, { useEffect, useState } from "react";
import {
  BookOpen,
  Globe,
  Lightbulb,
  Loader2,
  RefreshCw,
  Zap,
} from "lucide-react";
import { apiGet, apiPost } from "@/lib/api";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface WordInfoPanelProps {
  selectedNode: {
    kanji: string;
    hiragana: string;
    translation: string;
    pos?: string;
    level?: string | number;
    connections?: number;
    etymology?: string;
  } | null;
}

interface AIWordContent {
  word_kanji: string;
  definitions: string[];
  examples: string[];
  cultural_notes: string;
  kanji_breakdown: string;
  grammar_patterns: string[];
  collocations: string[];
  learning_tips: string;
  confidence_score: number;
  model_used: string;
  generated_at: string;
  has_existing_content: boolean;
}

const WordInfoPanel: React.FC<WordInfoPanelProps> = ({ selectedNode }) => {
  const [aiContent, setAiContent] = useState<AIWordContent | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);

  // Load AI content when selectedNode changes
  useEffect(() => {
    if (selectedNode?.kanji) {
      loadAIContent(selectedNode.kanji);
    } else {
      setAiContent(null);
    }
  }, [selectedNode?.kanji]);

  const loadAIContent = async (wordKanji: string) => {
    setLoading(true);
    setError(null);
    try {
      const content = await apiGet<AIWordContent>(
        `/api/v1/ai-content/word/${encodeURIComponent(wordKanji)}`
      );
      setAiContent(content);
    } catch (err: any) {
      const status = err?.response?.status;
      if (status === 401 || status === 403) {
        setError(
          "You need to be logged in to view AI-enhanced word content."
        );
        setAiContent(null);
      } else if (status === 404) {
        // No content available yet
        setAiContent(null);
      } else {
        setError(
          err instanceof Error ? err.message : "Failed to load AI content"
        );
        setAiContent(null);
      }
    } finally {
      setLoading(false);
    }
  };

  const generateContent = async () => {
    if (!selectedNode?.kanji) return;
    setIsGenerating(true);
    setError(null);
    try {
      const content = await apiPost<AIWordContent>(
        "/api/v1/ai-content/generate",
        {
          word_kanji: selectedNode.kanji,
          force_regenerate: false,
        }
      );
      setAiContent(content);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to generate AI content"
      );
    } finally {
      setIsGenerating(false);
    }
  };

  const regenerateContent = async () => {
    if (!selectedNode?.kanji) return;
    setIsGenerating(true);
    setError(null);
    try {
      const content = await apiPost<AIWordContent>(
        `/api/v1/ai-content/regenerate/${encodeURIComponent(selectedNode.kanji)}`
      );
      setAiContent(content);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to regenerate AI content"
      );
    } finally {
      setIsGenerating(false);
    }
  };

  if (!selectedNode) {
    return (
      <div className="text-muted-foreground text-center py-8">
        Select a node to view word information
      </div>
    );
  }

  console.log("WordInfoPanel loaded for:", selectedNode.kanji);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold text-lg">Word Information</h3>
        {aiContent && (
          <button
            onClick={regenerateContent}
            disabled={isGenerating}
            className="flex items-center gap-1 px-2 py-1 text-xs bg-blue-500/10 text-blue-700 hover:bg-blue-200 dark:hover:bg-blue-800 rounded transition-colors disabled:opacity-50"
          >
            {isGenerating ? (
              <Loader2 className="w-3 h-3 animate-spin" />
            ) : (
              <RefreshCw className="w-3 h-3" />
            )}
            Regenerate
          </button>
        )}
      </div>

      {/* Basic Word Information */}
      <div className="bg-muted p-4 rounded-lg">
        <div className="flex items-center gap-3 mb-3">
          <h4 className="font-bold text-2xl text-red-600">
            {selectedNode.kanji}
          </h4>
          <div className="text-muted-foreground">{selectedNode.hiragana}</div>
        </div>
        <div className="text-foreground font-medium mb-3">
          {selectedNode.translation}
        </div>
        <div className="grid grid-cols-2 gap-2 text-sm">
          <div>
            <span className="font-medium">Part of Speech:</span>{" "}
            {selectedNode.pos || "N/A"}
          </div>
          <div>
            <span className="font-medium">Level:</span>{" "}
            {selectedNode.level || "N/A"}
          </div>
          <div>
            <span className="font-medium">Connections:</span>{" "}
            {selectedNode.connections || 0}
          </div>
          {selectedNode.etymology && (
            <div>
              <span className="font-medium">Etymology:</span>{" "}
              {selectedNode.etymology}
            </div>
          )}
        </div>
      </div>

      {/* AI Content Section */}
      {loading && (
        <div className="flex items-center justify-center py-8">
          <Loader2 className="w-6 h-6 animate-spin mr-2" />
          <span className="text-muted-foreground">Loading AI content...</span>
        </div>
      )}

      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3">
          <div className="text-red-600 text-sm">{error}</div>
        </div>
      )}

      {!aiContent && !loading && !error && (
        <div className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-4 text-center">
          <BookOpen className="w-8 h-8 mx-auto mb-2 text-blue-600 dark:text-blue-400" />
          <p className="text-blue-600 mb-3">
            No AI-enhanced content available yet
          </p>
          <button
            onClick={generateContent}
            disabled={isGenerating}
            className="flex items-center gap-2 mx-auto px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors disabled:opacity-50"
          >
            {isGenerating ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Zap className="w-4 h-4" />
            )}
            Generate AI Content
          </button>
        </div>
      )}

      {aiContent && (
        <div className="space-y-4">
          {/* Definitions */}
          {aiContent.definitions && aiContent.definitions.length > 0 && (
            <div className="bg-blue-500/10 p-4 rounded-lg">
              <h5 className="font-semibold mb-3 flex items-center gap-2">
                <BookOpen className="w-4 h-4" />
                Definitions
              </h5>
              <div className="space-y-2">
                {aiContent.definitions.map((definition, index) => (
                  <div
                    key={index}
                    className="text-sm text-foreground pl-4 border-l-2 border-blue-300 markdown-content"
                  >
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                      {definition}
                    </ReactMarkdown>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Usage Examples */}
          {aiContent.examples && aiContent.examples.length > 0 && (
            <div className="bg-green-500/10 p-4 rounded-lg">
              <h5 className="font-semibold mb-3 flex items-center gap-2">
                <Globe className="w-4 h-4" />
                Usage Examples
              </h5>
              <div className="space-y-2">
                {aiContent.examples.map((example, index) => (
                  <div
                    key={index}
                    className="text-sm text-foreground pl-4 border-l-2 border-green-300 markdown-content"
                  >
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                      {example}
                    </ReactMarkdown>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Cultural Notes */}
          {aiContent.cultural_notes && (
            <div className="bg-purple-500/10 p-4 rounded-lg">
              <h5 className="font-semibold mb-3 flex items-center gap-2">
                <Globe className="w-4 h-4" />
                Cultural Context
              </h5>
              <div className="text-sm text-foreground markdown-content">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {aiContent.cultural_notes}
                </ReactMarkdown>
              </div>
            </div>
          )}

          {/* Kanji Breakdown */}
          {aiContent.kanji_breakdown && (
            <div className="bg-orange-50 dark:bg-orange-950 p-4 rounded-lg">
              <h5 className="font-semibold mb-3 flex items-center gap-2">
                <BookOpen className="w-4 h-4" />
                Kanji Analysis
              </h5>
              <div className="text-sm text-foreground markdown-content">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {aiContent.kanji_breakdown}
                </ReactMarkdown>
              </div>
            </div>
          )}

          {/* Grammar Patterns */}
          {aiContent.grammar_patterns && aiContent.grammar_patterns.length > 0 && (
            <div className="bg-yellow-500/10 p-4 rounded-lg">
              <h5 className="font-semibold mb-3 flex items-center gap-2">
                <BookOpen className="w-4 h-4" />
                Grammar Patterns
              </h5>
              <div className="space-y-1">
                {aiContent.grammar_patterns.map((pattern, index) => (
                  <div
                    key={index}
                    className="text-sm text-foreground pl-4 border-l-2 border-yellow-300 markdown-content"
                  >
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                      {pattern}
                    </ReactMarkdown>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Collocations */}
          {aiContent.collocations && aiContent.collocations.length > 0 && (
            <div className="bg-indigo-50 dark:bg-indigo-950 p-4 rounded-lg">
              <h5 className="font-semibold mb-3 flex items-center gap-2">
                <BookOpen className="w-4 h-4" />
                Common Combinations
              </h5>
              <div className="flex flex-wrap gap-2">
                {aiContent.collocations.map((collocation, index) => (
                  <span
                    key={index}
                    className="px-2 py-1 bg-indigo-100 dark:bg-indigo-900 text-indigo-800 dark:text-indigo-200 text-xs rounded"
                  >
                    {collocation}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Learning Tips */}
          {aiContent.learning_tips && (
            <div className="bg-amber-50 dark:bg-amber-950 p-4 rounded-lg">
              <h5 className="font-semibold mb-3 flex items-center gap-2">
                <Lightbulb className="w-4 h-4" />
                Learning Tips
              </h5>
              <div className="text-sm text-foreground markdown-content">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {aiContent.learning_tips}
                </ReactMarkdown>
              </div>
            </div>
          )}

          {/* AI Content Metadata */}
          <div className="bg-muted p-3 rounded-lg text-xs text-muted-foreground">
            <div className="flex justify-between items-center">
              <span>Generated by {aiContent.model_used}</span>
              <span>
                Confidence: {(aiContent.confidence_score * 100).toFixed(0)}%
              </span>
            </div>
            <div className="mt-1">
              Generated: {new Date(aiContent.generated_at).toLocaleString()}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default WordInfoPanel;
