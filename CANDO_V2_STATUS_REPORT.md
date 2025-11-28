# CanDo V2 Lesson Status Report

**Date:** October 29, 2025  
**Testing Method:** Playwright MCP  
**Test User:** bperak / Teachable1A

## Summary

✅ **Frontend:** CanDo browse page is working correctly  
⚠️ **Frontend:** V2 lesson viewer has API endpoint mismatch  
❌ **Backend:** Missing API endpoint for fetching lessons by can_do_id  
📦 **Generated Lessons:** 3 v2 lessons exist but are not loaded in database

---

## Detailed Findings

### 1. CanDo Browse Page (✅ Working)

**URL:** `http://localhost:3000/cando`

**Status:** Fully functional

**Features Tested:**
- Level filters (A1, A2, B1, B2) - ✅ Working
- Topic filters (Japanese & English) - ✅ Working  
- Search functionality - ✅ Present
- CanDo statement display - ✅ Working
- Bilingual descriptions (EN/JA) - ✅ Displayed
- "Start Lesson" buttons - ✅ Present
- "Data" buttons - ✅ Present

**Screenshot Evidence:** Frontend home page loaded successfully after login

---

### 2. V2 Lesson Viewer Page (⚠️ API Issue)

**URL:** `http://localhost:3000/cando/JF%3A105/v2`

**Status:** Page loads but cannot fetch lessons

**Issue:** API endpoint mismatch
- Frontend calls: `/api/v1/cando/lessons/fetch?can_do_id=JF:105`
- Backend has: 
  - `/api/v1/cando/lessons/fetch/{lesson_id}` (requires numeric ID)
  - `/api/v1/cando/lessons/latest?can_do_id=...` (correct query param format)

**Console Errors:**
```
[error] Failed to load resource: the server responded with a status of 404 (Not Found)
[log] Lesson not found, compiling new one...
```

**Current Behavior:**
- Page shows "Generating Your Lesson" spinner
- Falls back to compiling a new lesson (instead of loading existing)
- This defeats the purpose of having pre-generated lessons

---

### 3. Generated V2 Lessons (📦 Available but not imported)

**Location:** `d:\My_apps\aiLanguageTutor\generated\lessons_v2\`

**Generated Files:**
1. `canDo_JF_105_v1.json` (807 lines)
   - CanDo ID: `JF:105`
   - Level: A1
   - Topic: Health (健康)
   - Description: Doctor's instructions

2. `canDo_JF_106_v1.json` (879 lines)
   - CanDo ID: `JF:106`  
   - Level: A1

3. `canDo_JFまるごと_14_v1.json` (841 lines)
   - CanDo ID: `JFまるごと_14`
   - Level: A1

**Issue:** These JSON files are not loaded into the PostgreSQL database, so they cannot be fetched by the API.

---

### 4. Backend API Endpoints Analysis

**File:** `backend/app/api/v1/endpoints/cando.py`

**Available Endpoints:**
- ✅ `POST /lessons/compile_v2` - Compiles new v2 lessons
- ✅ `GET /lessons/list?can_do_id=...` - Lists lesson versions
- ✅ `GET /lessons/fetch/{lesson_id}` - Fetches by numeric ID
- ✅ `GET /lessons/latest?can_do_id=...` - Gets latest lesson for a can_do_id
- ❌ `GET /lessons/fetch?can_do_id=...` - **MISSING** (called by frontend)

**Scripts Available:**
- `backend/scripts/preload_lessons.py` - Compiles lessons in bulk
- `backend/scripts/canDo_creation_new.py` - Lesson generation pipeline
- ❌ No script to import existing JSON files into database

---

## Issues Identified

### Issue #1: API Endpoint Mismatch (High Priority)

**Problem:** Frontend calls non-existent endpoint  
**File:** `frontend/src/app/cando/[canDoId]/v2/page.tsx:36`
```typescript
const response = await apiGet<{ lesson: LessonRoot }>(
  `/api/v1/cando/lessons/fetch?can_do_id=${encodeURIComponent(canDoId)}`
)
```

**Solutions:**
1. **Option A:** Update frontend to use `/lessons/latest?can_do_id=...`
2. **Option B:** Add new backend endpoint `/lessons/fetch?can_do_id=...`

**Recommendation:** Option A (simpler, uses existing endpoint)

---

### Issue #2: Generated Lessons Not in Database (High Priority)

**Problem:** JSON files exist but are not accessible via API

**Current State:**
- Generated lessons are static JSON files
- Database has no records for these lessons
- API cannot serve them

**Required:**
- Import script to load JSON files into PostgreSQL `lessons` and `lesson_versions` tables
- Database schema must match LessonRoot structure

---

### Issue #3: No Import Workflow (Medium Priority)

**Problem:** No documented way to import pre-generated lessons

**Current Workflow:**
1. Generate lesson → saves to JSON file
2. ??? (missing step)
3. Lesson available in frontend

**Needed:**
- Import script: `scripts/import_generated_lessons.py`
- Command: `python scripts/import_generated_lessons.py --input generated/lessons_v2/`

---

## Recommendations

### Immediate Actions

1. **Fix API Endpoint Mismatch**
   - Update `frontend/src/app/cando/[canDoId]/v2/page.tsx`
   - Change `/lessons/fetch?can_do_id=...` to `/lessons/latest?can_do_id=...`
   - Test with existing endpoint

2. **Create Import Script**
   - Create `backend/scripts/import_lesson_json.py`
   - Import generated JSON files into PostgreSQL
   - Update database records

3. **Test Complete Flow**
   - Import the 3 generated lessons
   - Navigate to `/cando/JF:105/v2`
   - Verify lesson loads without recompiling

### Future Enhancements

1. **Unified Endpoint**
   - Add `/lessons/fetch?can_do_id=...` endpoint for consistency
   - Make it an alias to `/lessons/latest`

2. **Automatic Import**
   - Modify generation scripts to auto-import to database
   - Skip manual import step

3. **File-Based Fallback**
   - If database lookup fails, check `generated/lessons_v2/` folder
   - Serve directly from JSON files

---

## Testing Summary

### What Works ✅
- User authentication
- CanDo browse page with filters
- Dashboard statistics
- Navigation
- UI rendering

### What Needs Fixing ⚠️
- V2 lesson API endpoint
- Lesson import workflow
- Database population

### What's Missing ❌
- Import script for generated lessons
- Documentation for v2 workflow
- E2E test for v2 lesson loading

---

## Next Steps

1. **Fix Frontend API Call** (15 minutes)
   - Update endpoint URL
   - Test with Playwright

2. **Create Import Script** (30 minutes)
   - Write Python script
   - Import 3 existing lessons
   - Verify database records

3. **End-to-End Test** (10 minutes)
   - Load lesson in frontend
   - Navigate through lesson content
   - Document results

**Total Estimated Time:** ~1 hour

---

## Test Credentials Used

```
Username: bperak
Password: Teachable1A
```

---

## Generated By

Cursor AI Assistant with Playwright MCP integration

