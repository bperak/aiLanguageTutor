"use client"

import { useState, useEffect, useRef } from "react"
import { useRouter } from "next/navigation"
import { apiGet, apiPost } from "@/lib/api"
import { getToken } from "@/lib/auth"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { useToast } from "@/components/ToastProvider"
import ProfileDataReview from "./ProfileDataReview"
import PersonalizationSuggestions from "./PersonalizationSuggestions"
import LearningPathPreview from "./LearningPathPreview"
import Link from "next/link"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import type { Components } from "react-markdown"

interface ProfileBuildingChatProps {
  onComplete: (conversationId: string) => void
  onSkip: () => void
  onConversationCreated?: (conversationId: string) => void
}

export default function ProfileBuildingChat({
  onComplete,
  onSkip,
  onConversationCreated,
}: ProfileBuildingChatProps) {
  const { showToast } = useToast()
  const router = useRouter()
  const [messages, setMessages] = useState<Array<{ role: string; content: string; id?: string }>>([])
  const [input, setInput] = useState("")
  const [sending, setSending] = useState(false)
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const messagesEndRef = useRef<HTMLDivElement>(null)

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
    // Note: ? needs to be escaped in regex, using character class [?]
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
    code: ({ node, className, children, ...props }) => {
      const codeContent = String(children).trim()
      // Check if the code content looks like a CanDo lesson start URL (both inline and block)
      // Match with or without leading slash, and handle various formats
      if (codeContent.match(/(^|\/)api\/v1\/cando\/lessons\/start/)) {
        const canDoId = extractCanDoId(codeContent)
        if (canDoId) {
          return (
            <a
              href={`/cando/${encodeURIComponent(canDoId)}`}
              onClick={(e) => {
                e.preventDefault()
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
        <code className={className} {...props}>
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
    initializeSession()
  }, [])

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }

  const initializeSession = async () => {
    try {
      // Get user info for personalization
      const user = await apiGet<{ native_language?: string; full_name?: string }>("/api/v1/auth/me")
      
      // Create profile building conversation session
      const session = await apiPost<{ id: string }>("/api/v1/conversations/sessions", {
        title: "Profile Building",
        language_code: user.native_language || "en",
        session_type: "profile_building",
        ai_provider: "openai",
        ai_model: "gpt-4o-mini",
        system_prompt: "You are a friendly AI language tutor. Help the user build their learning profile through conversation.",
      })

      setSessionId(session.id)
      if (onConversationCreated) {
        onConversationCreated(session.id)
      }

      // Get initial greeting
      await sendInitialMessage(session.id)
      setLoading(false)
    } catch (err) {
      showToast("Failed to initialize profile building", "error")
      setLoading(false)
    }
  }

  const sendInitialMessage = async (sessionId: string) => {
    try {
      // Send initial message to start conversation
      await apiPost(`/api/v1/conversations/sessions/${sessionId}/messages`, {
        role: "user",
        content: "Hello! I'm ready to build my profile.",
        no_ai: true,
      })

      // Stream assistant reply
      const token = getToken()
      // Use relative URL for browser, same pattern as api.ts
      const baseUrl = typeof window !== "undefined" ? "" : (process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000")
      const url = `${baseUrl}/api/v1/conversations/sessions/${sessionId}/stream`
      
      const resp = await fetch(url, {
        method: "GET",
        headers: token ? { Authorization: `Bearer ${token}` } : undefined,
      })

      if (resp.ok && resp.body) {
        const reader = resp.body.getReader()
        const decoder = new TextDecoder()
        let buffer = ""
        let assistantReply = ""

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
                  // Check for completion signal and strip it
                  const completionSignal = "[PROFILE_COMPLETE]"
                  const cleanReply = assistantReply.includes(completionSignal)
                    ? assistantReply.replace(completionSignal, "").trim()
                    : assistantReply
                  setMessages([
                    { role: "user", content: "Hello! I'm ready to build my profile." },
                    { role: "assistant", content: cleanReply },
                  ])
                  // If completion signal detected, trigger completion
                  if (assistantReply.includes(completionSignal)) {
                    await handleComplete(sessionId)
                  }
                  return
                }
                assistantReply += data
              }
            }
          }
        }
      }
    } catch (err) {
      console.error("Failed to send initial message:", err)
    }
  }

  const sendMessage = async () => {
    if (!input.trim() || !sessionId || sending) return

    const userMessage = input.trim()
    setInput("")
    setSending(true)

    // Add user message to UI immediately
    const newMessages = [...messages, { role: "user", content: userMessage }]
    setMessages(newMessages)

    try {
      // Send user message
      await apiPost(`/api/v1/conversations/sessions/${sessionId}/messages`, {
        role: "user",
        content: userMessage,
        no_ai: true,
      })

      // Stream assistant reply
      const token = getToken()
      // Use relative URL for browser, same pattern as api.ts
      const baseUrl = typeof window !== "undefined" ? "" : (process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000")
      const url = `${baseUrl}/api/v1/conversations/sessions/${sessionId}/stream`
      
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
      let hasCompletionSignal = false

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
                // Check for completion signal and strip it
                const completionSignal = "[PROFILE_COMPLETE]"
                if (assistantReply.includes(completionSignal)) {
                  // Strip the signal from the message
                  const cleanReply = assistantReply.replace(completionSignal, "").trim()
                  setMessages([...newMessages, { role: "assistant", content: cleanReply }])
                  // Automatically trigger profile completion
                  await handleComplete()
                  return
                }
                // Refresh messages to get final state
                await loadMessages()
                return
              }
              assistantReply += data
              // Check for completion signal in real-time and strip from display
              const completionSignal = "[PROFILE_COMPLETE]"
              if (assistantReply.includes(completionSignal) && !hasCompletionSignal) {
                hasCompletionSignal = true
                // Strip the signal from displayed message
                const cleanReply = assistantReply.replace(completionSignal, "").trim()
                setMessages([...newMessages, { role: "assistant", content: cleanReply }])
              } else if (!hasCompletionSignal) {
                setMessages([...newMessages, { role: "assistant", content: assistantReply }])
              }
            }
          }
        }
      }
    } catch (err) {
      showToast("Failed to send message", "error")
      setSending(false)
    }
  }

  const loadMessages = async () => {
    if (!sessionId) return
    try {
      const msgs = await apiGet<Array<{ role: string; content: string; id: string }>>(
        `/api/v1/conversations/sessions/${sessionId}/messages?limit=100`
      )
      setMessages(msgs)
    } catch (err) {
      console.error("Failed to load messages:", err)
    }
  }

  const [showReview, setShowReview] = useState(false)
  const [extractedData, setExtractedData] = useState<any>(null)

  const handleComplete = async (overrideSessionId?: string) => {
    const activeSessionId = overrideSessionId || sessionId
    if (!activeSessionId) {
      showToast("No active conversation", "error")
      return
    }
    try {
      // First, extract the data to show for review
      const response = await apiPost<{ profile_data: any }>("/api/v1/profile/extract", {
        conversation_id: activeSessionId,
      })
      setExtractedData(response.profile_data)
      setShowReview(true)
    } catch (err) {
      showToast("Failed to extract profile data", "error")
    }
  }

  const handleApprove = async (profileData: any) => {
    if (!sessionId) {
      showToast("No active conversation", "error")
      return
    }
    try {
      // Call complete endpoint with extracted data
      await apiPost("/api/v1/profile/complete", {
        conversation_id: sessionId,
        profile_data: profileData,
      })
      showToast("Profile completed successfully!", "success")
      onComplete(sessionId)
    } catch (err) {
      const error = err as { response?: { data?: { detail?: string } } }
      showToast(error?.response?.data?.detail || "Failed to save profile", "error")
    }
  }

  if (loading) {
    return (
      <Card>
        <CardContent className="p-6">
          <div className="text-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900 mx-auto"></div>
            <p className="mt-2 text-sm text-muted-foreground">Initializing conversation...</p>
          </div>
        </CardContent>
      </Card>
    )
  }

  if (showReview && extractedData && sessionId) {
    return (
      <ProfileDataReview
        profileData={extractedData}
        conversationId={sessionId}
        onApprove={handleApprove}
        onEdit={() => setShowReview(false)}
      />
    )
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>Conversation with AI Tutor</CardTitle>
            <p className="text-sm text-muted-foreground">
              The AI tutor will ask you about your learning goals, previous experience, and preferences.
            </p>
          </div>
          <Link href="/">
            <Button variant="outline" size="sm">
              Back to Home
            </Button>
          </Link>
        </div>
        {/* Home Context Banner */}
        <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
          <p className="text-sm text-blue-900">
            <strong>💡 After completing your profile:</strong> You'll see a personalized learning path on your Home page, 
            customized recommendations, and progress tracking tailored to your goals and preferences.
          </p>
        </div>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {/* Chat Section - 2/3 width */}
          <div className="lg:col-span-2 space-y-4">
            {/* Messages */}
            <div className="h-96 overflow-y-auto border rounded-lg p-4 space-y-4 bg-slate-50">
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
            {sending && (
              <div className="flex justify-start">
                <div className="bg-white border rounded-lg p-3">
                  <div className="flex space-x-1">
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "0.1s" }}></div>
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "0.2s" }}></div>
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

            {/* Input */}
            <div className="flex gap-2">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyPress={(e) => e.key === "Enter" && !e.shiftKey && sendMessage()}
                placeholder="Type your message..."
                className="flex-1 px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                disabled={sending || !sessionId}
              />
              <Button onClick={sendMessage} disabled={sending || !sessionId || !input.trim()}>
                Send
              </Button>
            </div>

            {/* Actions */}
            <div className="flex justify-between items-center pt-4 border-t">
              <Button variant="outline" onClick={onSkip}>
                Skip for Now
              </Button>
              <Button onClick={() => { void handleComplete() }} disabled={!sessionId || messages.length < 4}>
                Complete Profile
              </Button>
            </div>
          </div>

          {/* Suggestions Sidebar - 1/3 width */}
          <div className="lg:col-span-1 space-y-4">
            <LearningPathPreview />
            <PersonalizationSuggestions
              conversationId={sessionId}
              onSuggestionClick={(suggestion) => {
                // When user clicks a suggestion, add it to input
                setInput(suggestion.replace(/^💡\s*/, ""))
              }}
            />
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

