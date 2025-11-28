"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { apiGet } from "@/lib/api"
import { getToken } from "@/lib/auth"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import UsageDataDashboard from "@/components/profile/UsageDataDashboard"
import Link from "next/link"
import { Button } from "@/components/ui/button"

type Me = {
  username: string
  email: string
  full_name?: string
  native_language?: string
  target_languages?: string[]
  current_level?: string
}

export default function ProfilePage() {
  const router = useRouter()
  const [me, setMe] = useState<Me | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const t = getToken()
    if (!t) {
      router.replace("/login")
      return
    }
    apiGet<Me>("/api/v1/auth/me")
      .then(setMe)
      .catch(() => router.replace("/login"))
      .finally(() => setLoading(false))
  }, [router])

  if (loading || !me) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-gray-900"></div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-white to-slate-50 p-4 sm:p-6">
      <div className="max-w-6xl mx-auto">
        <h1 className="text-2xl sm:text-3xl font-semibold mb-6">Profile</h1>

        <Tabs defaultValue="info" className="space-y-6">
          <TabsList>
            <TabsTrigger value="info">Profile Info</TabsTrigger>
            <TabsTrigger value="usage">Usage Data</TabsTrigger>
            <TabsTrigger value="learning-path">Learning Path</TabsTrigger>
            <TabsTrigger value="settings">Settings</TabsTrigger>
          </TabsList>

          <TabsContent value="info" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Basic Information</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div>
                    <label className="text-sm font-medium text-muted-foreground">Username</label>
                    <p className="text-lg">{me.username}</p>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-muted-foreground">Email</label>
                    <p className="text-lg">{me.email}</p>
                  </div>
                  {me.full_name && (
                    <div>
                      <label className="text-sm font-medium text-muted-foreground">Full Name</label>
                      <p className="text-lg">{me.full_name}</p>
                    </div>
                  )}
                  {me.native_language && (
                    <div>
                      <label className="text-sm font-medium text-muted-foreground">Native Language</label>
                      <p className="text-lg">{me.native_language}</p>
                    </div>
                  )}
                  {me.target_languages && me.target_languages.length > 0 && (
                    <div>
                      <label className="text-sm font-medium text-muted-foreground">Target Languages</label>
                      <p className="text-lg">{me.target_languages.join(", ")}</p>
                    </div>
                  )}
                  {me.current_level && (
                    <div>
                      <label className="text-sm font-medium text-muted-foreground">Current Level</label>
                      <p className="text-lg capitalize">{me.current_level}</p>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>

            <ProfileDataTab />
            <Card>
              <CardHeader>
                <CardTitle>Profile Building</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground mb-4">
                  Complete your profile to get a personalized learning path and better recommendations.
                </p>
                <Link href="/profile/build">
                  <Button>Build or Update Profile</Button>
                </Link>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="usage" className="space-y-4">
            <UsageDataDashboard />
          </TabsContent>

          <TabsContent value="learning-path" className="space-y-4">
            <LearningPathTab />
          </TabsContent>

          <TabsContent value="settings" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Settings</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <Link href="/settings">
                    <Button variant="outline">Go to Settings</Button>
                  </Link>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  )
}

