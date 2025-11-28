"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { apiGet } from "@/lib/api"
import { getToken } from "@/lib/auth"
import HomeChatInterface from "@/components/home/HomeChatInterface"

export default function Home() {
  const router = useRouter()
  const [loading, setLoading] = useState(true)
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [profileStatus, setProfileStatus] = useState<{ profile_completed: boolean; profile_skipped: boolean } | null>(null)

  useEffect(() => {
    const token = getToken()
    if (!token) {
      // Not authenticated - show landing page
      setIsAuthenticated(false)
      setLoading(false)
      return
    }

    // Check profile status
    apiGet<{ profile_completed: boolean; profile_skipped: boolean }>("/api/v1/profile/status")
      .then((status) => {
        setProfileStatus(status)
        setIsAuthenticated(true)
        
        // If profile not completed and not skipped, redirect to profile build
        if (!status.profile_completed && !status.profile_skipped) {
          router.push("/profile/build")
          return
        }
        
        setLoading(false)
      })
      .catch(() => {
        setIsAuthenticated(false)
        setLoading(false)
      })
  }, [router])

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

  // Landing page for unauthenticated users
  if (!isAuthenticated) {
    return (
      <div className="min-h-[calc(100vh-56px)] grid place-items-center p-8">
        <div className="text-center max-w-xl">
          <h1 className="text-4xl font-semibold tracking-tight">Learn languages with your AI tutor</h1>
          <p className="text-muted-foreground mt-3">Personalized, simple, and effective. Start with Japanese today.</p>
          <div className="mt-6 flex items-center justify-center gap-4">
            <a className="px-5 py-2 rounded-md bg-black text-white hover:opacity-90" href="/register">Get started</a>
            <a className="px-5 py-2 rounded-md border hover:bg-slate-50" href="/login">I already have an account</a>
          </div>
        </div>
      </div>
    )
  }

  // Main chat interface for authenticated users
  return (
    <div className="min-h-screen bg-gradient-to-b from-white to-slate-50">
      <HomeChatInterface profileStatus={profileStatus} />
    </div>
  )
}
