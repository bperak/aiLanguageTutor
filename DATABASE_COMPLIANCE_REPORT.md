# Database Compliance Report
## Frontend-Backend Database Contract Analysis

**Date:** 2026-01-07  
**Scope:** `/app/cando/[canDoId]/page.tsx` and related database operations

---

## 📊 **Executive Summary**

**Overall Compliance: B+ (Good with some issues)**

The frontend correctly handles most database operations, but there are several areas where database schema compliance could be improved, particularly around:
- Type mismatches between database and frontend
- Missing error handling for database-specific errors
- Incomplete handling of nullable fields
- Race conditions in concurrent updates

---

## 🗄️ **Database Schema Overview**

### **Relevant Tables:**

1. **`lessons`** (PostgreSQL)
   - `id` (SERIAL PRIMARY KEY)
   - `can_do_id` (TEXT NOT NULL)
   - `status` (TEXT NOT NULL DEFAULT 'active')
   - `created_at` (TIMESTAMPTZ)

2. **`lesson_versions`** (PostgreSQL)
   - `id` (SERIAL PRIMARY KEY)
   - `lesson_id` (INTEGER NOT NULL, FK to lessons.id)
   - `version` (INTEGER NOT NULL)
   - `lesson_plan` (JSONB NOT NULL) - **Main lesson data**
   - `exercises` (JSONB)
   - `manifest` (JSONB)
   - `dialogs` (JSONB)
   - `master` (JSONB)
   - `entities` (JSONB)
   - `timings` (JSONB)
   - `pdf_path` (TEXT)
   - `source` (TEXT)
   - `context` (JSONB)
   - `parent_version` (INTEGER)
   - `created_at` (TIMESTAMPTZ)

3. **`lesson_sessions`** (PostgreSQL)
   - `id` (UUID PRIMARY KEY)
   - `can_do_id` (TEXT NOT NULL)
   - `phase` (TEXT DEFAULT 'lexicon_and_patterns')
   - `completed_count` (INTEGER DEFAULT 0)
   - `scenario_json` (JSONB)
   - `master_json` (JSONB)
   - `variant_json` (JSONB)
   - `package_json` (JSONB)
   - `stage_progress` (JSONB)
   - `created_at`, `expires_at`, `updated_at` (TIMESTAMPTZ)

---

## ✅ **Compliant Areas**

### **1. API Endpoint Usage**
- ✅ Correctly uses `/api/v1/cando/lessons/list` with `can_do_id` parameter
- ✅ Correctly uses `/api/v1/cando/lessons/fetch/{id}` for individual lessons
- ✅ Correctly uses `/api/v1/cando/lessons/compile_v2_stream` for compilation
- ✅ Correctly uses `/api/v1/cando/lessons/generation-status` with `lesson_id` and `version`
- ✅ Correctly uses `/api/v1/cando/lessons/session/create` for session management

### **2. Data Structure Handling**
- ✅ Correctly expects `lesson_id` (integer) and `version` (integer) from API
- ✅ Correctly handles `lesson_plan` JSONB structure
- ✅ Correctly extracts `generation_status` from `lesson.meta.generation_status`
- ✅ Correctly handles `prelesson_kit_usage` metadata

### **3. Type Safety**
- ✅ Frontend types match backend JSONB structure for `LessonRoot`
- ✅ Proper handling of optional fields (`prelesson_kit_usage`, `generation_status`)

---

## ⚠️ **Compliance Issues**

### **🔴 CRITICAL ISSUES**

#### **1. Missing Database Error Handling**

**Location:** Throughout `page.tsx`  
**Issue:** Frontend doesn't handle database-specific errors (e.g., connection failures, constraint violations, deadlocks)

**Current Code:**
```typescript
try {
  const response = await apiGet<any>(`/api/v1/cando/lessons/list?...`);
  // ... handle response
} catch (e: any) {
  console.error("Failed to refresh lesson data:", e);
  // No specific handling for database errors
}
```

