"use client"

import React, { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import type { DrillsCard as DrillsCardType } from "@/types/lesson-root"

interface DrillsCardProps {
  data: DrillsCardType
}

export function DrillsCard({ data }: DrillsCardProps) {
  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle className="text-2xl">Practice Drills</CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        {data.drills.map((drill, idx) => (
          <Card key={drill.id} className="p-4">
            <CardHeader className="pb-3">
              <CardTitle className="text-lg flex items-center gap-2">
                <span>Drill {idx + 1}</span>
                <Badge variant="secondary">{drill.drill_type}</Badge>
              </CardTitle>
            </CardHeader>
            <CardContent className="pt-0">
            {drill.drill_type === "substitution" && (
              <SubstitutionDrill drill={drill} />
            )}

            {drill.drill_type === "pronunciation" && (
              <PronunciationDrill drill={drill} />
            )}
            </CardContent>
          </Card>
        ))}
      </CardContent>
    </Card>
  )
}

function SubstitutionDrill({ drill }: { drill: Extract<DrillsCardType["drills"][0], { drill_type: "substitution" }> }) {
  const [currentSeedIdx, setCurrentSeedIdx] = useState(0)
  const [userInput, setUserInput] = useState("")

  const currentSeed = drill.seed_items[currentSeedIdx]

  const nextSeed = () => {
    setCurrentSeedIdx((prev) => (prev + 1) % drill.seed_items.length)
    setUserInput("")
  }

  return (
    <div className="space-y-4">
      <div className="text-sm text-gray-600 dark:text-gray-400">
        Pattern: {drill.pattern_ref}
      </div>
      <div className="text-sm text-gray-600 dark:text-gray-400">
        Template: {drill.prompt_template.template}
      </div>
      
      <div className="bg-blue-50 dark:bg-blue-950 p-4 rounded-lg">
        <div className="font-semibold mb-2">Current word:</div>
        <div className="text-lg">
          {currentSeed.place} ({currentSeed.specialty_en})
        </div>
      </div>

      <div>
        <label className="block text-sm mb-2">Your sentence:</label>
        <input
          type="text"
          value={userInput}
          onChange={(e) => setUserInput(e.target.value)}
          className="w-full p-2 border rounded"
          placeholder="Create a sentence using this word..."
        />
      </div>

      <div className="flex gap-2">
        <Button onClick={nextSeed}>Next Word</Button>
      </div>

      <div className="text-xs text-gray-500">
        AI Support: {drill.ai_support.prompt}
      </div>
    </div>
  )
}

function PronunciationDrill({ drill }: { drill: Extract<DrillsCardType["drills"][0], { drill_type: "pronunciation" }> }) {
  const [currentIdx, setCurrentIdx] = useState(0)

  const currentTarget = drill.focus[currentIdx]

  const nextWord = () => {
    setCurrentIdx((prev) => (prev + 1) % drill.focus.length)
  }

  return (
    <div className="space-y-4">
      <div className="text-center">
        <div className="text-3xl font-bold mb-2">{currentTarget.ja}</div>
        <div className="text-xl text-gray-600 dark:text-gray-400 italic">
          {currentTarget.romaji}
        </div>
      </div>

      <div className="flex justify-center gap-2">
        <Button onClick={nextWord}>Next Word</Button>
      </div>

      <div className="text-xs text-gray-500 text-center">
        AI Support: {drill.ai_support.prompt}
      </div>

      <div className="text-sm text-gray-600 dark:text-gray-400 text-center">
        {currentIdx + 1} / {drill.focus.length}
      </div>
    </div>
  )
}

