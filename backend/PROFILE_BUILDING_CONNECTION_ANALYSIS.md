# Profile Building → Lesson Plan → Lesson Creation Connection Analysis

**Date:** 2025-12-30  
**Status:** ✅ **IMPROVED** - Profile context now explicitly passed and used in all stage prompts

## Executive Summary

Profile building **IS connected** to lesson compilation, but there's a **critical gap**: Profile context is fetched and passed to all stages, but the prompt builders for Content, Comprehension, Production, and Interaction stages don't explicitly instruct the LLM on how to use profile data for personalization.

## Current Flow

### 1. Profile Building ✅
- **Service**: `app/services/profile_building_service.py`
- **Data Collected**:
  - Learning goals (basic + path-level structures)
  - Previous knowledge (experience level, years studying, specific areas known/unknown)
  - Learning experiences (preferred methods, learning style, **4-stage preferences**: grammar_focus_areas, preferred_exercise_types, interaction_preferences)
  - Usage context (contexts, urgency, **register_preferences**, **formality_contexts**, **scenario_details**)
  - Cultural interests/background
  - Path-level structures (vocabulary/grammar/expressions goals, known items, learning targets)
- **Storage**: Saved to `user_profiles` table (JSONB fields)

### 2. Profile Context Building ✅
- **Function**: `_build_user_profile_context()` in `cando_v2_compile_service.py`
- **What it does**:
  - Fetches `UserProfile` and `User` from database
  - Formats profile data into a context string
  - Includes all profile fields (learning goals, previous knowledge, usage context, learning preferences, path-level structures)
  - Returns formatted string: `"\n\n**User Profile Context (personalize lesson accordingly):**\n- ..."`
- **Called from**: `compile_lessonroot()` and `regenerate_lesson_stage()`

### 3. Profile Context Usage in Compilation ⚠️

#### DomainPlan (Planner) ✅ **EXPLICITLY USES PROFILE**
- **File**: `scripts/cando_creation/prompts/planner.py`
- **Profile parameter**: `profile_context: str = ""`
- **Prompt includes**: Explicit personalization instructions:
  ```
  PERSONALIZATION:
  - Consider user profile context when selecting scenarios, vocabulary, and cultural themes.
  - Use register_preferences from profile to select appropriate register for scenarios (plain/polite/neutral).
  - Use cultural_interests from profile to select relevant cultural themes.
  - Use scenario_details from profile to create specific, relevant scenarios.
  - Use grammar_focus_areas from profile to emphasize relevant grammar functions.
  - Align content with user's learning goals and usage context.
  - Ensure difficulty matches user's current level.
  - If path-level structures (vocabulary_domain_goals, grammar_progression_goals) are provided, incorporate them into the plan.
  ```
- **Status**: ✅ **FULLY CONNECTED**

#### Content Stage ❌ **IMPLICITLY USES PROFILE (via kit_context)**
- **Files**: `scripts/cando_creation/prompts/content.py`
- **Functions**: `build_objective_prompt()`, `build_words_prompt()`, `build_grammar_prompt()`, `build_dialogue_prompt()`, `build_reading_prompt()`
- **Profile parameter**: ❌ **NONE** - Only accepts `kit_context` and `kit_requirements`
- **How profile is passed**: Profile context is concatenated with kit_context: `kit_context + profile_context`
- **Prompt instructions**: ❌ **NO EXPLICIT PROFILE PERSONALIZATION INSTRUCTIONS**
- **Status**: ⚠️ **PARTIALLY CONNECTED** - Profile data is in the prompt string but LLM isn't explicitly told how to use it

#### Comprehension Stage ❌ **IMPLICITLY USES PROFILE (via kit_context)**
- **Files**: `scripts/cando_creation/prompts/comprehension.py`
- **Functions**: `build_comprehension_exercises_prompt()`, `build_ai_comprehension_tutor_prompt()`
- **Profile parameter**: ❌ **NONE** - Only accepts `kit_context` and `kit_requirements`
- **How profile is passed**: Profile context is concatenated with kit_context: `kit_context + profile_context`
- **Prompt instructions**: ❌ **NO EXPLICIT PROFILE PERSONALIZATION INSTRUCTIONS**
- **Status**: ⚠️ **PARTIALLY CONNECTED** - Profile data is in the prompt string but LLM isn't explicitly told how to use it

