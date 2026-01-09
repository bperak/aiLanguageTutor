"use client";

import React, { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { JapaneseText } from "@/components/text/JapaneseText";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import type {
  ExercisesCard as ExercisesCardType,
  Exercise,
} from "@/types/lesson-root";

interface ExercisesCardProps {
  data: ExercisesCardType;
}

function MatchExercise({
  exercise,
}: {
  exercise: Extract<Exercise, { exercise_type: "match" }>;
}) {
  const [selected, setSelected] = useState<Record<number, string>>({});
  const [showFeedback, setShowFeedback] = useState(false);

  const handleSelect = (pairIdx: number, option: string) => {
    setSelected((prev) => ({ ...prev, [pairIdx]: option }));
    setShowFeedback(false);
  };

  const checkAnswers = () => {
    setShowFeedback(true);
  };

  return (
    <div className="space-y-4">
      <JapaneseText data={exercise.instructions} />
      <div className="space-y-3">
        {exercise.pairs.map((pair, idx) => (
          <div key={idx} className="border rounded-lg p-3">
            <div className="mb-2">
              <JapaneseText data={pair.left} />
            </div>
            <div className="flex flex-wrap gap-2">
              {pair.right_options_en.map((option) => (
                <Button
                  key={option}
                  variant={selected[idx] === option ? "default" : "outline"}
                  size="sm"
                  onClick={() => handleSelect(idx, option)}
                  className={
                    showFeedback && selected[idx] === option
                      ? selected[idx] === pair.answer_en
                        ? "bg-green-500 hover:bg-green-600"
                        : "bg-red-500 hover:bg-red-600"
                      : ""
                  }
                >
                  {option}
                </Button>
              ))}
            </div>
          </div>
        ))}
      </div>
      <Button onClick={checkAnswers}>Check Answers</Button>
    </div>
  );
}

function FillBlankExercise({
  exercise,
}: {
  exercise: Extract<Exercise, { exercise_type: "fill_blank" }>;
}) {
  const [userAnswer, setUserAnswer] = useState("");
  const [showFeedback, setShowFeedback] = useState(false);

  const checkAnswer = () => {
    setShowFeedback(true);
  };

  const isCorrect = exercise.answer_key_en.some(
    (ans) => ans.toLowerCase().trim() === userAnswer.toLowerCase().trim()
  );

  return (
    <div className="space-y-4">
      <div className="bg-muted p-4 rounded-lg">
        <JapaneseText data={exercise.item} />
      </div>
      <input
        type="text"
        value={userAnswer}
        onChange={(e) => {
          setUserAnswer(e.target.value);
          setShowFeedback(false);
        }}
        className="w-full p-2 border border-input bg-background text-foreground rounded"
        placeholder="Your answer..."
      />
      <Button onClick={checkAnswer}>Check Answer</Button>
      {showFeedback && (
        <div
          className={`p-3 rounded ${isCorrect ? "bg-green-500/10" : "bg-red-500/10"}`}
        >
          {isCorrect
            ? "Correct!"
            : `Possible answers: ${exercise.answer_key_en.join(", ")}`}
        </div>
      )}
    </div>
  );
}

function OrderExercise({
  exercise,
}: {
  exercise: Extract<Exercise, { exercise_type: "order" }>;
}) {
  const [currentOrder, setCurrentOrder] = useState<number[]>([
    ...Array(exercise.segments_ja.length).keys(),
  ]);
  const [showFeedback, setShowFeedback] = useState(false);

  const moveUp = (idx: number) => {
    if (idx === 0) return;
    const newOrder = [...currentOrder];
    [newOrder[idx - 1], newOrder[idx]] = [newOrder[idx], newOrder[idx - 1]];
    setCurrentOrder(newOrder);
    setShowFeedback(false);
  };

  const moveDown = (idx: number) => {
    if (idx === currentOrder.length - 1) return;
    const newOrder = [...currentOrder];
    [newOrder[idx], newOrder[idx + 1]] = [newOrder[idx + 1], newOrder[idx]];
    setCurrentOrder(newOrder);
    setShowFeedback(false);
  };

  const checkOrder = () => {
    setShowFeedback(true);
  };

  const isCorrect =
    JSON.stringify(currentOrder) === JSON.stringify(exercise.correct_order);

  return (
    <div className="space-y-4">
      <JapaneseText data={exercise.instructions} />
      <div className="space-y-2">
        {currentOrder.map((segIdx, displayIdx) => (
          <div key={displayIdx} className="flex items-center gap-2">
            <div className="flex flex-col gap-1">
              <Button
                size="sm"
                variant="outline"
                onClick={() => moveUp(displayIdx)}
                disabled={displayIdx === 0}
              >
                ↑
              </Button>
              <Button
                size="sm"
                variant="outline"
                onClick={() => moveDown(displayIdx)}
                disabled={displayIdx === currentOrder.length - 1}
              >
                ↓
              </Button>
            </div>
            <div className="flex-1 p-3 border rounded">
              {exercise.segments_ja[segIdx]}
            </div>
          </div>
        ))}
      </div>
      <Button onClick={checkOrder}>Check Order</Button>
      {showFeedback && (
        <div
          className={`p-3 rounded ${isCorrect ? "bg-green-500/10" : "bg-red-500/10"}`}
        >
          {isCorrect ? "Correct order!" : "Try again"}
        </div>
      )}
    </div>
  );
}

export function ExercisesCard({ data }: ExercisesCardProps) {
  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle className="text-2xl">Exercises</CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        {data.items.map((exercise, idx) => (
          <Card key={exercise.id} className="p-4">
            <CardHeader className="pb-3">
              <CardTitle className="text-lg flex items-center gap-2">
                <span>Exercise {idx + 1}</span>
                <Badge variant="secondary">{exercise.exercise_type}</Badge>
              </CardTitle>
            </CardHeader>
            <CardContent className="pt-0">
              {exercise.exercise_type === "match" && (
                <MatchExercise exercise={exercise as any} />
              )}
              {exercise.exercise_type === "fill_blank" && (
                <FillBlankExercise exercise={exercise as any} />
              )}
              {exercise.exercise_type === "order" && (
                <OrderExercise exercise={exercise as any} />
              )}
            </CardContent>
          </Card>
        ))}
      </CardContent>
    </Card>
  );
}
