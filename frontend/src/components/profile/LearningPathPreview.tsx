"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Info } from "lucide-react"

export default function LearningPathPreview() {
  return (
    <Card className="border-blue-200 bg-blue-50">
      <CardHeader>
        <CardTitle className="text-lg flex items-center gap-2">
          <Info className="h-4 w-4" />
          Your Learning Path Preview
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <p className="text-sm text-muted-foreground">
          After you complete your profile, we'll generate a personalized learning path based on:
        </p>
        <ul className="text-sm space-y-2 list-disc list-inside text-muted-foreground">
          <li>Your learning goals</li>
          <li>Your current level and experience</li>
          <li>Your preferred learning methods</li>
          <li>Where and when you'll use the language</li>
        </ul>
        <div className="pt-3 border-t">
          <p className="text-xs font-medium text-muted-foreground mb-2">What you'll see on Home:</p>
          <div className="space-y-1 text-xs text-muted-foreground">
            <p>✓ Personalized learning steps</p>
            <p>✓ Progress tracking</p>
            <p>✓ Next recommended activities</p>
            <p>✓ Customized AI guidance</p>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

