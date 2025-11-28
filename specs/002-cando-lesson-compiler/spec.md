# Feature Specification: CanDo Lesson Compiler and Session Revamp

**Feature Branch**: `002-cando-lesson-compiler`  
**Created**: 2025-10-09  
**Status**: Draft  
**Input**: Elevate start_lesson to compile a complete, printable LessonPackage for a CanDoDescriptor with multi-level variants (1–6), English metalanguage (future i18n), cultural notes, illustrations, extraction to Neo4j Word/GrammarPattern (creating Word when missing with needs_review), reusable template per can_do_id, on-demand PDF, and batch generation for all CanDo × levels. Sessions adapt delivery to the learner’s level and reference the compiled package; user-specific goals live in Postgres.

## User Scenarios & Testing (mandatory)

### Primary User Story
- As a learner, I start a lesson for a specific CanDo descriptor and receive a complete, level-appropriate lesson (content in Japanese, explanations in English) with cultural notes, illustrations, and exercises that align with the CanDo learning objective.
- As an educator/admin, I can pre-generate lessons for all CanDo descriptors across levels 1–6 and review linked words/grammar for coverage and consistency.

### Acceptance Scenarios
1. Given a valid `can_do_id` and learner level (e.g., 1), when start_lesson is invoked, then a LessonPackage is created or retrieved that includes variants for levels 1–6 and returns the closest variant to level 1, plus sessionId.
2. Given a compiled lesson, when inspecting `extractedEntities`, then each referenced Word resolves to an existing Word node or a newly created Word node flagged `needs_review=true`; each GrammarPattern resolves by id.
3. Given a compiled lesson, when requesting illustrations, then each illustration shows a prompt and an asset path (generated or pending) suitable for inclusion in a PDF.
4. Given a compiled lesson, when generating a PDF on demand, then the PDF includes objectives, content sections, cultural notes, illustrations, and exercises in a clean A4 layout.
5. Given batch generation is triggered, when it runs across all CanDo descriptors and levels 1–6, then a Lesson template is produced per (CanDo, level), linked to Word and GrammarPattern nodes, and accessible for sessions.
6. Given a lesson template exists for `can_do_id`, when a different learner at level 4 starts the lesson, then the session references the same template but surfaces the level-4 variant without duplicating the template.

### Edge Cases
- If the CanDo has no topic/level metadata, a default topic is used but the package still compiles and marks uncertain fields.
- If illustrations cannot be generated immediately, prompts are stored and asset paths are marked pending; lesson remains usable and PDF renders without missing assets breaking the flow.
- If a Word cannot be matched by kanji/hiragana/lemma, a new Word node is created with `needs_review=true` and the lesson proceeds.
- If GrammarPattern id is missing, the pattern mention is captured as text and included in an unresolved list for later mapping.
- If the learner level is outside 1–6, clamp to bounds and proceed.

## Requirements (mandatory)

### Functional Requirements
- **FR-001**: System MUST compile a LessonPackage for a given `can_do_id` containing: objectives, JP content, English metalanguage, cultural notes, illustrations, exercises, assessment hooks, and readability.
- **FR-002**: System MUST produce multi-level variants for levels 1–6 in every LessonPackage.
- **FR-003**: System MUST select the closest variant to the learner’s level at delivery time while retaining the original CanDo level and pragmatic notes in metadata.
- **FR-004**: System MUST extract entities (Words, GrammarPatterns) from lesson text and link them to the Neo4j graph; unknown Words MUST be created with `needs_review=true` and flagged in the package metadata.
- **FR-005**: System MUST store illustration prompts and asset paths for all key sections; model preference for images is Gemini 2.5 image; assets initially stored locally under `images/grammar/`.
- **FR-006**: System MUST render a PDF on demand from any LessonPackage using a fixed A4 template layout.
- **FR-007**: System MUST persist lessons as reusable templates per `can_do_id`, and sessions MUST reference these templates and adapt presentation to the learner’s level.
- **FR-008**: System MUST support batch generation to create LessonPackages for all CanDo descriptors at levels 1–6.
- **FR-009**: System MUST record user-specific goals and progress in Postgres while templates remain shared; sessions associate the user to the used Lesson template and variant level.
- **FR-010**: System MUST log extraction outcomes (matched vs created Words) and unresolved GrammarPattern mentions for review.
- **FR-011**: System MUST include cultural complexities and pragmatic guidance aligned to the CanDo objective within each package.
- **FR-012**: System MUST remain simple to operate and configure on Windows/PowerShell and use dotenv-managed keys.

