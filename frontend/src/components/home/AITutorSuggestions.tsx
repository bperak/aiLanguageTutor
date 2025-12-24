"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { useRouter } from "next/navigation"

interface AITutorSuggestionsProps {
  suggestions?: string[]
}

export default function AITutorSuggestions({ suggestions }: AITutorSuggestionsProps) {
  const router = useRouter()

  const defaultSuggestions = [
    "Complete your next learning step",
    "Review previous lessons",
    "Start a new CanDo session"
  ]

  const items = suggestions || defaultSuggestions

  const handleSuggestion = (suggestion: string) => {
    if (suggestion.includes("CanDo")) {
      router.push("/cando")
    } else if (suggestion.includes("profile") || suggestion.toLowerCase().includes("complete your profile")) {
      router.push("/profile/build")
    } else if (suggestion.includes("review")) {
      router.push("/srs")
    } else {
      router.push("/")
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Suggestions</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-2">
          {items.map((suggestion, idx) => (
            <Button
              key={idx}
              variant="outline"
              className="w-full text-left justify-start"
              onClick={() => handleSuggestion(suggestion)}
            >
              {suggestion}
            </Button>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}

