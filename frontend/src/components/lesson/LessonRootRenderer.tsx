"use client"

import React from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { 
  Accordion, 
  AccordionContent, 
  AccordionItem, 
  AccordionTrigger 
} from "@/components/ui/accordion"
import { ObjectiveCard } from "./cards/ObjectiveCard"
import { WordsCard } from "./cards/WordsCard"
import { GrammarPatternsCard } from "./cards/GrammarPatternsCard"
import { FormulaicExpressionsCard } from "./cards/FormulaicExpressionsCard"
import { LessonDialogueCard } from "./cards/LessonDialogueCard"
import { CultureCard } from "./cards/CultureCard"
import { ReadingCard } from "./ReadingCard"
import { ComprehensionExercisesCard } from "./cards/ComprehensionExercisesCard"
import { AIComprehensionTutorCard } from "./cards/AIComprehensionTutorCard"
import { GuidedDialogueCard } from "./cards/GuidedDialogueCard"
import { ProductionExercisesCard } from "./cards/ProductionExercisesCard"
import { AIProductionEvaluatorCard } from "./cards/AIProductionEvaluatorCard"
import { InteractiveDialogueCard } from "./cards/InteractiveDialogueCard"
import { InteractionActivitiesCard } from "./cards/InteractionActivitiesCard"
import { AIScenarioManagerCard } from "./cards/AIScenarioManagerCard"
import { ExercisesCard } from "./cards/ExercisesCard"
import { DrillsCard } from "./cards/DrillsCard"
import type { LessonRoot } from "@/types/lesson-root"
import { 
  Eye, 
  PenTool, 
  MessageSquare, 
  CheckCircle2, 
  Loader2,
  AlertCircle,
  RefreshCw
} from "lucide-react"

// Stage status for the 4-stage learning progression
interface StageStatus {
  content: string;
  comprehension: string;
  production: string;
  interaction: string;
}

export interface LessonRootRendererProps {
  lessonData: LessonRoot
  sessionId: string
  canDoId?: string  // Optional, will extract from lessonData if not provided
  onRegenerate?: () => void
  onDisplaySettings?: () => void
  onGenerateImages?: () => void
  isRegenerating?: boolean
  isGeneratingImages?: boolean
  // 4-stage learning progression props
  stageStatus?: StageStatus
  onRetryStage?: (stage: "comprehension" | "production" | "interaction") => Promise<void>
  activeStage?: "content" | "comprehension" | "production" | "interaction"
}


