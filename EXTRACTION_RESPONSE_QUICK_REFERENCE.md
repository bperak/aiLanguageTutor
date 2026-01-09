# Extraction Response - Quick Reference Guide

## What Is It?

The `extraction_response` feature stores the AI's complete assessment and reasoning when extracting profile data from conversations. This provides transparency and enables re-evaluation.

## Where Is It Stored?

- **Database**: `user_profiles.extraction_response` (JSONB column)
- **API**: Returned in `/api/v1/profile/extract` and `/api/v1/profile/data`
- **Frontend**: Displayed in `ProfileDataReview` component

## Structure

```typescript
{
  raw_ai_response: string,              // Full AI JSON response
  extracted_data: {...},                 // Parsed data structure
  model_used: "gpt-4.1",                // Model used
  provider: "openai",                    // AI provider
  extraction_timestamp: string,          // ISO timestamp
  conversation_message_count: number,   // Messages analyzed
  assessment: {
    has_goals: boolean,
    has_previous_knowledge: boolean,
    has_learning_experiences: boolean,
    has_usage_context: boolean,
    current_level_assessed: string | null
  }
}
```

## API Usage

### Extract Profile Data
```typescript
const response = await apiPost("/api/v1/profile/extract", {
  conversation_id: sessionId
})

// Access both profile data and extraction response
const profileData = response.profile_data
const extractionResponse = response.extraction_response
```

### Get Profile Data
```typescript
const response = await apiGet("/api/v1/profile/data")

// extraction_response is included if available
if (response.extraction_response) {
  // Show assessment to user
}
```

## Frontend Display

The assessment is shown as a blue information box with:
- ✓/○ indicators for each section
- Assessed learning level
- Model and timestamp

## Migration

The migration applies automatically on backend startup. To verify:
```sql
SELECT column_name 
FROM information_schema.columns 
WHERE table_name = 'user_profiles' 
  AND column_name = 'extraction_response';
```

## Troubleshooting

### extraction_response is null
- Check if profile was saved before this feature was implemented
- Verify migration was applied
- Check backend logs for extraction errors

### Assessment shows all ○
- Conversation may not have enough information
- Check `raw_ai_response` in database for details
- User may need to provide more information

### Frontend not showing assessment
- Verify `extractionResponse` prop is passed to `ProfileDataReview`
- Check API response includes `extraction_response`
- Verify TypeScript types are correct

## Benefits

1. **Transparency**: Users see what was extracted
2. **Trust**: Shows the assessment process
3. **Debugging**: Helps identify issues
4. **Re-evaluation**: Enables later review
