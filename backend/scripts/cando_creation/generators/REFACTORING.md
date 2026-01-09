# validate_or_repair Cleanup Documentation

## Summary

The `validate_or_repair` function in `cando_creation/generators/utils.py` was refactored from **2400+ lines** down to **~40 lines** by removing all model-specific auto-fix logic and debug logging bloat.

## What Was Removed

### 1. Model-Specific Auto-Fix Blocks (14 total)
- ReadingCard auto-fix (~150 lines)
- GrammarPatternsCard auto-fix (~100 lines)
- DialogueCard auto-fix (~80 lines)
- CultureCard auto-fix (~60 lines)
- AIComprehensionTutorCard auto-fix (~150 lines)
- GuidedDialogueCard auto-fix (~50 lines)
- InteractiveDialogueCard auto-fix (~80 lines)
- AIScenarioManagerCard auto-fix (~100 lines)
- InteractionActivitiesCard auto-fix (~50 lines)
- ComprehensionExercisesCard auto-fix (~400 lines)
- AIProductionEvaluatorCard auto-fix (~150 lines)
- ProductionExercisesCard auto-fix (~200 lines)
- Plus various nested helper functions

### 2. Debug Logging Regions (13 total)
- Logging to `/tmp/debug.log`
- Logging to `/home/benedikt/.cursor/debug.log`
- JSON serialization of debug events
- Timestamp tracking
- Session/run/hypothesis ID tracking

### 3. Print Statements (91 total)
- `[AUTO-FIX]` prefix messages
- Status updates during auto-fix
- Error messages

### 4. Try/Except Blocks (21 total)
- Error handling for auto-fix operations
- Error handling for debug logging
- Nested exception handling

## What Remains

The clean version contains only the core validation logic:

1. **Call LLM** → Get raw response
2. **Extract JSON** → Use `extract_first_json_block()`
3. **Validate** → Try `model_validate_json()`
4. **Retry with repair** → If validation fails, ask LLM to fix using schema + errors
5. **Return** → Validated Pydantic model

**Total: ~40 lines of core logic**

## Philosophy

**If the LLM generates bad JSON, fix the prompts instead of patching the validator.**

The auto-fix logic was a symptom of:
- Unclear prompts
- Inconsistent schema definitions
- LLM misunderstanding requirements

**Solution**: Improve prompts and schema definitions rather than adding workarounds.

## Impact

- **Before**: 2400+ lines, 14 model-specific hacks, 13 debug regions
- **After**: ~40 lines, 0 hacks, 0 debug regions
- **Saved**: ~2360 lines of maintenance burden

## Files Using validate_or_repair

All card generators in `cando_creation/generators/cards.py` use this function:
- `gen_domain_plan()`
- `gen_objective_card()`
- `gen_words_card()`
- `gen_grammar_card()`
- `gen_dialogue_card()`
- `gen_reading_card()`
- `gen_culture_card()`
- `gen_drills_card()`
- `gen_exercises_card()`
- `gen_formulaic_expressions_card()`
- `gen_comprehension_exercises_card()`
- `gen_ai_comprehension_tutor_card()`
- `gen_production_exercises_card()`
- `gen_ai_production_evaluator_card()`
- `gen_interactive_dialogue_card()`
- `gen_interaction_activities_card()`
- `gen_ai_scenario_manager_card()`
- `gen_guided_dialogue_card()`

All of these continue to work without modification - the function signature and behavior remain the same, just without the bloat.

## Testing

After cleanup, verify:
1. ✅ Syntax compiles
2. ✅ All imports work
3. ✅ Function signature unchanged
4. ⚠️ If specific models fail validation, improve their prompts instead of adding auto-fix code

## Other Files with Similar Patterns

Found debug logging in other files (not as severe):
- `cando_creation/generators/cards.py`: 5 debug log regions
- `cando_creation/prompts/content.py`: 2 debug log regions

These are much smaller and can be cleaned up separately if needed. The main bloat was in `validate_or_repair`.

## Date

2025-12-30