export function LessonRootRenderer({ 
  lessonData, 
  sessionId, 
  canDoId: canDoIdProp,
  onRegenerate, 
  onDisplaySettings,
  onGenerateImages,
  isRegenerating = false,
  isGeneratingImages = false,
  stageStatus = { content: "ready", comprehension: "pending", production: "pending", interaction: "pending" },
  onRetryStage,
  activeStage = "content",
}: LessonRootRendererProps) {
  const { lesson } = lessonData
  const { meta, cards } = lesson
  
  // Get canDoId from prop or extract from lesson data
  const canDoId = canDoIdProp || meta.can_do.uid || ""

  // Determine which sections have content
  const hasContentCards = cards.objective || cards.words || cards.grammar_patterns || 
    cards.formulaic_expressions || cards.lesson_dialogue || cards.cultural_explanation
  const hasComprehensionCards = cards.reading_comprehension || cards.comprehension_exercises || 
    cards.ai_comprehension_tutor
  const hasProductionCards = cards.guided_dialogue || cards.production_exercises || 
    cards.ai_production_evaluator || cards.exercises || cards.drills_ai
  const hasInteractionCards = cards.interactive_dialogue || cards.interaction_activities || 
    cards.ai_scenario_manager

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

      {/* Render content based on activeStage prop from parent */}
      {activeStage === "content" && (
        <div className="mt-6 space-y-4">
          {stageStatus.content === "pending" ? (
            <Card>
              <CardContent className="py-12 text-center">
                <Loader2 className="h-8 w-8 animate-spin mx-auto mb-4 text-primary" />
                <p className="text-muted-foreground">Content is being generated...</p>
              </CardContent>
            </Card>
          ) : hasContentCards ? (
            <Accordion type="multiple" defaultValue={["objective", "vocabulary", "grammar", "dialogue"]} className="space-y-4">
              {/* Objective */}
              {cards.objective && (
                <AccordionItem value="objective" className="border rounded-lg">
                  <AccordionTrigger className="px-4 hover:no-underline">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold">🎯 Learning Objective</span>
                      <CheckCircle2 className="h-4 w-4 text-green-500" />
                    </div>
                  </AccordionTrigger>
                  <AccordionContent className="px-4 pb-4">
                    <ObjectiveCard data={cards.objective} />
                  </AccordionContent>
                </AccordionItem>
              )}

              {/* Vocabulary */}
              {cards.words && (
                <AccordionItem value="vocabulary" className="border rounded-lg">
                  <AccordionTrigger className="px-4 hover:no-underline">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold">📚 Vocabulary</span>
                      <Badge variant="outline" className="text-xs">
                        {cards.words.items?.length || 0} words
                      </Badge>
                    </div>
                  </AccordionTrigger>
                  <AccordionContent className="px-4 pb-4">
                    <WordsCard data={cards.words} />
                  </AccordionContent>
                </AccordionItem>
              )}

              {/* Grammar */}
              {cards.grammar_patterns && (
                <AccordionItem value="grammar" className="border rounded-lg">
                  <AccordionTrigger className="px-4 hover:no-underline">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold">📝 Grammar Patterns</span>
                      <Badge variant="outline" className="text-xs">
                        {cards.grammar_patterns.patterns?.length || 0} patterns
                      </Badge>
                    </div>
                  </AccordionTrigger>
                  <AccordionContent className="px-4 pb-4">
                    <GrammarPatternsCard data={cards.grammar_patterns} />
                  </AccordionContent>
                </AccordionItem>
              )}

              {/* Formulaic Expressions */}
              {cards.formulaic_expressions && (
                <AccordionItem value="formulaic" className="border rounded-lg">
                  <AccordionTrigger className="px-4 hover:no-underline">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold">💬 Formulaic Expressions</span>
                      <Badge variant="outline" className="text-xs">
                        {cards.formulaic_expressions.items?.length || 0} expressions
                      </Badge>
                    </div>
                  </AccordionTrigger>
                  <AccordionContent className="px-4 pb-4">
                    <FormulaicExpressionsCard data={cards.formulaic_expressions} />
                  </AccordionContent>
                </AccordionItem>
              )}

              {/* Dialogue */}
              {cards.lesson_dialogue && (
                <AccordionItem value="dialogue" className="border rounded-lg">
                  <AccordionTrigger className="px-4 hover:no-underline">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold">🗣️ Lesson Dialogue</span>
                    </div>
                  </AccordionTrigger>
                  <AccordionContent className="px-4 pb-4">
                    <LessonDialogueCard data={cards.lesson_dialogue} canDoId={meta.can_do.uid} />
                  </AccordionContent>
                </AccordionItem>
              )}

              {/* Culture */}
              {cards.cultural_explanation && (
                <AccordionItem value="culture" className="border rounded-lg">
                  <AccordionTrigger className="px-4 hover:no-underline">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold">🌸 Cultural Context</span>
                    </div>
                  </AccordionTrigger>
                  <AccordionContent className="px-4 pb-4">
                    <CultureCard data={cards.cultural_explanation} />
                  </AccordionContent>
                </AccordionItem>
              )}
            </Accordion>
          ) : (
            <Card>
              <CardContent className="py-12 text-center text-muted-foreground">
                No content available for this stage.
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {activeStage === "comprehension" && (
        <div className="mt-6 space-y-4">
          {stageStatus.comprehension === "pending" || stageStatus.comprehension === "generating" ? (
            <Card>
              <CardContent className="py-12 text-center">
                <Loader2 className="h-8 w-8 animate-spin mx-auto mb-4 text-primary" />
                <p className="text-muted-foreground">Comprehension content is being generated...</p>
                <p className="text-xs text-muted-foreground mt-2">This may take a moment.</p>
              </CardContent>
            </Card>
          ) : stageStatus.comprehension === "failed" || stageStatus.comprehension === "error" ? (
            <Card>
              <CardContent className="py-12 text-center">
                <AlertCircle className="h-8 w-8 mx-auto mb-4 text-destructive" />
                <p className="text-muted-foreground mb-4">Failed to generate comprehension content.</p>
                {onRetryStage && (
                  <Button onClick={() => onRetryStage("comprehension")} variant="outline">
                    <RefreshCw className="h-4 w-4 mr-2" />
                    Retry Generation
                  </Button>
                )}
              </CardContent>
            </Card>
          ) : hasComprehensionCards ? (
            <Accordion type="multiple" defaultValue={["reading", "comprehension-exercises"]} className="space-y-4">
              {/* Reading Comprehension */}
              {cards.reading_comprehension && (
                <AccordionItem value="reading" className="border rounded-lg">
                  <AccordionTrigger className="px-4 hover:no-underline">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold">📖 Reading Comprehension</span>
                    </div>
                  </AccordionTrigger>
                  <AccordionContent className="px-4 pb-4">
                    <ReadingCard 
                      title={cards.reading_comprehension.title}
                      reading={cards.reading_comprehension.reading}
                    />
                  </AccordionContent>
                </AccordionItem>
              )}

              {/* Comprehension Exercises */}
              {cards.comprehension_exercises && (
                <AccordionItem value="comprehension-exercises" className="border rounded-lg">
                  <AccordionTrigger className="px-4 hover:no-underline">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold">✏️ Comprehension Exercises</span>
                    </div>
                  </AccordionTrigger>
                  <AccordionContent className="px-4 pb-4">
                    <ComprehensionExercisesCard data={cards.comprehension_exercises} />
                  </AccordionContent>
                </AccordionItem>
              )}

              {/* AI Comprehension Tutor */}
              {cards.ai_comprehension_tutor && (
                <AccordionItem value="ai-tutor" className="border rounded-lg">
                  <AccordionTrigger className="px-4 hover:no-underline">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold">🤖 AI Comprehension Tutor</span>
                      <Badge variant="secondary" className="text-xs">Interactive</Badge>
                    </div>
                  </AccordionTrigger>
                  <AccordionContent className="px-4 pb-4">
                    <AIComprehensionTutorCard data={cards.ai_comprehension_tutor} sessionId={sessionId} canDoId={canDoId} />
                  </AccordionContent>
                </AccordionItem>
              )}
            </Accordion>
          ) : (
            <Card>
              <CardContent className="py-12 text-center text-muted-foreground">
                <Eye className="h-12 w-12 mx-auto mb-4 opacity-20" />
                <p>Complete the Content stage first to unlock Comprehension exercises.</p>
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {activeStage === "production" && (
        <div className="mt-6 space-y-4">
          {stageStatus.production === "pending" || stageStatus.production === "generating" ? (
            <Card>
              <CardContent className="py-12 text-center">
                <Loader2 className="h-8 w-8 animate-spin mx-auto mb-4 text-primary" />
                <p className="text-muted-foreground">Production content is being generated...</p>
                <p className="text-xs text-muted-foreground mt-2">This may take a moment.</p>
              </CardContent>
            </Card>
          ) : stageStatus.production === "failed" || stageStatus.production === "error" ? (
            <Card>
              <CardContent className="py-12 text-center">
                <AlertCircle className="h-8 w-8 mx-auto mb-4 text-destructive" />
                <p className="text-muted-foreground mb-4">Failed to generate production content.</p>
                {onRetryStage && (
                  <Button onClick={() => onRetryStage("production")} variant="outline">
                    <RefreshCw className="h-4 w-4 mr-2" />
                    Retry Generation
                  </Button>
                )}
              </CardContent>
            </Card>
          ) : hasProductionCards ? (
            <Accordion type="multiple" defaultValue={["guided-dialogue", "production-exercises"]} className="space-y-4">
              {/* Guided Dialogue */}
              {cards.guided_dialogue && (
                <AccordionItem value="guided-dialogue" className="border rounded-lg">
                  <AccordionTrigger className="px-4 hover:no-underline">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold">🎯 Guided Dialogue Practice</span>
                      <Badge variant="secondary" className="text-xs">AI-Powered</Badge>
                    </div>
                  </AccordionTrigger>
                  <AccordionContent className="px-4 pb-4">
                    <GuidedDialogueCard data={cards.guided_dialogue} sessionId={sessionId} />
                  </AccordionContent>
                </AccordionItem>
              )}

              {/* Production Exercises */}
              {cards.production_exercises && (
                <AccordionItem value="production-exercises" className="border rounded-lg">
                  <AccordionTrigger className="px-4 hover:no-underline">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold">✍️ Production Exercises</span>
                    </div>
                  </AccordionTrigger>
                  <AccordionContent className="px-4 pb-4">
                    <ProductionExercisesCard data={cards.production_exercises} />
                  </AccordionContent>
                </AccordionItem>
              )}

              {/* Legacy Exercises (fallback) */}
              {cards.exercises && !cards.production_exercises && (
                <AccordionItem value="exercises" className="border rounded-lg">
                  <AccordionTrigger className="px-4 hover:no-underline">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold">✏️ Exercises</span>
                    </div>
                  </AccordionTrigger>
                  <AccordionContent className="px-4 pb-4">
                    <ExercisesCard data={cards.exercises} />
                  </AccordionContent>
                </AccordionItem>
              )}

              {/* Legacy Drills (fallback) */}
              {cards.drills_ai && (
                <AccordionItem value="drills" className="border rounded-lg">
                  <AccordionTrigger className="px-4 hover:no-underline">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold">🔄 Drills</span>
                    </div>
                  </AccordionTrigger>
                  <AccordionContent className="px-4 pb-4">
                    <DrillsCard data={cards.drills_ai} />
                  </AccordionContent>
                </AccordionItem>
              )}

              {/* AI Production Evaluator */}
              {cards.ai_production_evaluator && (
                <AccordionItem value="ai-evaluator" className="border rounded-lg">
                  <AccordionTrigger className="px-4 hover:no-underline">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold">🤖 AI Production Evaluator</span>
                      <Badge variant="secondary" className="text-xs">Interactive</Badge>
                    </div>
                  </AccordionTrigger>
                  <AccordionContent className="px-4 pb-4">
                    <AIProductionEvaluatorCard data={cards.ai_production_evaluator} sessionId={sessionId} canDoId={canDoId} />
                  </AccordionContent>
                </AccordionItem>
              )}
            </Accordion>
          ) : (
            <Card>
              <CardContent className="py-12 text-center text-muted-foreground">
                <PenTool className="h-12 w-12 mx-auto mb-4 opacity-20" />
                <p>Complete the Comprehension stage first to unlock Production exercises.</p>
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {activeStage === "interaction" && (
        <div className="mt-6 space-y-4">
          {stageStatus.interaction === "pending" || stageStatus.interaction === "generating" ? (
            <Card>
              <CardContent className="py-12 text-center">
                <Loader2 className="h-8 w-8 animate-spin mx-auto mb-4 text-primary" />
                <p className="text-muted-foreground">Interaction content is being generated...</p>
                <p className="text-xs text-muted-foreground mt-2">This may take a moment.</p>
              </CardContent>
            </Card>
          ) : stageStatus.interaction === "failed" || stageStatus.interaction === "error" ? (
            <Card>
              <CardContent className="py-12 text-center">
                <AlertCircle className="h-8 w-8 mx-auto mb-4 text-destructive" />
                <p className="text-muted-foreground mb-4">Failed to generate interaction content.</p>
                {onRetryStage && (
                  <Button onClick={() => onRetryStage("interaction")} variant="outline">
                    <RefreshCw className="h-4 w-4 mr-2" />
                    Retry Generation
                  </Button>
                )}
              </CardContent>
            </Card>
          ) : hasInteractionCards ? (
            <Accordion type="multiple" defaultValue={["interactive-dialogue", "activities"]} className="space-y-4">
              {/* Interactive Dialogue */}
              {cards.interactive_dialogue && (
                <AccordionItem value="interactive-dialogue" className="border rounded-lg">
                  <AccordionTrigger className="px-4 hover:no-underline">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold">💬 Interactive Dialogue</span>
                      <Badge variant="secondary" className="text-xs">AI Conversation</Badge>
                    </div>
                  </AccordionTrigger>
                  <AccordionContent className="px-4 pb-4">
                    <InteractiveDialogueCard data={cards.interactive_dialogue} sessionId={sessionId} canDoId={canDoId} />
                  </AccordionContent>
                </AccordionItem>
              )}

              {/* Interaction Activities */}
              {cards.interaction_activities && (
                <AccordionItem value="activities" className="border rounded-lg">
                  <AccordionTrigger className="px-4 hover:no-underline">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold">🎭 Interaction Activities</span>
                    </div>
                  </AccordionTrigger>
                  <AccordionContent className="px-4 pb-4">
                    <InteractionActivitiesCard data={cards.interaction_activities} sessionId={sessionId} canDoId={canDoId} />
                  </AccordionContent>
                </AccordionItem>
              )}

              {/* AI Scenario Manager */}
              {cards.ai_scenario_manager && (
                <AccordionItem value="ai-scenario" className="border rounded-lg">
                  <AccordionTrigger className="px-4 hover:no-underline">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold">🤖 AI Scenario Manager</span>
                      <Badge variant="secondary" className="text-xs">Role-Play</Badge>
                    </div>
                  </AccordionTrigger>
                  <AccordionContent className="px-4 pb-4">
                    <AIScenarioManagerCard data={cards.ai_scenario_manager} sessionId={sessionId} canDoId={canDoId} />
                  </AccordionContent>
                </AccordionItem>
              )}
            </Accordion>
          ) : (
            <Card>
              <CardContent className="py-12 text-center text-muted-foreground">
                <MessageSquare className="h-12 w-12 mx-auto mb-4 opacity-20" />
                <p>Complete the Production stage first to unlock Interaction activities.</p>
              </CardContent>
            </Card>
          )}
        </div>
      )}
    </div>
  )
}
