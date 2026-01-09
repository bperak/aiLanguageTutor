"use client";

import React, { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { JapaneseText } from "@/components/text/JapaneseText";
import type { AIProductionEvaluatorCard as AIProductionEvaluatorCardType } from "@/types/lesson-root";
import { Send } from "lucide-react";
import { evaluateProduction } from "@/lib/api/production-evaluator";

interface AIProductionEvaluatorCardProps {
  data: AIProductionEvaluatorCardType;
  sessionId: string;
  canDoId: string;
}

interface EvaluationResult {
  pattern_correctness?: number;
  fluency?: number;
  content_relevance?: number;
  feedback?: string;
  transliteration?: string;
  translation?: string;
  teaching_direction?: string;
}

export function AIProductionEvaluatorCard({
  data,
  sessionId,
  canDoId,
}: AIProductionEvaluatorCardProps) {
  const [currentStageIdx, setCurrentStageIdx] = useState(0);
  const [userInput, setUserInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [evaluation, setEvaluation] = useState<EvaluationResult | null>(null);
  const [submissions, setSubmissions] = useState<
    Array<{ input: string; evaluation: EvaluationResult }>
  >([]);

  const stagesLength = data.stages?.length || 0;
  const currentStage = data.stages?.[currentStageIdx];
  const progress =
    stagesLength > 0 ? ((currentStageIdx + 1) / stagesLength) * 100 : 0;
  const isCompleted = currentStageIdx >= stagesLength;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!userInput.trim() || isLoading || isCompleted) return;

    setIsLoading(true);
    setEvaluation(null);

    try {
      const response = await evaluateProduction({
        session_id: sessionId,
        can_do_id: canDoId,
        stage_idx: currentStageIdx,
        learner_input: userInput,
      });

      const evaluationResult: EvaluationResult = {
        pattern_correctness: response.feedback.rubric_scores.pattern_correctness,
        fluency: response.feedback.rubric_scores.fluency,
        content_relevance: response.feedback.rubric_scores.content_relevance,
        feedback:
          response.feedback.teaching_direction || "Evaluation complete",
        transliteration: response.transliteration || undefined,
        translation: response.translation || undefined,
        teaching_direction: response.feedback.teaching_direction || undefined,
      };
      setEvaluation(evaluationResult);
      setSubmissions((prev) => [
        ...prev,
        { input: userInput, evaluation: evaluationResult },
      ]);
      setUserInput("");
    } catch (error) {
      console.error("Failed to evaluate production:", error);
      setEvaluation({
        feedback: "Error evaluating production. Please try again.",
      });
    } finally {
      setIsLoading(false);
    }
  };

  if (isCompleted) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-2xl">
            🎉 Production Practice Complete!
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground">
            You've completed all production exercises. Great job!
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-2xl">
          {data.title?.en || data.title?.ja || "AI Production Evaluator"}
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
            {currentStage.expected_patterns &&
              currentStage.expected_patterns.length > 0 && (
                <div className="bg-yellow-500/10 p-4 rounded">
                  <div className="font-semibold mb-2">Expected Patterns:</div>
                  <div className="flex flex-wrap gap-2">
                    {currentStage.expected_patterns.map((pattern, idx) => (
                      <Badge key={idx} variant="outline">
                        {pattern}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}
            {currentStage.hints && currentStage.hints.length > 0 && (
              <div className="bg-green-500/10 p-4 rounded">
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

        <form onSubmit={handleSubmit} className="space-y-2">
          <textarea
            value={userInput}
            onChange={(e) => setUserInput(e.target.value)}
            placeholder="Type your production here..."
            className="w-full min-h-[120px] p-2 border border-input bg-background text-foreground rounded"
            disabled={isLoading || isCompleted}
          />
          <Button
            type="submit"
            disabled={isLoading || isCompleted || !userInput.trim()}
          >
            <Send className="w-4 h-4 mr-2" />
            {isLoading ? "Evaluating..." : "Submit for Evaluation"}
          </Button>
        </form>

        {evaluation && (
          <div className="mt-4 p-4 bg-muted rounded space-y-3">
            <div className="font-semibold">Evaluation Results:</div>
            {evaluation.pattern_correctness !== undefined && (
              <div>
                <div className="flex justify-between mb-1">
                  <span>Pattern Correctness:</span>
                  <span>{evaluation.pattern_correctness}/5</span>
                </div>
                <Progress value={(evaluation.pattern_correctness / 5) * 100} />
              </div>
            )}
            {evaluation.fluency !== undefined && (
              <div>
                <div className="flex justify-between mb-1">
                  <span>Fluency:</span>
                  <span>{evaluation.fluency}/5</span>
                </div>
                <Progress value={(evaluation.fluency / 5) * 100} />
              </div>
            )}
            {evaluation.content_relevance !== undefined && (
              <div>
                <div className="flex justify-between mb-1">
                  <span>Content Relevance:</span>
                  <span>{evaluation.content_relevance}/5</span>
                </div>
                <Progress value={(evaluation.content_relevance / 5) * 100} />
              </div>
            )}
            {evaluation.feedback && (
              <div className="mt-2 p-2 bg-blue-500/10 rounded">
                <strong>Feedback:</strong> {evaluation.feedback}
              </div>
            )}
            {evaluation.teaching_direction && (
              <div className="mt-2 p-2 bg-green-500/10 rounded">
                <strong>Teaching Direction:</strong>{" "}
                {evaluation.teaching_direction}
              </div>
            )}
          </div>
        )}

        {submissions.length > 0 && (
          <div className="mt-4">
            <div className="font-semibold mb-2">Previous Submissions:</div>
            <div className="space-y-2">
              {submissions
                .slice(-3)
                .reverse()
                .map((sub, idx) => (
                  <div key={idx} className="p-2 bg-muted rounded text-sm">
                    <div className="font-medium">{sub.input}</div>
                    {sub.evaluation.feedback && (
                      <div className="text-muted-foreground mt-1">
                        {sub.evaluation.feedback}
                      </div>
                    )}
                  </div>
                ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