#### Production Stage ❌ **IMPLICITLY USES PROFILE (via kit_context)**
- **Files**: `scripts/cando_creation/prompts/production.py`
- **Functions**: `build_production_exercises_prompt()`, `build_ai_production_evaluator_prompt()`
- **Profile parameter**: ❌ **NONE** - Only accepts `kit_context` and `kit_requirements`
- **How profile is passed**: Profile context is concatenated with kit_context: `kit_context + profile_context`
- **Prompt instructions**: ❌ **NO EXPLICIT PROFILE PERSONALIZATION INSTRUCTIONS**
- **Status**: ⚠️ **PARTIALLY CONNECTED** - Profile data is in the prompt string but LLM isn't explicitly told how to use it

#### Interaction Stage ❌ **IMPLICITLY USES PROFILE (via kit_context)**
- **Files**: `scripts/cando_creation/prompts/interaction.py`
- **Functions**: `build_interactive_dialogue_prompt()`, `build_interaction_activities_prompt()`
- **Profile parameter**: ❌ **NONE** - Only accepts `kit_context` and `kit_requirements`
- **How profile is passed**: Profile context is concatenated with kit_context: `kit_context + profile_context`
- **Prompt instructions**: ⚠️ **MINIMAL** - Only mentions "Align scenarios with user's usage context if profile provided" and "Align activities with user's learning goals and usage context if profile provided"
- **Status**: ⚠️ **PARTIALLY CONNECTED** - Profile data is in the prompt string but LLM isn't explicitly told how to use it

## Identified Gaps

### Critical Gap: Missing Explicit Profile Personalization Instructions

**Problem**: While profile context is passed to all stages (via `kit_context + profile_context`), the prompt builders don't explicitly instruct the LLM on how to use profile data for personalization.

**Impact**:
- LLM may ignore profile data or use it inconsistently
- Personalization is not guaranteed across all stages
- Profile building efforts may not translate to personalized lessons

**What's Missing**:
1. **Content Stage**: No instructions on using:
   - Register preferences for dialogue register selection
   - Cultural interests for cultural card content
   - Grammar focus areas for grammar pattern emphasis
   - Vocabulary domain goals for word selection
   - Scenario details for dialogue/reading scenarios

2. **Comprehension Stage**: No instructions on using:
   - Preferred exercise types (`preferred_exercise_types.comprehension`)
   - Reading topic interests (from cultural_interests or usage_context)
   - Difficulty pacing preferences (from current_level)

3. **Production Stage**: No instructions on using:
   - Preferred exercise types (`preferred_exercise_types.production`)
   - Feedback preferences (`feedback_preferences`)
   - Error tolerance (`error_tolerance`)
   - Grammar focus areas for exercise emphasis

