"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  getCanDoRecommendations,
  getCanDoEvidenceSummary,
  type CanDoRecommendations,
  type CanDoEvidenceSummary,
} from "@/lib/api/cando-progress";
import { apiGet } from "@/lib/api";
import {
  BookOpen,
  TrendingUp,
  Target,
  AlertCircle,
  CheckCircle,
  Circle,
} from "lucide-react";

interface CanDoItem {
  uid: string;
  titleEn?: string;
  titleJa?: string;
  level?: string;
  primaryTopic?: string;
}

export default function CanDoProgressPage() {
  const router = useRouter();
  const [recommendations, setRecommendations] =
    useState<CanDoRecommendations | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedCanDo, setSelectedCanDo] = useState<string | null>(null);
  const [evidenceSummary, setEvidenceSummary] =
    useState<CanDoEvidenceSummary | null>(null);
  const [allCanDos, setAllCanDos] = useState<CanDoItem[]>([]);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);

      const [recs, candos] = await Promise.all([
        getCanDoRecommendations(10),
        apiGet<{ items: CanDoItem[] }>("/api/v1/cando/list?limit=100"),
      ]);
      setRecommendations(recs);
      setAllCanDos(candos.items || []);
    } catch (e: any) {
      console.error("Failed to load progress data:", e);
      setError(e.message || "Failed to load progress data");
    } finally {
      setLoading(false);
    }
  };

  const loadEvidenceSummary = async (canDoId: string) => {
    try {
      const summary = await getCanDoEvidenceSummary(canDoId, 10);
      setEvidenceSummary(summary);
      setSelectedCanDo(canDoId);
    } catch (e: any) {
      console.error("Failed to load evidence summary:", e);
    }
  };

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-6">
        <Card className="p-8 text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4"></div>
          <p className="text-muted-foreground">Loading progress...</p>
        </Card>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-6">
        <Card className="p-8 text-center border-red-500/30 bg-red-500/10">
          <CardHeader>
            <CardTitle className="text-xl mb-2 text-red-600">❌ Error</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-red-600 mb-4">{error}</p>
            <Button onClick={loadData} variant="outline">
              🔄 Retry
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 py-6">
      <div className="mb-6">
        <h1 className="text-3xl font-bold mb-2">CanDo Lesson Progress</h1>
        <p className="text-muted-foreground">
          Track your learning progress and get personalized recommendations
        </p>
      </div>

      <Tabs defaultValue="overview" className="space-y-6">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="recommendations">Recommendations</TabsTrigger>
          <TabsTrigger value="lessons">All Lessons</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-6">
          {/* Statistics */}
          {recommendations && (
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-muted-foreground">
                    Lessons Studied
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">
                    {recommendations.total_lessons_studied}
                  </div>
                </CardContent>
              </Card>
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-muted-foreground">
                    Total Attempts
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">
                    {recommendations.total_attempts}
                  </div>
                </CardContent>
              </Card>
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-muted-foreground">
                    Review Items
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">
                    {recommendations.review_items.length}
                  </div>
                </CardContent>
              </Card>
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-muted-foreground">
                    Focus Areas
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">
                    {recommendations.focus_areas.length}
                  </div>
                </CardContent>
              </Card>
            </div>
          )}

          {/* Focus Areas */}
          {recommendations && recommendations.focus_areas.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Target className="w-5 h-5" />
                  Focus Areas
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground mb-4">
                  Stages that need more practice:
                </p>
                <div className="space-y-3">
                  {recommendations.focus_areas.map((area, idx) => (
                    <div key={idx} className="flex items-center justify-between">
                      <span className="capitalize font-medium">{area.stage}</span>
                      <div className="flex items-center gap-2">
                        <Progress
                          value={(area.practice_count / 10) * 100}
                          className="w-32"
                        />
                        <span className="text-sm text-muted-foreground">
                          {area.practice_count} attempts
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Common Errors */}
          {recommendations && recommendations.common_errors.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <AlertCircle className="w-5 h-5" />
                  Common Errors
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex flex-wrap gap-2">
                  {recommendations.common_errors.map((err, idx) => (
                    <Badge key={idx} variant="destructive">
                      {err}
                    </Badge>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="recommendations" className="space-y-6">
          {/* Next Lesson */}
          {recommendations?.next_lesson && (
            <Card className="border-blue-500/30 bg-blue-500/10">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <BookOpen className="w-5 h-5 text-blue-600 dark:text-blue-400" />
                  Recommended Next Lesson
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div>
                    <h3 className="font-semibold text-lg">
                      {recommendations.next_lesson.title}
                    </h3>
                    <div className="flex items-center gap-2 mt-2">
                      {recommendations.next_lesson.level && (
                        <Badge>{recommendations.next_lesson.level}</Badge>
                      )}
                      {recommendations.next_lesson.topic && (
                        <Badge variant="outline">
                          {recommendations.next_lesson.topic}
                        </Badge>
                      )}
                      <Badge variant="secondary">
                        {recommendations.next_lesson.reason}
                      </Badge>
                    </div>
                  </div>
                  <Button
                    onClick={() =>
                      router.push(`/cando/${recommendations.next_lesson!.can_do_id}`)
                    }
                    className="w-full"
                  >
                    Start Lesson
                  </Button>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Review Items */}
          {recommendations && recommendations.review_items.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <TrendingUp className="w-5 h-5" />
                  Review Items
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground mb-4">
                  Lessons that need more practice (low mastery level):
                </p>
                <div className="space-y-3">
                  {recommendations.review_items.map((item, idx) => {
                    const canDo = allCanDos.find(
                      (c) => c.uid === item.can_do_id
                    );
                    return (
                      <div
                        key={idx}
                        className="flex items-center justify-between p-3 border border-border rounded-lg hover:bg-accent cursor-pointer"
                        onClick={() => router.push(`/cando/${item.can_do_id}`)}
                      >
                        <div className="flex-1">
                          <h4 className="font-medium">
                            {canDo?.titleEn || canDo?.titleJa || item.can_do_id}
                          </h4>
                          <p className="text-sm text-muted-foreground">
                            Mastery Level: {item.mastery_level}/5
                          </p>
                        </div>
                        <Button variant="outline" size="sm">
                          Review
                        </Button>
                      </div>
                    );
                  })}
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="lessons" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>All CanDo Lessons</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {allCanDos.map((canDo) => (
                  <div
                    key={canDo.uid}
                    className="flex items-center justify-between p-3 border border-border rounded-lg hover:bg-accent cursor-pointer"
                    onClick={() => loadEvidenceSummary(canDo.uid)}
                  >
                    <div className="flex-1">
                      <h4 className="font-medium">
                        {canDo.titleEn || canDo.titleJa || canDo.uid}
                      </h4>
                      <div className="flex items-center gap-2 mt-1">
                        {canDo.level && (
                          <Badge variant="outline">{canDo.level}</Badge>
                        )}
                        {canDo.primaryTopic && (
                          <Badge variant="secondary">{canDo.primaryTopic}</Badge>
                        )}
                      </div>
                    </div>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={(e) => {
                        e.stopPropagation();
                        router.push(`/cando/${canDo.uid}`);
                      }}
                    >
                      Study
                    </Button>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Evidence Summary for Selected Lesson */}
          {selectedCanDo && evidenceSummary && (
            <Card>
              <CardHeader>
                <CardTitle>
                  Evidence Summary: {evidenceSummary.can_do_title}
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                  <div>
                    <p className="text-sm text-muted-foreground">Total Attempts</p>
                    <p className="text-2xl font-bold">
                      {evidenceSummary.total_attempts}
                    </p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Correct Rate</p>
                    <p className="text-2xl font-bold">
                      {(evidenceSummary.correct_rate * 100).toFixed(0)}%
                    </p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Mastery Level</p>
                    <p className="text-2xl font-bold">
                      {evidenceSummary.mastery_level}/5
                    </p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Stages</p>
                    <p className="text-sm">
                      {Object.keys(evidenceSummary.attempts_by_stage).length}{" "}
                      stages practiced
                    </p>
                  </div>
                </div>

                {evidenceSummary.common_error_tags.length > 0 && (
                  <div className="mt-4">
                    <p className="text-sm font-medium mb-2">Common Errors:</p>
                    <div className="flex flex-wrap gap-2">
                      {evidenceSummary.common_error_tags.map((tag, idx) => (
                        <Badge key={idx} variant="destructive">
                          {tag}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}

                {evidenceSummary.recent_attempts.length > 0 && (
                  <div className="mt-4">
                    <p className="text-sm font-medium mb-2">Recent Attempts:</p>
                    <div className="space-y-2">
                      {evidenceSummary.recent_attempts
                        .slice(0, 5)
                        .map((attempt, idx) => (
                          <div
                            key={idx}
                            className="flex items-center gap-2 text-sm"
                          >
                            {attempt.is_correct ? (
                              <CheckCircle className="w-4 h-4 text-green-600 dark:text-green-400" />
                            ) : (
                              <Circle className="w-4 h-4 text-red-600 dark:text-red-400" />
                            )}
                            <span className="capitalize">{attempt.stage}</span>
                            {attempt.user_response && (
                              <span className="text-muted-foreground">
                                - {attempt.user_response.substring(0, 50)}
                              </span>
                            )}
                          </div>
                        ))}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