**Database Errors Not Handled:**
- `503 Service Unavailable` (database connection pool exhausted)
- `500 Internal Server Error` (database constraint violations)
- `409 Conflict` (concurrent update conflicts)
- `504 Gateway Timeout` (long-running queries)

**Impact:** High - Users see generic errors instead of actionable messages

**Fix Required:**
```typescript
catch (e: any) {
  const status = e?.response?.status;
  if (status === 503) {
    setError("Database temporarily unavailable. Please try again in a moment.");
  } else if (status === 409) {
    setError("Lesson was updated by another process. Refreshing...");
    await refreshLessonData();
  } else if (status === 504) {
    setError("Request timed out. The lesson may be very large. Please try again.");
  } else {
    setError(e?.response?.data?.detail || e.message || "Failed to load lesson");
  }
}
```

---

#### **2. Race Condition in Concurrent Updates**

**Location:** Lines 472, 477, 483, 282, 289, 297  
**Issue:** Multiple `refreshLessonData()` calls can race when stages complete simultaneously, causing:
- Stale data overwriting fresh data
- Lost updates
- Inconsistent UI state

**Current Code:**
```typescript
if (s?.event === "comprehension_ready") {
  setStageStatus((prev) => ({ ...prev, comprehension: "complete" }));
  refreshLessonData().catch(...);  // ⚠️ No deduplication
}
if (s?.event === "production_ready") {
  setStageStatus((prev) => ({ ...prev, production: "complete" }));
  refreshLessonData().catch(...);  // ⚠️ Another concurrent call
}
```

**Database Impact:**
- Backend uses atomic JSONB updates (`jsonb_set`, `||` operators)
- But frontend can read stale data if multiple refreshes happen simultaneously

**Fix Required:**
```typescript
const refreshQueue = useRef<Promise<void> | null>(null);
const refreshLessonDataSafe = useCallback(async () => {
  // Wait for any in-flight refresh
  if (refreshQueue.current) {
    await refreshQueue.current;
  }
  // Start new refresh
  refreshQueue.current = refreshLessonData();
  try {
    await refreshQueue.current;
  } finally {
    refreshQueue.current = null;
  }
}, [refreshLessonData]);
```

---

#### **3. Missing Transaction Awareness**

**Location:** `refreshLessonData()` and polling  
**Issue:** Frontend doesn't account for database transaction isolation levels. If backend uses `READ COMMITTED`, frontend might see partial updates.

**Impact:** Medium - Could see inconsistent state during incremental compilation

**Fix Required:**
- Backend should use `SERIALIZABLE` or `REPEATABLE READ` for lesson updates
- Frontend should handle `409 Conflict` responses and retry

---

### **🟡 MEDIUM PRIORITY ISSUES**

#### **4. Nullable Field Handling**

**Location:** Lines 227-230  
**Issue:** Frontend assumes `latestLesson.id` and `latestLesson.version` are always present, but database allows NULL in some edge cases.

**Current Code:**
```typescript
if (latestLesson.id && latestLesson.version) {
  setLastLessonId(latestLesson.id);
  setLastVersion(latestLesson.version);
}
```

**Database Schema:**
- `lessons.id` is `SERIAL PRIMARY KEY` (NOT NULL) ✅
- `lesson_versions.version` is `INTEGER NOT NULL` ✅
- But API might return `null` if lesson doesn't exist

**Impact:** Low-Medium - Could cause polling to fail silently

**Fix Required:**
```typescript
if (latestLesson.id != null && latestLesson.version != null) {
  setLastLessonId(Number(latestLesson.id));  // Ensure it's a number
  setLastVersion(Number(latestLesson.version));
} else {
  console.warn("Lesson missing id or version:", latestLesson);
}
```

---

#### **5. JSONB Path Mismatch**

**Location:** Lines 205-212  
**Issue:** Frontend expects `lessonData.lesson.meta.generation_status`, but database stores it at `lesson_plan->'lesson'->'meta'->'generation_status'`. If backend returns different structure, frontend breaks.

