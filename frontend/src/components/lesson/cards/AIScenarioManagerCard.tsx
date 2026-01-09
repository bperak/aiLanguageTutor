"use client";

import React, { useState, useEffect, useRef } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { JapaneseText } from "@/components/text/JapaneseText";
import type { AIScenarioManagerCard as AIScenarioManagerCardType } from "@/types/lesson-root";
import { Send } from "lucide-react";
import { sendScenarioManagerTurn } from "@/lib/api/scenario-manager";

interface AIScenarioManagerCardProps {
  data: AIScenarioManagerCardType;
  sessionId: string;
  canDoId: string;
}

interface Message {
  role: "learner" | "ai";
  content: string;
  transliteration?: string | null;
  translation?: string | null;
  cultural_note?: string;
}

export function AIScenarioManagerCard({
  data,
  sessionId,
  canDoId,
}: AIScenarioManagerCardProps) {
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
      const response = await sendScenarioManagerTurn({
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
        cultural_note: response.feedback.cultural_note || undefined,
      };
      setMessages((prev) => [...prev, aiMessage]);

      // Advance to next stage if appropriate
      if (currentStageIdx < stagesLength - 1) {
        setTimeout(() => {
          setCurrentStageIdx((prev) => prev + 1);
          setMessages([]);
        }, 2000);
      }
    } catch (error) {
      console.error("Failed to send scenario manager turn:", error);
      const errorMessage: Message = {
        role: "ai",
        content: "申し訳ございません。エラーが発生しました。",
        translation: "Sorry, an error occurred.",
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
            🎉 Scenario Practice Complete!
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground">
            You've completed all scenario practice stages. Great job!
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-2xl">
          {data.title?.en || data.title?.ja || "AI Scenario Manager"}
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
              <div className="font-semibold mb-2">Scenario Type:</div>
              <div>{currentStage.scenario_type}</div>
            </div>
            <div className="bg-yellow-500/10 p-4 rounded">
              <div className="font-semibold mb-2">Goal:</div>
              <div>{currentStage.goal_en}</div>
            </div>
            {currentStage.context && (
              <div className="bg-green-500/10 p-4 rounded">
                <div className="font-semibold mb-2">Context:</div>
                <div>
                  {currentStage.context.en ||
                    currentStage.context.ja ||
                    Object.values(currentStage.context)[0]}
                </div>
              </div>
            )}
            {currentStage.roles && currentStage.roles.length > 0 && (
              <div>
                <div className="font-semibold mb-2">Roles:</div>
                <div className="flex flex-wrap gap-2">
                  {currentStage.roles.map((role, idx) => (
                    <Badge key={idx} variant="outline">
                      {role.name || role.description || JSON.stringify(role)}
                    </Badge>
                  ))}
                </div>
              </div>
            )}
            {currentStage.cultural_notes &&
              currentStage.cultural_notes.length > 0 && (
                <div className="bg-purple-500/10 p-4 rounded">
                  <div className="font-semibold mb-2">Cultural Notes:</div>
                  {currentStage.cultural_notes.map((note, idx) => (
                    <div key={idx} className="text-sm mt-1">
                      {note.en || note.ja || Object.values(note)[0]}
                    </div>
                  ))}
                </div>
              )}
          </>
        )}

        <div className="space-y-2 max-h-96 overflow-y-auto border rounded p-4">
          {messages.length === 0 && (
            <div className="text-center text-muted-foreground italic py-8">
              Start the scenario by typing a message below
            </div>
          )}
          {messages.map((msg, idx) => (
            <div
              key={idx}
              className={`flex ${
                msg.role === "learner" ? "justify-end" : "justify-start"
              }`}
            >
              <div
                className={`max-w-[80%] p-3 rounded-lg ${
                  msg.role === "learner"
                    ? "bg-blue-500 text-white"
                    : "bg-muted"
                }`}
              >
                {msg.role === "ai" && msg.content ? (
                  <>
                    <JapaneseText
                      data={{
                        std: msg.content,
                        furigana: "",
                        romaji: msg.transliteration || "",
                        translation: msg.translation
                          ? { en: msg.translation }
                          : {},
                      }}
                    />
                    {msg.transliteration && (
                      <div className="text-xs mt-1 opacity-75">
                        {msg.transliteration}
                      </div>
                    )}
                  </>
                ) : (
                  <div>{msg.content}</div>
                )}
                {msg.cultural_note && (
                  <div className="text-xs mt-2 italic opacity-90 bg-purple-500/10 p-1 rounded">
                    💡 {msg.cultural_note}
                  </div>
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
            placeholder="Type your message..."
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
