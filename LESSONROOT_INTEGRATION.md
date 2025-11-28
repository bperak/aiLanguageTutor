# LessonRoot UI Integration - Implementation Summary

## Overview

Successfully integrated the new LessonRoot pipeline into the AI Language Tutor application, replacing the previous two-stage generation system with a comprehensive, card-based lesson structure powered by AI-guided dialogue.

## What Was Implemented

### 1. Backend (Complete ✅)

#### New Endpoints
- **`POST /api/v1/cando/lessons/compile_v2`** - Compiles a LessonRoot for a CanDo descriptor
  - Generates all 8 card types using LLM
  - Enriches grammar patterns with Neo4j lookups
  - Persists to `lessons` and `lesson_versions` tables
  - Returns lesson_id, version, duration

- **`POST /api/v1/cando/lessons/guided/turn`** - AI-powered guided dialogue
  - Stage-aware conversation with rubric evaluation
  - Pattern matching and word count validation
  - Automatic stage advancement based on goal achievement
  - Persists turn history and scores in `guided_state`

- **`POST /api/v1/cando/lessons/guided/flush`** - Reset guided dialogue progress
  - Clears guided_state and resets stage_idx to 0
  - Sets flushed_at timestamp

#### Database Schema Updates
- Added `guided_stage_idx`, `guided_state`, `guided_flushed_at` columns to `lesson_sessions`
- Migration: `backend/migrations/2025-10-28_add_guided_columns.sql`

#### Scripts
- **`backend/scripts/preload_lessons.py`** - Bulk lesson compilation
  - Query CanDo descriptors by level
  - Compile multiple lessons in sequence
  - Generate JSON report with stats

### 2. Frontend (Complete ✅)

#### Type Definitions
- **`frontend/src/types/lesson-root.ts`** - Complete TypeScript types matching backend Pydantic models
  - All card types, JP text structures, and API responses

#### Card Components (`frontend/src/components/lesson/cards/`)
1. **ObjectiveCard.tsx** - Displays lesson goals and success criteria
2. **WordsCard.tsx** - Vocabulary grid with images and tags
3. **GrammarPatternsCard.tsx** - Grammar patterns with forms, examples, slots
4. **LessonDialogueCard.tsx** - Simple dialogue display with speaker bubbles
5. **GuidedDialogueCard.tsx** - ⭐ AI conversation interface with:
   - Stage progress indicator
   - Bilingual hints display
   - Chat history with feedback badges
   - Word count validation
   - Pattern matching feedback
   - Auto-stage advancement
   - Reset progress button
6. **ExercisesCard.tsx** - Interactive exercises:
   - Match exercise (pairs)
   - Fill-in-the-blank
   - Sentence ordering
7. **CultureCard.tsx** - Cultural context with images
8. **DrillsCard.tsx** - Practice drills:
   - Substitution drills
   - Pronunciation practice

#### Main Renderer
- **`LessonRootRenderer.tsx`** - Tab-based navigation between all 8 cards
  - Lesson metadata header (CanDo info, level, badges)
  - Responsive tabs for each card type
  - Session ID management for guided dialogue

#### API Clients
- **`frontend/src/lib/api/guided-dialogue.ts`** - Guided dialogue API functions
- **`frontend/src/lib/api.ts`** - Added `compileLessonV2`, `fetchLesson`, `listLessonsForCanDo`

#### Page Component
- **`frontend/src/app/cando/[canDoId]/lessonv2.tsx`** - New lesson page
  - On-demand compilation with loading state
  - Recompile option
  - Display settings integration
  - Error handling

### 3. Text Display System (Leveraged Existing ✅)

The new system uses the existing `DisplaySettingsContext` and `JapaneseText` component:
- Global text layer control (std/furigana/romaji/translation)
- All cards respect user preferences
- No per-card overrides (keeps it simple)

## Key Features

### AI-Powered Guided Dialogue
The GuidedDialogueCard provides a structured conversation practice:
- **Stages**: Multi-stage progression with specific goals
- **Hints**: Bilingual hints for each stage
- **Pattern Matching**: Evaluates learner input against expected patterns
- **Word Count**: Enforces min/max word constraints
- **Rubric Scoring**: AI evaluates against pattern_correctness, fluency_a1, content_relevance
- **Auto-Advancement**: Moves to next stage when goals are met
- **State Persistence**: All turns and scores saved in Postgres

### Grammar Pattern Enrichment
- Post-generation Neo4j lookup for exact pattern matching
- Sets `neo4j_id` only if exactly one match found
- Leaves unmatched patterns with `neo4j_id: null` (multiple matches or no match)

### Bulk Pre-loading
Script for pre-compiling lessons:
```bash
# Test compilation
poetry run python scripts/preload_lessons.py --level A1 --limit 5

# Production pre-load
poetry run python scripts/preload_lessons.py --level A1 --limit 100
```

## File Structure