4. **Interaction Stage**: Minimal instructions (only mentions usage context and learning goals, but doesn't specify how to use):
   - Interaction preferences (`interaction_preferences`)
   - Register preferences for scenario formality
   - Scenario details for specific contexts
   - Cultural background for cultural appropriateness

## Recommendations

### Priority 1: Add Explicit Profile Personalization Instructions to All Stage Prompts

**Action Items**:
1. **Content Stage Prompts** (`content.py`):
   - Add `profile_context: str = ""` parameter to all prompt builder functions
   - Add explicit personalization section similar to planner prompt
   - Specify how to use register preferences, cultural interests, grammar focus areas, vocabulary goals, scenario details

2. **Comprehension Stage Prompts** (`comprehension.py`):
   - Add `profile_context: str = ""` parameter to all prompt builder functions
   - Add explicit personalization section
   - Specify how to use preferred exercise types, reading interests, difficulty preferences

3. **Production Stage Prompts** (`production.py`):
   - Add `profile_context: str = ""` parameter to all prompt builder functions
   - Add explicit personalization section
   - Specify how to use preferred exercise types, feedback preferences, error tolerance, grammar focus

4. **Interaction Stage Prompts** (`interaction.py`):
   - Add `profile_context: str = ""` parameter to all prompt builder functions
   - Expand existing minimal personalization instructions
   - Specify how to use interaction preferences, register preferences, scenario details, cultural background

### Priority 2: Update Generator Functions to Pass Profile Context Separately

**Current**: Profile context is concatenated with kit_context: `kit_context + profile_context`

**Better**: Pass profile_context as a separate parameter so prompts can format it explicitly:
```python
# Current (implicit)
kit_context=kit_context + profile_context

# Better (explicit)
kit_context=kit_context,
profile_context=profile_context
```

This allows prompts to have a dedicated "PERSONALIZATION" section that clearly shows profile data.

### Priority 3: Verify Profile Data Completeness

**Check**: Ensure profile building service collects all data needed for 4-stage personalization:
- ✅ Register preferences - Collected
- ✅ Cultural interests - Collected
- ✅ Grammar focus areas - Collected
- ✅ Preferred exercise types - Collected
- ✅ Interaction preferences - Collected
- ✅ Scenario details - Collected
- ✅ Feedback preferences - Collected
- ✅ Error tolerance - Collected

**Status**: ✅ All required data is collected by profile building service.

## Current State Summary

| Stage | Profile Context Passed? | Explicit Instructions? | Status |
|-------|------------------------|------------------------|--------|
| DomainPlan (Planner) | ✅ Yes | ✅ Yes | ✅ **FULLY CONNECTED** |
| Content | ✅ Yes (via kit_context) | ❌ No | ⚠️ **PARTIALLY CONNECTED** |
| Comprehension | ✅ Yes (via kit_context) | ❌ No | ⚠️ **PARTIALLY CONNECTED** |
| Production | ✅ Yes (via kit_context) | ❌ No | ⚠️ **PARTIALLY CONNECTED** |
| Interaction | ✅ Yes (via kit_context) | ⚠️ Minimal | ⚠️ **PARTIALLY CONNECTED** |

## Conclusion

**Profile building IS connected** to lesson compilation:
- ✅ Profile data is collected comprehensively
- ✅ Profile context is fetched and formatted correctly
- ✅ Profile context is passed to all compilation stages
- ✅ DomainPlan explicitly uses profile for personalization

**However, there's a critical gap**:
- ❌ Content, Comprehension, Production, and Interaction stage prompts don't explicitly instruct the LLM on how to use profile data
- ⚠️ Profile context is only implicitly available via `kit_context + profile_context` concatenation
- ⚠️ LLM may not consistently use profile data for personalization

**Status**: ✅ **COMPLETED** - All stage prompt builders now have explicit `profile_context` parameters and personalization instructions. Profile context is passed separately (not concatenated) throughout the compilation pipeline.

## Implementation Summary

### Completed Changes

1. **Prompt Builders Updated** ✅
   - All Content stage prompts (`content.py`) - 9 functions updated
   - All Comprehension stage prompts (`comprehension.py`) - 2 functions updated
   - All Production stage prompts (`production.py`) - 2 functions updated
   - All Interaction stage prompts (`interaction.py`) - 3 functions updated
   - All prompts now include explicit `profile_context` parameter and PERSONALIZATION sections

2. **Generator Functions Updated** ✅
   - Stage generators (`stages.py`) - All 4 stage functions accept `profile_context`
   - Card generators (`cards.py`) - Key functions updated to accept and pass `profile_context`
   - DomainPlan generator already had `profile_context` support

3. **Compilation Service Updated** ✅
   - Changed from `kit_context + profile_context` concatenation to separate parameters
   - All stage generation calls now pass `profile_context` separately
   - Profile context is explicitly available to all prompts

### Impact

- ✅ Profile data is now explicitly available to all LLM prompts
- ✅ LLM receives clear instructions on how to use profile data for personalization
- ✅ Personalization is guaranteed across all lesson stages
- ✅ Profile building efforts now fully translate to personalized lessons

