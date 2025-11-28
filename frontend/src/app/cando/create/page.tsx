"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { createCanDo } from "@/lib/api"
import { Button } from "@/components/ui/button"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { useToast } from "@/components/ToastProvider"

export default function CreateCanDoPage() {
  const router = useRouter()
  const { showToast } = useToast()
  
  const [descriptionEn, setDescriptionEn] = useState("")
  const [descriptionJa, setDescriptionJa] = useState("")
  const [isCreating, setIsCreating] = useState(false)
  const [error, setError] = useState<string | null>(null)
  
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!descriptionEn.trim() && !descriptionJa.trim()) {
      setError("Please provide at least one description (English or Japanese)")
      return
    }
    
    setIsCreating(true)
    setError(null)
    
    try {
      const result = await createCanDo(
        descriptionEn.trim() || undefined,
        descriptionJa.trim() || undefined
      )
      
      if (result.success && result.canDo) {
        showToast("CanDo created successfully! Processing embeddings and relationships...", "success")
        // Redirect to the created CanDo detail page
        router.push(`/cando/${encodeURIComponent(result.canDo.uid)}`)
      } else {
        setError("Failed to create CanDo. Please try again.")
      }
    } catch (err: any) {
      const errorMessage = err?.response?.data?.detail || err?.message || "Failed to create CanDo"
      setError(errorMessage)
      showToast(errorMessage, "error")
    } finally {
      setIsCreating(false)
    }
  }
  
  return (
    <div className="max-w-3xl mx-auto px-4 py-8">
      <Card className="p-6">
        <CardHeader>
          <CardTitle className="text-2xl">Create New CanDo</CardTitle>
        </CardHeader>
        <CardContent>
        <p className="text-gray-600 mb-6">
          Create a new CanDo descriptor. Provide at least one description (English or Japanese).
          The system will automatically:
        </p>
        
        <ul className="list-disc list-inside text-sm text-gray-600 mb-6 space-y-1">
          <li>Translate the description if only one language is provided</li>
          <li>Generate titles in both languages</li>
          <li>Infer level, topic, skill domain, and type from the description</li>
          <li>Generate embeddings for semantic similarity</li>
          <li>Create similarity relationships with other CanDo-s</li>
        </ul>
        
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="descriptionEn" className="block text-sm font-medium text-gray-700 mb-2">
              English Description (Optional)
            </label>
            <textarea
              id="descriptionEn"
              value={descriptionEn}
              onChange={(e) => setDescriptionEn(e.target.value)}
              placeholder="e.g., Can talk about travel and transportation..."
              className="w-full border rounded-md px-3 py-2 min-h-[120px] focus:outline-none focus:ring-2 focus:ring-blue-500"
              disabled={isCreating}
            />
          </div>
          
          <div>
            <label htmlFor="descriptionJa" className="block text-sm font-medium text-gray-700 mb-2">
              Japanese Description (Optional)
            </label>
            <textarea
              id="descriptionJa"
              value={descriptionJa}
              onChange={(e) => setDescriptionJa(e.target.value)}
              placeholder="例：旅行と交通について話すことができる..."
              className="w-full border rounded-md px-3 py-2 min-h-[120px] focus:outline-none focus:ring-2 focus:ring-blue-500"
              disabled={isCreating}
            />
          </div>
          
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
              {error}
            </div>
          )}
          
          <div className="flex gap-3">
            <Button
              type="submit"
              disabled={isCreating || (!descriptionEn.trim() && !descriptionJa.trim())}
              className="flex-1"
            >
              {isCreating ? "Creating..." : "Create CanDo"}
            </Button>
            <Button
              type="button"
              variant="outline"
              onClick={() => router.back()}
              disabled={isCreating}
            >
              Cancel
            </Button>
          </div>
        </form>
        
        {isCreating && (
          <div className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded">
            <p className="text-sm text-blue-700">
              Creating CanDo and processing... This may take a moment as the system:
            </p>
            <ul className="list-disc list-inside text-sm text-blue-600 mt-2 space-y-1">
              <li>Translates descriptions (if needed)</li>
              <li>Generates titles using AI</li>
              <li>Infers metadata fields</li>
              <li>Generates embeddings</li>
              <li>Creates similarity relationships</li>
            </ul>
          </div>
        )}
        </CardContent>
      </Card>
    </div>
  )
}

