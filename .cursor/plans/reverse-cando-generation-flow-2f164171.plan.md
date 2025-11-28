<!-- 2f164171-f154-4509-8309-1c3df5d3480f af1e4609-75a2-46a4-98db-6a59d3da5d8b -->
# Add Reading Comprehension Card to LessonRoot

## Goal

Add a Reading (comprehension) card to the cando lesson system that:

- Contains elaborate narrative text (200+ words) grounded in and expanding on the Dialogue
- Includes 5-7 active comprehension questions
- Provides vocabulary/grammar extraction source for entity resolution
- Displays with std, furigana, romaji, translation (respecting Display settings)

## Implementation Plan

### 1. Backend: Add ReadingCard Model

**File**: `backend/scripts/canDo_creation_new.py`

**Add ReadingCard Pydantic model** (after DialogueCard, around line 222):

```python
class ComprehensionQA(BaseModel):
    model_config = ConfigDict(extra="forbid")
    q: JPText  # Question in Japanese
    a: JPText  # Answer in Japanese
    evidenceSpan: Optional[str] = None  # Text span in reading that supports answer

class ReadingCard(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["ReadingCard"] = "ReadingCard"
    title: Dict[str, str]  # Multilingual title
    reading: ReadingSection  # Contains title, content (JPText), comprehension (List[ComprehensionQA])
    notes_en: Optional[str] = None
    image: Optional[ImageSpec] = None
    gen: Optional[LLMGenSpec] = None
```

**Note**: ReadingSection already exists in `backend/app/models/multilingual.py` but needs to match our structure.

### 2. Backend: Add Reading Card Generation

**File**: `backend/scripts/canDo_creation_new.py`

**Add prompt builder** (after `build_dialogue_prompt`, around line 644):

```python
def build_reading_prompt(metalanguage: str, plan: DomainPlan, dialog: DialogueCard) -> Tuple[str, str]:
    """Build prompt for ReadingCard generation based on dialogue and plan."""
    user = f"""TARGET_MODEL: ReadingCard

INPUTS:
- metalanguage: {metalanguage}
- plan: {json.dumps(plan.model_dump(), ensure_ascii=False)}
- dialogue: {json.dumps({"setting": dialog.setting, "turns": [{"speaker": t.speaker, "text": t.ja.std} for t in dialog.turns[:5]]}, ensure_ascii=False)}

TASK:
Create a ReadingCard with an elaborate narrative text that:
1. Is grounded in the dialogue above (same setting, characters, context)
2. Expands on the dialogue with meta-narrative and scene elaboration
3. Contains at least 200 words of Japanese text
4. Uses vocabulary and grammar patterns consistent with the dialogue
5. Includes 5-7 comprehension questions that actively test understanding

Structure:
- title: {{"{metalanguage}", "ja"}} - Brief title for the reading
- reading.title: JPText - Title of the reading passage
- reading.content: JPText - Full reading text (200+ words, std/furigana/romaji/translation)
- reading.comprehension: Array of {{q: JPText, a: JPText, evidenceSpan?: string}} - 5-7 questions

Questions should test:
- Main ideas and details
- Character motivations
- Sequence of events
- Inferences from context
- Key vocabulary usage

CONSTRAINTS:
- Minimum 200 words in reading.content
- Exactly 5-7 comprehension questions
- Questions and answers in full JPText format
- Keep level-appropriate (same level as dialogue)
- Strict JSON.

OUTPUT: ReadingCard JSON only.
"""
    return STRICT_SYSTEM, user
```

**Add generation function** (after `gen_dialogue_card`, around line 830):

```python
def gen_reading_card(llm_call: LLMFn, metalanguage: str, plan: DomainPlan, dialog: DialogueCard, max_repair: int = 2) -> ReadingCard:
    sys, usr = build_reading_prompt(metalanguage, plan, dialog)
    card = validate_or_repair(llm_call, ReadingCard, sys, usr, max_repair=max_repair)
    card.gen = LLMGenSpec(system=sys, instruction=usr, constraints=[], examples=None)
    return card
```

### 3. Backend: Update CardsContainer

**File**: `backend/scripts/canDo_creation_new.py`

**Add reading_card to CardsContainer** (line 334-343):

