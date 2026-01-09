# Frontend Integration Guide for Extraction Response

## Overview
The backend now returns `extraction_response` containing the AI's assessment and reasoning. This guide shows how to integrate it into the frontend.

## API Response Structure

### `/api/v1/profile/extract` Response
```typescript
{
  profile_data: {
    learning_goals: string[],
    previous_knowledge: {...},
    learning_experiences: {...},
    usage_context: {...},
    additional_notes?: string
  },
  extraction_response: {
    raw_ai_response: string,           // Full AI JSON response
    extracted_data: {...},             // Parsed data structure
    model_used: "gpt-4.1",
    provider: "openai",
    extraction_timestamp: string,      // ISO timestamp
    conversation_message_count: number,
    assessment: {
      has_goals: boolean,
      has_previous_knowledge: boolean,
      has_learning_experiences: boolean,
      has_usage_context: boolean,
      current_level_assessed: string | null
    }
  }
}
```

### `/api/v1/profile/data` Response
```typescript
{
  user_id: string,
  learning_goals: string[],
  previous_knowledge: {...},
  learning_experiences: {...},
  usage_context: {...},
  additional_notes?: string,
  extraction_response?: {...},  // Same structure as above
  profile_building_conversation_id?: string,
  created_at: string,
  updated_at: string
}
```

## Frontend Integration Options

### Option 1: Display Assessment Summary (Recommended)
Show a summary card with what was extracted:

```typescript
// In ProfileDataReview.tsx
{extractionResponse && (
  <Card className="mt-4 border-blue-200 bg-blue-50">
    <CardHeader>
      <CardTitle className="text-sm">Extraction Assessment</CardTitle>
    </CardHeader>
    <CardContent>
      <div className="space-y-2 text-sm">
        <div className="flex items-center gap-2">
          <span className={extractionResponse.assessment.has_goals ? "text-green-600" : "text-gray-400"}>
            {extractionResponse.assessment.has_goals ? "✓" : "○"}
          </span>
          <span>Learning Goals</span>
        </div>
        <div className="flex items-center gap-2">
          <span className={extractionResponse.assessment.has_previous_knowledge ? "text-green-600" : "text-gray-400"}>
            {extractionResponse.assessment.has_previous_knowledge ? "✓" : "○"}
          </span>
          <span>Previous Knowledge</span>
        </div>
        <div className="flex items-center gap-2">
          <span className={extractionResponse.assessment.has_learning_experiences ? "text-green-600" : "text-gray-400"}>
            {extractionResponse.assessment.has_learning_experiences ? "✓" : "○"}
          </span>
          <span>Learning Experiences</span>
        </div>
        <div className="flex items-center gap-2">
          <span className={extractionResponse.assessment.has_usage_context ? "text-green-600" : "text-gray-400"}>
            {extractionResponse.assessment.has_usage_context ? "✓" : "○"}
          </span>
          <span>Usage Context</span>
        </div>
        {extractionResponse.assessment.current_level_assessed && (
          <div className="mt-2 pt-2 border-t">
            <span className="font-medium">Assessed Level: </span>
            <span>{extractionResponse.assessment.current_level_assessed}</span>
          </div>
        )}
      </div>
    </CardContent>
  </Card>
)}
```

### Option 2: Show Full Extraction Details (Advanced)
Add an expandable section showing the full extraction response:

```typescript
// Add state for showing details
const [showExtractionDetails, setShowExtractionDetails] = useState(false)

// In the component
{extractionResponse && (
  <Card className="mt-4">
    <CardHeader>
      <div className="flex items-center justify-between">
        <CardTitle className="text-sm">How We Assessed Your Profile</CardTitle>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setShowExtractionDetails(!showExtractionDetails)}
        >
          {showExtractionDetails ? "Hide" : "Show"} Details
        </Button>
      </div>
    </CardHeader>
    {showExtractionDetails && (
      <CardContent>
        <div className="space-y-4">
          <div>
            <h4 className="font-medium text-sm mb-2">Assessment Summary</h4>
            <pre className="text-xs bg-gray-100 p-2 rounded overflow-auto">
              {JSON.stringify(extractionResponse.assessment, null, 2)}
            </pre>
          </div>
          <div>
            <h4 className="font-medium text-sm mb-2">Extraction Timestamp</h4>
            <p className="text-xs text-muted-foreground">
              {new Date(extractionResponse.extraction_timestamp).toLocaleString()}
            </p>
          </div>
          <div>
            <h4 className="font-medium text-sm mb-2">Model Used</h4>
            <p className="text-xs text-muted-foreground">
              {extractionResponse.model_used} ({extractionResponse.provider})
            </p>
          </div>
        </div>
      </CardContent>
    )}
  </Card>
)}
```

### Option 3: Update TypeScript Types
Update the ProfileData type to include extraction_response:

```typescript
// In ProfileDataReview.tsx or a shared types file
type ExtractionResponse = {
  raw_ai_response: string
  extracted_data: any
  model_used: string
  provider: string
  extraction_timestamp: string
  conversation_message_count: number
  assessment: {
    has_goals: boolean
    has_previous_knowledge: boolean
    has_learning_experiences: boolean
    has_usage_context: boolean
    current_level_assessed: string | null
  }
}

type ProfileDataReviewProps = {
  profileData: ProfileData
  extractionResponse?: ExtractionResponse  // Add this
  conversationId: string
  onApprove: (profileData: ProfileData) => Promise<void>
  onEdit: () => void
}
```

## Implementation Steps

1. **Update ProfileBuildingChat.tsx**:
   - Store `extraction_response` from `/api/v1/profile/extract` response
   - Pass it to `ProfileDataReview` component

2. **Update ProfileDataReview.tsx**:
   - Accept `extractionResponse` prop
   - Display assessment summary (Option 1) or full details (Option 2)

3. **Update TypeScript Types**:
   - Add `ExtractionResponse` type definition
   - Update component props

## Benefits

1. **Transparency**: Users can see what information was extracted
2. **Trust**: Shows the assessment process
3. **Debugging**: Helps identify if extraction missed information
4. **Re-evaluation**: Users can review and request re-assessment if needed

## Example Implementation

See the code examples above for a complete implementation. The assessment summary (Option 1) is recommended as it's user-friendly and informative without being overwhelming.