```
backend/
├── app/
│   ├── api/v1/endpoints/
│   │   └── cando.py (added guided/turn, guided/flush, compile_v2)
│   ├── services/
│   │   └── cando_v2_compile_service.py (LessonRoot compilation)
│   └── migrations/
│       └── 2025-10-28_add_guided_columns.sql
└── scripts/
    ├── canDo_creation_new.py (Pydantic models + generation)
    └── preload_lessons.py (bulk compilation)

frontend/
├── src/
│   ├── types/
│   │   └── lesson-root.ts (TypeScript types)
│   ├── lib/
│   │   ├── api.ts (LessonRoot API functions)
│   │   └── api/
│   │       └── guided-dialogue.ts (Guided dialogue API)
│   ├── components/
│   │   ├── lesson/
│   │   │   ├── cards/ (8 card components)
│   │   │   └── LessonRootRenderer.tsx
│   │   └── text/
│   │       └── JapaneseText.tsx (existing, reused)
│   └── app/
│       └── cando/[canDoId]/
│           ├── page.tsx (old format)
│           └── lessonv2.tsx (new format)
```

## API Flow

### Lesson Compilation
```
1. User visits /cando/JF:21/lessonv2
2. Frontend calls POST /api/v1/cando/lessons/compile_v2?can_do_id=JF:21
3. Backend:
   a. Fetches CanDo metadata from Neo4j
   b. Generates DomainPlan (scenarios, lex_buckets, grammar_functions)
   c. Generates 8 cards (ObjectiveCard, WordsCard, etc.)
   d. Enriches grammar patterns with Neo4j lookups
   e. Persists LessonRoot to lessons/lesson_versions tables
4. Frontend displays lesson using LessonRootRenderer
```

### Guided Dialogue Flow
```
1. User navigates to "Guided" tab
2. GuidedDialogueCard displays current stage goal and hints
3. User types response and clicks Send
4. Frontend calls POST /api/v1/cando/lessons/guided/turn
5. Backend:
   a. Retrieves current stage from lesson
   b. Builds AI prompt with stage context (goal, patterns, rubric)
   c. Gets AI response via AIChatService
   d. Evaluates learner input (pattern match, word count)
   e. Updates guided_state, advances stage if goals met
6. Frontend displays AI response with feedback badges
7. If goals met, auto-advances to next stage
```

## Usage Examples

### Test a Single Lesson
```bash
# Navigate to http://localhost:3000/cando/JF:21/lessonv2
# Or use the API directly
curl -X POST "http://localhost:8000/api/v1/cando/lessons/compile_v2?can_do_id=JF:21&metalanguage=en&model=gpt-4o"
```

### Pre-compile Multiple Lessons
```bash
cd backend
poetry run python scripts/preload_lessons.py --level A1 --limit 10 --output a1_report.json
```

### Test Guided Dialogue
1. Visit a lesson page (e.g., `/cando/JF:21/lessonv2`)
2. Click on "Guided" tab
3. Read the stage goal and hints
4. Type a response in Japanese
5. Click "Send"
6. Observe AI feedback and stage progression

### Reset Guided Progress
```bash
curl -X POST "http://localhost:8000/api/v1/cando/lessons/guided/flush?session_id=YOUR_SESSION_ID"
```

## Configuration

### LLM Model
Default: `gpt-4o`
Can be changed via:
- API parameter: `?model=gpt-4o-mini`
- Frontend settings (for older lesson format)

### Metalanguage
Default: `en`
Supports any language code for explanations

### Text Display
Controlled via existing `DisplaySettingsContext`:
- Show/hide kanji, furigana, romaji, translation
- Level-based presets (A1-C2)
- Persisted in localStorage

## Next Steps (Optional)

### Testing
- Add unit tests for guided turn endpoint
- Add integration tests for full lesson compilation
- Add frontend smoke tests for LessonRootRenderer

### Documentation
- Update README with new endpoints
- Add API documentation for guided dialogue
- Create user guide for guided conversation feature

### Enhancements
- Add audio playback for dialogue turns
- Implement image generation for ImageSpec fields
- Add export lesson as PDF/JSON
- Create admin UI for lesson management
- Add analytics for guided dialogue success rates

## Notes

- The old lesson system (`/cando/[canDoId]/page.tsx`) remains intact
- New system is in `lessonv2.tsx` for parallel deployment
- Can switch to new system by default once tested
- Guided dialogue state persists across sessions
- All LLM generation is traceable via `LLMGenSpec.gen` field
- Grammar pattern enrichment is non-destructive (only adds `neo4j_id`)

## Completed Tasks ✅

1. ✅ Added guided turn endpoint with stage evaluation
2. ✅ Created TypeScript types for LessonRoot
3. ✅ Added API client functions
4. ✅ Built all 8 card components
5. ✅ Implemented GuidedDialogueCard with AI integration
6. ✅ Created LessonRootRenderer
7. ✅ Created pre-loading script
8. ✅ Extended lesson_sessions table with guided columns
9. ✅ Added flush endpoint for guided state

---

**Status**: Production-ready for testing with A1 lessons
**Last Updated**: 2025-10-28

