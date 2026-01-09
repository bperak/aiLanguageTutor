"use client";

import React, { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import type { InteractionActivitiesCard as InteractionActivitiesCardType } from "@/types/lesson-root";
import { Play, CheckCircle2 } from "lucide-react";

interface InteractionActivitiesCardProps {
  data: InteractionActivitiesCardType;
  sessionId: string;
  canDoId: string;
}

export function InteractionActivitiesCard({
  data,
  sessionId,
  canDoId,
}: InteractionActivitiesCardProps) {
  const [activeActivity, setActiveActivity] = useState<string | null>(null);
  const [completedActivities, setCompletedActivities] = useState<Set<string>>(
    new Set()
  );

  const title = data.title?.en || data.title?.ja || "Interaction Activities";

  const handleStartActivity = (activityId: string) => {
    setActiveActivity(activityId);
  };

  const handleCompleteActivity = (activityId: string) => {
    setCompletedActivities((prev) => new Set([...prev, activityId]));
    setActiveActivity(null);
  };

  const renderActivity = (activity: any, idx: number) => {
    const activityId = activity.id || `activity-${idx}`;
    const isActive = activeActivity === activityId;
    const isCompleted = completedActivities.has(activityId);

    return (
      <Card key={activityId} className="mb-4">
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="text-lg">
              Activity {idx + 1}:{" "}
              {activity.title?.en ||
                activity.title?.ja ||
                activity.activity_type?.replace(/_/g, " ").toUpperCase()}
            </CardTitle>
            {isCompleted && <CheckCircle2 className="w-5 h-5 text-green-500" />}
          </div>
          {activity.instructions && (
            <p className="text-sm text-muted-foreground mt-2">
              {activity.instructions.en ||
                activity.instructions.ja ||
                Object.values(activity.instructions)[0]}
            </p>
          )}
        </CardHeader>
        <CardContent className="space-y-4">
          {activity.scenario && (
            <div className="bg-blue-500/10 p-4 rounded">
              <div className="font-semibold mb-2">Scenario:</div>
              <div className="text-sm">
                {JSON.stringify(activity.scenario, null, 2)}
              </div>
            </div>
          )}
          {activity.roles && activity.roles.length > 0 && (
            <div>
              <div className="font-semibold mb-2">Roles:</div>
              <div className="flex flex-wrap gap-2">
                {activity.roles.map((role: string, roleIdx: number) => (
                  <Badge key={roleIdx} variant="outline">
                    {role}
                  </Badge>
                ))}
              </div>
            </div>
          )}
          {activity.goals && activity.goals.length > 0 && (
            <div>
              <div className="font-semibold mb-2">Goals:</div>
              <ul className="list-disc list-inside space-y-1">
                {activity.goals.map((goal: string, goalIdx: number) => (
                  <li key={goalIdx} className="text-sm">
                    {goal}
                  </li>
                ))}
              </ul>
            </div>
          )}
          {isActive ? (
            <div className="space-y-2">
              <div className="p-4 bg-yellow-500/10 rounded">
                <p className="text-sm font-semibold mb-2">
                  Activity in progress...
                </p>
                {activity.activity_type === "role_play" && (
                  <p className="text-sm">
                    Practice your role in this scenario. Use the scenario
                    context and roles above to guide your interaction.
                  </p>
                )}
                {activity.activity_type === "simulation" && (
                  <p className="text-sm">
                    Follow the scenario and complete the interaction goals
                    listed above.
                  </p>
                )}
                {activity.activity_type === "debate" && (
                  <p className="text-sm">
                    Engage in a structured debate following the scenario and
                    goals.
                  </p>
                )}
                {!activity.activity_type && (
                  <p className="text-sm">
                    Complete the activity following the instructions and goals
                    above.
                  </p>
                )}
              </div>
              <Button
                variant="outline"
                onClick={() => handleCompleteActivity(activityId)}
              >
                Complete Activity
              </Button>
            </div>
          ) : (
            <Button
              onClick={() => handleStartActivity(activityId)}
              disabled={isCompleted}
              className="w-full"
            >
              <Play className="w-4 h-4 mr-2" />
              {isCompleted ? "Completed" : "Start Activity"}
            </Button>
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
            {data.items.map((activity, idx) => renderActivity(activity, idx))}
          </div>
        ) : (
          <p className="text-muted-foreground italic">
            No interaction activities available
          </p>
        )}
      </CardContent>
    </Card>
  );
}
