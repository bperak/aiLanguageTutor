<!-- 15ff37d2-6081-4153-ad57-69337ed2dc24 763423a9-6cd1-4e56-aa5b-ad431e231d73 -->
# CanDo Title Generation and Manual Creation

## Overview

1. Add `titleEn` and `titleJa` properties to all existing CanDoDescriptor nodes (AI-generated from descriptions)
2. Set up automatic procedure for future CanDo-s (runs immediately on creation)
3. Enable manual creation of new CanDo from frontend (minimal fields - descriptions only)

## Implementation Plan

### 1. Title Generation Service

**File**: `backend/app/services/cando_title_service.py` (new)

- Create `CanDoTitleService` class
- Method: `generate_title(description_en: str, description_ja: str, language: str) -> str`
  - Uses `AIChatService` to generate concise full-sentence titles
  - Prompt: "Generate a concise full-sentence title (starting with 'Can...') from this CanDo description: {description}"
  - Returns title in requested language (en/ja)
- Method: `generate_titles(description_en: str, description_ja: str) -> Dict[str, str]`
  - Generates both titleEn and titleJa in parallel
  - Returns `{"titleEn": "...", "titleJa": "..."}`

### 2. Migration Script for Existing CanDoDescriptors

**File**: `resources/generate_cando_titles.py` (new)

- Fetches all CanDoDescriptors without titles
- Generates titles in batches using `CanDoTitleService`
- Updates nodes with `titleEn` and `titleJa` properties
- Progress tracking and error handling
- Supports `--dry-run` and `--batch-size` options

### 3. Automatic Procedure for New CanDo-s

**File**: `backend/app/services/cando_creation_service.py` (new)

- Create `CanDoCreationService` class
- Method: `create_cando_with_auto_processing(description_en: str, description_ja: str, session: AsyncSession) -> Dict[str, Any]`
  - Creates CanDoDescriptor node with minimal fields
  - Infers: uid (auto-generated), level (from description analysis), topic (from description), skillDomain (default), type (default), source ("manual")
  - Immediately runs:

    1. Generate titles (titleEn, titleJa) using `CanDoTitleService`
    2. Generate embedding using `CanDoEmbeddingService.update_cando_embedding()`
    3. Create similarity relationships using `CanDoEmbeddingService.update_similarity_for_cando()`

  - Returns created CanDoDescriptor with all properties

### 4. API Endpoint for Manual Creation

**File**: `backend/app/api/v1/endpoints/cando.py` (modify)

- Add POST endpoint: `@router.post("/create")`
- Request body schema:
  ```python
  class CreateCanDoRequest(BaseModel):
      descriptionEn: str
      descriptionJa: str
  ```

- Endpoint logic:
  - Validates descriptions are not empty
  - Calls `CanDoCreationService.create_cando_with_auto_processing()`
  - Returns created CanDoDescriptor with all generated fields
- Error handling for creation failures

### 5. Frontend UI for Manual Creation

**File**: `frontend/src/app/cando/create/page.tsx` (new)

- Form with two text areas:
  - `descriptionEn` (English description)
  - `descriptionJa` (Japanese description)
- Submit button that calls `POST /api/v1/cando/create`
- Loading state during creation and auto-processing
- Success: Redirect to created CanDo detail page
- Error handling with user-friendly messages
- Optional: Preview of what will be generated (titles, inferred fields)

**File**: `frontend/src/lib/api.ts` (modify)

- Add `createCanDo(descriptionEn: string, descriptionJa: string)` function
- Handles API call to `/api/v1/cando/create`

### 6. Update Existing Services

**File**: `backend/app/services/cando_embedding_service.py` (modify)

- Update `update_cando_embedding()` to also check/update titles if missing
- Ensure compatibility with new title fields

**File**: `backend/app/api/v1/endpoints/cando.py` (modify)

- Update `/list` endpoint to include `titleEn` and `titleJa` in response
- Update other endpoints that return CanDoDescriptor data to include titles

### 7. Tests

**File**: `backend/tests/test_cando_title_service.py` (new)

- Test title generation for English and Japanese
- Test batch title generation
- Mock AI service calls

**File**: `backend/tests/test_cando_creation_service.py` (new)

- Test CanDo creation with auto-processing
- Test title generation integration
- Test embedding generation integration
- Test similarity relationship creation integration

## Files to Create

1. `backend/app/services/cando_title_service.py` - Title generation service
2. `backend/app/services/cando_creation_service.py` - Creation service with auto-processing
3. `resources/generate_cando_titles.py` - Migration script for existing CanDo-s
4. `frontend/src/app/cando/create/page.tsx` - Frontend creation UI
5. `backend/tests/test_cando_title_service.py` - Title service tests
6. `backend/tests/test_cando_creation_service.py` - Creation service tests

## Files to Modify

1. `backend/app/api/v1/endpoints/cando.py` - Add POST `/create` endpoint, update list endpoint
2. `backend/app/services/cando_embedding_service.py` - Ensure title compatibility
3. `frontend/src/lib/api.ts` - Add createCanDo function

## Implementation Order

1. Create `CanDoTitleService` with title generation methods
2. Create migration script to add titles to existing CanDo-s
3. Create `CanDoCreationService` with auto-processing
4. Add POST `/create` API endpoint
5. Create frontend UI for manual creation
6. Update existing endpoints to include titles
7. Add tests

## Notes

- Title format: Full sentence starting with "Can..." (e.g., "Can talk about travel and transportation")
- Auto-processing runs synchronously (immediately on creation)
- Minimal fields required: Only `descriptionEn` and `descriptionJa`
- Other fields inferred: uid (auto-generated), level (from description), topic (from description), skillDomain (default), type (default), source ("manual")
- All processing (titles, embeddings, relationships) happens automatically on creation

### To-dos

- [x] Create migration script to generate embeddings for all existing CanDoDescriptors