```python
class CardsContainer(BaseModel):
    model_config = ConfigDict(extra="forbid")
    objective: ObjectiveCard
    words: WordsCard
    grammar_patterns: GrammarPatternsCard
    lesson_dialogue: DialogueCard
    reading_comprehension: ReadingCard  # NEW
    guided_dialogue: GuidedDialogueCard
    exercises: ExercisesCard
    cultural_explanation: CultureCard
    drills_ai: DrillsCard
```

### 4. Backend: Update assemble_lesson Function

**File**: `backend/scripts/canDo_creation_new.py`

**Update function signature** (line 865):

```python
def assemble_lesson(
    metalanguage: str,
    cando: Dict[str, Any],
    plan: DomainPlan,
    obj: ObjectiveCard,
    words: WordsCard,
    grammar: GrammarPatternsCard,
    dialog: DialogueCard,
    reading: ReadingCard,  # NEW
    guided: GuidedDialogueCard,
    exercises: ExercisesCard,
    culture: CultureCard,
    drills: DrillsCard,
    ...
) -> LessonRoot:
```

**Update CardsContainer creation** (line 903):

```python
cards = CardsContainer(
    objective=obj,
    words=words,
    grammar_patterns=grammar,
    lesson_dialogue=dialog,
    reading_comprehension=reading,  # NEW
    guided_dialogue=guided,
    exercises=exercises,
    cultural_explanation=culture,
    drills_ai=drills,
)
```

### 5. Backend: Update Compilation Sequence

**File**: `backend/app/services/cando_v2_compile_service.py`

**Add helper to extract reading text** (after `_extract_dialogue_text`, around line 103):

```python
def _extract_reading_text(reading: Any) -> str:
    """Extract all Japanese text from ReadingCard for entity extraction.
    
    Extracts text from reading.content (JPText structure).
    """
    if not hasattr(reading, 'reading') or not reading.reading:
        return ""
    
    reading_section = reading.reading
    lines: List[str] = []
    
    # Add title if present
    if hasattr(reading_section, 'title') and reading_section.title:
        if hasattr(reading_section.title, 'std') and reading_section.title.std:
            lines.append(str(reading_section.title.std))
        elif hasattr(reading_section.title, 'kanji') and reading_section.title.kanji:
            lines.append(str(reading_section.title.kanji))
    
    # Add content text
    if hasattr(reading_section, 'content') and reading_section.content:
        content = reading_section.content
        if hasattr(content, 'std') and content.std:
            lines.append(str(content.std))
        elif hasattr(content, 'kanji') and content.kanji:
            lines.append(str(content.kanji))
    
    return "\n".join(lines)
```

**Update compilation sequence** (around line 276):

```python
# Generate reading card AFTER dialogue (based on dialogue)
reading = pipeline.gen_reading_card(llm_call, metalanguage, plan, dialog)

# Extract entities from BOTH dialogue AND reading
dialogue_text = _extract_dialogue_text(dialog)
reading_text = _extract_reading_text(reading)
combined_text = "\n".join([dialogue_text, reading_text])  # Combine for extraction

# Update extraction to use combined_text instead of just dialogue_text
if combined_text and len(combined_text.strip()) > 10:
    extracted = await session_service._extract_entities_from_text(
        text_blob=combined_text, provider="gemini"
    )
    # ... rest of extraction logic
```

**Update assemble_lesson call** (line 294):

```python
root = pipeline.assemble_lesson(
    metalanguage,
    cando_input,
    plan,
    obj,
    words,
    grammar,
    dialog,
    reading,  # NEW
    guided,
    exercises,
    culture,
    drills,
    lesson_id=f"canDo_{can_do_id}_v1",
)
```

### 6. Frontend: Add Reading Tab

**File**: `frontend/src/components/lesson/LessonRootRenderer.tsx`

**Add reading tab** (line 55-63):

```typescript
<TabsList className="grid w-full grid-cols-4 lg:grid-cols-9">  // Changed from 8 to 9
  <TabsTrigger value="objective">Objective</TabsTrigger>
  <TabsTrigger value="words">Vocabulary</TabsTrigger>
  <TabsTrigger value="grammar">Grammar</TabsTrigger>
  <TabsTrigger value="dialogue">Dialogue</TabsTrigger>
  <TabsTrigger value="reading">Reading</TabsTrigger>  // NEW
  <TabsTrigger value="guided">Guided</TabsTrigger>
  // ... rest
```

**Add tab content** (after dialogue tab, line 80):

```typescript
<TabsContent value="reading" className="mt-6">
  <ReadingCard 
    title={cards.reading_comprehension?.title}
    reading={cards.reading_comprehension?.reading}
  />
</TabsContent>
```

