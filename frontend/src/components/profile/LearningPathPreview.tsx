"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Info, CheckCircle2, Circle } from "lucide-react"

interface LearningPathPreviewProps {
  conversationId?: string | null
  profileData?: any | null
  isLoading?: boolean
}

export default function LearningPathPreview({ 
  conversationId, 
  profileData,
  isLoading = false
}: LearningPathPreviewProps) {
  const isBuilding = !!(conversationId && profileData)

  const hasData = (field: string) => {
    if (!profileData) return false
    const value = profileData[field]
    if (Array.isArray(value)) return value.length > 0
    if (typeof value === 'object' && value !== null) {
      return Object.keys(value).length > 0 && Object.values(value).some(v => {
        if (Array.isArray(v)) return v.length > 0
        if (typeof v === 'string') return v.trim().length > 0
        return v !== null && v !== undefined
      })
    }
    return !!value && String(value).trim().length > 0
  }

  const getFieldValue = (field: string, subField?: string) => {
    if (!profileData) return null
    const value = profileData[field]
    if (subField && typeof value === 'object' && value !== null) {
      return value[subField]
    }
    return value
  }

  const formatArrayValue = (value: any): string => {
    if (Array.isArray(value)) {
      return value.filter(v => v && String(v).trim()).join(', ')
    }
    if (typeof value === 'string') {
      return value
    }
    return String(value || '')
  }

  return (
    <Card className="border-blue-200 bg-blue-50 dark:bg-blue-950/20 dark:border-blue-800">
      <CardHeader>
        <CardTitle className="text-lg flex items-center gap-2">
          <Info className="h-4 w-4" />
          Your Learning Path Preview
          {(isBuilding || isLoading) && (
            <span className="ml-auto text-xs font-normal text-blue-600 dark:text-blue-400 animate-pulse">
              {isLoading ? "Updating..." : "Building..."}
            </span>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {!isBuilding ? (
          <>
            <p className="text-sm text-muted-foreground">
              After you complete your profile, we'll generate a personalized learning path based on:
            </p>
            <ul className="text-sm space-y-2 list-disc list-inside text-muted-foreground">
              <li>Your learning goals</li>
              <li>Your current level and experience</li>
              <li>Your preferred learning methods</li>
              <li>Where and when you'll use the language</li>
            </ul>
          </>
        ) : (
          <div className="space-y-4">
            {/* Learning Goals */}
            <div>
              <div className="flex items-center gap-2 mb-2">
                {hasData('learning_goals') ? (
                  <CheckCircle2 className="h-4 w-4 text-green-600 dark:text-green-400" />
                ) : (
                  <Circle className="h-4 w-4 text-muted-foreground" />
                )}
                <p className="text-sm font-medium">Learning Goals</p>
              </div>
              {hasData('learning_goals') ? (
                <ul className="text-sm space-y-1 ml-6 text-muted-foreground">
                  {Array.isArray(profileData.learning_goals) && profileData.learning_goals.length > 0 ? (
                    profileData.learning_goals.slice(0, 3).map((goal: string, idx: number) => (
                      <li key={idx} className="list-none">• {goal}</li>
                    ))
                  ) : (
                    <li className="text-xs italic list-none">Goals identified</li>
                  )}
                </ul>
              ) : (
                <p className="text-xs text-muted-foreground ml-6 italic">Not yet identified</p>
              )}
            </div>

            {/* Previous Knowledge */}
            <div>
              <div className="flex items-center gap-2 mb-2">
                {hasData('previous_knowledge') ? (
                  <CheckCircle2 className="h-4 w-4 text-green-600 dark:text-green-400" />
                ) : (
                  <Circle className="h-4 w-4 text-muted-foreground" />
                )}
                <p className="text-sm font-medium">Current Level</p>
              </div>
              {hasData('previous_knowledge') ? (
                <div className="text-sm ml-6 text-muted-foreground space-y-1">
                  {getFieldValue('previous_knowledge', 'proficiency_level') && (
                    <p>• Level: {getFieldValue('previous_knowledge', 'proficiency_level')}</p>
                  )}
                  {getFieldValue('previous_knowledge', 'experience_level') && (
                    <p>• Experience: {getFieldValue('previous_knowledge', 'experience_level')}</p>
                  )}
                  {getFieldValue('previous_knowledge', 'years_studying') !== undefined && (
                    <p>• Years: {getFieldValue('previous_knowledge', 'years_studying')}</p>
                  )}
                  {getFieldValue('previous_knowledge', 'years_of_study') !== undefined && (
                    <p>• Years: {getFieldValue('previous_knowledge', 'years_of_study')}</p>
                  )}
                  {getFieldValue('previous_knowledge', 'specific_areas_known') && (
                    <p>• Areas: {formatArrayValue(getFieldValue('previous_knowledge', 'specific_areas_known')).substring(0, 50)}{formatArrayValue(getFieldValue('previous_knowledge', 'specific_areas_known')).length > 50 ? '...' : ''}</p>
                  )}
                </div>
              ) : (
                <p className="text-xs text-muted-foreground ml-6 italic">Not yet identified</p>
              )}
            </div>

            {/* Learning Experiences */}
            <div>
              <div className="flex items-center gap-2 mb-2">
                {hasData('learning_experiences') ? (
                  <CheckCircle2 className="h-4 w-4 text-green-600 dark:text-green-400" />
                ) : (
                  <Circle className="h-4 w-4 text-muted-foreground" />
                )}
                <p className="text-sm font-medium">Learning Preferences</p>
              </div>
              {hasData('learning_experiences') ? (
                <div className="text-sm ml-6 text-muted-foreground space-y-1">
                  {getFieldValue('learning_experiences', 'preferred_methods') && (
                    <p>• Methods: {formatArrayValue(getFieldValue('learning_experiences', 'preferred_methods')).substring(0, 50)}{formatArrayValue(getFieldValue('learning_experiences', 'preferred_methods')).length > 50 ? '...' : ''}</p>
                  )}
                  {getFieldValue('learning_experiences', 'learning_style') && (
                    <p>• Style: {getFieldValue('learning_experiences', 'learning_style')}</p>
                  )}
                  {getFieldValue('learning_experiences', 'time_available') && (
                    <p>• Time: {getFieldValue('learning_experiences', 'time_available')}</p>
                  )}
                  {getFieldValue('learning_experiences', 'study_schedule') && (
                    <p>• Schedule: {getFieldValue('learning_experiences', 'study_schedule')}</p>
                  )}
                </div>
              ) : (
                <p className="text-xs text-muted-foreground ml-6 italic">Not yet identified</p>
              )}
            </div>

            {/* Usage Context */}
            <div>
              <div className="flex items-center gap-2 mb-2">
                {hasData('usage_context') ? (
                  <CheckCircle2 className="h-4 w-4 text-green-600 dark:text-green-400" />
                ) : (
                  <Circle className="h-4 w-4 text-muted-foreground" />
                )}
                <p className="text-sm font-medium">Usage Context</p>
              </div>
              {hasData('usage_context') ? (
                <div className="text-sm ml-6 text-muted-foreground space-y-1">
                  {getFieldValue('usage_context', 'contexts') && (
                    <p>• Contexts: {formatArrayValue(getFieldValue('usage_context', 'contexts')).substring(0, 50)}{formatArrayValue(getFieldValue('usage_context', 'contexts')).length > 50 ? '...' : ''}</p>
                  )}
                  {getFieldValue('usage_context', 'specific_situations') && (
                    <p>• Situations: {formatArrayValue(getFieldValue('usage_context', 'specific_situations')).substring(0, 50)}{formatArrayValue(getFieldValue('usage_context', 'specific_situations')).length > 50 ? '...' : ''}</p>
                  )}
                  {getFieldValue('usage_context', 'urgency') && (
                    <p>• Urgency: {getFieldValue('usage_context', 'urgency')}</p>
                  )}
                </div>
              ) : (
                <p className="text-xs text-muted-foreground ml-6 italic">Not yet identified</p>
              )}
            </div>
          </div>
        )}

        <div className="pt-3 border-t">
          <p className="text-xs font-medium text-muted-foreground mb-2">What you'll see on Home:</p>
          <div className="space-y-1 text-xs text-muted-foreground">
            <p>✓ Personalized learning steps</p>
            <p>✓ Progress tracking</p>
            <p>✓ Next recommended activities</p>
            <p>✓ Customized AI guidance</p>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
