"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { apiGet, apiPost } from "@/lib/api"
import { getToken } from "@/lib/auth"
import { useToast } from "@/components/ToastProvider"
import ProfileBuildingChat from "@/components/profile/ProfileBuildingChat"

export default function ProfileBuildPage() {
  const router = useRouter()
  const { showToast } = useToast()
  const [loading, setLoading] = useState(true)
  const [conversationId, setConversationId] = useState<string | null>(null)

  useEffect(() => {
    const token = getToken()
    if (!token) {
      router.replace("/login")
      return
    }

    // Allow access even if profile is completed (for updates)
    apiGet<{ profile_completed: boolean; profile_skipped: boolean }>("/api/v1/profile/status")
      .then(() => {
        setLoading(false)
      })
      .catch(() => {
        setLoading(false)
      })
  }, [router])

  const handleProfileComplete = async (conversationId: string) => {
    // NOTE: The actual save happens inside the profile building flow (review/approve).
    // Keeping this callback side-effect free avoids duplicate /profile/complete calls.
    router.push("/")
  }

  const handleProfileSkip = async () => {
    try {
      await apiPost("/api/v1/profile/skip", {})
      showToast("You can complete your profile later from Settings", "info")
      router.push("/")
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } } }
      showToast(
        error?.response?.data?.detail || "Failed to skip profile",
        "error"
      )
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-gray-900 mx-auto"></div>
          <p className="mt-4 text-muted-foreground">Loading...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-white to-slate-50 p-4 sm:p-6">
      <div className="max-w-4xl mx-auto">
        <div className="mb-6">
          <div className="flex items-center justify-between mb-2">
            <div>
              <h1 className="text-2xl sm:text-3xl font-semibold">Build Your Learning Profile</h1>
              <p className="text-muted-foreground mt-2">
                Let's get to know you better so we can create a personalized learning experience.
              </p>
            </div>
            <Link href="/" className="text-sm text-blue-600 hover:text-blue-800">
              ← Back to Home
            </Link>
          </div>
          <div className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded-lg">
            <p className="text-sm text-blue-900">
              <strong>What happens after you complete your profile:</strong> Your personalized learning path will appear on your Home page, 
              along with customized recommendations and progress tracking based on your goals and preferences.
            </p>
          </div>
        </div>

        <ProfileBuildingChat
          onComplete={handleProfileComplete}
          onSkip={handleProfileSkip}
          onConversationCreated={setConversationId}
        />
      </div>
    </div>
  )
}

