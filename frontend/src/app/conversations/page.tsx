"use client"

import { useEffect, useRef, useState } from "react"
import useSWR from "swr"
import { useRouter } from "next/navigation"
import { apiGet, apiPost, apiPut } from "@/lib/api"
import { getToken } from "@/lib/auth"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Toast } from "@/components/Toast"
import { useToast } from "@/components/ToastProvider"
import { Modal } from "@/components/ui/Modal"

type Session = { id: string; title?: string | null; created_at: string }
type Message = { id: string; role: "user" | "assistant" | "system"; content: string; order: number }
type SendResult = { user_message?: { id: string }; assistant_message?: { id: string } | null }
type SessionDetails = { id: string; title?: string | null; ai_provider?: string; ai_model?: string }

export default function ConversationsPage() {
  const { showToast } = useToast()
  const router = useRouter()
  useEffect(() => { if (!getToken()) router.replace("/login") }, [router])

  const { data: sessions, mutate } = useSWR<Session[]>(
    "/api/v1/conversations/sessions",
    (url: string) => apiGet<Session[]>(url)
  )
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null)
  const { data: messages, mutate: mutateMessages } = useSWR<Message[]>(
    currentSessionId ? `/api/v1/conversations/sessions/${currentSessionId}/messages` : null,
    (url: string) => apiGet<Message[]>(url)
  )
  const { data: sessionDetails, mutate: mutateSessionDetails } = useSWR<SessionDetails>(
    currentSessionId ? `/api/v1/conversations/sessions/${currentSessionId}` : null,
    (url: string) => apiGet<SessionDetails>(url)
  )
  const [input, setInput] = useState("")
  const [creating, setCreating] = useState(false)
  const [sending, setSending] = useState(false)
  const [provider, setProvider] = useState<string>(() => {
    if (typeof window === "undefined") return "openai"
    return localStorage.getItem("conv_provider") || "openai"
  })
  const [model, setModel] = useState<string>(() => {
    if (typeof window === "undefined") return "gpt-4o-mini"
    return localStorage.getItem("conv_model") || "gpt-4o-mini"
  })
  const messagesEndRef = useRef<HTMLDivElement | null>(null)
  const [editingTitle, setEditingTitle] = useState<string | null>(null)
  const [newTitle, setNewTitle] = useState("")
  const [toast, setToast] = useState<string | null>(null)
  const [streamingText, setStreamingText] = useState<string>("")
  const [sessionQuery, setSessionQuery] = useState("")
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null)
  type SearchItem = { message_id: string; session_id: string; session_title?: string | null; role: string; content: string; created_at: string }
  type SearchResult = { items: SearchItem[] }
  const searchKey = sessionQuery.trim() ? `/api/v1/conversations/search?q=${encodeURIComponent(sessionQuery.trim())}` : null
  const { data: globalSearch } = useSWR<SearchResult | undefined>(
    searchKey,
    (url: string) => apiGet<SearchResult>(url)
  )

  function safeFileName(base: string): string {
    return base.replace(/[^a-z0-9\-_]+/gi, "_").slice(0, 60)
  }

  function exportAsJSON() {
    try {
      if (!messages) return
      const data = JSON.stringify(messages, null, 2)
      const blob = new Blob([data], { type: "application/json" })
      const url = URL.createObjectURL(blob)
      const a = document.createElement("a")
      const title = sessionDetails?.title || "chat"
      a.href = url
      a.download = `${safeFileName(title)}_${new Date().toISOString()}.json`
      document.body.appendChild(a)
      a.click()
      URL.revokeObjectURL(url)
      a.remove()
    } catch {
      setToast("Failed to export JSON")
    }
  }

  function exportAsTXT() {
    try {
      if (!messages) return
      const lines = messages.map((m) => `${m.role.toUpperCase()}: ${m.content}`)
      const blob = new Blob([lines.join("\n\n")], { type: "text/plain;charset=utf-8" })
      const url = URL.createObjectURL(blob)
      const a = document.createElement("a")
      const title = sessionDetails?.title || "chat"
      a.href = url
      a.download = `${safeFileName(title)}_${new Date().toISOString()}.txt`
      document.body.appendChild(a)
      a.click()
      URL.revokeObjectURL(url)
      a.remove()
    } catch {
      setToast("Failed to export TXT")
    }
  }

  async function exportAllSessions() {
    try {
      const allSessions = await apiGet<Session[]>("/api/v1/conversations/sessions")
      const result: Array<{ session: Session; messages: Message[] }> = []
      for (const s of allSessions) {
        try {
          const msgs = await apiGet<Message[]>(`/api/v1/conversations/sessions/${s.id}/messages`)
          result.push({ session: s, messages: msgs })
        } catch {
          result.push({ session: s, messages: [] })
        }
      }
      const data = JSON.stringify({ exported_at: new Date().toISOString(), items: result }, null, 2)
      const blob = new Blob([data], { type: "application/json" })
      const url = URL.createObjectURL(blob)
      const a = document.createElement("a")
      a.href = url
      a.download = `all_sessions_${new Date().toISOString()}.json`
      document.body.appendChild(a)
      a.click()
      URL.revokeObjectURL(url)
      a.remove()
    } catch {
      setToast("Failed to export all sessions")
    }
  }

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  // Clear streaming placeholder once real messages arrive
  useEffect(() => {
    if (messages && streamingText) setStreamingText("")
  }, [messages, streamingText])

  async function createSession() {
    try {
      setCreating(true)
      const res = await apiPost<{ id: string }>("/api/v1/conversations/sessions", {
        language_code: "ja",
        ai_provider: provider,
        ai_model: model,
        title: "New chat",
      })
      await mutate()
      setCurrentSessionId(res.id)
    } finally {
      setCreating(false)
    }
  }

  async function sendMessage() {
    if (!currentSessionId || !input.trim()) return
    setSending(true)
    try {
      await apiPost<SendResult>(`/api/v1/conversations/sessions/${currentSessionId}/messages`, {
        role: "user",
        content: input.trim(),
        no_ai: true,
      })
      setInput("")
      await mutateMessages()
      // Stream assistant reply via fetch + ReadableStream to include Authorization header
      setStreamingText("")
      const token = getToken()
      const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000"
      const url = `${baseUrl}/api/v1/conversations/sessions/${currentSessionId}/stream`
      const resp = await fetch(url, {
        method: "GET",
        headers: token ? { Authorization: `Bearer ${token}` } : undefined,
      })
      if (!resp.ok || !resp.body) {
        showToast(`Streaming error: ${resp.status}`)
        throw new Error(`stream http ${resp.status}`)
      }
      const reader = resp.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ""
      if (!reader) {
        throw new Error("No stream reader")
      }
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        let idx
        while ((idx = buffer.indexOf("\n\n")) !== -1) {
          const raw = buffer.slice(0, idx)
          buffer = buffer.slice(idx + 2)
          const lines = raw.split("\n")
          for (const line of lines) {
            if (line.startsWith("data: ")) {
              const data = line.slice(6)
              if (data === "[DONE]") {
                setSending(false)
                setStreamingText("")
                await mutateMessages()
                return
              }
              setStreamingText((prev) => prev + data)
            }
          }
        }
      }
      setSending(false)
      await mutateMessages()
    } catch {
      showToast("Streaming failed")
      setSending(false)
    }
  }

  return (
    <div className="min-h-screen p-4 sm:p-6 max-w-5xl mx-auto grid gap-4 sm:gap-6 md:grid-cols-[280px_1fr]">
      <div aria-label="Conversation sidebar" className="order-2 md:order-1">
        <h2 className="font-semibold mb-2">Sessions</h2>
        <div className="grid gap-2 mb-3 p-3 border rounded">
          <div className="grid gap-1">
            <Label htmlFor="provider">Provider</Label>
            <select id="provider" className="border rounded h-9 px-2" value={provider} onChange={(e) => {
              const p = e.target.value
              setProvider(p)
              setModel(p === "openai" ? "gpt-4o-mini" : "gemini-2.5-flash")
              if (typeof window !== "undefined") {
                localStorage.setItem("conv_provider", p)
                localStorage.setItem("conv_model", p === "openai" ? "gpt-4o-mini" : "gemini-2.5-flash")
              }
            }}>
              <option value="openai">OpenAI</option>
              <option value="gemini">Gemini</option>
            </select>
          </div>
          <div className="grid gap-1">
            <Label htmlFor="model">Model</Label>
            <Input id="model" value={model} onChange={(e) => {
              setModel(e.target.value)
              if (typeof window !== "undefined") localStorage.setItem("conv_model", e.target.value)
            }} />
          </div>
          <div className="grid gap-1">
            <Label htmlFor="sessionSearch">Search sessions</Label>
            <Input id="sessionSearch" placeholder="Filter sessions or search messages..." value={sessionQuery} onChange={(e) => setSessionQuery(e.target.value)} />
          </div>
          <Button onClick={createSession} size="sm" disabled={creating}>{creating ? "Creating..." : "New session"}</Button>
        </div>
        <div className="space-y-2" role="list" aria-label="Session list">
          {sessions?.filter((s) => (s.title || "Untitled").toLowerCase().includes(sessionQuery.toLowerCase())).map((s) => (
            <div key={s.id} role="listitem" className={`w-full px-3 py-2 rounded border ${currentSessionId === s.id ? "bg-slate-100" : "bg-white"}`}>
              {editingTitle === s.id ? (
                <div className="flex gap-2">
                  <Input value={newTitle} onChange={(e) => setNewTitle(e.target.value)} />
                  <Button size="sm" onClick={async () => {
                    if (!newTitle.trim()) { setEditingTitle(null); return }
                    try {
                      await apiPut(`/api/v1/conversations/sessions/${s.id}`, { title: newTitle.trim() })
                      await mutate()
                      setEditingTitle(null)
                    } catch {
                      setEditingTitle(null)
                    }
                  }}>Save</Button>
                </div>
              ) : (
                <div
                  role="button"
                  tabIndex={0}
                  className="w-full text-left cursor-pointer"
                  onClick={() => setCurrentSessionId(s.id)}
                  onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") setCurrentSessionId(s.id) }}
                >
                  <div className="flex items-center justify-between">
                    <span>{s.title || "Untitled"}</span>
                    <Button
                      asChild
                      size="sm"
                      variant="ghost"
                    >
                      <span
                        role="button"
                        tabIndex={0}
                        onClick={(e) => { e.stopPropagation(); setEditingTitle(s.id); setNewTitle(s.title || "") }}
                        onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.stopPropagation(); setEditingTitle(s.id); setNewTitle(s.title || "") } }}
                      >
                        Rename
                      </span>
                    </Button>
                    <Button size="sm" variant="destructive" onClick={(e) => { e.stopPropagation(); setConfirmDeleteId(s.id) }}>Delete</Button>
                  </div>
                </div>
              )}
            </div>
          ))}
          {!sessions && (
            <div className="space-y-2 animate-pulse">
              <div className="h-8 rounded bg-slate-200" />
              <div className="h-8 rounded bg-slate-200" />
              <div className="h-8 rounded bg-slate-200" />
            </div>
          )}
          {sessionQuery.trim() && globalSearch?.items && (
            <div className="mt-4">
              <h3 className="text-sm font-medium text-muted-foreground mb-1">Matches in messages</h3>
              <div className="space-y-2 max-h-48 overflow-auto">
                {globalSearch.items.map((it) => (
                  <div key={it.message_id} className="p-2 rounded border bg-white hover:bg-slate-50 cursor-pointer" onClick={() => setCurrentSessionId(it.session_id)}>
                    <div className="text-xs text-muted-foreground">{it.session_title || "Untitled"} · {new Date(it.created_at).toLocaleString()}</div>
                    <div className="text-sm"><span className="font-medium">{it.role}:</span> {it.content}</div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
      <div className="order-1 md:order-2">
        <Card>
          <CardHeader>
            <CardTitle>
              <div className="flex items-center justify-between">
                <span role="heading" aria-level={2}>Chat</span>
                <div className="flex items-center gap-2">
                  <Button size="sm" variant="outline" onClick={exportAllSessions}>Export All</Button>
                  <Button size="sm" variant="ghost" onClick={exportAsTXT} disabled={!messages}>Export TXT</Button>
                  <Button size="sm" variant="ghost" onClick={exportAsJSON} disabled={!messages}>Export JSON</Button>
                  {editingTitle === currentSessionId ? (
                    <div className="flex items-center gap-2">
                      <Input value={newTitle} onChange={(e) => setNewTitle(e.target.value)} className="h-8 w-40" />
                      <Button size="sm" onClick={async () => {
                        if (!currentSessionId || !newTitle.trim()) { setEditingTitle(null); return }
                    try {
                          await apiPut(`/api/v1/conversations/sessions/${currentSessionId}`, { title: newTitle.trim() })
                          await mutate()
                          await mutateSessionDetails()
                          setToast("Title updated")
                        } catch { setToast("Failed to update title") }
                        finally { setEditingTitle(null) }
                      }}>Save</Button>
                    </div>
                  ) : (
                    <Button size="sm" variant="ghost" onClick={() => { if (currentSessionId) { setEditingTitle(currentSessionId); setNewTitle(sessionDetails?.title || "") } }}>Rename</Button>
                  )}
                  {sessionDetails && (
                    <span className="text-xs text-muted-foreground">{sessionDetails.ai_provider} · {sessionDetails.ai_model}</span>
                  )}
                </div>
              </div>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-[420px] overflow-auto border rounded p-3 bg-white/60">
              {messages?.map((m) => (
                <div key={m.id} className={`mb-2 ${m.role === "user" ? "text-right" : "text-left"}`}>
                  <div className={`inline-block px-3 py-2 rounded ${m.role === "user" ? "bg-blue-600 text-white" : "bg-slate-200"}`}>
                    {m.content}
                  </div>
                </div>
              )) || (!messages ? (
                <div className="space-y-2 animate-pulse">
                  <div className="h-4 rounded bg-slate-200" />
                  <div className="h-4 rounded bg-slate-200 w-5/6" />
                  <div className="h-4 rounded bg-slate-200 w-4/6" />
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">No messages yet. Start by sending one below.</p>
              ))}
              {sending && (
                <div className="mb-2 text-left">
                  <div className="inline-block px-3 py-2 rounded bg-slate-200 animate-pulse">Assistant is typing…</div>
                </div>
              )}
              {streamingText && (
                <div className="mb-2 text-left">
                  <div className="inline-block px-3 py-2 rounded bg-slate-200 whitespace-pre-wrap">{streamingText}</div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
            <div className="mt-3 flex gap-2">
              <Input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Type your message..."
                disabled={sending}
                onKeyDown={(e) => {
                  const isSubmitKey = (e.key === "Enter" && !e.shiftKey) || ((e.key === "Enter") && (e.ctrlKey || e.metaKey))
                  if (isSubmitKey) {
                    e.preventDefault()
                    void sendMessage()
                  }
                }}
              />
              <Button onClick={sendMessage} disabled={sending}>{sending ? "Sending..." : "Send"}</Button>
            </div>
            {sending && <p className="mt-2 text-xs text-muted-foreground">Assistant is responding...</p>}
          </CardContent>
        </Card>
      </div>
      {toast && <Toast message={toast} />}
      <Modal
        open={!!confirmDeleteId}
        title="Delete session?"
        description="This will permanently delete the session and its messages."
        onClose={() => setConfirmDeleteId(null)}
      >
        <div className="flex justify-end gap-2">
          <button className="px-3 h-9 rounded border" onClick={() => setConfirmDeleteId(null)}>Cancel</button>
          <button
            className="px-3 h-9 rounded bg-red-600 text-white"
            onClick={async () => {
              if (!confirmDeleteId) return
              try {
                await apiPost(`/api/v1/conversations/sessions/${confirmDeleteId}/delete`, {})
              } catch {
                // fallback to RESTful
                await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000"}/api/v1/conversations/sessions/${confirmDeleteId}`, {
                  method: "DELETE",
                  headers: getToken() ? { Authorization: `Bearer ${getToken()}` } : undefined,
                })
              }
              setConfirmDeleteId(null)
              await mutate()
              if (currentSessionId === confirmDeleteId) setCurrentSessionId(null)
              showToast("Session deleted")
            }}
          >
            Delete
          </button>
        </div>
      </Modal>
    </div>
  )
}


