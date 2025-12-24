"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { useRouter } from "next/navigation"

interface NextStepWidgetProps {
  nextStep?: {
    step_id?: string
    title?: string
    description?: string
    can_do_descriptors?: string[]
  }
}

export default function NextStepWidget({ nextStep }: NextStepWidgetProps) {
  const router = useRouter()

  if (!nextStep) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Next Step</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground mb-4">Complete your profile to see your personalized learning path.</p>
          <Button onClick={() => router.push("/profile/build")} className="w-full">
            Complete Profile
          </Button>
        </CardContent>
      </Card>
    )
  }

  const handleStart = () => {
    // Navigate to appropriate learning activity
    if (nextStep.can_do_descriptors && nextStep.can_do_descriptors.length > 0) {
      router.push(`/cando/${nextStep.can_do_descriptors[0]}`)
    } else {
      router.push("/profile")
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Next Step</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          <div>
            <h3 className="font-semibold text-lg">{nextStep.title}</h3>
            <p className="text-sm text-muted-foreground mt-1">{nextStep.description}</p>
          </div>
          <Button onClick={handleStart} className="w-full">
            Start Now
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}

