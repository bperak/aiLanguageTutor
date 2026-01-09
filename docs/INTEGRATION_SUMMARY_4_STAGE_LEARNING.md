# 4-Stage Learning Integration Summary

## User Flow Integration

### Entry Point
- **Route**: `/cando/[canDoId]`
- **Component**: `frontend/src/app/cando/[canDoId]/page.tsx`
- **User Journey**:
  1. User navigates to a CanDo lesson page
  2. System creates/retrieves lesson session
  3. System attempts to fetch existing lesson from database
  4. If no lesson exists, triggers compilation via `compileLessonV2Stream`
  5. Lesson is displayed with 4-stage progress tracking

### Compilation Flow

**Inputs**:
- `can_do_id`: CanDo descriptor ID (from URL)
- `metalanguage`: Language for instructions (default: "en")
- `model`: LLM model (default: "gpt-4.1")
- `user_id`: Optional user ID for pre-lesson kit integration
- `fast_model`: Optional override for fast model

**Process**:
1. **Plan Generation** (5% progress)
   - Generates domain plan with vocabulary buckets, grammar functions, scenarios
   - Output: `DomainPlan` object

2. **Content Stage** (20% progress)
   - Generates: Objective, Vocabulary, Grammar, Formulaic Expressions, Dialogue, Culture
   - Parallel generation within stage (except Objective which depends on plan)
   - Output: Dictionary with all content cards

3. **Comprehension Stage** (50% progress)
   - Generates Reading first (depends on Dialogue)
   - Then generates Comprehension Exercises and AI Comprehension Tutor in parallel
   - Output: Dictionary with reading, exercises, and tutor cards

4. **Production Stage** (75% progress)
   - Generates: Guided Dialogue, Production Exercises, AI Production Evaluator
   - All generated in parallel
   - Output: Dictionary with all production cards

5. **Interaction Stage** (90% progress)
   - Generates: Interactive Dialogue, Interaction Activities, AI Scenario Manager
   - All generated in parallel
   - Output: Dictionary with all interaction cards

6. **Assembly** (95% progress)
   - Assembles all cards into `LessonRoot` structure
   - Saves to database (lessons + lesson_versions tables)
   - Output: Complete `LessonRoot` JSON

**Outputs**:
- `lesson_id`: Database ID of saved lesson
- `version`: Version number
- `lesson`: Complete `LessonRoot` structure
- `prelesson_kit_usage`: Optional kit usage statistics

### Display Flow

**Page Structure**:
```
CanDoDetailPage
├── Progress Tracking Card (if progress loaded)
│   ├── 4 Stage Tabs (Content, Comprehension, Production, Interaction)
│   ├── Progress Bars per Stage
│   └── Stage Completion Buttons
├── LessonRootRenderer (for each stage tab)
│   ├── Lesson Header (title, description, badges)
│   └── 4-Stage Tabs
│       ├── Content Tab
│       │   ├── Objective
│       │   ├── Vocabulary
│       │   ├── Grammar
│       │   ├── Formulaic Expressions
│       │   ├── Dialogue
│       │   └── Culture
│       ├── Comprehension Tab
│       │   ├── Reading
│       │   ├── Comprehension Exercises
│       │   └── AI Comprehension Tutor
│       ├── Production Tab
│       │   ├── Guided Dialogue
│       │   ├── Production Exercises
│       │   └── AI Production Evaluator
│       └── Interaction Tab
│           ├── Interactive Dialogue
│           ├── Interaction Activities
│           └── AI Scenario Manager
└── Evidence Summary Card (if evidence exists)
```

### Progress Tracking Integration

**API Endpoints**:
- `GET /api/v1/cando/lessons/{can_do_id}/progress?session_id={session_id}`
  - Returns stage completion status, mastery levels, next recommended stage
- `POST /api/v1/cando/lessons/{can_do_id}/stages/{stage}/complete?session_id={session_id}&mastery_level={level}`
  - Marks a stage as complete
- `POST /api/v1/cando/lessons/{can_do_id}/evidence/record`
  - Records learning evidence (interactions, attempts, scores)

**Progress Data Structure**:
```typescript
{
  can_do_id: string
  session_id?: string
  stages: {
    content?: { completed: boolean, mastery_level: number, last_attempted?: string }
    comprehension?: { completed: boolean, mastery_level: number, last_attempted?: string }
    production?: { completed: boolean, mastery_level: number, last_attempted?: string }
    interaction?: { completed: boolean, mastery_level: number, last_attempted?: string }
  }
  next_recommended_stage?: string
  all_complete: boolean
}
```

**Stage Selection Logic**:
1. If `next_recommended_stage` exists, use it
2. Otherwise, find first incomplete stage (content → comprehension → production → interaction)
3. If all complete, default to content

### AI Component Integration

**Session Management**:
- All AI components require `sessionId` and `canDoId`
- Session is created before lesson compilation via `/api/v1/cando/lessons/session/create`
- Session persists lesson state, stage progress, and interaction history