**Current Code:**
```typescript
if (lessonData.lesson?.meta?.generation_status) {
  const status = lessonData.lesson.meta.generation_status;
  setStageStatus({
    content: status.content || "pending",
    // ...
  });
}
```

**Database Structure:**
```sql
lesson_plan JSONB = {
  "lesson": {
    "meta": {
      "generation_status": {
        "content": "complete",
        "comprehension": "pending",
        ...
      }
    }
  }
}
```

**Impact:** Medium - If backend changes JSONB structure, frontend breaks

**Fix Required:**
```typescript
// Add defensive checks
const generationStatus = lessonData?.lesson?.meta?.generation_status;
if (generationStatus && typeof generationStatus === 'object') {
  setStageStatus({
    content: String(generationStatus.content || "pending"),
    comprehension: String(generationStatus.comprehension || "pending"),
    production: String(generationStatus.production || "pending"),
    interaction: String(generationStatus.interaction || "pending"),
  });
}
```

---

#### **6. Missing Version Validation**

**Location:** Lines 256, 464, 673, 757  
**Issue:** Frontend doesn't validate that `version` is a positive integer before using it in API calls.

**Current Code:**
```typescript
const statusResponse = await apiGet<any>(
  `/api/v1/cando/lessons/generation-status?lesson_id=${lastLessonId}&version=${lastVersion}`
);
```

**Database Constraint:**
- `version INTEGER NOT NULL` (no CHECK constraint for > 0)
- But backend expects `version >= 1`

**Impact:** Low - Could cause 400 errors if version is 0 or negative

**Fix Required:**
```typescript
if (lastLessonId && lastVersion && lastVersion > 0) {
  const statusResponse = await apiGet<any>(
    `/api/v1/cando/lessons/generation-status?lesson_id=${lastLessonId}&version=${lastVersion}`
  );
}
```

---

#### **7. Session Expiration Not Handled**

**Location:** Lines 332-353  
**Issue:** Frontend creates lesson sessions but doesn't handle expiration. Database has `expires_at` column (2 hours TTL), but frontend doesn't check or refresh.

**Database Schema:**
```sql
expires_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP + INTERVAL '2 hours'
```

**Current Code:**
```typescript
const sessionResponse = await apiPost<{ session_id: string }>(
  "/api/v1/cando/lessons/session/create",
  { can_do_id: canDoId }
);
setLessonSessionId(sessionId);
// ⚠️ No expiration handling
```

**Impact:** Medium - Session could expire during long compilation, causing errors

**Fix Required:**
```typescript
// Check session expiration before use
const checkSessionExpiration = async (sessionId: string) => {
  try {
    const session = await apiGet(`/api/v1/cando/lessons/session/${sessionId}`);
    if (new Date(session.expires_at) < new Date()) {
      // Session expired, create new one
      const newSession = await apiPost("/api/v1/cando/lessons/session/create", { can_do_id: canDoId });
      return newSession.session_id;
    }
    return sessionId;
  } catch (e) {
    // Session not found, create new one
    const newSession = await apiPost("/api/v1/cando/lessons/session/create", { can_do_id: canDoId });
    return newSession.session_id;
  }
};
```

---

### **🟢 LOW PRIORITY ISSUES**

#### **8. Missing Index Awareness**

**Issue:** Frontend doesn't optimize queries based on database indexes. For example, `can_do_id` is indexed, but frontend doesn't leverage this for filtering.

**Database Indexes:**
```sql
CREATE INDEX idx_lessons_can_do_id ON lessons(can_do_id);
CREATE INDEX idx_lesson_versions_lesson_id ON lesson_versions(lesson_id);
CREATE UNIQUE INDEX uq_lesson_versions_lesson_version ON lesson_versions(lesson_id, version);
```

**Impact:** Low - Backend handles optimization, but frontend could batch requests

