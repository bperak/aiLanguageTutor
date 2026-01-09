"use client";

import React, { useState, useEffect, useRef } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { JapaneseText } from "@/components/text/JapaneseText";
import {
  sendGuidedTurn,
  flushGuidedState,
  getGuidedInitialMessage,
} from "@/lib/api/guided-dialogue";
import type {
  GuidedDialogueCard as GuidedDialogueCardType,
  GuidedTurnResponse,
} from "@/types/lesson-root";
import { ChevronDown, ChevronUp } from "lucide-react";

interface GuidedDialogueCardProps {
  data: GuidedDialogueCardType;
  sessionId: string;
  initialStageIdx?: number;
}

interface Message {
  role: "learner" | "ai";
  content: string;
  transliteration?: string | null;
  translation?: string | null;
  feedback?: GuidedTurnResponse["feedback"];
  teachingDirection?: string;
  hints?: string[];
}

export function GuidedDialogueCard({
  data,
  sessionId,
  initialStageIdx = 0,
}: GuidedDialogueCardProps) {
  const [currentStageIdx, setCurrentStageIdx] = useState(initialStageIdx);
  const [messages, setMessages] = useState<Message[]>([]);
  const [userInput, setUserInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [showHints, setShowHints] = useState(true);
  const [loadingInitialMessage, setLoadingInitialMessage] = useState(true);
  const [collapsedFeedback, setCollapsedFeedback] = useState<Set<number>>(
    new Set()
  );
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Guard against missing stages data
  if (
    !data ||
    !data.stages ||
    !Array.isArray(data.stages) ||
    data.stages.length === 0
  ) {
    return (
      <Card className="w-full">
        <CardHeader>
          <CardTitle className="text-2xl">Guided Dialogue</CardTitle>
        </CardHeader>
        <CardContent className="pt-6">
          <p className="text-muted-foreground italic">
            Guided dialogue content is not available yet. It will appear once
            the production stage is generated.
          </p>
        </CardContent>
      </Card>
    );
  }

  const currentStage = data.stages[currentStageIdx];
  const progress = ((currentStageIdx + 1) / data.stages.length) * 100;
  const isCompleted = currentStageIdx >= data.stages.length;

  // Fetch initial message on mount
  useEffect(() => {
    const fetchInitialMessage = async () => {
      if (isCompleted) {
        setLoadingInitialMessage(false);
        return;
      }

      // Only fetch if we have a valid sessionId
      if (!sessionId || sessionId.trim() === "") {
        console.warn("No sessionId provided, skipping initial message fetch");
        setLoadingInitialMessage(false);
        return;
      }

      try {
        setLoadingInitialMessage(true);
        console.log(
          "Fetching initial message for session:",
          sessionId,
          "stage:",
          currentStageIdx
        );

        const initialMessage = await getGuidedInitialMessage({
          session_id: sessionId,
          stage_idx: currentStageIdx,
        });
        console.log("Initial message received:", initialMessage);

        // Handle both "ok" status and fallback responses
        if (initialMessage.status === "ok" || initialMessage.message) {
          const aiMessage: Message = {
            role: "ai",
            content: initialMessage.message,
            transliteration: initialMessage.transliteration || undefined,
            translation: initialMessage.translation || undefined,
            teachingDirection: initialMessage.feedback,
            hints: initialMessage.hints,
          };
          setMessages([aiMessage]);
        }
      } catch (error) {
        console.error("Failed to fetch initial message:", error);
        // Continue without initial message if it fails - show a default greeting
        const defaultMessage: Message = {
          role: "ai",
          content: "こんにちは！よろしくお願いします。",
          translation: "Hello! Nice to meet you.",
          teachingDirection:
            "Let's start practicing. Use the hints above to guide your response.",
        };
        setMessages([defaultMessage]);
      } finally {
        setLoadingInitialMessage(false);
      }
    };

    fetchInitialMessage();
  }, [sessionId, currentStageIdx, isCompleted]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const toggleFeedbackCollapse = (index: number) => {
    setCollapsedFeedback((prev) => {
      const next = new Set(prev);
      if (next.has(index)) {
        next.delete(index);
      } else {
        next.add(index);
      }
      return next;
    });
  };

  const handleSend = async () => {
    if (!userInput.trim() || isLoading) return;

    const learnerMessage: Message = {
      role: "learner",
      content: userInput,
    };
    setMessages((prev) => [...prev, learnerMessage]);
    setUserInput("");
    setIsLoading(true);

    try {
      const response = await sendGuidedTurn({
        session_id: sessionId,
        stage_idx: currentStageIdx,
        learner_input: userInput,
      });

      const aiMessage: Message = {
        role: "ai",
        content: response.ai_response,
        transliteration: response.transliteration || undefined,
        translation: response.translation || undefined,
        teachingDirection: response.feedback.teaching_direction || undefined,
        feedback: response.feedback,
      };
      setMessages((prev) => [...prev, aiMessage]);

      // Update stage if advanced
      if (response.stage_progress.advanced) {
        const newStageIdx = response.stage_progress.new_stage;
        setCurrentStageIdx(newStageIdx);

        // Fetch initial message for new stage
        if (!response.stage_progress.completed) {
          try {
            const initialMessage = await getGuidedInitialMessage({
              session_id: sessionId,
              stage_idx: newStageIdx,
            });

            if (initialMessage.status === "ok") {
              const newAiMessage: Message = {
                role: "ai",
                content: initialMessage.message,
                transliteration: initialMessage.transliteration,
                translation: initialMessage.translation,
                teachingDirection: initialMessage.feedback,
                hints: initialMessage.hints,
              };
              setMessages((prev) => [...prev, newAiMessage]);
            }
          } catch (error) {
            console.error(
              "Failed to fetch initial message for new stage:",
              error
            );
          }
        } else {
          setMessages((prev) => [
            ...prev,
            {
              role: "ai",
              content:
                "🎉 Congratulations! You've completed all guided dialogue stages!",
            },
          ]);
        }
      }
    } catch (error) {
      console.error("Failed to send turn:", error);
      setMessages((prev) => [
        ...prev,
        {
          role: "ai",
          content: "Sorry, there was an error. Please try again.",
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleFlush = async () => {
    if (!confirm("Are you sure you want to reset your progress?")) return;

    try {
      await flushGuidedState(sessionId);
      setCurrentStageIdx(0);
      setMessages([]);
      setUserInput("");
      setCollapsedFeedback(new Set());

      // Re-fetch initial message after flush
      setLoadingInitialMessage(true);
      const initialMessage = await getGuidedInitialMessage({
        session_id: sessionId,
        stage_idx: 0,
      });

      if (initialMessage.status === "ok") {
        const aiMessage: Message = {
          role: "ai",
          content: initialMessage.message,
          transliteration: initialMessage.transliteration,
          translation: initialMessage.translation,
          teachingDirection: initialMessage.feedback,
          hints: initialMessage.hints,
        };
        setMessages([aiMessage]);
      }
    } catch (error) {
      console.error("Failed to flush state:", error);
      alert("Failed to reset progress. Please try again.");
    } finally {
      setLoadingInitialMessage(false);
    }
  };

  const wordCount = userInput.trim().split(/\s+/).length;
  const minWords = currentStage?.learner_turn_schema?.min_words || 0;
  const maxWords = currentStage?.learner_turn_schema?.max_words || 100;
  const wordCountOk = wordCount >= minWords && wordCount <= maxWords;

  if (isCompleted) {
    return (
      <Card className="w-full">
        <CardHeader>
          <CardTitle className="text-2xl">
            Guided Dialogue - Completed! 🎉
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center py-8">
            <p className="text-lg mb-4">
              You've successfully completed all stages!
            </p>
            <Button onClick={handleFlush} variant="outline">
              Start Over
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="w-full">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-2xl">Guided Dialogue</CardTitle>
          <Button variant="ghost" size="sm" onClick={handleFlush}>
            Reset Progress
          </Button>
        </div>

        {/* Progress bar */}
        <div className="mt-4">
          <div className="flex justify-between text-sm mb-2">
            <span>
              Stage {currentStageIdx + 1} of {data.stages?.length || 0}
            </span>
            <span>{Math.round(progress)}%</span>
          </div>
          <Progress value={progress} />
        </div>

        {/* Current stage goal */}
        {currentStage && (
          <div className="mt-4 p-4 bg-blue-500/10 rounded-lg">
            <div className="text-sm font-semibold text-blue-700 dark:text-blue-300 mb-1">
              Current Goal
            </div>
            <div>{currentStage.goal_en}</div>
          </div>
        )}
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Hints toggle */}
        {currentStage &&
          currentStage.hints &&
          currentStage.hints.length > 0 && (
            <div>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowHints(!showHints)}
              >
                {showHints ? "Hide" : "Show"} Hints
              </Button>
              {showHints && (
                <div className="mt-2 space-y-2">
                  {currentStage.hints
                    .filter((hint) => {
                      const hintAny = hint as any;
                      const hasJPTextFormat =
                        hint &&
                        (hint.std ||
                          hint.kanji ||
                          (hint.translation &&
                            (typeof hint.translation === "string" ||
                              (hint.translation as any).en ||
                              (hint.translation as any).ja)));
                      const hasBilingualFormat = hint && (hintAny.en || hintAny.ja);
                      return hasJPTextFormat || hasBilingualFormat;
                    })
                    .map((hint, idx) => {
                      const hintAny = hint as any;
                      let hintData: any = hint;
                      if (hintAny.en || hintAny.ja) {
                        hintData = {
                          std: hintAny.ja || "",
                          translation: { en: hintAny.en || "" },
                        };
                      }
                      return (
                        <div
                          key={idx}
                          className="p-3 bg-yellow-500/10 rounded border-l-4 border-yellow-400"
                        >
                          <JapaneseText data={hintData} />
                        </div>
                      );
                    })}
                </div>
              )}
            </div>
          )}

        {/* Message history */}
        <div className="border border-border rounded-lg p-4 h-96 overflow-y-auto bg-muted">
          {loadingInitialMessage && messages.length === 0 && (
            <div className="text-center text-muted-foreground py-8">
              Loading initial message...
            </div>
          )}
          {!loadingInitialMessage && messages.length === 0 && (
            <div className="text-center text-muted-foreground py-8">
              Start the conversation! Use the hints above to guide you.
            </div>
          )}
          <div className="space-y-6">
            {messages.map((msg, idx) => (
              <div key={idx} className="space-y-2">
                {/* Conversation Bubble */}
                <div
                  className={`flex ${msg.role === "learner" ? "justify-end" : "justify-start"}`}
                >
                  <div
                    className={`max-w-[80%] ${msg.role === "learner" ? "text-right" : ""}`}
                  >
                    <div className="text-xs font-semibold text-muted-foreground mb-1">
                      {msg.role === "learner" ? "You" : "AI Tutor"}
                    </div>
                    <div
                      className={`rounded-lg p-3 ${
                        msg.role === "learner"
                          ? "bg-blue-500 text-white"
                          : "bg-card border border-border"
                      }`}
                    >
                      {msg.content}
                    </div>

                    {/* Transliteration and Translation for AI messages */}
                    {msg.role === "ai" &&
                      (msg.transliteration || msg.translation) && (
                        <div className="mt-3 space-y-2 pt-3 border-t border-border">
                          {msg.transliteration && (
                            <div className="bg-blue-500/10 p-2 rounded border-l-4 border-blue-300">
                              <p className="text-xs font-semibold text-blue-500 mb-1">
                                🔤 Pronunciation (Romaji):
                              </p>
                              <p className="text-sm text-blue-700 dark:text-blue-300 font-mono italic">
                                {msg.transliteration}
                              </p>
                            </div>
                          )}
                          {msg.translation && (
                            <div className="bg-muted p-2 rounded border-l-4 border-border">
                              <p className="text-xs font-semibold text-foreground mb-1">
                                🌍 English Translation:
                              </p>
                              <p className="text-sm text-muted-foreground">
                                {msg.translation}
                              </p>
                            </div>
                          )}
                        </div>
                      )}
                  </div>
                </div>

                {/* Teaching Direction Feedback Panel (after AI responses) */}
                {msg.role === "ai" && msg.teachingDirection && (
                  <div className="ml-4">
                    <div className="bg-gradient-to-r from-amber-50 to-orange-50 dark:from-amber-950 dark:to-orange-950 border border-amber-200 dark:border-amber-800 rounded-lg overflow-hidden">
                      <button
                        onClick={() => toggleFeedbackCollapse(idx)}
                        className="w-full p-3 text-left flex items-center justify-between hover:bg-amber-100 dark:hover:bg-amber-900 transition-colors"
                      >
                        <div className="flex items-center gap-2">
                          <span className="text-amber-800 dark:text-amber-200 font-medium text-sm">
                            🧑‍🏫 Teaching Direction & Strategy
                          </span>
                        </div>
                        {collapsedFeedback.has(idx) ? (
                          <ChevronDown className="h-4 w-4 text-amber-600 dark:text-amber-400" />
                        ) : (
                          <ChevronUp className="h-4 w-4 text-amber-600 dark:text-amber-400" />
                        )}
                      </button>
                      {!collapsedFeedback.has(idx) && (
                        <div className="px-3 pb-3 space-y-3">
                          <div className="bg-card p-3 rounded-lg border-l-4 border-amber-400">
                            <h5 className="font-medium text-amber-800 dark:text-amber-200 mb-1 text-sm">
                              Teaching Strategy:
                            </h5>
                            <p className="text-amber-700 dark:text-amber-300 text-sm">
                              {msg.teachingDirection}
                            </p>
                          </div>
                          {msg.hints && msg.hints.length > 0 && (
                            <div className="bg-blue-500/10 p-3 rounded-lg border-l-4 border-blue-400">
                              <h5 className="font-medium text-blue-500 mb-2 flex items-center gap-1 text-sm">
                                💡 Learning Tips
                              </h5>
                              <ul className="text-blue-700 dark:text-blue-300 text-xs space-y-1">
                                {msg.hints.map((hint, i) => (
                                  <li key={i} className="flex items-start gap-1">
                                    <span className="text-blue-500 dark:text-blue-400 mt-0.5">
                                      •
                                    </span>
                                    <span>{hint}</span>
                                  </li>
                                ))}
                              </ul>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {/* Feedback badges for learner messages */}
                {msg.role === "learner" && msg.feedback && (
                  <div className="ml-4 mt-2 flex flex-wrap gap-2 justify-end">
                    <Badge
                      variant={
                        msg.feedback.pattern_matched ? "default" : "destructive"
                      }
                    >
                      Pattern: {msg.feedback.pattern_matched ? "✓" : "✗"}
                    </Badge>
                    <Badge
                      variant={
                        msg.feedback.word_count_ok ? "default" : "secondary"
                      }
                    >
                      Words: {msg.feedback.word_count}
                    </Badge>
                    {msg.feedback.goals_met && (
                      <Badge variant="default" className="bg-green-500">
                        Goals Met! ✓
                      </Badge>
                    )}
                  </div>
                )}
              </div>
            ))}
            <div ref={messagesEndRef} />
          </div>
        </div>

        {/* Input area */}
        {currentStage && (
          <div className="space-y-2">
            <div className="flex gap-2">
              <input
                type="text"
                value={userInput}
                onChange={(e) => setUserInput(e.target.value)}
                onKeyPress={(e) => e.key === "Enter" && handleSend()}
                className="flex-1 p-3 border border-input bg-background text-foreground rounded-lg"
                placeholder="Type your response in Japanese..."
                disabled={isLoading}
              />
              <Button
                onClick={handleSend}
                disabled={isLoading || !userInput.trim()}
              >
                {isLoading ? "..." : "Send"}
              </Button>
            </div>

            {/* Word count indicator */}
            <div className="flex items-center gap-2 text-sm">
              <span className={wordCountOk ? "text-green-600" : "text-red-600"}>
                {wordCount} words
              </span>
              <span className="text-muted-foreground">
                (Required: {minWords}-{maxWords})
              </span>
              {currentStage.learner_turn_schema &&
                !currentStage.learner_turn_schema.allow_romaji && (
                  <Badge variant="outline" className="text-xs">
                    No romaji
                  </Badge>
                )}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
