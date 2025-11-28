# CanDo V2 Debugging Guide

**Current Status:** Lesson loads from database but crashes due to data structure mismatch

---

## The Error

```
Cannot destructure property 'meta' of 'lesson' as it is undefined.
at LessonRootRenderer (src/components/lesson/LessonRootRenderer.tsx:24:3)
```

**What this means:** The `LessonRootRenderer` component receives `lessonData` but `lessonData.lesson` is undefined.

---

## Data Flow Analysis

### 1. Database Structure ✅ CORRECT
```sql
SELECT lesson_plan FROM lesson_versions WHERE lesson_id = 9;
-- Returns: {"lesson": {"meta": {...}, "cards": {...}, ...}}
```

### 2. Backend API Response ✅ SHOULD BE CORRECT
Endpoint: `/api/v1/cando/lessons/latest?can_do_id=JF:105`

Returns:
```json
{
  "can_do_id": "JF:105",
  "lesson_id": 9,
  "version": 7,
  "master": {"lesson": {"meta": {...}, "cards": {...}}},  // From lesson_plan column
  "entities": {},
  "timings": {}
}
```

### 3. Frontend Loading Code
```typescript
const response = await apiGet(`/api/v1/cando/lessons/latest?can_do_id=JF:105`)
const lessonData = response.master || response.lesson_plan
setLessonData(lessonData)  // Should be {"lesson": {...}}
```

### 4. Component Expectation
```typescript
interface LessonRootRendererProps {
  lessonData: LessonRoot  // Type: {lesson: {...}}
}

const { lesson } = lessonData  // lesson is undefined!
```

---

## Root Cause Hypothesis

The `response.master` or `response.lesson_plan` from the API is **NOT** in the expected format.

### Possible Issues:

**A) API returns different structure than expected**
- Maybe `master` doesn't contain the lesson data
- Maybe it's in a different format

**B) Frontend type mismatch**
- The `LessonRoot` type expects `{lesson: {...}}`  
- But we might be getting just `{meta, cards, ...}` (unwrapped)

**C) Serialization issue**
- JSONB from PostgreSQL might not be deserializing correctly
- Python might be returning the data in a different format

---

## Quick Fix Option 1: Check and Transform Data

Update `frontend/src/app/cando/[canDoId]/v2/page.tsx`:

```typescript
const response = await apiGet<any>(`/api/v1/cando/lessons/latest?can_do_id=${encodeURIComponent(canDoId)}`)

if (response?.master || response?.lesson_plan) {
  let lessonData = response.master || response.lesson_plan
  
  // DEBUG: Log the actual structure
  console.log("Raw lesson data:", JSON.stringify(lessonData, null, 2))
  
  // TRANSFORM: Ensure it's in the right format
  if (!lessonData.lesson) {
    // If it's already unwrapped, wrap it
    lessonData = { lesson: lessonData }
  }
  
  console.log("Final lesson data:", JSON.stringify(lessonData, null, 2))
  setLessonData(lessonData)
  setIsCompiling(false)
  return
}
```

---

## Quick Fix Option 2: Update Backend API

Make the backend return the data in a consistent format.

Update `backend/app/api/v1/endpoints/cando.py` line 1140-1148:

```python
# Get the lesson_plan and ensure it's properly formatted
lesson_plan = row.lesson_plan
if isinstance(lesson_plan, str):
    lesson_plan = json.loads(lesson_plan)

return {
    "can_do_id": can_do_id,
    "lesson_id": int(lesson_id),
    "version": int(row.version),
    "lesson": lesson_plan,  # Return as "lesson" directly, not "master"
    "entities": row.entities or {},
    "timings": row.timings or {},
    "created_at": row.created_at,
}
```

Then update frontend to use:
```typescript
const lessonData = response.lesson || response.master || response.lesson_plan
```

---

## Quick Fix Option 3: Direct Database Query Test

Test what the API actually returns:

```powershell
# From PowerShell
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/cando/lessons/latest?can_do_id=JF:105" | ConvertTo-Json -Depth 10 > api_response.json

# Check the file
Get-Content api_response.json
```

This will show you the EXACT structure the API is returning.

---

## Recommended Debugging Steps

### Step 1: Check API Response
Open your browser's DevTools:
1. Go to: http://localhost:3000/cando/JF:105/v2
2. Open Console (F12)
3. Look at the network tab
4. Find the request to `/api/v1/cando/lessons/latest?can_do_id=JF:105`
5. Check the Response

**What to look for:**
- Does `response.master` exist?
- Does `response.master.lesson` exist?
- Or is it `response.lesson`?

### Step 2: Add Defensive Code
Add this to `frontend/src/app/cando/[canDoId]/v2/page.tsx` before `setLessonData()`:

```typescript
// Defensive check
if (!lessonData || typeof lessonData !== 'object') {
  console.error("Invalid lessonData:", lessonData)
  setError("Invalid lesson data structure")
  setIsCompiling(false)
  return
}

if (!lessonData.lesson) {
  console.warn("lessonData missing 'lesson' property. Keys:", Object.keys(lessonData))
  // Try to fix it
  if (lessonData.meta && lessonData.cards) {
    // Data is unwrapped, wrap it
    lessonData = { lesson: lessonData }
  } else {
    setError("Lesson data has unexpected structure")
    setIsCompiling(false)
    return
  }
}
```

### Step 3: Check Type Definitions
Verify the `LessonRoot` type matches what we're actually getting:

```typescript
// In frontend/src/types/lesson-root.ts
export interface LessonRoot {
  lesson: Lesson  // This is what the component expects
}
```

If the API returns something different, either:
- Change the type definition, OR
- Transform the data in the loading code

---

## The Simplest Solution

Since you're seeing the "Generating" message, the issue is that the frontend can't load the saved lesson. The simplest fix is to **check the exact API response structure** and **transform it to match** what the component expects.

Add this RIGHT after fetching:

```typescript
const response = await apiGet<any>(`/api/v1/cando/lessons/latest?can_do_id=${encodeURIComponent(canDoId)}`)

// Log everything
console.log("Full API response:", response)
console.log("response.master:", response?.master)
console.log("response.lesson_plan:", response?.lesson_plan)
console.log("response.lesson:", response?.lesson)

// Try all possible paths
let lessonData = response?.lesson || response?.master || response?.lesson_plan

// Ensure correct structure
if (lessonData && !lessonData.lesson && lessonData.meta) {
  // It's unwrapped, wrap it
  lessonData = { lesson: lessonData }
}

console.log("Final lessonData being set:", lessonData)

if (lessonData) {
  setLessonData(lessonData)
  setIsCompiling(false)
  return
}
```

Then **reload the page** and check the browser console to see what's actually being received!

---

## Files to Check/Modify

1. **Frontend loading code:** `frontend/src/app/cando/[canDoId]/v2/page.tsx` (lines 35-47)
2. **Backend API:** `backend/app/api/v1/endpoints/cando.py` (lines 1117-1152)
3. **Type definitions:** `frontend/src/types/lesson-root.ts`

---

## Next Steps

1. Open browser DevTools
2. Navigate to: http://localhost:3000/cando/JF:105/v2
3. Check Console for the log messages
4. Check Network tab for API response
5. Share the console output with me

The lesson IS in the database and the API IS working. We just need to align the data format between backend → frontend → component.