**Import ReadingCard** (line 10):

```typescript
import { ReadingCard } from "./ReadingCard"
```

### 7. Frontend: Update TypeScript Types

**File**: `frontend/src/types/lesson-root.ts`

**Add ReadingCard interface** (after DialogueCard, around line 179):

```typescript
export interface ComprehensionQA {
  q: JapaneseText
  a: JapaneseText
  evidenceSpan?: string | null
}

export interface ReadingSection {
  title: JapaneseText
  content: JapaneseText
  comprehension: ComprehensionQA[]
}

export interface ReadingCard {
  type: "ReadingCard"
  title: Record<string, string>
  reading: ReadingSection
  notes_en?: string | null
  image?: ImageSpec | null
  gen?: LLMGenSpec | null
}
```

**Add to CardsContainer** (line 289-298):

```typescript
export interface CardsContainer {
  objective: ObjectiveCard
  words: WordsCard
  grammar_patterns: GrammarPatternsCard
  lesson_dialogue: DialogueCard
  reading_comprehension: ReadingCard  // NEW
  guided_dialogue: GuidedDialogueCard
  exercises: ExercisesCard
  cultural_explanation: CultureCard
  drills_ai: DrillsCard
}
```

### 8. Frontend: Update ReadingCard Component

**File**: `frontend/src/components/lesson/ReadingCard.tsx`

**Ensure component supports JPText structure** - The component already exists and should work, but verify it handles:

- `reading.content` as JapaneseText object (std, furigana, romaji, translation)
- `reading.comprehension` as array of {q: JPText, a: JPText}
- Display settings integration (romaji/translation visibility)

### 9. Backend: Update Extraction Logic Priority

**File**: `backend/app/services/cando_v2_compile_service.py`

**Update to prioritize reading text** - Since reading is more elaborate (200+ words), we should:

- Extract from reading first (primary source)
- Supplement with dialogue if reading extraction is sparse
- Combine both sources for comprehensive entity resolution

### 10. Update Tests

**Files**:

- `backend/tests/test_lessonroot_integration.py`
- Frontend component tests (if any)

**Add reading_comprehension to required cards list** (line 110-119).

## Files to Modify

1. `backend/scripts/canDo_creation_new.py`

   - Add ReadingCard model
   - Add ComprehensionQA model (or reuse from multilingual.py)
   - Add build_reading_prompt()
   - Add gen_reading_card()
   - Update CardsContainer
   - Update assemble_lesson()

2. `backend/app/services/cando_v2_compile_service.py`

   - Add _extract_reading_text() helper
   - Update compilation sequence to generate reading card
   - Update entity extraction to include reading text
   - Update assemble_lesson call

3. `frontend/src/types/lesson-root.ts`

   - Add ReadingCard interface
   - Add ComprehensionQA interface
   - Add ReadingSection interface
   - Update CardsContainer

4. `frontend/src/components/lesson/LessonRootRenderer.tsx`

   - Add reading tab
   - Add ReadingCard import
   - Add tab content

5. `backend/tests/test_lessonroot_integration.py`

   - Add "reading_comprehension" to required cards

## Dependencies

- ReadingCard component already exists in frontend
- ReadingSection model exists in multilingual.py (may need adaptation)
- JapaneseText display system already supports all needed formats

## Notes

- Reading card should be generated AFTER dialogue (to ground it in dialogue)
- Entity extraction should use BOTH dialogue and reading text (reading as primary)
- Reading text must be 200+ words minimum
- Comprehension questions should actively test understanding, not just recall

### To-dos

- [ ] Add ReadingCard and ComprehensionQA Pydantic models to canDo_creation_new.py
- [ ] Create build_reading_prompt() function that generates reading card based on dialogue and plan
- [ ] Create gen_reading_card() generation function
- [ ] Add reading_comprehension field to CardsContainer model
- [ ] Update assemble_lesson() to include reading card parameter
- [ ] Add _extract_reading_text() helper function in cando_v2_compile_service.py
- [ ] Update compile_lessonroot() to generate reading card after dialogue
- [ ] Update entity extraction to include reading text (combine with dialogue text)
- [ ] Update TypeScript types in lesson-root.ts to include ReadingCard, ComprehensionQA, ReadingSection
- [ ] Add reading tab to LessonRootRenderer component and import ReadingCard
- [ ] Update test_lessonroot_integration.py to include reading_comprehension in required cards