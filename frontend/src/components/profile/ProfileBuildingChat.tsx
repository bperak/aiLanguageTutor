"use client"

import { useState, useEffect, useRef } from "react"
import { useRouter } from "next/navigation"
import { apiGet, apiPost } from "@/lib/api"
import { getToken } from "@/lib/auth"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { useToast } from "@/components/ToastProvider"
import ProfileDataReview from "./ProfileDataReview"
import LearningPathPreview from "./LearningPathPreview"
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
  const [profilePreviewData, setProfilePreviewData] = useState<any>(null)
  const [profilePreviewLoading, setProfilePreviewLoading] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const messagesContainerRef = useRef<HTMLDivElement>(null)
  const [shouldAutoScroll, setShouldAutoScroll] = useState(true)

  // Helper function to extract can_do_id from URL
  const extractCanDoId = (url: string): string | null => {
    const cleanUrl = url.trim()
    try {
      const urlObj = new URL(cleanUrl, window.location.origin)
      const canDoId = urlObj.searchParams.get("can_do_id")
      if (canDoId) return canDoId
    } catch {
      // If that fails, try regex extraction
    }
    const match = cleanUrl.match(/[?&]can_do_id=([^&\s]+)/)
    return match ? decodeURIComponent(match[1]) : null
  }

  // Preprocess message content to convert CanDo URLs to clickable links
  const preprocessMessage = (content: string): string => {
    let processed = content.replace(/`(\/api\/v1\/cando\/lessons\/start[?]can_do_id=([^`\s&]+))`/g, (match, url, canDoId) => {
      return `[Start Lesson: ${canDoId}](/cando/${encodeURIComponent(canDoId)})`
    })
    
    processed = processed.replace(/```[\s\n]*(\/api\/v1\/cando\/lessons\/start[?]can_do_id=([^\s&`]+))[\s\n]*```/g, (match, url, canDoId) => {
      return `[Start Lesson: ${canDoId}](/cando/${encodeURIComponent(canDoId)})`
    })
    
    processed = processed.replace(/(^|[^`])(\/api\/v1\/cando\/lessons\/start[?]can_do_id=([^\s&`]+))([^`]|$)/g, (match, before, url, canDoId, after) => {
      if (before !== '`' && after !== '`') {
        return `${before}[Start Lesson: ${canDoId}](/cando/${encodeURIComponent(canDoId)})${after}`
      }
      return match
    })
    
    return processed
  }

  // Custom markdown components to handle links
  const markdownComponents: Components = {
    code: ({ node, className, children, ...props }) => {
      const codeContent = String(children).trim()
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
              className="text-blue-600 hover:text-blue-700 dark:text-blue-300 dark:hover:text-blue-200 underline cursor-pointer font-medium"
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
              className="text-blue-600 hover:text-blue-700 dark:text-blue-300 dark:hover:text-blue-200 underline"
              {...props}
            >
              {children}
            </a>
          )
        }
      }
      if (href && href.startsWith("/cando/")) {
        return (
          <a
            href={href}
            onClick={(e) => {
              e.preventDefault()
              router.push(href)
            }}
            className="text-blue-600 hover:text-blue-700 dark:text-blue-300 dark:hover:text-blue-200 underline cursor-pointer"
            {...props}
          >
            {children}
          </a>
        )
      }
      return (
        <a
          href={href}
          target={href?.startsWith("http") ? "_blank" : undefined}
          rel={href?.startsWith("http") ? "noreferrer" : undefined}
          className="text-blue-600 hover:text-blue-700 dark:text-blue-300 dark:hover:text-blue-200 underline"
          {...props}
        >
          {children}
        </a>
      )
    },
  }

  // Update profile preview as conversation progresses
  const updateProfilePreview = async () => {
    if (!sessionId || messages.length < 2) return // Need at least user + assistant message
    
    setProfilePreviewLoading(true)
    try {
      // Add timeout to prevent hanging
      const timeoutPromise = new Promise((_, reject) => 
        setTimeout(() => reject(new Error("Profile preview update timeout")), 10000)
      )
      
      const response = await Promise.race([
        apiPost<{ profile_data: any; extraction_response?: any }>("/api/v1/profile/extract", {
          conversation_id: sessionId,
        }),
        timeoutPromise
      ]) as { profile_data: any; extraction_response?: any }
      
      if (response.profile_data) {
        setProfilePreviewData(response.profile_data)
        console.log("Profile preview updated:", response.profile_data)
      }
    } catch (err: any) {
      // Log error for debugging but don't show to user
      const errorMsg = err?.response?.data?.detail || err?.message || "Unknown error"
      if (errorMsg.includes("timeout")) {
        console.debug("Profile preview update timed out - this is normal if the API is slow")
      } else {
        console.debug("Could not update profile preview:", errorMsg)
      }
      // Don't update state on error - keep previous data
    } finally {
      setProfilePreviewLoading(false)
    }
  }

  useEffect(() => {
    initializeSession()
    
    // Safety timeout: always exit loading state after 10 seconds
    const safetyTimeout = setTimeout(() => {
      if (loading) {
        console.warn("Loading timeout - forcing exit from loading state")
        setLoading(false)
        // Try to load messages if session exists
        if (sessionId) {
          loadMessages().catch(console.error)
        }
      }
    }, 10000)
    
    return () => clearTimeout(safetyTimeout)
  }, [])

  // Handle scroll behavior - only auto-scroll if user hasn't manually scrolled up
  useEffect(() => {
    if (shouldAutoScroll && messages.length > 0) {
      scrollToBottom()
    }
  }, [messages, shouldAutoScroll])

  // Update profile preview when messages change (debounced)
  useEffect(() => {
    if (sessionId && messages.length >= 2) {
      // Debounce the preview update to avoid too many API calls
      const timer = setTimeout(() => {
        updateProfilePreview()
      }, 2000) // Wait 2 seconds after last message change
      return () => clearTimeout(timer)
    }
  }, [messages, sessionId])

  // Check if user has scrolled up manually
  const handleScroll = () => {
    if (!messagesContainerRef.current) return
    const container = messagesContainerRef.current
    const isNearBottom = container.scrollHeight - container.scrollTop - container.clientHeight < 100
    setShouldAutoScroll(isNearBottom)
  }

  const scrollToBottom = () => {
    if (messagesEndRef.current && shouldAutoScroll) {
      messagesEndRef.current.scrollIntoView({ behavior: "smooth" })
    }
  }

  const initializeSession = async () => {
    try {
      const user = await apiGet<{ native_language?: string; full_name?: string }>("/api/v1/auth/me")
      
      // First, check if there's an existing active profile building session
      let session: { id: string } | null = null
      try {
        const existingSession = await apiGet<{ id: string } | null>("/api/v1/conversations/sessions/profile-building/active")
        if (existingSession && existingSession.id) {
          session = existingSession
          console.log("Found existing profile building session:", session.id)
        }
      } catch (err) {
        console.log("No existing session found, will create new one")
      }
      
      // If no existing session, create a new one
      if (!session) {
        session = await apiPost<{ id: string }>("/api/v1/conversations/sessions", {
          title: "Profile Building",
          language_code: user.native_language || "en",
          session_type: "profile_building",
          ai_provider: "openai",
          ai_model: "gpt-4o-mini",
          system_prompt: "You are a friendly AI language tutor. Help the user build their learning profile through conversation.",
        })
        console.log("Created new profile building session:", session.id)
      }

      setSessionId(session.id)
      console.log("Session initialized:", session.id)
      if (onConversationCreated) {
        onConversationCreated(session.id)
      }

      // Load existing messages if session already exists
      const existingMessages = await loadMessagesForSession(session.id)
      
      // Only send initial message if there are no existing messages
      if (!existingMessages || existingMessages.length === 0) {
        await sendInitialMessage(session.id)
      } else {
        console.log(`Loaded ${existingMessages.length} existing messages from session`)
        // Update profile preview with existing conversation
        if (existingMessages.length >= 2) {
          await updateProfilePreview()
        }
      }
      
      setLoading(false)
      console.log("Loading complete, sessionId:", session.id)
    } catch (err: any) {
      console.error("Error in initializeSession:", err)
      const error = err as { response?: { status?: number } }
      if (error?.response?.status === 401) {
        showToast("Please log in to build your profile")
        // Redirect to login after a short delay
        setTimeout(() => {
          router.push("/login")
        }, 2000)
      } else {
        showToast("Failed to initialize profile building. Please try again.")
      }
      setLoading(false)
    } finally {
      // Always set loading to false, even if something goes wrong
      setLoading(false)
    }
  }

  const sendInitialMessage = async (sessionId: string) => {
    try {
      await apiPost(`/api/v1/conversations/sessions/${sessionId}/messages`, {
        role: "user",
        content: "Hello! I'm ready to build my profile.",
        no_ai: true,
      })

      const token = getToken()
      const baseUrl = typeof window !== "undefined" ? "" : (process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000")
      const url = `${baseUrl}/api/v1/conversations/sessions/${sessionId}/stream`
      
      // Add timeout to prevent hanging
      const controller = new AbortController()
      const timeoutId = setTimeout(() => controller.abort(), 30000) // 30 second timeout
      
      try {
        const resp = await fetch(url, {
          method: "GET",
          headers: token ? { Authorization: `Bearer ${token}` } : undefined,
          signal: controller.signal,
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
                    clearTimeout(timeoutId)
                    const completionSignal = "[PROFILE_COMPLETE]"
                    const cleanReply = assistantReply.includes(completionSignal)
                      ? assistantReply.replace(completionSignal, "").trim()
                      : assistantReply
                    setMessages([
                      { role: "user", content: "Hello! I'm ready to build my profile." },
                      { role: "assistant", content: cleanReply },
                    ])
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
      } catch (fetchErr: any) {
        clearTimeout(timeoutId)
        if (fetchErr.name === 'AbortError') {
          console.warn("Stream timeout, loading messages from API instead")
          // Fallback: load messages from API if stream times out
          try {
            await loadMessages()
          } catch (loadErr) {
            console.error("Failed to load messages:", loadErr)
            // Set a default message if loading fails
            setMessages([
              { role: "user", content: "Hello! I'm ready to build my profile." },
              { role: "assistant", content: "Hello! I'm here to help you build your learning profile. Let's start by learning about your goals and experience." },
            ])
          }
        } else {
          throw fetchErr
        }
      }
    } catch (err) {
      console.error("Failed to send initial message:", err)
      // Even if stream fails, try to load existing messages
      try {
        await loadMessages()
      } catch (loadErr) {
        console.error("Failed to load messages:", loadErr)
        // Set a default message if loading fails
        setMessages([
          { role: "user", content: "Hello! I'm ready to build my profile." },
          { role: "assistant", content: "Hello! I'm here to help you build your learning profile. Let's start by learning about your goals and experience." },
        ])
      }
    }
  }

  const sendMessage = async () => {
    if (!input.trim() || !sessionId || sending) return

    const userMessage = input.trim()
    setInput("")
    setSending(true)
    setShouldAutoScroll(true) // Auto-scroll when sending new message

    // Focus input after clearing (for better UX)
    setTimeout(() => inputRef.current?.focus(), 100)

    const newMessages = [...messages, { role: "user", content: userMessage }]
    setMessages(newMessages)

    try {
      await apiPost(`/api/v1/conversations/sessions/${sessionId}/messages`, {
        role: "user",
        content: userMessage,
        no_ai: true,
      })

      const token = getToken()
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

      // Add timeout for stream reading (30 seconds)
      const streamTimeout = setTimeout(() => {
        reader.cancel()
        console.error("Stream timeout - cancelling reader")
        setSending(false)
        showToast("Response timeout. Please try again.")
        // Load messages to show what we have so far
        void loadMessages()
      }, 30000)

      try {
        while (true) {
          const { done, value } = await reader.read()
          if (done) {
            clearTimeout(streamTimeout)
            break
          }

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
                  clearTimeout(streamTimeout)
                  setSending(false)
                  const completionSignal = "[PROFILE_COMPLETE]"
                  if (assistantReply.includes(completionSignal)) {
                    const cleanReply = assistantReply.replace(completionSignal, "").trim()
                    setMessages([...newMessages, { role: "assistant", content: cleanReply }])
                    await handleComplete()
                    return
                  }
                  await loadMessages()
                  return
                }
                assistantReply += data
                const completionSignal = "[PROFILE_COMPLETE]"
                if (assistantReply.includes(completionSignal) && !hasCompletionSignal) {
                  hasCompletionSignal = true
                  const cleanReply = assistantReply.replace(completionSignal, "").trim()
                  setMessages([...newMessages, { role: "assistant", content: cleanReply }])
                } else if (!hasCompletionSignal) {
                  setMessages([...newMessages, { role: "assistant", content: assistantReply }])
                }
              }
            }
          }
        }
        // Stream completed normally
        clearTimeout(streamTimeout)
        setSending(false)
        await loadMessages()
      } catch (streamErr) {
        clearTimeout(streamTimeout)
        console.error("Stream error:", streamErr)
        setSending(false)
        showToast("Stream error. Please try again.")
        await loadMessages()
      }
    } catch (err) {
      console.error("Error in sendMessage:", err)
      showToast("Failed to send message")
      setSending(false)
    } finally {
      // Ensure sending is always reset, even if something goes wrong
      setSending(false)
    }
  }

  const loadMessagesForSession = async (sessionIdToLoad: string) => {
    try {
      const msgs = await apiGet<Array<{ role: string; content: string; id: string }>>(
        `/api/v1/conversations/sessions/${sessionIdToLoad}/messages?limit=100`
      )
      setMessages(msgs)
      return msgs
    } catch (err) {
      console.error("Failed to load messages:", err)
      return []
    }
  }

  const loadMessages = async () => {
    if (!sessionId) return []
    return await loadMessagesForSession(sessionId)
  }

  const [showReview, setShowReview] = useState(false)
  const [extractedData, setExtractedData] = useState<any>(null)

  const handleComplete = async (overrideSessionId?: string) => {
    const activeSessionId = overrideSessionId || sessionId
    if (!activeSessionId) {
      showToast("No active conversation")
      return
    }
    try {
      const response = await apiPost<{ profile_data: any }>("/api/v1/profile/extract", {
        conversation_id: activeSessionId,
      })
      setExtractedData(response.profile_data)
      setShowReview(true)
    } catch (err) {
      showToast("Failed to extract profile data")
    }
  }

  const handleApprove = async (profileData: any) => {
    if (!sessionId) {
      showToast("No active conversation")
      return
    }
    try {
      await apiPost("/api/v1/profile/complete", {
        conversation_id: sessionId,
        profile_data: profileData,
      })
      showToast("Profile completed successfully!")
      onComplete(sessionId)
    } catch (err) {
      const error = err as { response?: { data?: { detail?: string } } }
      showToast(error?.response?.data?.detail || "Failed to save profile")
    }
  }

  if (loading) {
    return (
      <Card>
        <CardContent className="p-6">
          <div className="text-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto"></div>
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
        </div>
        <div className="mt-4 p-3 bg-blue-500/10 border border-blue-500/30 rounded-lg">
          <p className="text-sm text-blue-700 dark:text-blue-200">
            <strong>💡 After completing your profile:</strong> You&apos;ll see a personalized learning path on your Home page, 
            customized recommendations, and progress tracking tailored to your goals and preferences.
          </p>
        </div>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 max-w-7xl mx-auto">
          <div className="lg:col-span-2 space-y-4">
            <div 
              ref={messagesContainerRef}
              onScroll={handleScroll}
              className="h-96 overflow-y-auto border rounded-lg p-4 space-y-4 bg-muted/40"
            >
              {messages.map((msg, idx) => (
                <div
                  key={idx}
                  className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                >
                  <div
                    className={`max-w-[80%] rounded-lg p-3 ${
                      msg.role === "user"
                        ? "bg-blue-600 text-white"
                        : "bg-card border text-foreground"
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
                  <div className="bg-card border rounded-lg p-3">
                    <div className="flex space-x-1">
                      <div className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce"></div>
                      <div className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce" style={{ animationDelay: "0.1s" }}></div>
                      <div className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce" style={{ animationDelay: "0.2s" }}></div>
                    </div>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* Input - Changed to textarea for better typing experience */}
            <div className="flex gap-2">
              <div className="flex-1 relative">
                <textarea
                  ref={inputRef}
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) {
                      e.preventDefault()
                      sendMessage()
                    }
                  }}
                  placeholder={!sessionId ? "Initializing conversation..." : "Type your message..."}
                  rows={2}
                  className="flex-1 w-full px-4 py-2 border border-input rounded-lg bg-background text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring resize-none disabled:opacity-50 disabled:cursor-not-allowed"
                  disabled={sending || !sessionId || loading}
                  style={{ minHeight: "44px", maxHeight: "120px" }}
                />
                {!sessionId && !loading && (
                  <div className="absolute inset-0 flex items-center justify-center bg-background/80 rounded-lg pointer-events-none">
                    <p className="text-sm text-muted-foreground">Please wait while we initialize your session...</p>
                  </div>
                )}
              </div>
              <Button onClick={sendMessage} disabled={sending || !sessionId || !input.trim() || loading}>
                Send
              </Button>
            </div>

            <div className="flex justify-between items-center pt-4 border-t">
              <Button variant="outline" onClick={onSkip}>
                Skip for Now
              </Button>
              <Button onClick={() => { void handleComplete() }} disabled={!sessionId || messages.length < 4}>
                Complete Profile
              </Button>
            </div>
          </div>

          <div className="lg:col-span-1 space-y-4">
            <LearningPathPreview 
              conversationId={sessionId}
              profileData={profilePreviewData}
              isLoading={profilePreviewLoading}
            />
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
