"use client"

import React, { useState } from "react"
import { Card, CardContent } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { ObjectiveCard } from "./cards/ObjectiveCard"
import { WordsCard } from "./cards/WordsCard"
import { GrammarPatternsCard } from "./cards/GrammarPatternsCard"
import { LessonDialogueCard } from "./cards/LessonDialogueCard"
import { ReadingCard } from "./ReadingCard"
import { GuidedDialogueCard } from "./cards/GuidedDialogueCard"
import { ExercisesCard } from "./cards/ExercisesCard"
import { CultureCard } from "./cards/CultureCard"
import { DrillsCard } from "./cards/DrillsCard"
import type { LessonRoot } from "@/types/lesson-root"

interface LessonRootRendererProps {
  lessonData: LessonRoot
  sessionId: string
  onRegenerate?: () => void
  onDisplaySettings?: () => void
  onGenerateImages?: () => void
  isRegenerating?: boolean
  isGeneratingImages?: boolean
}

export function LessonRootRenderer({ 
  lessonData, 
  sessionId, 
  onRegenerate, 
  onDisplaySettings,
  onGenerateImages,
  isRegenerating = false,
  isGeneratingImages = false
}: LessonRootRendererProps) {
  const { lesson } = lessonData
  const { meta, cards } = lesson

  return (
    <div className="w-full max-w-6xl mx-auto space-y-6">
      {/* Lesson Header */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <h1 className="text-3xl font-bold mb-2">
                {meta.can_do.titleEn || meta.can_do.primaryTopic_en}
              </h1>
              {meta.can_do.titleJa && (
                <h2 className="text-xl font-semibold text-gray-600 dark:text-gray-400 mb-2 italic">
                  {meta.can_do.titleJa}
                </h2>
              )}
              <p className="text-gray-600 dark:text-gray-400 mb-4">
                {meta.can_do.description.en}
              </p>
              <div className="flex items-center gap-2 flex-wrap">
                <Badge variant="secondary">{meta.can_do.level}</Badge>
                <Badge variant="outline">{meta.can_do.skillDomain_ja}</Badge>
                <Badge variant="outline">{meta.can_do.type_ja}</Badge>
                {onDisplaySettings && (
                  <Button 
                    variant="outline" 
                    size="sm" 
                    onClick={onDisplaySettings}
                    className="h-6 text-xs"
                  >
                    ⚙️ Display
                  </Button>
                )}
                {onGenerateImages && (
                  <Button 
                    variant="outline" 
                    size="sm" 
                    onClick={onGenerateImages}
                    disabled={isGeneratingImages || isRegenerating}
                    className="h-6 text-xs"
                  >
                    {isGeneratingImages ? "⏳ Generating..." : "🖼️ Generate Images"}
                  </Button>
                )}
                {onRegenerate && (
                  <Button 
                    variant="outline" 
                    size="sm" 
                    onClick={onRegenerate}
                    disabled={isRegenerating || isGeneratingImages}
                    className="h-6 text-xs"
                  >
                    🔄 Regenerate
                  </Button>
                )}
              </div>
            </div>
            <div className="text-sm text-gray-500">
              <div>Source: {meta.can_do.source}</div>
              <div>ID: {meta.can_do.uid}</div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Card Tabs */}
      <Tabs defaultValue="objective" className="w-full">
        <TabsList className="grid w-full grid-cols-4 lg:grid-cols-9">
          <TabsTrigger value="objective">Objective</TabsTrigger>
          <TabsTrigger value="words">Vocabulary</TabsTrigger>
          <TabsTrigger value="grammar">Grammar</TabsTrigger>
          <TabsTrigger value="dialogue">Dialogue</TabsTrigger>
          <TabsTrigger value="reading">Reading</TabsTrigger>
          <TabsTrigger value="guided">Guided</TabsTrigger>
          <TabsTrigger value="exercises">Exercises</TabsTrigger>
          <TabsTrigger value="culture">Culture</TabsTrigger>
          <TabsTrigger value="drills">Drills</TabsTrigger>
        </TabsList>

        <TabsContent value="objective" className="mt-6">
          <ObjectiveCard data={cards.objective} />
        </TabsContent>

        <TabsContent value="words" className="mt-6">
          <WordsCard data={cards.words} />
        </TabsContent>

        <TabsContent value="grammar" className="mt-6">
          <GrammarPatternsCard data={cards.grammar_patterns} />
        </TabsContent>

        <TabsContent value="dialogue" className="mt-6">
          <LessonDialogueCard data={cards.lesson_dialogue} canDoId={meta.can_do.uid} />
        </TabsContent>

        <TabsContent value="reading" className="mt-6">
          <ReadingCard 
            title={cards.reading_comprehension?.title}
            reading={cards.reading_comprehension?.reading}
          />
        </TabsContent>

        <TabsContent value="guided" className="mt-6">
          <GuidedDialogueCard data={cards.guided_dialogue} sessionId={sessionId} />
        </TabsContent>

        <TabsContent value="exercises" className="mt-6">
          <ExercisesCard data={cards.exercises} />
        </TabsContent>

        <TabsContent value="culture" className="mt-6">
          <CultureCard data={cards.cultural_explanation} />
        </TabsContent>

        <TabsContent value="drills" className="mt-6">
          <DrillsCard data={cards.drills_ai} />
        </TabsContent>
      </Tabs>
    </div>
  )
}