---

#### **9. No Pagination for Large Lessons**

**Location:** `refreshLessonData()`  
**Issue:** If `lesson_plan` JSONB is very large (>10MB), frontend loads it all at once. No streaming or pagination.

**Database:**
- `lesson_plan JSONB` can be very large
- No size limit in schema

**Impact:** Low - Could cause memory issues for very large lessons

**Fix Required:**
- Backend should implement pagination or streaming for large lessons
- Frontend should handle partial data loading

---

#### **10. Missing Database Constraint Validation**

**Issue:** Frontend doesn't validate data against database constraints before sending to API.

**Database Constraints:**
- `lessons.can_do_id TEXT NOT NULL`
- `lesson_versions.version INTEGER NOT NULL`
- `lesson_versions.lesson_id INTEGER NOT NULL REFERENCES lessons(id)`

**Impact:** Low - Backend validates, but frontend could provide better UX

---

## 🔍 **Backend Database Operations Analysis**

### **Atomic Updates (✅ Good):**
Backend uses atomic JSONB operations to prevent race conditions:
```sql
UPDATE lesson_versions 
SET lesson_plan = jsonb_set(
  jsonb_set(
    COALESCE(lesson_plan, '{}'::jsonb),
    '{lesson,meta,generation_status}',
    COALESCE(lesson_plan->'lesson'->'meta'->'generation_status', '{}'::jsonb) || :status::jsonb
  ),
  '{lesson,meta,errors}',
  COALESCE(lesson_plan->'lesson'->'meta'->'errors', '{}'::jsonb) || :errors::jsonb
)
WHERE lesson_id = :lid AND version = :ver
```

**Frontend Compliance:** ✅ Correctly handles incremental updates

---

### **Transaction Handling (⚠️ Needs Improvement):**
Backend uses async transactions but doesn't always commit/rollback properly in error cases.

**Frontend Impact:** Should handle `409 Conflict` responses and retry

---

### **Connection Pooling (✅ Good):**
Backend uses SQLAlchemy connection pooling with proper async context management.

**Frontend Impact:** Should handle `503 Service Unavailable` when pool is exhausted

---

## 📋 **Data Type Mapping**

| Database Type | Frontend Type | Status | Notes |
|--------------|---------------|--------|-------|
| `INTEGER` (lesson_id) | `number` | ✅ | Correct |
| `INTEGER` (version) | `number` | ✅ | Correct |
| `TEXT` (can_do_id) | `string` | ✅ | Correct |
| `JSONB` (lesson_plan) | `object` | ✅ | Correct |
| `TIMESTAMPTZ` | `string` (ISO) | ✅ | Correct |
| `UUID` (session_id) | `string` | ✅ | Correct |
| `JSONB` (generation_status) | `object` | ✅ | Correct |
| `JSONB` (prelesson_kit_usage) | `object` | ✅ | Fixed (was `any`) |

---

## 🎯 **Recommendations**

### **Immediate (This Sprint):**
1. ✅ Add database error handling (503, 409, 504)
2. ✅ Fix race conditions in `refreshLessonData()`
3. ✅ Add session expiration handling

### **Short Term:**
4. Add defensive checks for nullable fields
5. Validate version numbers before API calls
6. Add retry logic for database errors

### **Medium Term:**
7. Implement request deduplication
8. Add transaction conflict handling
9. Add database connection monitoring

---

## ✅ **Summary**

**Database Compliance Score: B+**

**Strengths:**
- ✅ Correct API endpoint usage
- ✅ Proper data structure handling
- ✅ Good type safety
- ✅ Handles JSONB structure correctly

**Weaknesses:**
- ⚠️ Missing database-specific error handling
- ⚠️ Race conditions in concurrent updates
- ⚠️ No session expiration handling
- ⚠️ Missing validation for nullable fields

**Overall:** The frontend is **mostly compliant** with the database schema, but needs improvements in error handling and concurrent update scenarios.
