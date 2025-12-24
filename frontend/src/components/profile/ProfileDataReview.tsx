"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { useToast } from "@/components/ToastProvider"

type ProfileData = {
  learning_goals: string[]
  previous_knowledge: {
    has_experience: boolean
    experience_level?: string
    years_studying?: number
    formal_classes: boolean
    self_study: boolean
    specific_areas_known: string[]
    specific_areas_unknown: string[]
  }
  learning_experiences: {
    preferred_methods: string[]
    methods_that_worked: string[]
    methods_that_didnt_work: string[]
    learning_style?: string
    study_schedule?: string
    motivation_level?: string
    challenges_faced: string[]
  }
  usage_context: {
    contexts: string[]
    urgency?: string
    specific_situations: string[]
    target_date?: string
  }
  additional_notes?: string
}

type ProfileDataReviewProps = {
  profileData: ProfileData
  conversationId: string
  onApprove: (profileData: ProfileData) => Promise<void>
  onEdit: () => void
}

export default function ProfileDataReview({
  profileData,
  conversationId,
  onApprove,
  onEdit,
}: ProfileDataReviewProps) {
  const { showToast } = useToast()
  const router = useRouter()
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)

  const handleApprove = async () => {
    setSaving(true)
    try {
      // The parent owns the actual save to avoid duplicate /profile/complete calls.
      await onApprove(profileData)
      setSaved(true)
      showToast("Profile saved! Generating your learning path...", "success")
    } catch (err: any) {
      showToast(err?.message || "Failed to save profile", "error")
    } finally {
      setSaving(false)
    }
  }

  if (saved) {
    return (
      <div className="space-y-4">
        <Card className="border-green-200 bg-green-50">
          <CardHeader>
            <CardTitle>Profile Completed! 🎉</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm text-muted-foreground">
              Your profile has been saved and your personalized learning path is being generated.
            </p>
            <div className="p-4 bg-white rounded-lg border">
              <p className="text-sm font-medium mb-2">What's next on your Home page:</p>
              <ul className="text-sm space-y-1 list-disc list-inside text-muted-foreground">
                <li>View your personalized learning path</li>
                <li>See your next recommended learning steps</li>
                <li>Track your progress</li>
                <li>Get customized AI guidance</li>
              </ul>
            </div>
            <Button onClick={() => router.push("/")} className="w-full">
              Go to Home
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>Review Your Profile Information</CardTitle>
          <p className="text-sm text-muted-foreground">
            Please review the information we extracted from our conversation. You can edit it or approve it.
          </p>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Learning Goals */}
          <div>
            <h3 className="font-semibold mb-2">Learning Goals</h3>
            <div className="space-y-1">
              {profileData.learning_goals.length > 0 ? (
                profileData.learning_goals.map((goal, idx) => (
                  <div key={idx} className="flex items-center gap-2">
                    <span className="text-sm">•</span>
                    <span className="text-sm">{goal}</span>
                  </div>
                ))
              ) : (
                <p className="text-sm text-muted-foreground">No goals specified</p>
              )}
            </div>
          </div>

          {/* Previous Knowledge */}
          <div>
            <h3 className="font-semibold mb-2">Previous Knowledge</h3>
            <div className="space-y-2 text-sm">
              <div>
                <span className="font-medium">Experience Level: </span>
                <span className="text-muted-foreground">
                  {profileData.previous_knowledge.experience_level || "Not specified"}
                </span>
              </div>
              {profileData.previous_knowledge.years_studying !== undefined && (
                <div>
                  <span className="font-medium">Years Studying: </span>
                  <span className="text-muted-foreground">
                    {profileData.previous_knowledge.years_studying}
                  </span>
                </div>
              )}
              {profileData.previous_knowledge.specific_areas_known.length > 0 && (
                <div>
                  <span className="font-medium">Areas Known: </span>
                  <span className="text-muted-foreground">
                    {profileData.previous_knowledge.specific_areas_known.join(", ")}
                  </span>
                </div>
              )}
            </div>
          </div>

          {/* Learning Experiences */}
          <div>
            <h3 className="font-semibold mb-2">Learning Preferences</h3>
            <div className="space-y-2 text-sm">
              {profileData.learning_experiences.preferred_methods.length > 0 && (
                <div>
                  <span className="font-medium">Preferred Methods: </span>
                  <span className="text-muted-foreground">
                    {profileData.learning_experiences.preferred_methods.join(", ")}
                  </span>
                </div>
              )}
              {profileData.learning_experiences.learning_style && (
                <div>
                  <span className="font-medium">Learning Style: </span>
                  <span className="text-muted-foreground">
                    {profileData.learning_experiences.learning_style}
                  </span>
                </div>
              )}
              {profileData.learning_experiences.motivation_level && (
                <div>
                  <span className="font-medium">Motivation Level: </span>
                  <span className="text-muted-foreground">
                    {profileData.learning_experiences.motivation_level}
                  </span>
                </div>
              )}
            </div>
          </div>

          {/* Usage Context */}
          <div>
            <h3 className="font-semibold mb-2">Usage Context</h3>
            <div className="space-y-2 text-sm">
              {profileData.usage_context.contexts.length > 0 && (
                <div>
                  <span className="font-medium">Contexts: </span>
                  <span className="text-muted-foreground">
                    {profileData.usage_context.contexts.join(", ")}
                  </span>
                </div>
              )}
              {profileData.usage_context.specific_situations.length > 0 && (
                <div>
                  <span className="font-medium">Specific Situations: </span>
                  <span className="text-muted-foreground">
                    {profileData.usage_context.specific_situations.join(", ")}
                  </span>
                </div>
              )}
              {profileData.usage_context.target_date && (
                <div>
                  <span className="font-medium">Target Date: </span>
                  <span className="text-muted-foreground">
                    {profileData.usage_context.target_date}
                  </span>
                </div>
              )}
            </div>
          </div>

          {/* Additional Notes */}
          {profileData.additional_notes && (
            <div>
              <h3 className="font-semibold mb-2">Additional Notes</h3>
              <p className="text-sm text-muted-foreground">{profileData.additional_notes}</p>
            </div>
          )}

          {/* Actions */}
          <div className="flex justify-between pt-4 border-t">
            <Button variant="outline" onClick={onEdit} disabled={saving}>
              Edit
            </Button>
            <Button onClick={handleApprove} disabled={saving}>
              {saving ? "Saving..." : "Approve & Save"}
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