**API Endpoints for AI Components**:
1. **Comprehension Tutor**: `/api/v1/cando/lessons/comprehension/ai-tutor/turn`
   - Input: `session_id`, `can_do_id`, `stage_idx`, `learner_input`
   - Output: AI response with feedback, comprehension score, keywords found

2. **Production Evaluator**: `/api/v1/cando/lessons/production/ai-evaluator/evaluate`
   - Input: `session_id`, `can_do_id`, `stage_idx`, `learner_input`
   - Output: AI response with rubric scores (pattern_correctness, fluency, content_relevance)

3. **Interactive Dialogue**: `/api/v1/cando/lessons/interaction/conversation/turn`
   - Input: `session_id`, `can_do_id`, `stage_idx`, `learner_input`
   - Output: AI response with teaching direction

4. **Scenario Manager**: `/api/v1/cando/lessons/interaction/scenario-manager/turn`
   - Input: `session_id`, `can_do_id`, `stage_idx`, `learner_input`
   - Output: AI response with cultural notes and teaching direction

**Data Flow for AI Components**:
1. User interacts with AI component (types input, submits)
2. Frontend calls API endpoint with session/lesson data
3. Backend retrieves lesson from session or database
4. Backend extracts relevant card (e.g., `ai_comprehension_tutor`)
5. Backend calls AI service with stage-specific prompt
6. Backend parses structured AI response
7. Backend returns formatted response to frontend
8. Frontend displays response and updates UI

### Pre-Lesson Kit Integration

**Input**:
- `user_id`: Optional user ID parameter
- System fetches active learning path for user
- System extracts pre-lesson kit for the CanDo

**Process**:
- Kit context and requirements are passed to all stage generation functions
- Generation prompts include kit vocabulary, grammar, and phrases
- Kit usage is tracked during compilation

**Output**:
- `prelesson_kit_usage`: Statistics showing:
  - Words used vs. required
  - Grammar patterns used vs. required
  - Phrases used vs. required
  - Overall usage percentage
  - Whether all requirements are met

**Display**:
- Kit availability badge shown at top of lesson page
- Detailed usage statistics displayed in card
- Visual indicators for requirement compliance

### Error Handling

**Compilation Errors**:
- Progress callbacks include error events
- Frontend displays error messages with retry option
- Backend logs errors with traceback

**API Errors**:
- All AI endpoints have try-catch blocks
- HTTPException for expected errors (404, 400)
- 500 errors with detailed messages for unexpected errors
- Frontend displays user-friendly error messages

**Missing Data**:
- All components check for optional cards
- Fallback messages when cards are missing
- Graceful degradation when data is incomplete

### Backward Compatibility

**Legacy Cards**:
- `ExercisesCard` still supported (fallback for comprehension/production)
- `DrillsCard` still supported
- Old lesson formats can still be displayed

**Data Migration**:
- New cards are optional in `CardsContainer`
- Old lessons work without new cards
- System gracefully handles missing new card types

## Integration Checklist

✅ **Compilation Flow**
- Sequential stage generation implemented
- Progress callbacks working
- Pre-lesson kit integration working
- Error handling comprehensive

✅ **Display Flow**
- 4-stage tabs in LessonRootRenderer
- Stage-specific content organized correctly
- Progress tracking integrated
- Stage completion buttons working

✅ **AI Components**
- All 4 AI endpoints implemented
- Frontend components connected to APIs
- Session management working
- Error handling in place

✅ **Progress Tracking**
- Progress API endpoints compatible with 4 stages
- Stage completion tracking working
- Evidence recording structure supports new stages
- Next recommended stage logic working

✅ **User Experience**
- Loading messages reflect 4-stage structure
- Progress bars show stage-specific progress
- Stage selection based on completion status
- Smooth transitions between stages

## Testing Recommendations

1. **End-to-End Compilation**:
   - Test compilation with and without pre-lesson kit
   - Verify all 4 stages generate correctly
   - Check progress callbacks fire correctly

2. **Display Integration**:
   - Test lesson display with all card types
   - Verify stage tabs switch correctly
   - Check progress tracking updates

3. **AI Component Integration**:
   - Test each AI endpoint with valid/invalid inputs
   - Verify session management
   - Check error handling

4. **Progress Tracking**:
   - Test stage completion marking
   - Verify progress retrieval
   - Check evidence recording

5. **Backward Compatibility**:
   - Test old lesson formats still display
   - Verify missing new cards handled gracefully
   - Check fallback behavior

## Known Limitations

1. **Evidence Recording**: AI components don't automatically record evidence yet (can be added as enhancement)
2. **Stage Progression**: Manual stage completion buttons (could be automated based on activity)
3. **Adaptive Difficulty**: Not yet implemented (planned enhancement)

## Future Enhancements

1. Automatic evidence recording from AI interactions
2. Adaptive difficulty based on performance
3. Conversation history tracking
4. Enhanced cultural context provider
5. Real-time progress updates during interactions

