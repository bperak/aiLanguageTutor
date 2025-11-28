"use client"

import React from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { JapaneseText } from "@/components/text/JapaneseText"
import { Badge } from "@/components/ui/badge"
import type { ObjectiveCard as ObjectiveCardType } from "@/types/lesson-root"

interface ObjectiveCardProps {
  data: ObjectiveCardType
}

export function ObjectiveCard({ data }: ObjectiveCardProps) {
  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle className="text-2xl">
          <JapaneseText data={data.title} />
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="prose dark:prose-invert">
          <JapaneseText data={data.body} />
        </div>

        {data.success_criteria && data.success_criteria.length > 0 && (
          <div className="mt-6">
            <h3 className="text-lg font-semibold mb-2">Success Criteria</h3>
            <ul className="space-y-2">
              {data.success_criteria.map((criterion, idx) => (
                <li key={idx} className="flex items-start">
                  <span className="mr-2 mt-1">✓</span>
                  <span>{criterion}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {data.outcomes && data.outcomes.length > 0 && (
          <div className="mt-4">
            <h3 className="text-lg font-semibold mb-2">Learning Outcomes</h3>
            <div className="flex flex-wrap gap-2">
              {data.outcomes.map((outcome, idx) => (
                <Badge key={idx} variant="secondary">
                  {outcome}
                </Badge>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

