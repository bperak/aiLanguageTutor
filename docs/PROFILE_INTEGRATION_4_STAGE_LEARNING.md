# Profile Integration with 4-Stage Learning Progression

## Overview

This document describes how user profiles and learning paths integrate with the 4-stage learning progression (Content → Comprehension → Production → Interaction) for personalized lesson generation.

## User Journey Flow

```
Profile Building → Learning Path Generation → CanDo Lesson (4-Stage) → Progress Tracking
```

### 1. Profile Building

**Entry Point**: `/profile/build`
**Component**: `ProfileBuildingChat.tsx`

**Process**:
- User answers questions about:
  - Learning goals (e.g., "I want to travel to Japan")
  - Previous knowledge (languages, Japanese experience)
  - Learning experiences (formal classes, self-study, etc.)
  - Usage context (primary use case, frequency)
- Profile data saved to `user_profiles` table
- Profile completion triggers learning path generation

**Output**: `UserProfile` object with:
- `learning_goals`: List of goals
- `previous_knowledge`: Dict with languages, experience
- `learning_experiences`: Dict with formal/self-study info
- `usage_context`: Dict with use case, frequency
- `additional_notes`: Free text

### 2. Learning Path Generation

**Trigger**: Profile completion
**Service**: `LearningPathService.generate_learning_path()`

**Process**:
1. Analyze profile for path requirements
2. Select initial CanDo descriptors based on:
   - User's current level
   - Learning goals
   - Usage context
3. Build semantic path with complexity ordering
4. Generate pre-lesson kits for each CanDo step
5. Save path to `learning_paths` table

**Output**: `LearningPathData` with:
- `steps[]`: Each step contains:
  - `can_do_id`: CanDo descriptor ID
  - `prelesson_kit`: Words, grammar, phrases needed before lesson
  - `can_do_context`: Situation, pragmatic act, notes

### 3. CanDo Lesson Compilation (4-Stage)

**Entry Point**: `/cando/[canDoId]`
**Service**: `compile_lessonroot()`

**Inputs**:
- `can_do_id`: CanDo descriptor ID
- `user_id`: Optional user ID (for profile/kit integration)
- `metalanguage`: Language for instructions
- `model`: LLM model

**Profile Integration Process**:

1. **Fetch Pre-Lesson Kit** (if `user_id` provided):
   - Query user's active learning path
   - Extract pre-lesson kit for this CanDo
   - Build kit context (words, grammar, phrases)
   - Calculate usage requirements

2. **Fetch Profile Context** (if `user_id` provided):
   - Query `user_profiles` table
   - Extract:
     - Learning goals
     - Previous knowledge
     - Usage context
     - Current level
   - Build profile context string

