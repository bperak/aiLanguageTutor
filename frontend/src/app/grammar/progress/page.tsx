"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import {
  AlertCircle,
  ArrowLeft,
  BookOpen,
  CheckCircle,
  Target,
  TrendingUp,
} from "lucide-react";
import { apiGet } from "@/lib/api";
import {
  getUserPatternProgress,
  type PatternProgress,
} from "@/lib/api/grammar-progress";

export default function GrammarProgressPage() {
  const router = useRouter();
  const [progressData, setProgressData] = useState<PatternProgress[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadProgress();
  }, []);

  const loadProgress = async () => {
    try {
      setLoading(true);
      const data = await getUserPatternProgress({ limit: 100 });
      setProgressData(data);
    } catch (error) {
      console.error("Error loading progress:", error);
      setProgressData([]);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="flex items-center justify-center h-64">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4"></div>
            <p className="text-muted-foreground">Loading progress...</p>
          </div>
        </div>
      </div>
    );
  }

  const mastered = progressData.filter((p) => p.mastery_level >= 5).length;
  const inProgress = progressData.filter(
    (p) => p.mastery_level >= 2 && p.mastery_level < 5
  ).length;
  const justStarted = progressData.filter((p) => p.mastery_level === 1).length;
  const averageMastery =
    progressData.length > 0
      ? progressData.reduce((sum, p) => sum + p.mastery_level, 0) /
        progressData.length
      : 0;

  return (
    <div className="container mx-auto px-4 py-8">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-3">
          <Button variant="ghost" onClick={() => router.push("/grammar")}>
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back to Grammar
          </Button>
        </div>
        <h1 className="text-2xl md:text-3xl font-bold text-foreground mb-2">
          Grammar Learning Progress
        </h1>
        <p className="text-muted-foreground">
          Track your progress across all grammar patterns
        </p>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Total Studied
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{progressData.length}</div>
            <p className="text-xs text-muted-foreground mt-1">patterns</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Mastered
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{mastered}</div>
            <p className="text-xs text-muted-foreground mt-1">level 5/5</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              In Progress
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-blue-600">{inProgress}</div>
            <p className="text-xs text-muted-foreground mt-1">level 2-4</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Average Mastery
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {averageMastery.toFixed(1)}
            </div>
            <p className="text-xs text-muted-foreground mt-1">out of 5</p>
          </CardContent>
        </Card>
      </div>

      {/* Progress List */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <TrendingUp className="w-5 h-5" />
            Pattern Progress
          </CardTitle>
        </CardHeader>
        <CardContent>
          {progressData.length === 0 ? (
            <div className="text-center py-8">
              <BookOpen className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
              <p className="text-muted-foreground">No progress yet</p>
              <p className="text-sm text-muted-foreground mt-2">
                Start studying patterns to see your progress here
              </p>
              <Button onClick={() => router.push("/grammar")} className="mt-4">
                Browse Patterns
              </Button>
            </div>
          ) : (
            <div className="space-y-4">
              {progressData.map((progress) => (
                <div
                  key={progress.pattern_id}
                  className="border rounded-lg p-4 hover:bg-muted/50 transition-colors cursor-pointer"
                  onClick={() =>
                    router.push(`/grammar/study/${progress.pattern_id}`)
                  }
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-2">
                        <h3 className="font-semibold">
                          {progress.pattern_name}
                        </h3>
                        {progress.is_completed && (
                          <Badge variant="default" className="bg-green-600">
                            <CheckCircle className="w-3 h-3 mr-1" />
                            Mastered
                          </Badge>
                        )}
                        {progress.mastery_level >= 2 &&
                          progress.mastery_level < 5 && (
                            <Badge variant="secondary">In Progress</Badge>
                          )}
                        {progress.mastery_level === 1 && (
                          <Badge variant="outline">Just Started</Badge>
                        )}
                      </div>
                      <div className="flex items-center gap-4 text-sm text-muted-foreground">
                        <span>Mastery: {progress.mastery_level}/5</span>
                        <span>Studies: {progress.study_count}</span>
                        {progress.last_studied && (
                          <span>
                            Last:{" "}
                            {new Date(
                              progress.last_studied
                            ).toLocaleDateString()}
                          </span>
                        )}
                      </div>
                      <Progress
                        value={(progress.mastery_level / 5) * 100}
                        className="mt-2 h-2"
                      />
                    </div>
                    <div className="ml-4 text-right">
                      {progress.next_review_date && (
                        <div className="text-xs text-muted-foreground">
                          Review:{" "}
                          {new Date(
                            progress.next_review_date
                          ).toLocaleDateString()}
                        </div>
                      )}
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
