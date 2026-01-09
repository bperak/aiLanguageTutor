"use client";

import React, { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { BarChart3, Loader2, Target, TrendingUp } from "lucide-react";
import {
  getScriptItemProgress,
  getScriptProgressSummary,
  type ScriptItemProgress,
  type ScriptProgressSummary,
} from "@/lib/api/script";

function ScriptProgressPageContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const scriptType =
    (searchParams.get("type") as "hiragana" | "katakana") || null;

  const [summary, setSummary] = useState<ScriptProgressSummary | null>(null);
  const [itemProgress, setItemProgress] = useState<ScriptItemProgress[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadProgress = async () => {
      try {
        setLoading(true);
        const [summaryData, itemsData] = await Promise.all([
          getScriptProgressSummary(scriptType || undefined),
          getScriptItemProgress({
            script_type: scriptType || undefined,
            limit: 200,
          }),
        ]);
        setSummary(summaryData);
        setItemProgress(itemsData);
      } catch (err: unknown) {
        setError(
          err instanceof Error ? err.message : "Failed to load progress"
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
    loadProgress();
  }, [scriptType, router]);

  if (loading) {
    return (
      <div className="max-w-6xl mx-auto px-4 py-8">
        <div className="flex items-center justify-center h-64">
          <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
        </div>
      </div>
    );
  }

  if (error || !summary) {
    return (
      <div className="max-w-6xl mx-auto px-4 py-8">
        <Card>
          <CardContent className="text-center py-12">
            <p className="text-muted-foreground">
              {error || "No progress data available"}
            </p>
            <Button onClick={() => router.push("/script")} className="mt-4">
              Back to Overview
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  const masteryRate =
    summary.items_practiced > 0
      ? (summary.mastered_items / summary.items_practiced) * 100
      : 0;

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold text-foreground">
          Script Progress
        </h1>
        <p className="text-muted-foreground mt-2">
          {scriptType
            ? `Viewing ${scriptType} progress`
            : "Viewing all script progress"}
        </p>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Total Attempts
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{summary.total_attempts}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Correct Rate
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {(summary.correct_rate * 100).toFixed(1)}%
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Items Practiced
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{summary.items_practiced}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Mastered
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{summary.mastered_items}</div>
          </CardContent>
        </Card>
      </div>

      {/* Mastery Progress */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Target className="w-5 h-5" />
            Mastery Progress
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span>Overall Mastery</span>
              <span>{masteryRate.toFixed(1)}%</span>
            </div>
            <Progress value={masteryRate} className="h-2" />
          </div>
        </CardContent>
      </Card>

      {/* Item Progress List */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <BarChart3 className="w-5 h-5" />
            Item Progress
          </CardTitle>
        </CardHeader>
        <CardContent>
          {itemProgress.length === 0 ? (
            <p className="text-center text-muted-foreground py-8">
              No practice data yet. Start practicing to see your progress!
            </p>
          ) : (
            <div className="space-y-2">
              {itemProgress.map((item) => (
                <div
                  key={item.item_id}
                  className="flex items-center gap-4 p-3 border rounded-lg"
                >
                  <div className="flex-1">
                    <div className="font-medium">{item.item_id}</div>
                    <div className="text-sm text-muted-foreground">
                      {item.attempts} attempts •{" "}
                      {(item.correct_rate * 100).toFixed(0)}% correct
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="text-sm text-muted-foreground">
                      Mastery:
                    </div>
                    <div className="flex gap-1">
                      {[1, 2, 3, 4, 5].map((level) => (
                        <div
                          key={level}
                          className={`w-3 h-3 rounded-full ${
                            level <= item.mastery_level
                              ? "bg-primary"
                              : "bg-muted"
                          }`}
                        />
                      ))}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

export default function ScriptProgressPage() {
  return (
    <Suspense
      fallback={
        <div className="max-w-6xl mx-auto px-4 py-8">
          <div className="flex items-center justify-center h-64">
            <Loader2 className="w-8 h-8 animate-spin text-primary" />
          </div>
        </div>
      }
    >
      <ScriptProgressPageContent />
    </Suspense>
  );
}
