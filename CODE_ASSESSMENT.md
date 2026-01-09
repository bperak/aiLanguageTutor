# Code Assessment Report
## Frontend: `/app/cando/[canDoId]/page.tsx`

**Date:** 2026-01-07  
**File:** `frontend/src/app/cando/[canDoId]/page.tsx`

---

## ✅ **Strengths**

1. **Type Safety**: Good use of TypeScript types for most state variables
2. **Error Handling**: Comprehensive error handling with user-friendly messages
3. **Loading States**: Proper loading states and progress indicators
4. **User Experience**: "Generate Lesson" button when no lesson exists
5. **Detailed Progress**: Stage-by-stage compilation progress display
6. **LocalStorage Persistence**: Stage status persisted to localStorage
7. **Polling Mechanism**: Adaptive polling for generation status updates

---

## ⚠️ **Issues Found**

### **1. CRITICAL: Missing Incremental Mode in `loadLessonV2`**

**Location:** Line 433-454  
**Issue:** `loadLessonV2` doesn't pass `incremental: true` to `compileLessonV2Stream`, and doesn't handle incremental stage events (`content_ready`, `comprehension_ready`, etc.)

**Impact:** 
- Initial compilation won't show incremental updates
- Users won't see content stage immediately when ready
- Inconsistent behavior between initial load and regeneration

**Fix Required:**
```typescript
// Current (line 433):
const result = await compileLessonV2Stream(
  canDoId,
  "en",
  "gpt-4o",
  (s) => { /* basic progress only */ },
  userId,
  fastModelOverride
  // Missing: incremental parameter
);

// Should be:
const result = await compileLessonV2Stream(
  canDoId,
  "en",
  "gpt-4o",
  (s) => {
    // Add event handlers like regenerateLesson has
    if (s?.event === "content_ready") { /* ... */ }
    if (s?.event === "comprehension_ready") { /* ... */ }
    // etc.
  },
  userId,
  fastModelOverride,
  true  // Enable incremental mode
);
```

---

### **2. Type Safety: `prelessonKitUsage` Typed as `any`**

**Location:** Line 82  
**Issue:** `prelessonKitUsage` is typed as `any` instead of a proper interface

**Impact:** No type safety, potential runtime errors

**Fix Required:**
```typescript
// Current:
const [prelessonKitUsage, setPrelessonKitUsage] = useState<any>(null);

// Should be:
interface PrelessonKitUsage {
  words?: { count: number; total: number; required?: number; meets_requirement: boolean };
  grammar?: { count: number; total: number; required?: number; meets_requirement: boolean };
  phrases?: { count: number; total: number; required?: number; meets_requirement: boolean };
  all_requirements_met: boolean;
  usage_percentage: number;
}
const [prelessonKitUsage, setPrelessonKitUsage] = useState<PrelessonKitUsage | null>(null);
```

---

### **3. Error Handling: `refreshLessonData` Silently Fails**

**Location:** Line 177-230  
**Issue:** `refreshLessonData` catches errors but only logs them, doesn't notify user or update UI state

**Impact:** Users won't know if lesson refresh fails

**Fix Required:**
```typescript
// Current:
} catch (e) {
  console.error("Failed to refresh lesson data:", e);
}

// Should be:
} catch (e: any) {
  console.error("Failed to refresh lesson data:", e);
  // Optionally show toast or update error state
  // showToast("Failed to refresh lesson data. Please try again.");
}
```

---

### **4. Missing Error Details for Failed Stages**

**Location:** Line 632-643  
**Issue:** Failed stage error handling doesn't check for `retryable` flag or show detailed error messages like backup version does

**Impact:** Users get less helpful error messages

**Fix Required:**
```typescript
// Current:
showToast(
  `${stageName.charAt(0).toUpperCase() + stageName.slice(1)} Stage Failed`
);

// Should be (like backup):
showToast({
  title: `${stageName.charAt(0).toUpperCase() + stageName.slice(1)} Stage Failed`,
  description: s.error?.retryable 
    ? "This error may be temporary. You can retry this stage." 
    : s.error?.message || "An error occurred during generation",
  variant: "destructive",
});
```

---

### **5. Potential Race Condition: `refreshLessonData` in Event Handlers**

**Location:** Lines 618, 623, 629  
**Issue:** `refreshLessonData()` is called without `await` in event handlers, which could cause race conditions

**Impact:** Potential for stale data or inconsistent UI state

**Fix Required:**
```typescript
// Current:
if (s?.event === "comprehension_ready") {
  setStageStatus((prev) => ({ ...prev, comprehension: "complete" }));
  refreshLessonData();  // Missing await
}

// Should be:
if (s?.event === "comprehension_ready") {
  setStageStatus((prev) => ({ ...prev, comprehension: "complete" }));
  await refreshLessonData();
}
```

---

### **6. Missing Dependency in `loadLessonV2` useCallback**

**Location:** Line 480  
**Issue:** `loadLessonV2` depends on `refreshLessonData` but `refreshLessonData` is also a useCallback that might change

**Impact:** Potential stale closures or unnecessary re-renders

**Current Dependencies:** `[canDoId, parseAndSetLessonData, refreshLessonData, fastModelOverride]`

**Note:** This might be intentional, but should be verified.

---

## 📊 **Code Quality Metrics**

- **Lines of Code:** ~1,254 lines
- **State Variables:** 15 (well organized)
- **useEffect Hooks:** 4 (properly structured)
- **useCallback Hooks:** 3 (good memoization)
- **Type Safety:** Good (except `prelessonKitUsage`)
- **Error Handling:** Good (with room for improvement)
- **User Feedback:** Excellent (toasts, progress indicators)

---

## 🔍 **Comparison with Backup**

### **What We Have (Current):**
✅ "Generate Lesson" button when no lesson exists  
✅ Detailed compilation progress with stage indicators  
✅ Error handling with "Create CanDo Descriptor" button  
✅ TypeScript type safety (mostly)  
✅ Proper loading states  

### **What Backup Has That We're Missing:**
❌ Incremental mode handling in `loadLessonV2`  
❌ Event handlers for `content_ready`, `comprehension_ready`, etc. in initial compilation  
❌ Better error messages for failed stages (with retryable flag)  
❌ Proper typing for `prelessonKitUsage`  

---

## 🎯 **Priority Fixes**

### **High Priority:**
1. Add incremental mode and event handlers to `loadLessonV2` (Issue #1)
2. Fix race conditions with `await refreshLessonData()` (Issue #5)

### **Medium Priority:**
3. Add proper TypeScript type for `prelessonKitUsage` (Issue #2)
4. Improve error handling in `refreshLessonData` (Issue #3)
5. Enhance failed stage error messages (Issue #4)

---

## ✅ **Recommendations**

1. **Consistency**: Make `loadLessonV2` handle events the same way as `regenerateLesson`
2. **Type Safety**: Create proper interfaces for all state types
3. **Error Handling**: Add user-facing error notifications for all error cases
4. **Testing**: Add unit tests for event handlers and error scenarios
5. **Documentation**: Add JSDoc comments for complex functions

---

## 📝 **Summary**

The code is **generally well-structured** with good error handling and user feedback. The main issues are:
- Missing incremental mode support in initial compilation
- Some type safety gaps
- Inconsistent error handling patterns

**Overall Grade: B+** (Good, with room for improvement)
