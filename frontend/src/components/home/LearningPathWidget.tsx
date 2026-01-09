"use client"

import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { useRouter } from "next/navigation"
import { apiPost } from "@/lib/api"
import { useToast } from "@/components/ToastProvider"
import { BookOpen, ArrowRight, Loader2, RefreshCw } from "lucide-react"

interface LearningPathWidgetProps {
  learningPathInfo?: {
    path_id?: string
    path_name?: string
    total_steps?: number
    current_step?: string
    progress_percentage?: number
    has_path?: boolean
    generating?: boolean
    steps?: Array<{
      step_id: string
      title: string
      description?: string
      can_do_descriptors?: string[]
      vocabulary?: any[]
      grammar?: any[]
      formulaic_expressions?: any[]
    }>
  }
}

export default function LearningPathWidget({ learningPathInfo }: LearningPathWidgetProps) {
  const router = useRouter()
  const { showToast } = useToast()
  const [regenerating, setRegenerating] = useState(false)

  const handleRegenerate = async () => {
    setRegenerating(true)
    try {
      await apiPost("/api/v1/profile/learning-path/generate", {
        force_regenerate: true
      })
      showToast("Learning path regenerated! Refreshing...")
      // Reload page to show new path
      setTimeout(() => {
        window.location.reload()
      }, 1000)
    } catch (err: any) {
      showToast(err?.response?.data?.detail || "Failed to regenerate path")
      setRegenerating(false)
    }
  }

  // Show widget even if no path info yet (allows regeneration)
  if (!learningPathInfo || (!learningPathInfo.has_path && !learningPathInfo.generating)) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <BookOpen className="h-5 w-5" />
            Learning Path
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground mb-4">
            Your learning path will appear here after profile completion.
          </p>
          <Button 
            onClick={handleRegenerate} 
            className="w-full"
            variant="outline"
            disabled={regenerating}
          >
            {regenerating ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Generating...
              </>
            ) : (
              <>
                <RefreshCw className="h-4 w-4 mr-2" />
                Generate Learning Path
              </>
            )}
          </Button>
        </CardContent>
      </Card>
    )
  }

  if (learningPathInfo.generating) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <BookOpen className="h-5 w-5" />
            Learning Path
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            Your personalized learning path is being generated. Please check back in a moment.
          </div>
        </CardContent>
      </Card>
    )
  }

  if (!learningPathInfo.has_path) {
    return null
  }

  const handleViewPath = () => {
    // Navigate to a learning path view page or show modal
    // For now, we can navigate to profile or show the path in a modal
    router.push("/profile")
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <BookOpen className="h-5 w-5" />
          Your Learning Path
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div>
          <h3 className="font-semibold text-lg">{learningPathInfo.path_name || "Personalized Learning Path"}</h3>
          {learningPathInfo.total_steps && (
            <p className="text-sm text-muted-foreground mt-1">
              {learningPathInfo.total_steps} steps • {Math.round(learningPathInfo.progress_percentage || 0)}% complete
            </p>
          )}
        </div>

        {learningPathInfo.steps && learningPathInfo.steps.length > 0 && (
          <div className="space-y-2">
            <p className="text-sm font-medium">Next Steps:</p>
            <ul className="space-y-1 text-sm">
              {learningPathInfo.steps.slice(0, 3).map((step, idx) => (
                <li key={step.step_id || idx} className="flex items-start gap-2">
                  <span className="text-muted-foreground">•</span>
                  <span>{step.title}</span>
                  {step.can_do_descriptors && step.can_do_descriptors.length > 0 && (
                    <span className="text-xs text-muted-foreground ml-auto">
                      {step.vocabulary?.length || 0} words • {step.grammar?.length || 0} grammar
                    </span>
                  )}
                </li>
              ))}
            </ul>
          </div>
        )}

        <div className="space-y-2">
          <Button 
            onClick={handleViewPath} 
            className="w-full"
            variant="outline"
          >
            View your personalized learning path
            <ArrowRight className="h-4 w-4 ml-2" />
          </Button>
          <Button 
            onClick={handleRegenerate} 
            className="w-full"
            variant="ghost"
            size="sm"
            disabled={regenerating}
          >
            {regenerating ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Regenerating...
              </>
            ) : (
              <>
                <RefreshCw className="h-4 w-4 mr-2" />
                Regenerate Path
              </>
            )}
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}
