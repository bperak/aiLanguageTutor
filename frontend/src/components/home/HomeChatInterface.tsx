"use client"

import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import { apiGet, apiPost } from "@/lib/api"
import { getToken } from "@/lib/auth"
import { useToast } from "@/components/ToastProvider"
import ProgressSummary from "./ProgressSummary"
import NextStepWidget from "./NextStepWidget"
import AITutorSuggestions from "./AITutorSuggestions"
import SessionsCard from "./SessionsCard"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import type { Components } from "react-markdown"
import { formatSessionName } from "@/lib/utils"

interface HomeChatInterfaceProps {
  profileStatus: { profile_completed: boolean; profile_skipped: boolean } | null
}

export default function HomeChatInterface({ profileStatus }: HomeChatInterfaceProps) {
  const { showToast } = useToast()
  const router = useRouter()
  const [homeStatus, setHomeStatus] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null)
  const [messages, setMessages] = useState<Array<{ role: string; content: string }>>([])
  const [input, setInput] = useState("")
  const [sending, setSending] = useState(false)
  const [streamingText, setStreamingText] = useState("")

  // Helper function to extract can_do_id from URL
  const extractCanDoId = (url: string): string | null => {
    // Clean the URL first
    const cleanUrl = url.trim()
    try {
      // Try parsing as full URL first
      const urlObj = new URL(cleanUrl, window.location.origin)
      const canDoId = urlObj.searchParams.get("can_do_id")
      if (canDoId) return canDoId
    } catch {
      // If that fails, try regex extraction
    }
    // Try to extract from path format like /api/v1/cando/lessons/start?can_do_id=JF:21
    const match = cleanUrl.match(/[?&]can_do_id=([^&\s]+)/)
    return match ? decodeURIComponent(match[1]) : null
  }

  // Preprocess message content to convert CanDo URLs to clickable links
  const preprocessMessage = (content: string): string => {
    // Match URLs in code blocks (backticks) - handle both inline and block code
    // Pattern 1: `URL` (inline code) - this is the most common case
    // Pattern 2: ```\nURL\n``` (code block)
    // Pattern 3: Plain URL (not in backticks)
    
    // First, handle the exact pattern from the image: `/api/v1/cando/lessons/start?can_do_id=JF:21`
    // This is the most specific pattern - match inline code with backticks
    // Note: ? needs to be escaped in regex, but in a string it's fine
    let processed = content.replace(/`(\/api\/v1\/cando\/lessons\/start[?]can_do_id=([^`\s&]+))`/g, (match, url, canDoId) => {
      console.log('✅ Matched inline code pattern:', match, 'canDoId:', canDoId)
      return `[Start Lesson: ${canDoId}](/cando/${encodeURIComponent(canDoId)})`
    })
    
    // Then handle code blocks: ```\nURL\n```
    processed = processed.replace(/```[\s\n]*(\/api\/v1\/cando\/lessons\/start[?]can_do_id=([^\s&`]+))[\s\n]*```/g, (match, url, canDoId) => {
      console.log('✅ Matched code block:', match, 'canDoId:', canDoId)
      return `[Start Lesson: ${canDoId}](/cando/${encodeURIComponent(canDoId)})`
    })
    
    // Finally, handle plain URLs (not in backticks)
    processed = processed.replace(/(^|[^`])(\/api\/v1\/cando\/lessons\/start[?]can_do_id=([^\s&`]+))([^`]|$)/g, (match, before, url, canDoId, after) => {
      // Only replace if it's not already in backticks
      if (before !== '`' && after !== '`') {
        console.log('✅ Matched plain URL:', match, 'canDoId:', canDoId)
        return `${before}[Start Lesson: ${canDoId}](/cando/${encodeURIComponent(canDoId)})${after}`
      }
      return match
    })
    
    console.log('Preprocessed content:', processed.substring(0, 200))
    return processed
  }

  // Custom markdown components to handle links
  const markdownComponents: Components = {
    code: (props: any) => {
      const { node, inline, className, children, ...restProps } = props
      const codeContent = String(children).trim()
      console.log('🔍 Code component - content:', codeContent, 'inline:', inline)
      
      // Check if the code content looks like a CanDo lesson start URL (both inline and block)
      // Match with or without leading slash, and handle various formats
      if (codeContent.match(/\/api\/v1\/cando\/lessons\/start/)) {
        const canDoId = extractCanDoId(codeContent)
        console.log('🔍 Code component - extracted canDoId:', canDoId)
        if (canDoId) {
          return (
            <a
              href={`/cando/${encodeURIComponent(canDoId)}`}
              onClick={(e) => {
                e.preventDefault()
                console.log('🔗 Navigating to:', `/cando/${encodeURIComponent(canDoId)}`)
                router.push(`/cando/${encodeURIComponent(canDoId)}`)
              }}
              className="text-blue-600 hover:text-blue-800 underline cursor-pointer font-medium"
            >
              Start Lesson: {canDoId}
            </a>
          )
        }
      }
      return (
        <code className={className} {...restProps}>
          {children}
        </code>
      )
    },
    a: ({ node, href, children, ...props }) => {
      // Handle CanDo lesson start URLs (API endpoints)
      if (href && href.includes("/api/v1/cando/lessons/start")) {
        const canDoId = extractCanDoId(href)
        if (canDoId) {
          return (
            <a
              href={`/cando/${encodeURIComponent(canDoId)}`}
              onClick={(e) => {
                e.preventDefault()
                router.push(`/cando/${encodeURIComponent(canDoId)}`)
              }}
              className="text-blue-600 hover:text-blue-800 underline"
              {...props}
            >
              {children}
            </a>
          )
        }
      }
      // Handle CanDo frontend routes
      if (href && href.startsWith("/cando/")) {
        return (
          <a
            href={href}
            onClick={(e) => {
              e.preventDefault()
              router.push(href)
            }}
            className="text-blue-600 hover:text-blue-800 underline cursor-pointer"
            {...props}
          >
            {children}
          </a>
        )
      }
      // Regular links
      return (
        <a
          href={href}
          target={href?.startsWith("http") ? "_blank" : undefined}
          rel={href?.startsWith("http") ? "noreferrer" : undefined}
          className="text-blue-600 hover:text-blue-800 underline"
          {...props}
        >
          {children}
        </a>
      )
    },
  }

  useEffect(() => {
    loadHomeStatus()
    loadHomeSessions()
  }, [])

  useEffect(() => {
    if (currentSessionId) {
      loadMessages()
    }
  }, [currentSessionId])

  // Refresh messages when session changes
  const handleSessionChange = (sessionId: string) => {
    setCurrentSessionId(sessionId)
    // loadMessages will be called by useEffect when currentSessionId changes
  }

  const loadHomeStatus = async () => {
    try {
      const status = await apiGet("/api/v1/home/status")
      setHomeStatus(status)
      setLoading(false)
    } catch (err) {
      showToast("Failed to load home status", "error")
      setLoading(false)
    }
  }

  const loadHomeSessions = async () => {
    try {
      const sessions = await apiGet<Array<{ id: string; title: string }>>("/api/v1/home/sessions")
      if (sessions && sessions.length > 0) {
        setCurrentSessionId(sessions[0].id)
      } else {
        // Fetch greeting and progress before creating session
        const status = await apiGet<{
          greeting?: string
          recent_lessons?: any[]
          progress_summary?: any
          next_learning_step?: any
        }>("/api/v1/home/status")
        // Create default home session with greeting context using date-based naming
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
        setCurrentSessionId(newSession.id)
      }
    } catch (err) {
      console.error("Failed to load home sessions:", err)
    }
  }

  const loadMessages = async () => {
    if (!currentSessionId) return
    try {
      const msgs = await apiGet<Array<{ role: string; content: string }>>(
        `/api/v1/conversations/sessions/${currentSessionId}/messages?limit=50`
      )
      setMessages(msgs)
    } catch (err) {
      console.error("Failed to load messages:", err)
    }
  }

  const sendMessage = async () => {
    if (!input.trim() || !currentSessionId || sending) return

    const userMessage = input.trim()
    setInput("")
    setSending(true)

    // Add user message immediately
    const updatedMessages = [...messages, { role: "user", content: userMessage }]
    setMessages(updatedMessages)

    try {
      // Send message
      await apiPost(`/api/v1/home/sessions/${currentSessionId}/messages`, {
        role: "user",
        content: userMessage,
        no_ai: true,
      })

      // Stream reply
      const token = getToken()
      const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000"
      const url = `${baseUrl}/api/v1/home/sessions/${currentSessionId}/stream`

      const resp = await fetch(url, {
        method: "GET",
        headers: token ? { Authorization: `Bearer ${token}` } : undefined,
      })

      if (!resp.ok || !resp.body) {
        throw new Error(`Stream error: ${resp.status}`)
      }

      const reader = resp.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ""
      let assistantReply = ""
      let currentEvent = ""

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
            // Handle event type lines
            if (line.startsWith("event: ")) {
              currentEvent = line.slice(7).trim()
              continue
            }
            
            // Handle data lines
            if (line.startsWith("data: ")) {
              const data = line.slice(6)
              
              // Handle error events
              if (currentEvent === "error" || data === "streaming_failed") {
                setSending(false)
                setStreamingText("")
                showToast("Failed to generate response. Please try again.", "error")
                return
              }
              
              if (data === "[DONE]") {
                setSending(false)
                setStreamingText("")
                // Add the assistant reply to messages directly from streamed content
                // This ensures it appears immediately even if background persistence hasn't completed
                if (assistantReply.trim()) {
                  setMessages((prevMessages) => [
                    ...prevMessages,
                    { role: "assistant", content: assistantReply }
                  ])
                }
                // Reload messages after a short delay to sync with persisted version
                // (background task needs time to persist)
                setTimeout(async () => {
                  await loadMessages()
                }, 500)
                return
              }
              
              // Reset event type after processing data
              currentEvent = ""
              assistantReply += data
              setStreamingText(assistantReply)
              // streamingText is displayed separately in the UI while streaming
            }
          }
        }
      }
    } catch (err) {
      console.error("Failed to send message:", err)
      showToast("Failed to send message", "error")
      setSending(false)
      setStreamingText("")
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-gray-900"></div>
      </div>
    )
  }

  return (
    <div className="max-w-6xl mx-auto p-4 sm:p-6">
      {/* Next Step Widget (if profile completed) */}
      {profileStatus?.profile_completed && homeStatus?.next_learning_step && (
        <div className="mb-6">
          <NextStepWidget nextStep={homeStatus?.next_learning_step} />
        </div>
      )}

      {/* Main Chat Interface */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Chat Section - 2/3 width on desktop */}
        <div className="lg:col-span-2">
          <Card>
            <CardHeader>
              <CardTitle>Learning Assistant</CardTitle>
            </CardHeader>
            <CardContent>
              {/* Messages */}
              <div className="max-h-[calc(100vh-280px)] overflow-y-auto border rounded-lg p-4 space-y-4 bg-slate-50 mb-4">
                {messages.map((msg, idx) => (
                  <div
                    key={idx}
                    className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                  >
                    <div
                      className={`max-w-[80%] rounded-lg p-3 ${
                        msg.role === "user"
                          ? "bg-blue-600 text-white"
                          : "bg-white border text-gray-900"
                      }`}
                    >
                      <div className={`text-sm markdown-content ${msg.role === "user" ? "prose-invert" : ""}`}>
                        <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
                          {preprocessMessage(msg.content)}
                        </ReactMarkdown>
                      </div>
                    </div>
                  </div>
                ))}
                {sending && streamingText && (
                  <div className="flex justify-start">
                    <div className="max-w-[80%] bg-white border rounded-lg p-3">
                      <div className="text-sm markdown-content">
                        <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
                          {preprocessMessage(streamingText)}
                        </ReactMarkdown>
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* Input */}
              <div className="flex gap-2">
                <input
                  type="text"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyPress={(e) => e.key === "Enter" && !e.shiftKey && sendMessage()}
                  placeholder="Ask your AI tutor anything..."
                  className="flex-1 px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  disabled={sending || !currentSessionId}
                />
                <Button onClick={sendMessage} disabled={sending || !currentSessionId || !input.trim()}>
                  Send
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Sidebar - 1/3 width on desktop */}
        <div className="lg:col-span-1 space-y-4">
          <AITutorSuggestions suggestions={homeStatus?.suggestions} />
          <SessionsCard
            currentSessionId={currentSessionId}
            onSessionChange={handleSessionChange}
          />
          <ProgressSummary progressSummary={homeStatus?.progress_summary} />
        </div>
      </div>
    </div>
  )
}

