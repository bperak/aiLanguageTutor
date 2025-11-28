"use client"

import { useEffect, useState } from "react"
import { useParams, useSearchParams } from "next/navigation"
import { apiGet, apiPost, compileLessonV2 } from "@/lib/api"
import { DisplaySettingsPanel } from "@/components/settings/DisplaySettingsPanel"
import { LessonRootRenderer } from "@/components/lesson/LessonRootRenderer"
import { Button } from "@/components/ui/button"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { useDisplaySettings } from "@/contexts/DisplaySettingsContext"
import { useToast } from "@/components/ToastProvider"
import type { LessonRoot } from "@/types/lesson-root"

export default function CanDoDetailPage() {
  const params = useParams<{ canDoId: string }>()
  const searchParams = useSearchParams()
  const canDoId = decodeURIComponent(params.canDoId)
  const { applyLevelPreset } = useDisplaySettings()
  const { showToast } = useToast()
  
  const [lessonRootData, setLessonRootData] = useState<LessonRoot | null>(null)
  const [isCompilingV2, setIsCompilingV2] = useState(false)
  const [isGeneratingImages, setIsGeneratingImages] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [lessonSessionId, setLessonSessionId] = useState<string>("")
  const [showSettings, setShowSettings] = useState(false)
  
  // Apply level from URL query parameter
  useEffect(() => {
    const levelParam = searchParams.get('level')
    if (levelParam) {
      const level = parseInt(levelParam, 10)
      if (level >= 1 && level <= 6) {
        applyLevelPreset(level)
      }
    }
  }, [searchParams, applyLevelPreset])

  // Helper function to parse and set lesson data
  const parseAndSetLessonData = (lessonDetail: any): LessonRoot | null => {
    let lessonData: LessonRoot | null = null
    
    // Case 1: Already in LessonRoot format {lesson: {...}}
    if (lessonDetail && typeof lessonDetail === "object" && lessonDetail.lesson) {
      console.log("✅ Found lesson in LessonRoot format")
      lessonData = lessonDetail as LessonRoot
    }
    // Case 2: Unwrapped structure (direct lesson with meta and cards)
    else if (lessonDetail && typeof lessonDetail === "object" && lessonDetail.meta && lessonDetail.cards) {
      console.log("📦 Wrapping unwrapped lesson data")
      lessonData = { lesson: lessonDetail }
    }
    // Case 3: Check if it's nested in lesson_plan property
    else if (lessonDetail?.lesson_plan) {
      const plan = lessonDetail.lesson_plan
      if (plan?.lesson) {
        lessonData = plan as LessonRoot
      } else if (plan?.meta && plan?.cards) {
        lessonData = { lesson: plan }
      }
    }
    
    return lessonData
  }

  // Load LessonRoot V2 (tries to fetch existing, falls back to compilation)
  const loadLessonV2 = async () => {
    setError(null)
    setIsCompilingV2(true)
    
    // Create or get existing lesson session (lightweight - doesn't generate lesson)
    // Note: This must happen before we try to use the session for guided dialogue
    let sessionId = ""
    try {
      console.log("🔄 Creating/retrieving lesson session for:", canDoId)
      // Use lightweight session creation endpoint that doesn't generate full lesson
      const sessionResponse = await apiPost<{ session_id: string }>("/api/v1/cando/lessons/session/create", {
        can_do_id: canDoId
      })
      if (sessionResponse && sessionResponse.session_id) {
        sessionId = sessionResponse.session_id
        setLessonSessionId(sessionId)
        console.log("✅ Session created/retrieved:", sessionId)
      } else {
        console.error("❌ Invalid session response:", sessionResponse)
        throw new Error("No session_id in response")
      }
    } catch (sessionError: any) {
      console.error("⚠️ Failed to create session:", sessionError)
      // Don't use fallback UUID - session must exist in database
      setError(`Failed to create lesson session: ${sessionError.message || "Unknown error"}`)
      setIsCompilingV2(false)
      return
    }
    
    if (!sessionId) {
      setError("Failed to create lesson session")
      setIsCompilingV2(false)
      return
    }

    try {
      console.log("🔍 Fetching lesson list for:", canDoId)
      // Try to fetch existing lesson first
      const response = await apiGet<any>(`/api/v1/cando/lessons/list?can_do_id=${encodeURIComponent(canDoId)}`)
      console.log("📋 Lesson list response:", response)
      
      if (response?.lessons && response.lessons.length > 0) {
        // Get the latest version
        const latestLesson = response.lessons[0]
        console.log("📚 Fetching lesson ID:", latestLesson.id)
        const lessonDetail = await apiGet<any>(`/api/v1/cando/lessons/fetch/${latestLesson.id}`)
        console.log("✅ Lesson fetched successfully!", lessonDetail)
        
        const lessonData = parseAndSetLessonData(lessonDetail)
        
        if (!lessonData || !lessonData.lesson) {
          console.error("❌ No lesson data in response. Structure:", JSON.stringify(lessonDetail, null, 2))
          setError("No lesson data found - the lesson may be empty or corrupted")
          setIsCompilingV2(false)
          return
        }
        
        console.log("✅ Lesson data ready with structure:", {
          hasLesson: !!lessonData.lesson,
          hasMeta: !!lessonData.lesson.meta,
          hasCards: !!lessonData.lesson.cards,
        })
        setLessonRootData(lessonData)
        setIsCompilingV2(false)
        return
      }
      
      console.log("⚠️ No lessons found in database")
    } catch (e: any) {
      console.error("❌ Fetch failed:", e)
      const errorMessage = e?.response?.data?.detail || e?.message || "Failed to load lesson"
      console.error("Error details:", errorMessage)
      // If it's a 404 or empty lesson error, show a specific message
      if (e?.response?.status === 404 || errorMessage.includes("empty")) {
        setError(`Lesson not found or empty: ${errorMessage}. Falling back to compilation...`)
        // Don't clear loading state - let it continue to compilation
      } else {
        console.log("🔄 Falling back to compilation...")
        // Don't clear loading state - let it continue to compilation
      }
    }

    // Compile new lesson
    try {
      console.log("🏗️ Starting compilation for:", canDoId)
      const result = await compileLessonV2(canDoId, "en", "gpt-4o")
      console.log("✅ Compilation result:", result)
      
      // Fetch the compiled lesson from lessons table
      const response = await apiGet<any>(`/api/v1/cando/lessons/list?can_do_id=${encodeURIComponent(canDoId)}`)
      if (response?.lessons && response.lessons.length > 0) {
        const latestLesson = response.lessons[0]
        const lessonDetail = await apiGet<any>(`/api/v1/cando/lessons/fetch/${latestLesson.id}`)
        console.log("✅ Compiled lesson fetched!", lessonDetail)
        
        const lessonData = parseAndSetLessonData(lessonDetail)
        
        if (!lessonData || !lessonData.lesson) {
          console.error("❌ No lesson data after compilation. Structure:", JSON.stringify(lessonDetail, null, 2))
          setError("No lesson data after compilation - the lesson may be empty or corrupted")
          return
        }
        
        console.log("✅ Compiled lesson data ready")
        setLessonRootData(lessonData)
      }
    } catch (e: any) {
      console.error("💥 Compilation failed:", e)
      setError(e.message || "Failed to compile lesson")
    } finally {
      setIsCompilingV2(false)
    }
  }

  // Generate images for the lesson
  const generateImages = async () => {
    setError(null)
    setIsGeneratingImages(true)
    
    try {
      console.log("🖼️ Generating images for:", canDoId)
      const result = await apiPost<any>(
        `/api/v1/cando/lessons/generate-images?can_do_id=${encodeURIComponent(canDoId)}`
      )
      console.log("✅ Image generation result:", result)
      console.log("📊 Generation stats:", {
        images_generated: result.images_generated,
        images_skipped: result.images_skipped,
        message: result.message,
        fullResult: result
      })
      
      if (result.images_generated > 0) {
        console.log(`✅ Generated ${result.images_generated} image(s), reloading lesson...`)
        showToast(`✅ Successfully generated ${result.images_generated} image(s)! Reloading...`)
        // Wait a moment for files to be written
        await new Promise(resolve => setTimeout(resolve, 1000))
        // Reload the lesson to get updated image paths
        await loadLessonV2()
      } else if (result.message) {
        // Show message even if no images were generated
        console.log("ℹ️", result.message)
        console.log("⚠️ Images may already exist or there were no images to generate")
        showToast(`ℹ️ ${result.message}`)
      } else {
        console.log("ℹ️ No images generated")
        console.log("⚠️ Check if GEMINI_API_KEY is set and images already exist")
        showToast("⚠️ No images were generated. Check if GEMINI_API_KEY is set or images already exist.")
      }
    } catch (e: any) {
      console.error("💥 Image generation failed:", e)
      const errorMessage = e?.response?.data?.detail || e?.message || "Failed to generate images"
      console.error("Error details:", errorMessage)
      const userMessage = errorMessage.includes("GEMINI_API_KEY") 
        ? "❌ Image generation requires GEMINI_API_KEY to be set in backend .env file"
        : `❌ Image generation failed: ${errorMessage}`
      showToast(userMessage)
      setError(userMessage)
    } finally {
      setIsGeneratingImages(false)
    }
  }

  // Regenerate lesson - force compilation (skip fetch, always create new version)
  const regenerateLesson = async () => {
    setError(null)
    setIsCompilingV2(true)
    setLessonSessionId(crypto.randomUUID())

    try {
      console.log("🔄 Force regenerating lesson for:", canDoId)
      const result = await compileLessonV2(canDoId, "en", "gpt-4o")
      console.log("✅ Regeneration result:", result)
      
      // Fetch the regenerated lesson from lessons table
      const response = await apiGet<any>(`/api/v1/cando/lessons/list?can_do_id=${encodeURIComponent(canDoId)}`)
      if (response?.lessons && response.lessons.length > 0) {
        const latestLesson = response.lessons[0]
        const lessonDetail = await apiGet<any>(`/api/v1/cando/lessons/fetch/${latestLesson.id}`)
        console.log("✅ Regenerated lesson fetched!", lessonDetail)
        
        const lessonData = parseAndSetLessonData(lessonDetail)
        
        if (!lessonData || !lessonData.lesson) {
          console.error("❌ No lesson data after regeneration. Structure:", JSON.stringify(lessonDetail, null, 2))
          setError("No lesson data after regeneration - the lesson may be empty or corrupted")
          return
        }
        
        console.log("✅ Regenerated lesson data ready")
        setLessonRootData(lessonData)
      }
    } catch (e: any) {
      console.error("💥 Regeneration failed:", e)
      setError(e.message || "Failed to regenerate lesson")
    } finally {
      setIsCompilingV2(false)
    }
  }

  useEffect(() => {
    loadLessonV2()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [canDoId])

  if (isCompilingV2) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-6">
        <Card className="p-8 text-center">
          <CardHeader>
            <CardTitle className="text-xl mb-2">🚀 Generating Your Lesson</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
            <p className="text-gray-600">
              This may take 1-3 minutes as we create personalized content with all 8 card types...
            </p>
          </CardContent>
        </Card>
      </div>
    )
  }

  if (error) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-6">
        <Card className="p-8 text-center border-red-200 bg-red-50">
          <CardHeader>
            <CardTitle className="text-xl mb-2 text-red-800">❌ Error Loading Lesson</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-red-600 mb-4">{error}</p>
            <Button onClick={loadLessonV2} variant="outline">
              🔄 Retry
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  if (!lessonRootData) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-6">
        <Card className="p-8 text-center">
          <CardHeader>
            <CardTitle className="text-xl mb-2">Loading Lesson...</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="max-w-7xl mx-auto px-4 py-6">
      <LessonRootRenderer 
        lessonData={lessonRootData} 
        sessionId={lessonSessionId}
        onRegenerate={regenerateLesson}
        onDisplaySettings={() => setShowSettings(true)}
        onGenerateImages={generateImages}
        isRegenerating={isCompilingV2}
        isGeneratingImages={isGeneratingImages}
      />
      
      {/* Display Settings Modal */}
      {showSettings && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white dark:bg-gray-800 rounded-lg max-w-2xl w-full mx-4">
            <DisplaySettingsPanel />
            <div className="p-4 border-t">
              <Button onClick={() => setShowSettings(false)} className="w-full">
                Close
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
