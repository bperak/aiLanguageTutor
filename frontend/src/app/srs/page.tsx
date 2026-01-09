"use client";

import React, { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import {
  Calendar,
  Target,
  TrendingUp,
  Clock,
  CheckCircle2,
  Star,
  ArrowRight,
  BookOpen,
} from "lucide-react";
import {
  getPatternsDueForReview,
  getUserProgressSummary,
  recordStudyWithSRS,
} from "@/lib/api/grammar-progress";

interface DueReviewItem {
  pattern_id: string;
  pattern_name: string;
  pattern: string;
  pattern_romaji: string;
  example_sentence: string;
  example_romaji: string;
  classification: string;
  textbook: string;
  mastery_level: number;
  next_review_date: string;
  study_count: number;
  days_overdue?: number;
}

interface ProgressSummary {
  total_patterns_studied: number;
  average_mastery_level: number;
  patterns_due_today: number;
  patterns_overdue: number;
  current_streak_days: number;
  total_study_sessions: number;
  estimated_daily_reviews: number;
}

export default function SRSPage() {
  const [dueItems, setDueItems] = useState<DueReviewItem[]>([]);
  const [progressSummary, setProgressSummary] = useState<ProgressSummary | null>(null);
  const [currentReviewIndex, setCurrentReviewIndex] = useState(0);
  const [showAnswer, setShowAnswer] = useState(false);
  const [sessionActive, setSessionActive] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadSRSData();
  }, []);

  const loadSRSData = async () => {
    try {
      setLoading(true);
      const [dueData, summaryData] = await Promise.all([
        getPatternsDueForReview(),
        getUserProgressSummary(),
      ]);

      // Add days overdue calculation
      const today = new Date();
      const enhancedDueData = (dueData as unknown as DueReviewItem[]).map(
        (item) => {
          const reviewDate = new Date(item.next_review_date);
          const daysDiff = Math.floor(
            (today.getTime() - reviewDate.getTime()) / (1000 * 60 * 60 * 24)
          );
          return { ...item, days_overdue: daysDiff > 0 ? daysDiff : 0 };
        }
      );

      // Sort by urgency (overdue first, then by review date)
      enhancedDueData.sort((a, b) => {
        if (a.days_overdue && b.days_overdue)
          return b.days_overdue - a.days_overdue;
        if (a.days_overdue && !b.days_overdue) return -1;
        if (!a.days_overdue && b.days_overdue) return 1;
        return (
          new Date(a.next_review_date).getTime() -
          new Date(b.next_review_date).getTime()
        );
      });
      setDueItems(enhancedDueData);

      // Map backend summary to local view model
      const mappedSummary: ProgressSummary = {
        total_patterns_studied:
          (summaryData as any).total_patterns_studied ?? 0,
        average_mastery_level: (summaryData as any).average_mastery_level ?? 0,
        patterns_due_today: (summaryData as any).patterns_due_today ?? 0,
        patterns_overdue: (summaryData as any).patterns_overdue ?? 0,
        current_streak_days: (summaryData as any).current_streak_days ?? 0,
        total_study_sessions: (summaryData as any).total_study_sessions ?? 0,
        estimated_daily_reviews:
          (summaryData as any).estimated_daily_reviews ??
          (summaryData as any).patterns_due_today ??
          0,
      };
      setProgressSummary(mappedSummary);
    } catch (error) {
      console.error("Error loading SRS data:", error);
    } finally {
      setLoading(false);
    }
  };

  const startReviewSession = () => {
    if (dueItems.length > 0) {
      setSessionActive(true);
      setCurrentReviewIndex(0);
      setShowAnswer(false);
    }
  };

  const handleSRSGrade = async (grade: "again" | "hard" | "good" | "easy") => {
    if (!dueItems[currentReviewIndex]) return;
    const currentItem = dueItems[currentReviewIndex];

    try {
      await recordStudyWithSRS(
        currentItem.pattern_id,
        grade,
        60,
        getConfidenceFromGrade(grade)
      );

      // Move to next item or finish session
      if (currentReviewIndex < dueItems.length - 1) {
        setCurrentReviewIndex((prev) => prev + 1);
        setShowAnswer(false);
      } else {
        // Session complete
        setSessionActive(false);
        await loadSRSData();
      }
    } catch (error) {
      console.error("Error recording SRS grade:", error);
    }
  };

  const getConfidenceFromGrade = (grade: string): number => {
    const gradeMap = { again: 1, hard: 2, good: 4, easy: 5 };
    return gradeMap[grade as keyof typeof gradeMap] || 3;
  };

  const getMasteryColor = (level: number): string => {
    if (level >= 4) return "text-green-600";
    if (level >= 3) return "text-blue-600";
    if (level >= 2) return "text-yellow-600";
    return "text-red-600";
  };

  const getUrgencyBadge = (item: DueReviewItem) => {
    if (item.days_overdue && item.days_overdue > 0) {
      return <Badge variant="destructive">Overdue {item.days_overdue}d</Badge>;
    }
    const today = new Date().toDateString();
    const reviewDate = new Date(item.next_review_date).toDateString();
    if (today === reviewDate) {
      return <Badge variant="default">Due Today</Badge>;
    }
    return <Badge variant="outline">Scheduled</Badge>;
  };

  if (loading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="flex items-center justify-center h-64">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
            <p className="text-muted-foreground">
              Loading your SRS schedule...
            </p>
          </div>
        </div>
      </div>
    );
  }

  if (sessionActive && dueItems.length > 0) {
    const currentItem = dueItems[currentReviewIndex];
    return (
      <div className="container mx-auto px-4 py-8 max-w-4xl">
        {/* Session Header */}
        <div className="mb-6">
          <div className="flex justify-between items-center mb-4">
            <h1 className="text-2xl font-bold">SRS Review Session</h1>
            <div className="flex items-center gap-4">
              <span className="text-sm text-muted-foreground">
                {currentReviewIndex + 1} of {dueItems.length}
              </span>
              <Button variant="outline" onClick={() => setSessionActive(false)}>
                End Session
              </Button>
            </div>
          </div>
          <Progress
            value={(currentReviewIndex / dueItems.length) * 100}
            className="w-full"
          />
        </div>

        {/* Review Card */}
        <Card className="mb-6">
          <CardHeader className="pb-4">
            <div className="flex justify-between items-start">
              <div>
                <CardTitle className="text-3xl mb-2">
                  {currentItem.pattern}
                </CardTitle>
                <p className="text-xl text-muted-foreground italic">
                  {currentItem.pattern_romaji}
                </p>
                <div className="flex items-center gap-2 mt-3">
                  <Badge>{currentItem.textbook}</Badge>
                  <Badge variant="outline">{currentItem.classification}</Badge>
                  <div className="flex items-center gap-1">
                    <Star
                      className={`w-4 h-4 ${getMasteryColor(currentItem.mastery_level)}`}
                    />
                    <span className="text-sm font-medium">
                      Level {currentItem.mastery_level}/5
                    </span>
                  </div>
                </div>
              </div>
              {getUrgencyBadge(currentItem)}
            </div>
          </CardHeader>
          <CardContent>
            {!showAnswer ? (
              <div className="text-center py-8">
                <p className="text-lg mb-6">
                  How well do you remember this pattern?
                </p>
                <Button onClick={() => setShowAnswer(true)} size="lg">
                  Show Answer
                </Button>
              </div>
            ) : (
              <div className="space-y-6">
                <div className="bg-blue-500/10 p-4 rounded-lg">
                  <p className="text-lg font-medium mb-2">
                    {currentItem.example_sentence}
                  </p>
                  <p className="text-muted-foreground italic">
                    {currentItem.example_romaji}
                  </p>
                </div>
                <div className="text-center">
                  <p className="text-sm font-medium mb-4">
                    How difficult was this?
                  </p>
                  <div className="grid grid-cols-2 gap-3">
                    <Button
                      onClick={() => handleSRSGrade("again")}
                      variant="outline"
                      className="text-red-600 hover:bg-red-500/10 h-auto p-4 flex-col"
                    >
                      <span className="font-medium">Again</span>
                      <span className="text-xs mt-1">Review in 1 day</span>
                    </Button>
                    <Button
                      onClick={() => handleSRSGrade("hard")}
                      variant="outline"
                      className="text-orange-600 hover:bg-orange-50 h-auto p-4 flex-col"
                    >
                      <span className="font-medium">Hard</span>
                      <span className="text-xs mt-1">Review in 3 days</span>
                    </Button>
                    <Button
                      onClick={() => handleSRSGrade("good")}
                      variant="outline"
                      className="text-blue-600 hover:bg-blue-500/10 h-auto p-4 flex-col"
                    >
                      <span className="font-medium">Good</span>
                      <span className="text-xs mt-1">Review in 1 week</span>
                    </Button>
                    <Button
                      onClick={() => handleSRSGrade("easy")}
                      variant="outline"
                      className="text-green-600 hover:bg-green-500/10 h-auto p-4 flex-col"
                    >
                      <span className="font-medium">Easy</span>
                      <span className="text-xs mt-1">Review in 2+ weeks</span>
                    </Button>
                  </div>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-foreground mb-2">
          Spaced Repetition System
        </h1>
        <p className="text-muted-foreground">
          Review grammar patterns at optimal intervals to maximize retention
        </p>
      </div>

      {/* Progress Overview */}
      {progressSummary && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Due Today</CardTitle>
              <Calendar className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-blue-600 dark:text-blue-400">
                {dueItems.length}
              </div>
              <p className="text-xs text-muted-foreground">
                {
                  dueItems.filter(
                    (item) => item.days_overdue && item.days_overdue > 0
                  ).length
                }{" "}
                overdue
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">
                Average Mastery
              </CardTitle>
              <Target className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {progressSummary.average_mastery_level.toFixed(1)}/5
              </div>
              <Progress
                value={(progressSummary.average_mastery_level / 5) * 100}
                className="mt-2"
              />
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Study Streak</CardTitle>
              <TrendingUp className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-green-600 dark:text-green-400">
                {progressSummary.current_streak_days}
              </div>
              <p className="text-xs text-muted-foreground">days in a row</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">
                Total Sessions
              </CardTitle>
              <CheckCircle2 className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {progressSummary.total_study_sessions}
              </div>
              <p className="text-xs text-muted-foreground">completed</p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Due Items */}
      <Card>
        <CardHeader>
          <div className="flex justify-between items-center">
            <CardTitle className="flex items-center gap-2">
              <Clock className="w-5 h-5" />
              Due for Review ({dueItems.length})
            </CardTitle>
            {dueItems.length > 0 && (
              <Button onClick={startReviewSession} className="flex items-center gap-2">
                <BookOpen className="w-4 h-4" />
                Start Review Session
              </Button>
            )}
          </div>
        </CardHeader>
        <CardContent>
          {dueItems.length === 0 ? (
            <div className="text-center py-12">
              <CheckCircle2 className="w-16 h-16 text-green-500 mx-auto mb-4" />
              <h3 className="text-lg font-semibold mb-2">All caught up! 🎉</h3>
              <p className="text-muted-foreground mb-4">
                No patterns are due for review right now. Great job staying on
                top of your studies!
              </p>
              <Button
                variant="outline"
                onClick={() => (window.location.href = "/grammar")}
              >
                <BookOpen className="w-4 h-4 mr-2" />
                Study New Patterns
              </Button>
            </div>
          ) : (
            <div className="space-y-4">
              {dueItems.slice(0, 10).map((item) => (
                <div
                  key={item.pattern_id}
                  className="border border-border rounded-lg p-4 hover:bg-accent transition-colors"
                >
                  <div className="flex justify-between items-start">
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-2">
                        <h3 className="text-lg font-semibold">{item.pattern}</h3>
                        <span className="text-muted-foreground italic">
                          {item.pattern_romaji}
                        </span>
                        {getUrgencyBadge(item)}
                      </div>
                      <p className="text-muted-foreground mb-2">
                        {item.example_sentence}
                      </p>
                      <div className="flex items-center gap-4 text-sm text-muted-foreground">
                        <div className="flex items-center gap-1">
                          <Star
                            className={`w-4 h-4 ${getMasteryColor(item.mastery_level)}`}
                          />
                          <span>Level {item.mastery_level}/5</span>
                        </div>
                        <span>Studies: {item.study_count}</span>
                        <Badge variant="outline">{item.textbook}</Badge>
                      </div>
                    </div>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() =>
                        (window.location.href = `/grammar/study/${item.pattern_id}`)
                      }
                    >
                      <ArrowRight className="w-4 h-4" />
                    </Button>
                  </div>
                </div>
              ))}
              {dueItems.length > 10 && (
                <div className="text-center py-4">
                  <p className="text-muted-foreground">
                    And {dueItems.length - 10} more patterns due for review...
                  </p>
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
