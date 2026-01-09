# Pre-Lesson Kit Integration Testing Guide

## Overview

The pre-lesson kit integration automatically fetches and integrates pre-lesson preparation materials (words, grammar patterns, fixed phrases) from a user's learning path into CanDo lesson compilation.

## Prerequisites

1. **User must be logged in** - Pre-lesson kit is only fetched when a `user_id` is available
2. **User must have a learning path** - The learning path must contain a step for the CanDo with a pre-lesson kit
3. **Backend must be running** - Docker containers must be active

## Testing Steps

### 1. Login

```bash
# Login via API
curl -X POST "https://ailanguagetutor.syntagent.com/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"admin_bperak","password":"Teachable1A"}'
```

Or login via the web UI at: https://ailanguagetutor.syntagent.com/login

### 2. Navigate to CanDo Lesson Page

Navigate to a CanDo lesson page, for example:
- https://ailanguagetutor.syntagent.com/cando/JFまるごと:336

### 3. Check Browser Console

Open browser console (F12) and look for these messages:

#### During Compilation:
- `👤 User ID for kit integration: {userId}` - Confirms user ID is available
- `🟦 Compile status: {prelesson_kit_available: true/false}` - Shows if kit was found
- `📊 Pre-lesson kit usage: {...}` - Shows usage statistics after compilation

#### When Loading Existing Lesson:
- `📦 Pre-lesson kit available (from existing lesson): true/false`
- `📊 Pre-lesson kit usage (from existing lesson): {...}`

### 4. Verify UI Display

The UI should show a "Pre-Lesson Kit Integration" card with:
- **Kit Availability Badge**: "✓ Kit Available" or "No Kit Found"
- **Usage Statistics**:
  - Words: X / Y used (Z required)
  - Grammar: X / Y used (Z required)
  - Phrases: X / Y used (Z required)
- **Overall Usage**: Percentage and requirement status

### 5. Check Backend Logs

```bash
docker logs ai-tutor-backend --tail 100 | grep -i "prelesson\|kit"
```

Expected log messages:
- `compile_lesson_v2_stream_fetching_kit` - Kit fetch initiated
- `compile_lesson_v2_stream_kit_found` - Kit found in learning path
- `compile_lesson_v2_stream_kit_not_found` - No kit found (normal if not in learning path)
- `prelesson_kit_fetched_from_path` - Kit successfully fetched
- `prelesson_kit_integrated_into_compilation` - Kit integrated into lesson
- `prelesson_kit_usage_tracked` - Usage statistics calculated
- `prelesson_kit_requirements_not_met` - Warning if requirements not met

### 6. Test Compilation Flow

1. **Trigger Compilation**:
   - Click "Regenerate" button on an existing lesson
   - Or navigate to a CanDo without an existing lesson

2. **Watch Console**:
   - User ID should be logged
   - Kit availability status should appear
   - Usage statistics should appear after compilation completes

3. **Verify Storage**:
   - Pre-lesson kit info is stored in `lesson_plan->lesson->meta->prelesson_kit_usage`
   - Pre-lesson kit availability is stored in `lesson_plan->lesson->meta->prelesson_kit_available`

## Expected Behavior

### When Kit is Available:
- ✅ Kit is fetched from user's learning path
- ✅ Kit context is integrated into compilation prompts
- ✅ Usage statistics are calculated and stored
- ✅ UI displays kit information card
- ✅ Console shows kit availability and usage

### When Kit is Not Available:
- ⚠️ Compilation continues without kit
- ⚠️ UI shows "No Kit Found" badge
- ⚠️ Console logs indicate kit not found
- ✅ Lesson compiles successfully (kit is optional)

## Troubleshooting

### Kit Not Found
- **Check**: User has a learning path with this CanDo
- **Check**: Learning path step has a pre-lesson kit generated
- **Check**: User ID is correctly passed to compilation endpoint

### Usage Statistics Not Showing
- **Check**: Lesson was compiled with a kit (not just loaded)
- **Check**: Backend logs show `prelesson_kit_usage_tracked`
- **Check**: Browser console for usage data

### UI Card Not Displaying
- **Check**: `prelessonKitAvailable !== null || prelessonKitUsage` condition
- **Check**: Browser console for kit data extraction
- **Check**: Lesson metadata contains `prelesson_kit_usage` or `prelesson_kit_available`

## Automated Testing

Use the test script:
```bash
./scripts/test_prelesson_kit.sh
```

Or manually test with:
```bash
# Set environment variables
export BASE_URL="https://ailanguagetutor.syntagent.com"
export CAN_DO_ID="JFまるごと:336"
export USERNAME="admin_bperak"
export PASSWORD="Teachable1A"

# Run test
./scripts/test_prelesson_kit.sh
```

## Code Locations

### Backend:
- **Kit Fetching**: `backend/app/services/cando_v2_compile_service.py::_fetch_prelesson_kit_from_path`
- **Kit Integration**: `backend/app/services/cando_v2_compile_service.py::compile_lessonroot`
- **Usage Tracking**: `backend/app/services/cando_v2_compile_service.py::_track_kit_usage`
- **API Endpoint**: `backend/app/api/v1/endpoints/cando.py::compile_lesson_v2_stream`

### Frontend:
- **Kit Display**: `frontend/src/app/cando/[canDoId]/page.tsx`
- **Kit Extraction**: `frontend/src/app/cando/[canDoId]/page.tsx::loadLessonV2`
- **UI Component**: `frontend/src/app/cando/[canDoId]/page.tsx` (lines 796-875)

## Success Criteria

✅ User can see pre-lesson kit information for compiled lessons
✅ Console logs show kit integration messages
✅ Backend logs show kit fetch and integration
✅ UI displays kit usage statistics
✅ Kit information persists in lesson metadata
✅ Existing lessons display kit info when available
