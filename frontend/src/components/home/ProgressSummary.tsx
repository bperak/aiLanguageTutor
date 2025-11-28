"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

interface ProgressSummaryProps {
  progressSummary?: {
    total_sessions?: number
    total_messages?: number
    last_session_at?: string | null
  }
}

export default function ProgressSummary({ progressSummary }: ProgressSummaryProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Your Progress</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          <div className="flex justify-between items-center">
            <span className="text-sm text-muted-foreground">Total Sessions</span>
            <span className="text-lg font-semibold">{progressSummary?.total_sessions || 0}</span>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-sm text-muted-foreground">Total Messages</span>
            <span className="text-lg font-semibold">{progressSummary?.total_messages || 0}</span>
          </div>
          {progressSummary?.last_session_at && (
            <div className="flex justify-between items-center">
              <span className="text-sm text-muted-foreground">Last Session</span>
              <span className="text-sm">
                {new Date(progressSummary.last_session_at).toLocaleDateString()}
              </span>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )
}

