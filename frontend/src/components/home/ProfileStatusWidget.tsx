"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { useRouter } from "next/navigation"
import Link from "next/link"

interface ProfileStatusWidgetProps {
  profileCompleted: boolean
  profileSkipped: boolean
  profileData?: {
    learning_goals?: string[]
    previous_knowledge?: {
      experience_level?: string
    }
    learning_experiences?: {
      learning_style?: string
      preferred_methods?: string[]
    }
  }
}

export default function ProfileStatusWidget({
  profileCompleted,
  profileSkipped,
  profileData,
}: ProfileStatusWidgetProps) {
  const router = useRouter()

  if (profileSkipped) {
    return (
      <Card className="border-amber-200 bg-amber-50">
        <CardHeader>
          <CardTitle className="text-lg">Profile Building</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground mb-4">
            Complete your profile to unlock personalized learning paths and better recommendations.
          </p>
          <Link href="/profile/build">
            <Button className="w-full">Build Your Profile</Button>
          </Link>
        </CardContent>
      </Card>
    )
  }

  if (!profileCompleted) {
    return (
      <Card className="border-blue-200 bg-blue-50">
        <CardHeader>
          <CardTitle className="text-lg">Complete Your Profile</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground mb-4">
            Complete your profile to unlock personalized learning paths and better recommendations.
          </p>
          <Link href="/profile/build">
            <Button className="w-full">Complete Profile</Button>
          </Link>
        </CardContent>
      </Card>
    )
  }

  // Profile is completed - show summary
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">Your Profile</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {profileData?.learning_goals && profileData.learning_goals.length > 0 && (
          <div>
            <p className="text-xs font-medium text-muted-foreground mb-1">Learning Goals</p>
            <p className="text-sm">
              {profileData.learning_goals.slice(0, 2).join(", ")}
              {profileData.learning_goals.length > 2 && "..."}
            </p>
          </div>
        )}
        {profileData?.previous_knowledge?.experience_level && (
          <div>
            <p className="text-xs font-medium text-muted-foreground mb-1">Level</p>
            <p className="text-sm capitalize">{profileData.previous_knowledge.experience_level}</p>
          </div>
        )}
        {profileData?.learning_experiences?.learning_style && (
          <div>
            <p className="text-xs font-medium text-muted-foreground mb-1">Learning Style</p>
            <p className="text-sm capitalize">{profileData.learning_experiences.learning_style}</p>
          </div>
        )}
        <div className="pt-2 border-t">
          <Link href="/profile/build">
            <Button variant="outline" size="sm" className="w-full">
              Update Profile
            </Button>
          </Link>
        </div>
      </CardContent>
    </Card>
  )
}

