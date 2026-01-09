"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Trophy, MessageSquare, Calendar, TrendingUp } from "lucide-react";

interface ProgressSummaryProps {
  progressSummary?: {
    total_sessions?: number;
    total_messages?: number;
    last_session_at?: string | null;
  };
}

function getAchievementLevel(sessions: number): { level: string; icon: string; color: string } {
  if (sessions >= 100) return { level: "Master Learner", icon: "🏆", color: "text-yellow-500" };
  if (sessions >= 50) return { level: "Advanced Learner", icon: "⭐", color: "text-purple-500" };
  if (sessions >= 25) return { level: "Dedicated Learner", icon: "🎯", color: "text-blue-500" };
  if (sessions >= 10) return { level: "Active Learner", icon: "🌟", color: "text-green-500" };
  if (sessions >= 5) return { level: "Getting Started", icon: "🌱", color: "text-teal-500" };
  return { level: "New Learner", icon: "👋", color: "text-gray-500" };
}

function getDaysSinceLastSession(lastSessionAt: string | null): number | null {
  if (!lastSessionAt) return null;
  const lastSession = new Date(lastSessionAt);
  const now = new Date();
  const diffTime = Math.abs(now.getTime() - lastSession.getTime());
  const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24));
  return diffDays;
}

function formatLastSession(days: number | null): string {
  if (days === null) return "No sessions yet";
  if (days === 0) return "Today";
  if (days === 1) return "Yesterday";
  if (days < 7) return `${days} days ago`;
  if (days < 30) return `${Math.floor(days / 7)} weeks ago`;
  return `${Math.floor(days / 30)} months ago`;
}

export default function ProgressSummary({
  progressSummary,
}: ProgressSummaryProps) {
  const sessions = progressSummary?.total_sessions || 0;
  const messages = progressSummary?.total_messages || 0;
  const daysSince = getDaysSinceLastSession(progressSummary?.last_session_at || null);
  const achievement = getAchievementLevel(sessions);
  const avgMessagesPerSession = sessions > 0 ? Math.round(messages / sessions) : 0;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <TrendingUp className="h-5 w-5" />
          Your Progress
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {/* Achievement Level */}
          <div className="text-center p-3 bg-muted/50 rounded-lg">
            <div className={`text-2xl mb-1 ${achievement.color}`}>{achievement.icon}</div>
            <div className="font-semibold text-sm">{achievement.level}</div>
            <div className="text-xs text-muted-foreground mt-1">
              {sessions} {sessions === 1 ? "session" : "sessions"} completed
            </div>
          </div>

          {/* Key Stats */}
          <div className="grid grid-cols-2 gap-3">
            <div className="flex items-center gap-2 p-2 bg-muted/30 rounded">
              <MessageSquare className="h-4 w-4 text-muted-foreground" />
              <div>
                <div className="text-xs text-muted-foreground">Messages</div>
                <div className="font-semibold">{messages}</div>
              </div>
            </div>
            <div className="flex items-center gap-2 p-2 bg-muted/30 rounded">
              <Trophy className="h-4 w-4 text-muted-foreground" />
              <div>
                <div className="text-xs text-muted-foreground">Avg/Session</div>
                <div className="font-semibold">{avgMessagesPerSession}</div>
              </div>
            </div>
          </div>

          {/* Last Session */}
          {daysSince !== null && (
            <div className="flex items-center gap-2 p-2 border-t pt-3">
              <Calendar className="h-4 w-4 text-muted-foreground" />
              <div className="flex-1">
                <div className="text-xs text-muted-foreground">Last Active</div>
                <div className="text-sm font-medium">{formatLastSession(daysSince)}</div>
              </div>
            </div>
          )}

          {/* Encouragement Message */}
          {sessions > 0 && (
            <div className="text-xs text-center text-muted-foreground pt-2 border-t">
              {sessions < 5 && "Keep going! You're building great habits."}
              {sessions >= 5 && sessions < 10 && "Great progress! You're on a roll."}
              {sessions >= 10 && sessions < 25 && "Impressive dedication! Keep it up."}
              {sessions >= 25 && "Outstanding commitment! You're a true learner."}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