3. **Domain Plan Generation**:
   - Combine kit context + profile context
   - Pass to `gen_domain_plan()`
   - Plan includes:
     - Communicative functions
     - Scenarios (aligned with user's usage context)
     - Vocabulary buckets
     - Grammar functions
     - Cultural themes (aligned with user's goals)

4. **4-Stage Generation** (all stages receive kit + profile context):
   - **Content Stage**: Objective, Vocabulary, Grammar, Formulaic Expressions, Dialogue, Culture
     - Dialogue scenarios align with user's usage context
     - Vocabulary includes kit words
     - Cultural themes match user's learning goals
   
   - **Comprehension Stage**: Reading, Comprehension Exercises, AI Comprehension Tutor
     - Exercises align with user's current level
     - Reading content matches user's interests/goals
   
   - **Production Stage**: Guided Dialogue, Production Exercises, AI Production Evaluator
     - Exercises use scenarios from user's usage context
     - Personalization tasks align with learning goals
   
   - **Interaction Stage**: Interactive Dialogue, Interaction Activities, AI Scenario Manager
     - Scenarios match user's real-world usage needs
     - Cultural notes adapted to user's context

**Output**: Complete `LessonRoot` with all 4 stages personalized

### 4. Progress Tracking

**Integration**: Progress API tracks completion across all 4 stages
- Content stage completion
- Comprehension stage completion
- Production stage completion
- Interaction stage completion

**Evidence Recording**: User interactions in each stage are recorded
- AI tutor interactions
- Exercise attempts
- Production evaluations
- Scenario interactions

## Technical Implementation

### Profile Context Fetching

**Location**: `backend/app/services/cando_v2_compile_service.py`

```python
# Fetch user profile data for personalization context
profile_context = ""
if user_id:
    # Query user_profiles and users tables
    # Extract learning goals, previous knowledge, usage context, current level
    # Build formatted context string
    profile_context = "\n\n**User Profile Context (personalize lesson accordingly):**\n..."
```

### Context Integration

**Domain Plan Generation**:
```python
plan = await asyncio.to_thread(
    pipeline.gen_domain_plan,
    llm_call_main,
    cando_input,
    metalanguage,
    kit_context=kit_context + profile_context,  # Combined context
    kit_requirements=kit_requirements,
)
```

**All Stage Generation**:
```python
content_cards = await pipeline.gen_content_stage(
    ...,
    kit_context=kit_context + profile_context,  # Profile context included
    kit_requirements=kit_requirements,
)
```

### Prompt Updates

**Domain Plan Prompt** (`build_planner_prompt`):
- Includes kit context (words, grammar, phrases)
- Includes profile context (goals, usage, level)
- Instructions to personalize scenarios and cultural themes

**All Card Generation Prompts**:
- Include kit context for vocabulary/grammar alignment
- Include profile context for personalization
- Explicit instructions to align with user's goals and usage context

## Personalization Examples

### Example 1: Travel Goal

**Profile**:
- Learning goal: "I want to travel to Japan"
- Usage context: Primary use case = "Travel"

**Lesson Personalization**:
- Scenarios: Airport, hotel, restaurant, shopping
- Vocabulary: Travel-related words (切符, ホテル, 予約)
- Cultural themes: Japanese travel etiquette, transportation systems
- Interaction activities: Booking hotel, ordering food, asking directions

### Example 2: Business Goal

**Profile**:
- Learning goal: "I need Japanese for business"
- Usage context: Primary use case = "Professional"

**Lesson Personalization**:
- Scenarios: Business meetings, email communication, presentations
- Vocabulary: Business terms (会議, 提案, 契約)
- Cultural themes: Japanese business etiquette, keigo usage
- Interaction activities: Business negotiations, formal presentations

### Example 3: Academic Goal

**Profile**:
- Learning goal: "I'm studying Japanese at university"
- Usage context: Primary use case = "Academic"

**Lesson Personalization**:
- Scenarios: Classroom discussions, academic presentations
- Vocabulary: Academic terms (研究, 論文, 発表)
- Cultural themes: Academic culture, formal register
- Interaction activities: Academic discussions, presentations

## Benefits

1. **Relevance**: Lessons align with user's actual needs and goals
2. **Engagement**: Content matches user's interests and usage context
3. **Efficiency**: Pre-lesson kits ensure vocabulary/grammar continuity
4. **Progression**: Learning path guides user through appropriate CanDo sequence
5. **Adaptation**: All 4 stages adapt to user's profile

## Data Flow

```
User Profile (user_profiles table)
    ↓
Learning Path Generation (learning_paths table)
    ↓
Pre-Lesson Kit (in path steps)
    ↓
CanDo Lesson Compilation
    ├─ Domain Plan (with profile context)
    ├─ Content Stage (personalized scenarios)
    ├─ Comprehension Stage (level-appropriate)
    ├─ Production Stage (goal-aligned exercises)
    └─ Interaction Stage (usage-context scenarios)
    ↓
Progress Tracking (4-stage completion)
```

## API Integration

**Compilation Endpoint**:
```
POST /api/v1/cando/lessons/compile_v2_stream?can_do_id={id}&user_id={user_id}
```

**Profile Context**:
- Automatically fetched if `user_id` provided
- Combined with kit context
- Passed to all generation stages

**Frontend**:
- Automatically includes `user_id` when user is authenticated
- Displays kit usage statistics
- Shows personalized content

## Future Enhancements

1. **Adaptive Difficulty**: Adjust difficulty based on user's performance in previous stages
2. **Goal-Specific Content**: Generate additional content based on specific learning goals
3. **Usage Context Scenarios**: More detailed scenario customization based on usage context
4. **Progress-Based Personalization**: Use progress data to further personalize future lessons
5. **Cultural Context Adaptation**: Deeper cultural customization based on user's background