### Key Entities (include if feature involves data)
- **Lesson (template)**: Represents a compiled lesson tied to one `can_do_id`; includes metadata (original CanDo level, topic), `variants` (1–6), `content` (JP + metalanguage), `culturalNotes`, `illustrations` (prompts, asset paths), `exercises`, `assessmentPlan`, `extractedEntities` (WordRefs, GrammarPatternRefs), and `pdf` settings. Relations: `EXEMPLIFIES` → CanDoDescriptor; `INTRODUCES` → Word; `FOCUSES_ON` → GrammarPattern.
- **LessonVariant**: The level-specific view (1–6) with scaffolding differences (furigana/romaji support, complexity, examples).
- **IllustrationAsset**: Prompt, model metadata, asset url/path, status (generated/pending), alt text.
- **ExtractedEntity**:
  - WordRef: text, kanji, hiragana, wordId (or pending), mentions (section/offsets), `created` flag, `needs_review` flag.
  - GrammarPatternRef: pattern text, patternId, mentions (section/index), unresolved flag.
- **Session**: References a Lesson (template) and the selected variant level; stores transient dialogue and phase state.
- **UserGoal (Postgres)**: User-specific learning goals and level; associated with sessions and completion tracking.

---

## Execution Flow (main)
```
1. Receive request with can_do_id, learner_level.
2. Retrieve CanDo metadata (topic, original level).
3. Compile or load Lesson (template):
   - Generate core content, metalanguage, cultural notes, exercises.
   - Produce variants 1–6 (complexity, scaffolding adjustments).
   - Generate illustration prompts and (optionally) assets; store paths.
   - Extract entities → link to Word/GrammarPattern; create missing Word nodes with needs_review.
   - Compute readability and assessment hooks; store metadata.
4. Persist Lesson template and graph links; ensure idempotent reuse per can_do_id and level variant.
5. Return sessionId, LessonPackage summary, and the selected variant for the learner level.
6. On demand: render PDF using the stored template content and assets.
7. Batch mode: iterate all CanDo × levels 1–6 to compile and persist templates.
```

---

## Open Questions / Decisions to Confirm
- Persistence model for LessonPackage JSON:
  - Option A: Store full LessonPackage JSON in Neo4j on the Lesson node.
  - Option B: Store LessonPackage JSON in Postgres (JSONB) or blob storage and reference it from Neo4j by id.
  - Proposal: Core linkage (Lesson ↔ CanDo, Words, GrammarPatterns) in Neo4j; large LessonPackage JSON in Postgres JSONB (or blob) with a reference in Neo4j for graph queries. Keeps graph lean and JSON query-friendly. [Please confirm]
- Metalanguage: English now; later dynamic per user (i18n). [Confirmed for now]
- GrammarPattern resolution: keep id-based matching; optionally maintain a mapping table for legacy names → ids to speed extraction. [Please confirm]
- Illustration storage: local path now (`images/grammar`), with potential future move to cloud/S3. [Please confirm]
- Template reuse granularity: one Lesson (template) per (CanDo, compiled package with variants 1–6); delivery selects variant per learner level. [Confirmed]

---

## Review & Acceptance Checklist

### Content Quality
- [x] No low-level implementation code; focuses on user value and outcomes
- [x] Written for stakeholders with clear business value
- [x] All mandatory sections completed

### Requirement Completeness
- [ ] No [NEEDS CLARIFICATION] markers remain (see Open Questions)
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable at feature level
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified

---

## Execution Status
- [x] User description parsed
- [x] Key concepts extracted
- [x] Ambiguities marked (in Open Questions)
- [x] User scenarios defined
- [x] Requirements generated
- [x] Entities identified
- [ ] Review checklist fully passed (pending decisions above)
