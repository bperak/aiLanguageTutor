"use client"

import { useState, useEffect } from "react"
import { apiGet, apiPost } from "@/lib/api"
import { Button } from "@/components/ui/button"
import { formatSessionName, cleanSessionTitle } from "@/lib/utils"

interface HomeSessionSelectorProps {
  currentSessionId: string | null
  onSessionChange: (sessionId: string) => void
}

export default function HomeSessionSelector({
  currentSessionId,
  onSessionChange,
}: HomeSessionSelectorProps) {
  const [sessions, setSessions] = useState<Array<{ id: string; title: string; created_at?: string }>>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    loadSessions()
  }, [])

  const loadSessions = async () => {
    try {
      const data = await apiGet<Array<{ id: string; title: string; created_at?: string }>>("/api/v1/home/sessions")
      setSessions(data)
    } catch (err) {
      console.error("Failed to load sessions:", err)
    }
  }

  const createNewSession = async () => {
    setLoading(true)
    try {
      // Use date-based naming
      const sessionName = formatSessionName(new Date())
      const newSession = await apiPost<{ id: string }>("/api/v1/home/sessions", {
        session_name: sessionName
      })
      await loadSessions()
      onSessionChange(newSession.id)
    } catch (err) {
      console.error("Failed to create session:", err)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex items-center gap-2">
      <select
        value={currentSessionId || ""}
        onChange={(e) => onSessionChange(e.target.value)}
        className="px-3 py-1 text-sm border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
      >
        {sessions.map((s) => {
          const displayName = s.created_at 
            ? formatSessionName(s.created_at)
            : cleanSessionTitle(s.title)
          return (
            <option key={s.id} value={s.id}>
              {displayName}
            </option>
          )
        })}
      </select>
      <Button
        size="sm"
        variant="outline"
        onClick={createNewSession}
        disabled={loading}
      >
        + New
      </Button>
    </div>
  )
}

