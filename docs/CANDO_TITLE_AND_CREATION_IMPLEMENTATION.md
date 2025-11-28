# CanDo Title Generation and Manual Creation - Implementation Summary

## Overview

This implementation adds:
1. AI-generated titles for all CanDoDescriptor nodes
2. Automatic processing pipeline for new CanDo-s
3. Manual CanDo creation from frontend with minimal input

## Components Implemented

### 1. Title Generation Service

**File**: `backend/app/services/cando_title_service.py`

- `CanDoTitleService` class
- `generate_title()` - Generates title in specified language (en/ja)
- `generate_titles()` - Generates both titles in parallel
- Uses `AIChatService` with GPT-4o-mini
- Title format: Full sentence starting with "Can..." (e.g., "Can talk about travel and transportation")

### 2. Migration Script

**File**: `resources/generate_cando_titles.py`

- Generates titles for all existing CanDoDescriptors
- Batch processing with progress tracking
- Supports `--dry-run` and `--batch-size` options
- Updates nodes with `titleEn` and `titleJa` properties

### 3. Creation Service with Auto-Processing

**File**: `backend/app/services/cando_creation_service.py`

- `CanDoCreationService` class
- `translate_description()` - Translates between English and Japanese
- `infer_cando_fields()` - Uses AI to infer level, topic, skillDomain, type
- `create_cando_with_auto_processing()` - Complete creation pipeline:
  1. Translation (if only one description provided)
  2. Field inference (level, topic, skillDomain, type)
  3. Title generation (titleEn, titleJa)
  4. Embedding generation
  5. Similarity relationship creation

### 4. API Endpoint

**File**: `backend/app/api/v1/endpoints/cando.py`

- `POST /api/v1/cando/create`
- Request model: `CreateCanDoRequest` (descriptionEn, descriptionJa - both optional)
- Validates at least one description is provided
- Returns created CanDoDescriptor with all generated fields

### 5. Frontend UI

**File**: `frontend/src/app/cando/create/page.tsx`

- Form with English and Japanese description text areas
- Loading states during creation
- Error handling with user-friendly messages
- Redirects to created CanDo detail page on success
- Shows processing steps during creation

**File**: `frontend/src/lib/api.ts`

- Added `createCanDo()` function

**File**: `frontend/src/app/cando/page.tsx`

- Added "Create New CanDo" button in header

### 6. Updates to Existing Services

**File**: `backend/app/services/cando_embedding_service.py`

- Updated `update_cando_embedding()` to:
  - Accept optional description parameters
  - Check and generate titles if missing
  - Integrate with `CanDoTitleService`

**File**: `backend/app/api/v1/endpoints/cando.py`

- Updated `/list` endpoint to include `titleEn` and `titleJa` in response

### 7. Tests

**File**: `backend/tests/test_cando_title_service.py`

- Tests for title generation (English, Japanese, both)
- Tests for error handling

**File**: `backend/tests/test_cando_creation_service.py`

- Tests for translation
- Tests for field inference
- Tests for complete creation pipeline

## Usage

### Generate Titles for Existing CanDo-s

```powershell
cd backend
poetry run python ../resources/generate_cando_titles.py --batch-size 50
```

### Create New CanDo via API

```bash
curl -X POST http://localhost:8000/api/v1/cando/create \
  -H "Content-Type: application/json" \
  -d '{
    "descriptionEn": "Can talk about travel and transportation",
    "descriptionJa": "旅行と交通について話すことができる"
  }'
```

Or with only one language (will be translated):

```bash
curl -X POST http://localhost:8000/api/v1/cando/create \
  -H "Content-Type: application/json" \
  -d '{
    "descriptionEn": "Can talk about travel and transportation"
  }'
```

### Create New CanDo via Frontend

1. Navigate to `/cando` page
2. Click "Create New CanDo" button
3. Fill in at least one description (English or Japanese)
4. Click "Create CanDo"
5. System automatically:
   - Translates if needed
   - Generates titles
   - Infers fields
   - Generates embeddings
   - Creates similarity relationships

## Data Model Changes

### New Properties

- `CanDoDescriptor.titleEn` - String (AI-generated English title)
- `CanDoDescriptor.titleJa` - String (AI-generated Japanese title)

### New Source

- `CanDoDescriptor.source = "manual"` - For manually created CanDo-s

## Automatic Processing Pipeline

When a new CanDo is created:

1. **Translation** (if needed)
   - If only English provided → Translate to Japanese
   - If only Japanese provided → Translate to English

2. **Field Inference** (AI)
   - Level (A1-C2)
   - Primary Topic (Japanese and English)
   - Skill Domain (産出/受容/やりとり)
   - Type (言語活動, etc.)

3. **Title Generation** (AI)
   - Generate `titleEn` (full sentence starting with "Can...")
   - Generate `titleJa` (full sentence in Japanese)

4. **Embedding Generation**
   - Create vector embedding from combined descriptions
   - Store in `descriptionEmbedding` property

5. **Similarity Relationships**
   - Find similar CanDoDescriptors using vector search
   - Create `SEMANTICALLY_SIMILAR` relationships with metadata

## Files Created

1. `backend/app/services/cando_title_service.py`
2. `backend/app/services/cando_creation_service.py`
3. `resources/generate_cando_titles.py`
4. `frontend/src/app/cando/create/page.tsx`
5. `backend/tests/test_cando_title_service.py`
6. `backend/tests/test_cando_creation_service.py`
7. `docs/CANDO_TITLE_AND_CREATION_IMPLEMENTATION.md`

## Files Modified

1. `backend/app/api/v1/endpoints/cando.py` - Added `/create` endpoint, updated `/list`
2. `backend/app/services/cando_embedding_service.py` - Added title generation check
3. `frontend/src/lib/api.ts` - Added `createCanDo()` function
4. `frontend/src/app/cando/page.tsx` - Added "Create New CanDo" button

## Next Steps

1. Run migration script to generate titles for existing CanDo-s:
   ```powershell
   poetry run python ../resources/generate_cando_titles.py
   ```

2. Test the creation endpoint:
   ```bash
   curl -X POST http://localhost:8000/api/v1/cando/create \
     -H "Content-Type: application/json" \
     -d '{"descriptionEn": "Can understand basic greetings"}'
   ```

3. Test the frontend UI:
   - Navigate to `/cando/create`
   - Create a test CanDo
   - Verify all fields are generated correctly

## Notes

- All processing runs synchronously (immediately on creation)
- Translation uses AI (OpenAI GPT-4o-mini)
- Field inference uses AI with JSON response format
- Title generation uses AI with specific prompts
- UID format: `manual:{timestamp}` or `manual:{timestamp}:{counter}` if collision
- All generated fields are stored in Neo4j
- Similarity relationships are created automatically with threshold 0.65

---

**Implementation Date**: 2025-11-15  
**Status**: ✅ Complete and Ready for Testing

