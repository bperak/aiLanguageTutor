"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { apiGet } from "@/lib/api"
import { ChevronDown, ChevronUp, Lightbulb } from "lucide-react"

interface PersonalizationSuggestionsProps {
  conversationId: string | null
  onSuggestionClick?: (suggestion: string) => void
}

export default function PersonalizationSuggestions({
  conversationId,
  onSuggestionClick,
}: PersonalizationSuggestionsProps) {
  const [suggestions, setSuggestions] = useState<string[]>([])
  const [loading, setLoading] = useState(false)
  const [isExpanded, setIsExpanded] = useState(true)

  useEffect(() => {
    if (conversationId) {
      loadSuggestions()
    }
  }, [conversationId])

  const loadSuggestions = async () => {
    if (!conversationId) return
    setLoading(true)
    try {
      const data = await apiGet<{ suggestions: string[] }>(
        `/api/v1/profile/suggestions?conversation_id=${conversationId}`
      )
      setSuggestions(data.suggestions || [])
    } catch (err) {
      console.error("Failed to load suggestions:", err)
      // Fallback suggestions
      setSuggestions([
        "Example learning goal: 'I want to have basic conversations when traveling'",
        "Example learning goal: 'I want to read Japanese manga or books'",
        "Learning method suggestion: Try flashcards for vocabulary",
        "Learning method suggestion: Practice with conversation partners",
      ])
    } finally {
      setLoading(false)
    }
  }

  if (suggestions.length === 0 && !loading) {
    return null
  }

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Lightbulb className="w-4 h-4 text-yellow-500" />
            <CardTitle className="text-sm">Personalization Suggestions</CardTitle>
          </div>
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="text-muted-foreground hover:text-foreground"
          >
            {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </button>
        </div>
      </CardHeader>
      {isExpanded && (
        <CardContent className="pt-0">
          {loading ? (
            <div className="text-sm text-muted-foreground">Loading suggestions...</div>
          ) : (
            <div className="space-y-2">
              {suggestions.map((suggestion, idx) => (
                <button
                  key={idx}
                  onClick={() => onSuggestionClick?.(suggestion)}
                  className="w-full text-left text-sm p-2 rounded-md hover:bg-slate-100 border border-slate-200 transition-colors"
                >
                  {suggestion}
                </button>
              ))}
            </div>
          )}
        </CardContent>
      )}
    </Card>
  )
}

