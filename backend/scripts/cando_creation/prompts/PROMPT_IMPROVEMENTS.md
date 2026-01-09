# Prompt Improvements Documentation

**Date:** 2025-12-30  
**Purpose:** Document improvements made to prompts to ensure correct JSON generation without auto-fix logic.

## Summary

After removing auto-fix logic from `validate_or_repair`, prompts were strengthened to ensure LLMs generate correct JSON structure on the first attempt. This prevents validation errors and reduces the need for repair loops.

## Changes Made

### 1. `build_ai_comprehension_tutor_prompt` (comprehension.py)

**Problem:** LLM sometimes returned `question` as a string instead of JPText object.

**Solution:**
- Added explicit CORRECT/WRONG examples for JPText structure
- Added concrete JSON example showing complete structure
- Emphasized that question MUST be a complete JPText object with all required fields
- Added explicit rules about hints array structure

**Key additions:**
```python
CRITICAL RULES - READ CAREFULLY:
1. question field MUST be a JPText object, NOT a string:
   CORRECT: {"std": "質問", "furigana": "しつもん", "romaji": "shitsumon", "translation": {"en": "question"}}
   WRONG: "質問" (string is invalid)
   WRONG: {"ja": "質問"} (missing required JPText fields)

2. hints must be an array of objects, each with "en" and "ja" keys:
   CORRECT: [{"en": "Hint 1", "ja": "ヒント1"}, {"en": "Hint 2", "ja": "ヒント2"}]
   WRONG: {"en": "Hint", "ja": "ヒント"} (single object, not array)
   WRONG: ["Hint 1", "Hint 2"] (strings, not objects)
```

### 2. `build_ai_production_evaluator_prompt` (production.py)

**Problem:** Missing explicit rules about hints array and title structure.

**Solution:**
- Added JSON schema reference
- Added explicit rules about hints array structure
- Added concrete example showing correct structure
- Emphasized title must be dict, not string

**Key additions:**
```python
CRITICAL RULES - READ CAREFULLY:
1. hints must be an array of objects, each with "en" and "ja" keys:
   CORRECT: [{"en": "Hint 1", "ja": "ヒント1"}, {"en": "Hint 2", "ja": "ヒント2"}]
   WRONG: {"en": "Hint", "ja": "ヒント"} (single object, not array)
   WRONG: ["Hint 1", "Hint 2"] (strings, not objects)

2. title must be {"en": "...", "ja": "..."} (dict with en/ja keys, NOT a string)
```

### 3. `build_comprehension_exercises_prompt` (comprehension.py)

**Problem:** JPText structure rules were present but not emphasized enough.

**Solution:**
- Strengthened JPText rules with explicit CORRECT/WRONG examples
- Added emphasis on complete JPText structure (std, furigana, romaji, translation)
- Clarified rules for different exercise types
- Added explicit rule about title structure

**Key additions:**
```python
2. JPText structure - question and answer MUST be JPText objects, NOT strings:
   CORRECT: {"std": "質問", "furigana": "しつもん", "romaji": "shitsumon", "translation": {"en": "question"}}
   WRONG: "質問" (string is invalid)
   WRONG: {"ja": "質問"} (missing required JPText fields: std, furigana, romaji, translation)
```

## Test Updates

### `test_ai_comprehension_tutor_question_must_be_jptext`

**Before:** Tested auto-fix functionality (expecting string to be converted to JPText)

**After:** Tests that correct JSON is generated (fake LLM returns proper JPText structure)

**Change:**
- Renamed from `test_ai_comprehension_tutor_question_autofix_to_jptext`
- Updated to reflect that prompts should generate correct JSON
- Fake LLM now returns correct JPText structure instead of string

## Principles Applied

1. **Explicit Examples:** Show both CORRECT and WRONG examples
2. **Concrete Structure:** Provide complete JSON examples, not just descriptions
3. **Emphasis:** Use bold formatting and repetition for critical rules
4. **Schema Reference:** Include schema when helpful, but prioritize clear examples
5. **Common Mistakes:** Address known LLM mistakes explicitly (strings vs objects, arrays vs single items)

## Impact

- **Before:** LLM might generate strings for JPText fields → validation error → auto-fix → retry
- **After:** LLM generates correct JPText structure → validation passes → no retry needed

This reduces:
- LLM API calls (fewer retries)
- Latency (faster generation)
- Cost (fewer tokens used)
- Complexity (no auto-fix logic needed)

## Future Improvements

Consider adding similar improvements to:
- Other prompts that use JPText fields
- Prompts that use complex nested structures
- Any prompt where LLM commonly makes structural mistakes

## Date

2025-12-30

