"use client";

import React, { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { JapaneseText } from "@/components/text/JapaneseText";
import type { ComprehensionExercisesCard as ComprehensionExercisesCardType } from "@/types/lesson-root";

interface ComprehensionExercisesCardProps {
  data: ComprehensionExercisesCardType;
}

export function ComprehensionExercisesCard({
  data,
}: ComprehensionExercisesCardProps) {
  const [answers, setAnswers] = useState<Record<string, any>>({});
  const [showAnswers, setShowAnswers] = useState<Record<string, boolean>>({});

  const title =
    data.title?.en || data.title?.ja || "Comprehension Exercises";

  const handleAnswer = (exerciseId: string, answer: any) => {
    setAnswers({ ...answers, [exerciseId]: answer });
  };

  const toggleShowAnswer = (exerciseId: string) => {
    setShowAnswers({ ...showAnswers, [exerciseId]: !showAnswers[exerciseId] });
  };

  const renderExercise = (exercise: any, idx: number) => {
    const exerciseId = exercise.id || `exercise-${idx}`;
    const userAnswer = answers[exerciseId];
    const isShowingAnswer = showAnswers[exerciseId];

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
          {exercise.question && (
            <div>
              <strong>Question:</strong>
              <JapaneseText data={exercise.question} />
            </div>
          )}
          {exercise.text_passage && (
            <div className="bg-muted p-4 rounded">
              <JapaneseText data={exercise.text_passage} />
            </div>
          )}
          {exercise.exercise_type === "gap_fill" && exercise.options && (
            <div className="space-y-2">
              {exercise.options.map((option: any, optIdx: number) => (
                <Button
                  key={optIdx}
                  variant={userAnswer === optIdx ? "default" : "outline"}
                  onClick={() => handleAnswer(exerciseId, optIdx)}
                  className="w-full text-left"
                >
                  <JapaneseText data={option} />
                </Button>
              ))}
            </div>
          )}
          {exercise.exercise_type === "matching" && exercise.pairs && (
            <div className="space-y-2">
              {exercise.pairs.map((pair: any, pairIdx: number) => (
                <div
                  key={pairIdx}
                  className="flex items-center gap-4 p-2 border rounded"
                >
                  <JapaneseText data={pair.left} />
                  <span>→</span>
                  <select
                    className="flex-1 p-2 border border-input bg-background text-foreground rounded"
                    onChange={(e) =>
                      handleAnswer(exerciseId, {
                        ...userAnswer,
                        [pairIdx]: e.target.value,
                      })
                    }
                  >
                    <option value="">Select...</option>
                    {pair.right_options_en?.map(
                      (opt: string, optIdx: number) => (
                        <option key={optIdx} value={opt}>
                          {opt}
                        </option>
                      )
                    )}
                  </select>
                </div>
              ))}
            </div>
          )}
          {exercise.exercise_type === "ordering" && exercise.segments && (
            <div className="space-y-2">
              {exercise.segments.map((segment: string, segIdx: number) => (
                <div key={segIdx} className="p-2 border rounded cursor-move">
                  {segIdx + 1}. {segment}
                </div>
              ))}
            </div>
          )}
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => toggleShowAnswer(exerciseId)}
            >
              {isShowingAnswer ? "Hide" : "Show"} Answer
            </Button>
          </div>
          {isShowingAnswer && exercise.correct_answer !== undefined && (
            <div className="mt-2 p-2 bg-green-500/10 rounded">
              <strong>Correct Answer:</strong> {String(exercise.correct_answer)}
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
            No comprehension exercises available
          </p>
        )}
      </CardContent>
    </Card>
  );
}
