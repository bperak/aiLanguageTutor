"use client"

import { useState, useEffect } from "react"
import { apiGet, apiPost, apiPut, apiDelete } from "@/lib/api"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Modal } from "@/components/ui/Modal"
import { Plus, MessageSquare, Edit2, Trash2, X, Check } from "lucide-react"
import { formatSessionName, cleanSessionTitle } from "@/lib/utils"
import { useToast } from "@/components/ToastProvider"

interface SessionsCardProps {
  currentSessionId: string | null
  onSessionChange: (sessionId: string) => void
}

export default function SessionsCard({
  currentSessionId,
  onSessionChange,
}: SessionsCardProps) {
  const { showToast } = useToast()
  const [sessions, setSessions] = useState<Array<{ id: string; title: string; created_at?: string }>>([])
  const [loading, setLoading] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editName, setEditName] = useState("")
  const [deleteId, setDeleteId] = useState<string | null>(null)

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
      // Fetch greeting and progress before creating session
      const status = await apiGet<{
        greeting?: string
        recent_lessons?: any[]
        progress_summary?: any
        next_learning_step?: any
      }>("/api/v1/home/status")
      // Use date-based naming
      const sessionName = formatSessionName(new Date())
      const newSession = await apiPost<{ id: string }>("/api/v1/home/sessions", {
        session_name: sessionName,
        greeting: status.greeting,
        user_actions: {
          recent_lessons: status.recent_lessons || [],
          progress: status.progress_summary,
          next_step: status.next_learning_step
        }
      })
      await loadSessions()
      onSessionChange(newSession.id)
    } catch (err) {
      console.error("Failed to create session:", err)
      showToast("Failed to create session", "error")
    } finally {
      setLoading(false)
    }
  }

  const handleEdit = (session: { id: string; title: string; created_at?: string }) => {
    setEditingId(session.id)
    setEditName(cleanSessionTitle(session.title))
  }

  const handleSaveEdit = async (sessionId: string) => {
    if (!editName.trim()) {
      setEditingId(null)
      return
    }
    try {
      await apiPut(`/api/v1/conversations/sessions/${sessionId}`, { title: `Home: ${editName.trim()}` })
      await loadSessions()
      setEditingId(null)
      showToast("Session renamed", "success")
    } catch (err) {
      console.error("Failed to update session:", err)
      showToast("Failed to rename session", "error")
      setEditingId(null)
    }
  }

  const handleCancelEdit = () => {
    setEditingId(null)
    setEditName("")
  }

  const handleDelete = async () => {
    if (!deleteId) return
    try {
      await apiDelete(`/api/v1/conversations/sessions/${deleteId}`)
      await loadSessions()
      if (currentSessionId === deleteId) {
        // If we deleted the current session, switch to the first available or null
        const remaining = sessions.filter(s => s.id !== deleteId)
        if (remaining.length > 0) {
          onSessionChange(remaining[0].id)
        } else {
          onSessionChange("")
        }
      }
      setDeleteId(null)
      showToast("Session deleted", "success")
    } catch (err) {
      console.error("Failed to delete session:", err)
      showToast("Failed to delete session", "error")
      setDeleteId(null)
    }
  }

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base flex items-center gap-2">
          <MessageSquare className="w-4 h-4" />
          Sessions
        </CardTitle>
      </CardHeader>
      <CardContent className="p-0">
        {/* Scrollable sessions list */}
        <div className="max-h-64 overflow-y-auto px-4 pb-2">
          {sessions.length === 0 ? (
            <div className="text-sm text-muted-foreground py-4 text-center">
              No sessions yet
            </div>
          ) : (
            <div className="space-y-1">
              {sessions.map((s) => {
                // Use formatted date-based name if created_at is available, otherwise clean the title
                const displayName = s.created_at 
                  ? formatSessionName(s.created_at)
                  : cleanSessionTitle(s.title)
                
                const isEditing = editingId === s.id
                
                return (
                  <div
                    key={s.id}
                    className={`group flex items-center gap-1 px-3 py-2 rounded-md text-sm transition-colors ${
                      currentSessionId === s.id
                        ? "bg-blue-100 text-blue-900 font-medium"
                        : "hover:bg-slate-100 text-slate-700"
                    }`}
                  >
                    {isEditing ? (
                      <div className="flex items-center gap-1 flex-1">
                        <Input
                          value={editName}
                          onChange={(e) => setEditName(e.target.value)}
                          onKeyDown={(e) => {
                            if (e.key === "Enter") {
                              handleSaveEdit(s.id)
                            } else if (e.key === "Escape") {
                              handleCancelEdit()
                            }
                          }}
                          className="h-7 text-sm flex-1"
                          autoFocus
                        />
                        <Button
                          size="sm"
                          variant="ghost"
                          className="h-7 w-7 p-0"
                          onClick={() => handleSaveEdit(s.id)}
                        >
                          <Check className="w-3 h-3" />
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          className="h-7 w-7 p-0"
                          onClick={handleCancelEdit}
                        >
                          <X className="w-3 h-3" />
                        </Button>
                      </div>
                    ) : (
                      <>
                        <button
                          onClick={() => onSessionChange(s.id)}
                          className="flex-1 text-left"
                        >
                          {displayName}
                        </button>
                        <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                          <Button
                            size="sm"
                            variant="ghost"
                            className="h-6 w-6 p-0"
                            onClick={(e) => {
                              e.stopPropagation()
                              handleEdit(s)
                            }}
                          >
                            <Edit2 className="w-3 h-3" />
                          </Button>
                          <Button
                            size="sm"
                            variant="ghost"
                            className="h-6 w-6 p-0 text-red-600 hover:text-red-700"
                            onClick={(e) => {
                              e.stopPropagation()
                              setDeleteId(s.id)
                            }}
                          >
                            <Trash2 className="w-3 h-3" />
                          </Button>
                        </div>
                      </>
                    )}
                  </div>
                )
              })}
            </div>
          )}
        </div>
        {/* + New button at bottom */}
        <div className="px-4 pb-4 pt-2 border-t">
          <Button
            size="sm"
            variant="outline"
            onClick={createNewSession}
            disabled={loading}
            className="w-full"
          >
            <Plus className="w-4 h-4 mr-2" />
            New Session
          </Button>
        </div>
      </CardContent>
      <Modal
        open={!!deleteId}
        title="Delete session?"
        description="This will permanently delete the session and its messages."
        onClose={() => setDeleteId(null)}
      >
        <div className="flex justify-end gap-2">
          <Button variant="outline" onClick={() => setDeleteId(null)}>
            Cancel
          </Button>
          <Button variant="destructive" onClick={handleDelete}>
            Delete
          </Button>
        </div>
      </Modal>
    </Card>
  )
}

