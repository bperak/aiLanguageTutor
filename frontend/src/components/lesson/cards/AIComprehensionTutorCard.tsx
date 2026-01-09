"use client";

import React, { useState, useEffect, useRef } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { JapaneseText } from "@/components/text/JapaneseText";
import type { AIComprehensionTutorCard as AIComprehensionTutorCardType } from "@/types/lesson-root";
import { Send } from "lucide-react";
import { sendComprehensionTutorTurn } from "@/lib/api/comprehension-tutor";

interface AIComprehensionTutorCardProps {
  data: AIComprehensionTutorCardType;
  sessionId: string;
  canDoId: string;
}

interface Message {
  role: "learner" | "ai";
  content: string;
  transliteration?: string | null;
  translation?: string | null;
  feedback?: string;
}

export function AIComprehensionTutorCard({
  data,
  sessionId,
  canDoId,
}: AIComprehensionTutorCardProps) {
  const [currentStageIdx, setCurrentStageIdx] = useState(0);
  const [messages, setMessages] = useState<Message[]>([]);
  const [userInput, setUserInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const stagesLength = data.stages?.length || 0;
  const currentStage = data.stages?.[currentStageIdx];
  const progress =
    stagesLength > 0 ? ((currentStageIdx + 1) / stagesLength) * 100 : 0;
  const isCompleted = currentStageIdx >= stagesLength;

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!userInput.trim() || isLoading || isCompleted) return;

    const learnerMessage: Message = {
      role: "learner",
      content: userInput,
    };
    setMessages((prev) => [...prev, learnerMessage]);
    setUserInput("");
    setIsLoading(true);

    try {
      const response = await sendComprehensionTutorTurn({
        session_id: sessionId,
        can_do_id: canDoId,
        stage_idx: currentStageIdx,
        learner_input: userInput,
      });

      const aiMessage: Message = {
        role: "ai",
        content: response.ai_response,
        transliteration: response.transliteration || undefined,
        translation: response.translation || undefined,
        feedback:
          response.feedback.teaching_direction ||
          response.feedback.comprehension_score?.toString(),
      };
      setMessages((prev) => [...prev, aiMessage]);

      // Advance to next stage if appropriate (based on comprehension score)
      if (
        response.feedback.comprehension_score >= 0.7 &&
        currentStageIdx < stagesLength - 1
      ) {
        setTimeout(() => {
          setCurrentStageIdx((prev) => prev + 1);
          setMessages([]);
        }, 2000);
      }
    } catch (error) {
      console.error("Failed to send comprehension tutor turn:", error);
      // Show error message to user
      const errorMessage: Message = {
        role: "ai",
        content: "申し訳ございません。エラーが発生しました。",
        translation: "Sorry, an error occurred.",
        feedback: "Please try again.",
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  if (isCompleted) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-2xl">
            🎉 Comprehension Practice Complete!
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground">
            You've completed all comprehension questions. Great job!
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-2xl">
          {data.title?.en || data.title?.ja || "AI Comprehension Tutor"}
        </CardTitle>
        <div className="flex items-center gap-4 mt-2">
          <Progress value={progress} className="flex-1" />
          <Badge>
            Stage {currentStageIdx + 1} of {stagesLength}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {currentStage && (
          <>
            <div className="bg-blue-500/10 p-4 rounded">
              <div className="font-semibold mb-2">Goal:</div>
              <div>{currentStage.goal_en}</div>
            </div>
            {currentStage.question && (
              <div className="p-4 border rounded">
                <div className="font-semibold mb-2">Question:</div>
                <JapaneseText data={currentStage.question} />
              </div>
            )}
            {currentStage.hints && currentStage.hints.length > 0 && (
              <div className="bg-yellow-500/10 p-4 rounded">
                <div className="font-semibold mb-2">Hints:</div>
                {currentStage.hints.map((hint, idx) => (
                  <div key={idx} className="text-sm">
                    {hint.en || hint.ja || Object.values(hint)[0]}
                  </div>
                ))}
              </div>
            )}
          </>
        )}

        <div className="space-y-2 max-h-96 overflow-y-auto border rounded p-4">
          {messages.map((msg, idx) => (
            <div
              key={idx}
              className={`flex ${
                msg.role === "learner" ? "justify-end" : "justify-start"
              }`}
            >
              <div
                className={`max-w-[80%] p-2 rounded ${
                  msg.role === "learner"
                    ? "bg-blue-500 text-white"
                    : "bg-muted"
                }`}
              >
                {msg.role === "ai" && msg.content ? (
                  <JapaneseText
                    data={{
                      std: msg.content,
                      furigana: "",
                      romaji: "",
                      translation: msg.translation
                        ? { en: msg.translation }
                        : {},
                    }}
                  />
                ) : (
                  <div>{msg.content}</div>
                )}
                {msg.transliteration && (
                  <div className="text-xs mt-1 opacity-75">
                    {msg.transliteration}
                  </div>
                )}
                {msg.feedback && (
                  <div className="text-xs mt-1 italic">{msg.feedback}</div>
                )}
              </div>
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>

        <form onSubmit={handleSubmit} className="flex gap-2">
          <input
            type="text"
            value={userInput}
            onChange={(e) => setUserInput(e.target.value)}
            placeholder="Type your answer..."
            className="flex-1 p-2 border border-input bg-background text-foreground rounded"
            disabled={isLoading || isCompleted}
          />
          <Button
            type="submit"
            disabled={isLoading || isCompleted || !userInput.trim()}
          >
            <Send className="w-4 h-4" />
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
