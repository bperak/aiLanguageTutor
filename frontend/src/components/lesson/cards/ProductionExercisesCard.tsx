"use client";

import React, { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { JapaneseText } from "@/components/text/JapaneseText";
import type { ProductionExercisesCard as ProductionExercisesCardType } from "@/types/lesson-root";

interface ProductionExercisesCardProps {
  data: ProductionExercisesCardType;
}

export function ProductionExercisesCard({
  data,
}: ProductionExercisesCardProps) {
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [showFeedback, setShowFeedback] = useState<Record<string, boolean>>({});

  const title = data.title?.en || data.title?.ja || "Production Exercises";

  const handleAnswerChange = (exerciseId: string, answer: string) => {
    setAnswers({ ...answers, [exerciseId]: answer });
  };

  const toggleFeedback = (exerciseId: string) => {
    setShowFeedback({ ...showFeedback, [exerciseId]: !showFeedback[exerciseId] });
  };

  const renderExercise = (exercise: any, idx: number) => {
    const exerciseId = exercise.id || `exercise-${idx}`;
    const userAnswer = answers[exerciseId] || "";
    const isShowingFeedback = showFeedback[exerciseId];

    return (
      <Card key={exerciseId} className="mb-4">
        <CardHeader>
          <CardTitle className="text-lg">
            Exercise {idx + 1}:{" "}
            {exercise.exercise_type?.replace(/_/g, " ").toUpperCase()}
          </CardTitle>
          {exercise.instructions && (
            <p className="text-sm text-muted-foreground">
              {exercise.instructions.en ||
                exercise.instructions.ja ||
                Object.values(exercise.instructions)[0]}
            </p>
          )}
        </CardHeader>
        <CardContent className="space-y-4">
          {exercise.prompt && (
            <div>
              <strong>Prompt:</strong>
              {typeof exercise.prompt === "string" ? (
                <p>{exercise.prompt}</p>
              ) : (
                <JapaneseText data={exercise.prompt} />
              )}
            </div>
          )}
          {exercise.template && (
            <div className="bg-muted p-4 rounded">
              <strong>Template:</strong>
              <JapaneseText data={exercise.template} />
            </div>
          )}
          {exercise.source_sentence && (
            <div>
              <strong>Source Sentence:</strong>
              <JapaneseText data={exercise.source_sentence} />
            </div>
          )}
          {exercise.scrambled_words && (
            <div>
              <strong>Scrambled Words:</strong>
              <div className="flex flex-wrap gap-2 mt-2">
                {exercise.scrambled_words.map(
                  (word: string, wordIdx: number) => (
                    <Badge key={wordIdx} variant="outline">
                      {word}
                    </Badge>
                  )
                )}
              </div>
            </div>
          )}
          <div>
            <label className="block text-sm font-medium mb-2">
              Your Answer:
            </label>
            <textarea
              value={userAnswer}
              onChange={(e) => handleAnswerChange(exerciseId, e.target.value)}
              placeholder="Type your answer here..."
              className="w-full min-h-[100px] p-2 border border-input bg-background text-foreground rounded"
            />
          </div>
          {exercise.expected_elements &&
            exercise.expected_elements.length > 0 && (
              <div className="text-sm text-muted-foreground">
                <strong>Expected elements:</strong>{" "}
                {exercise.expected_elements.join(", ")}
              </div>
            )}
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => toggleFeedback(exerciseId)}
              disabled={!userAnswer.trim()}
            >
              {isShowingFeedback ? "Hide" : "Get"} Feedback
            </Button>
          </div>
          {isShowingFeedback && userAnswer && (
            <div className="mt-2 p-2 bg-blue-500/10 rounded">
              <strong>Feedback:</strong> Use the AI Production Evaluator card to
              get detailed feedback on your production exercises.
              <p className="text-sm mt-1 text-muted-foreground">
                Copy your answer and paste it into the AI Production Evaluator
                for evaluation and rubric-based feedback.
              </p>
            </div>
          )}
        </CardContent>
      </Card>
    );
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-2xl">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        {data.items && data.items.length > 0 ? (
          <div className="space-y-4">
            {data.items.map((exercise, idx) => renderExercise(exercise, idx))}
          </div>
        ) : (
          <p className="text-muted-foreground italic">
            No production exercises available
          </p>
        )}
      </CardContent>
    </Card>
  );
}
