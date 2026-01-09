"use client";

import React, { Suspense, useCallback, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { ArrowRight, CheckCircle2, Loader2, XCircle } from "lucide-react";
import {
  checkScriptAnswer,
  getScriptItems,
  type ScriptItem,
  type ScriptPracticeCheckResponse,
} from "@/lib/api/script";

type PracticeMode = "kana_to_romaji" | "romaji_to_kana" | "mcq";

function ScriptPracticePageContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const scriptType =
    (searchParams.get("type") as "hiragana" | "katakana") || "hiragana";

  const [items, setItems] = useState<ScriptItem[]>([]);
  const [currentItemIndex, setCurrentItemIndex] = useState(0);
  const [mode, setMode] = useState<PracticeMode>("kana_to_romaji");
  const [userAnswer, setUserAnswer] = useState("");
  const [checking, setChecking] = useState(false);
  const [result, setResult] = useState<ScriptPracticeCheckResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [mcqChoices, setMcqChoices] = useState<string[]>([]);

  // Load items
  useEffect(() => {
    const loadItems = async () => {
      try {
        setLoading(true);
        const data = await getScriptItems({
          script_type: scriptType,
          limit: 500,
        });
        setItems(data);
        if (data.length > 0) {
          setCurrentItemIndex(0);
        }
      } catch (err: unknown) {
        setError(
          err instanceof Error ? err.message : "Failed to load script items"
        );
        if (
          (err as { response?: { status?: number } })?.response?.status === 401
        ) {
          router.push("/login");
        }
      } finally {
        setLoading(false);
      }
    };
    loadItems();
  }, [scriptType, router]);

  const currentItem = items[currentItemIndex];

  const generateChoices = useCallback(
    (item: ScriptItem): string[] => {
      // Generate 4 choices: correct + 3 random wrong
      const allItems = items.filter((i) => i.id !== item.id);
      const wrong = allItems
        .sort(() => Math.random() - 0.5)
        .slice(0, 3)
        .map((i) => i.romaji);
      const choices = [item.romaji, ...wrong].sort(() => Math.random() - 0.5);
      return choices;
    },
    [items]
  );

  // Update MCQ choices when item or mode changes
  useEffect(() => {
    if (currentItem && mode === "mcq") {
      setMcqChoices(generateChoices(currentItem));
    } else {
      setMcqChoices([]);
    }
  }, [currentItem, mode, generateChoices]);

  const handleCheck = useCallback(async () => {
    if (!currentItem || !userAnswer.trim()) return;
    try {
      setChecking(true);
      setResult(null);
      const response = await checkScriptAnswer({
        item_id: currentItem.id,
        mode,
        user_answer: userAnswer,
        choices: mode === "mcq" ? mcqChoices : undefined,
      });
      setResult(response);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to check answer");
    } finally {
      setChecking(false);
    }
  }, [currentItem, mode, userAnswer, mcqChoices]);

  const handleNext = useCallback(() => {
    setResult(null);
    setUserAnswer("");
    setMcqChoices([]);
    setCurrentItemIndex((prev) => (prev + 1) % items.length);
  }, [items.length]);

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-8">
        <div className="flex items-center justify-center h-64">
          <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
        </div>
      </div>
    );
  }

  if (error || items.length === 0) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-8">
        <Card>
          <CardContent className="text-center py-12">
            <p className="text-muted-foreground">
              {error || "No items available"}
            </p>
            <Button onClick={() => router.push("/script")} className="mt-4">
              Back to Overview
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold text-foreground">
          Script Practice
        </h1>
        <p className="text-muted-foreground mt-2 capitalize">
          {scriptType} Practice
        </p>
      </div>

      {/* Mode Selector */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Practice Mode</CardTitle>
        </CardHeader>
        <CardContent>
          <Select
            value={mode}
            onValueChange={(v) => {
              setMode(v as PracticeMode);
              setResult(null);
              setUserAnswer("");
            }}
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="kana_to_romaji">Kana → Romaji</SelectItem>
              <SelectItem value="romaji_to_kana">Romaji → Kana</SelectItem>
              <SelectItem value="mcq">Multiple Choice</SelectItem>
            </SelectContent>
          </Select>
        </CardContent>
      </Card>

      {/* Practice Card */}
      <Card>
        <CardHeader>
          <CardTitle>
            Item {currentItemIndex + 1} of {items.length}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Prompt */}
          <div className="text-center py-8">
            {mode === "kana_to_romaji" && (
              <div>
                <p className="text-sm text-muted-foreground mb-4">
                  Type the romaji for:
                </p>
                <div className="text-6xl font-bold">{currentItem.kana}</div>
              </div>
            )}
            {mode === "romaji_to_kana" && (
              <div>
                <p className="text-sm text-muted-foreground mb-4">
                  Type the kana for:
                </p>
                <div className="text-4xl font-bold">{currentItem.romaji}</div>
              </div>
            )}
            {mode === "mcq" && (
              <div>
                <p className="text-sm text-muted-foreground mb-4">
                  Select the romaji for:
                </p>
                <div className="text-6xl font-bold mb-4">{currentItem.kana}</div>
                <div className="grid grid-cols-2 gap-2 max-w-md mx-auto">
                  {mcqChoices.map((choice, idx) => (
                    <Button
                      key={idx}
                      variant={userAnswer === choice ? "default" : "outline"}
                      onClick={() => setUserAnswer(choice)}
                      className="w-full"
                    >
                      {choice}
                    </Button>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Answer Input (for typing modes) */}
          {mode !== "mcq" && (
            <Input
              value={userAnswer}
              onChange={(e) => setUserAnswer(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !checking && !result) {
                  handleCheck();
                }
              }}
              placeholder="Type your answer..."
              className="text-center text-lg"
              disabled={checking || !!result}
            />
          )}

          {/* Result */}
          {result && (
            <div
              className={`p-4 rounded-lg ${
                result.is_correct ? "bg-green-500/10" : "bg-red-500/10"
              }`}
            >
              <div className="flex items-center gap-2 mb-2">
                {result.is_correct ? (
                  <CheckCircle2 className="w-5 h-5 text-green-600" />
                ) : (
                  <XCircle className="w-5 h-5 text-red-600" />
                )}
                <span
                  className={`font-semibold ${
                    result.is_correct ? "text-green-600" : "text-red-600"
                  }`}
                >
                  {result.is_correct ? "Correct!" : "Incorrect"}
                </span>
              </div>
              <p className="text-sm text-muted-foreground">{result.feedback}</p>
              {!result.is_correct && (
                <p className="text-sm mt-2">
                  Expected: <strong>{result.expected_answer}</strong>
                </p>
              )}
            </div>
          )}

          {/* Actions */}
          <div className="flex gap-2">
            {!result ? (
              <Button
                onClick={handleCheck}
                disabled={checking || !userAnswer.trim()}
                className="flex-1"
              >
                {checking ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Checking...
                  </>
                ) : (
                  "Check Answer"
                )}
              </Button>
            ) : (
              <Button onClick={handleNext} className="flex-1">
                Next <ArrowRight className="w-4 h-4 ml-2" />
              </Button>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

export default function ScriptPracticePage() {
  return (
    <Suspense
      fallback={
        <div className="max-w-4xl mx-auto px-4 py-8">
          <div className="flex items-center justify-center h-64">
            <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
          </div>
        </div>
      }
    >
      <ScriptPracticePageContent />
    </Suspense>
  );
}