function ProfileDataTab() {
  const [profileData, setProfileData] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    apiGet("/api/v1/profile/data")
      .then(setProfileData)
      .catch(() => {
        // No profile data exists yet
        setProfileData(null)
      })
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <Card>
        <CardContent className="p-6">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900 mx-auto"></div>
        </CardContent>
      </Card>
    )
  }

  if (!profileData) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Profile Data</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground mb-4">
            No profile data found. Complete your profile to see your information here.
          </p>
          <Link href="/profile/build">
            <Button>Complete Profile</Button>
          </Link>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Your Profile Data</CardTitle>
        <p className="text-sm text-muted-foreground">
          Last updated: {new Date(profileData.updated_at).toLocaleDateString()}
        </p>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Learning Goals */}
        <div>
          <h3 className="font-semibold mb-2">Learning Goals</h3>
          <div className="space-y-1">
            {profileData.learning_goals && profileData.learning_goals.length > 0 ? (
              profileData.learning_goals.map((goal: string, idx: number) => (
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
        {profileData.previous_knowledge && (
          <div>
            <h3 className="font-semibold mb-2">Previous Knowledge</h3>
            <div className="space-y-2 text-sm">
              {profileData.previous_knowledge.experience_level && (
                <div>
                  <span className="font-medium">Experience Level: </span>
                  <span className="text-muted-foreground capitalize">
                    {profileData.previous_knowledge.experience_level}
                  </span>
                </div>
              )}
              {profileData.previous_knowledge.years_studying !== undefined && (
                <div>
                  <span className="font-medium">Years Studying: </span>
                  <span className="text-muted-foreground">
                    {profileData.previous_knowledge.years_studying}
                  </span>
                </div>
              )}
              {profileData.previous_knowledge.specific_areas_known?.length > 0 && (
                <div>
                  <span className="font-medium">Areas Known: </span>
                  <span className="text-muted-foreground">
                    {profileData.previous_knowledge.specific_areas_known.join(", ")}
                  </span>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Learning Experiences */}
        {profileData.learning_experiences && (
          <div>
            <h3 className="font-semibold mb-2">Learning Preferences</h3>
            <div className="space-y-2 text-sm">
              {profileData.learning_experiences.preferred_methods?.length > 0 && (
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
                  <span className="text-muted-foreground capitalize">
                    {profileData.learning_experiences.learning_style}
                  </span>
                </div>
              )}
              {profileData.learning_experiences.motivation_level && (
                <div>
                  <span className="font-medium">Motivation Level: </span>
                  <span className="text-muted-foreground capitalize">
                    {profileData.learning_experiences.motivation_level}
                  </span>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Usage Context */}
        {profileData.usage_context && (
          <div>
            <h3 className="font-semibold mb-2">Usage Context</h3>
            <div className="space-y-2 text-sm">
              {profileData.usage_context.contexts?.length > 0 && (
                <div>
                  <span className="font-medium">Contexts: </span>
                  <span className="text-muted-foreground">
                    {profileData.usage_context.contexts.join(", ")}
                  </span>
                </div>
              )}
              {profileData.usage_context.specific_situations?.length > 0 && (
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
        )}

        {/* Additional Notes */}
        {profileData.additional_notes && (
          <div>
            <h3 className="font-semibold mb-2">Additional Notes</h3>
            <p className="text-sm text-muted-foreground">{profileData.additional_notes}</p>
          </div>
        )}

        <div className="pt-4 border-t">
          <Link href="/profile/build">
            <Button variant="outline">Update Profile</Button>
          </Link>
        </div>
      </CardContent>
    </Card>
  )
}

function LearningPathTab() {
  const [learningPath, setLearningPath] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    apiGet("/api/v1/profile/learning-path")
      .then(setLearningPath)
      .catch(() => {
        // No learning path exists yet
        setLearningPath(null)
      })
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <Card>
        <CardContent className="p-6">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900 mx-auto"></div>
        </CardContent>
      </Card>
    )
  }

  if (!learningPath) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Learning Path</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground mb-4">
            No learning path found. Complete your profile to generate a personalized learning path.
          </p>
          <Link href="/profile/build">
            <Button>Complete Profile</Button>
          </Link>
        </CardContent>
      </Card>
    )
  }

  const pathData = learningPath.path_data || {}
  const progressData = learningPath.progress_data || {}
  const steps = pathData.steps || []

  return (
    <Card>
      <CardHeader>
        <CardTitle>{learningPath.path_name || "Learning Path"}</CardTitle>
        <p className="text-sm text-muted-foreground">Version {learningPath.version}</p>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {pathData.description && (
            <p className="text-sm text-muted-foreground">{pathData.description}</p>
          )}
          
          <div className="space-y-2">
            <h3 className="font-semibold">Steps</h3>
            {steps.map((step: any, idx: number) => {
              const isCompleted = progressData.completed_step_ids?.includes(step.step_id)
              const isCurrent = progressData.current_step_id === step.step_id
              
              return (
                <div
                  key={step.step_id || idx}
                  className={`p-3 border rounded-lg ${
                    isCompleted ? "bg-green-50 border-green-200" :
                    isCurrent ? "bg-blue-50 border-blue-200" :
                    "bg-white"
                  }`}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <h4 className="font-medium">{step.title}</h4>
                      <p className="text-sm text-muted-foreground mt-1">{step.description}</p>
                      {step.estimated_duration_days && (
                        <p className="text-xs text-muted-foreground mt-1">
                          Estimated: {step.estimated_duration_days} days
                        </p>
                      )}
                    </div>
                    <div className="ml-4">
                      {isCompleted && <span className="text-xs text-green-600">✓ Completed</span>}
                      {isCurrent && <span className="text-xs text-blue-600">Current</span>}
                    </div>
                  </div>
                </div>
              )
            })}
          </div>

          {progressData.progress_percentage !== undefined && (
            <div className="mt-4">
              <div className="flex justify-between text-sm mb-2">
                <span>Progress</span>
                <span>{Math.round(progressData.progress_percentage)}%</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className="bg-blue-600 h-2 rounded-full transition-all"
                  style={{ width: `${progressData.progress_percentage}%` }}
                ></div>
              </div>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
