# Feature Specification: CanDo-driven lesson orchestration over Neo4j

**Feature Branch**: `canDoDescriptorsIntegration`  
**Created**: [DATE]  
**Status**: Draft  
**Input**: User description: "trebamo sada napraviti od svega u graf bazi strukturu za stvaranje lekcija, ajmo malo razmotriti neki prijedlog - nemojmo sve uzeti zdravo za govoto , već vidi što se može uvesti a što je možda previše"

## Execution Flow (main)
```
1. Parse user description from Input
   → If empty: ERROR "No feature description provided"
2. Extract key concepts from description
   → Identify: actors, actions, data, constraints
3. For each unclear aspect:
   → Mark with [NEEDS CLARIFICATION: specific question]
4. Fill User Scenarios & Testing section
   → If no clear user flow: ERROR "Cannot determine user scenarios"
5. Generate Functional Requirements
   → Each requirement must be testable
   → Mark ambiguous requirements
6. Identify Key Entities (if data involved)
7. Run Review Checklist
   → If any [NEEDS CLARIFICATION]: WARN "Spec has uncertainties"
   → If implementation details found: ERROR "Remove tech details"
8. Return: SUCCESS (spec ready for planning)
```

---

## ⚡ Quick Guidelines
- ✅ Focus on WHAT users need and WHY
- ❌ Avoid HOW to implement (no tech stack, APIs, code structure)
- 👥 Written for business stakeholders, not developers

### Section Requirements
- **Mandatory sections**: Must be completed for every feature
- **Optional sections**: Include only when relevant to the feature
- When a section doesn't apply, remove it entirely (don't leave as "N/A")

### For AI Generation
When creating this spec from a user prompt:
1. **Mark all ambiguities**: Use [NEEDS CLARIFICATION: specific question] for any assumption you'd need to make
2. **Don't guess**: If the prompt doesn't specify something (e.g., "login system" without auth method), mark it
3. **Think like a tester**: Every vague requirement should fail the "testable and unambiguous" checklist item
4. **Common underspecified areas**:
   - User types and permissions
   - Data retention/deletion policies  
   - Performance targets and scale
   - Error handling behaviors
   - Integration requirements
   - Security/compliance needs

---

## User Scenarios & Testing *(mandatory)*

### Primary User Story
As a tutor orchestrator, I want to activate CanDo-driven lessons from the graph, generate exercises, grade user responses, update mastery, and recommend next steps, so that learners progress along meaningful paths aligned to textbooks and their goals.

### Acceptance Scenarios
1. **Given** a valid `can_do_id` and existing graph nodes (CanDoDescriptor linked to Level/Topic; optional Word/GrammarPattern), **When** ActivateCanDo is called, **Then** the system returns a valid LessonPlan JSON including at least 1 Word and 1 GrammarPattern (or clear candidate suggestions if missing) and logs `lesson_activated`.
2. **Given** a LessonPlan, **When** GenerateExercises is called with targets and difficulty, **Then** the system returns an ExerciseBundle with ≥3 exercises of varied types and clear `answer_schema`.
3. **Given** a user answer to an exercise, **When** GradeResponse is called, **Then** the system returns a ScoreReport with rubric scores, hints, next_actions, overall score, and writes attempt/score events.
4. **Given** a user mastery state and recent scores, **When** UpdateMastery is called, **Then** it updates a mastery probability on the (:User)-[:MASTERED]->(:CanDoDescriptor) edge and returns status (passed/retry/scaffold).
5. **Given** a user and optional preferences, **When** RecommendNext is called, **Then** it returns 3–5 candidate CanDo items with reasons and textbook paths if applicable.

### Edge Cases
- Missing Word/GrammarPattern links for a CanDoDescriptor → system proposes candidates but still generates a lesson (flagged).
- Very common topics/levels (large clusters) → avoid overwhelming exercises; cap or down-weight generic items.
- A0 users → shorter exercises, tolerant scoring; ensure self-intro focus.
- Privacy → no personal data in generated content; log only anonymized/user-id scoped events.
- Offline textbook content → if `ContentStore` missing, skip passages gracefully.

## Requirements *(mandatory)*

### Functional Requirements
- **FR-001**: System MUST implement the five orchestrations: ActivateCanDo, GenerateExercises, GradeResponse, UpdateMastery, RecommendNext.
- **FR-002**: ActivateCanDo MUST return a valid LessonPlan JSON per schema, with `lexicon` and `patterns` non-empty or accompanied by candidate mappings if links are missing.
- **FR-003**: GenerateExercises MUST return ≥3 exercises with defined types, constraints, targets, and `answer_schema`.
- **FR-004**: GradeResponse MUST compute rubric scores (coverage, cohesion, language), overall, hints, next_actions, and log events.
- **FR-005**: UpdateMastery MUST update mastery probability on (:User)-[:MASTERED {p, ts}]->(:CanDoDescriptor) using the provided formula and return a status bucket.
- **FR-006**: RecommendNext MUST combine prerequisites, mastery p, and textbook-unit mappings to produce 3–5 candidates with reasons; include textbook path when requested.
- **FR-007**: System MUST log events (view, attempt, score, hint, time_on_task) to UserStore and optionally annotate edges in Neo4j.
- **FR-008**: UI localization MUST be supported for meta-explanations (`ui_lang`), while exercises target L2 output.
- **FR-009**: Content MUST avoid personal data and inappropriate material.
- **FR-010**: The system SHOULD propose spaced-review sets when SEEN.count ≥ 2 and interval expired.
- **FR-011**: The system SHOULD gracefully degrade when Word/Pattern links or textbook content are missing.

### Key Entities *(include if feature involves data)*
- **CanDoDescriptor**: target ability descriptor; attrs: uid, level, topic, domain, type, texts.
- **Word**: lexemes; linked via USES (proposed or curated).
- **GrammarPattern**: constructions; linked via REALIZES/USES.
- **Level/Topic**: classification nodes for scope and filtering.
- **Textbook/Unit**: curriculum mapping for learning paths.
- **User**: learner; edges MASTERED (p), SEEN (count, last_ts), ATTEMPTED.
- **Cohort**: group assignments via ASSIGNED.

---

## Review & Acceptance Checklist
*GATE: Automated checks run during main() execution*

### Content Quality
- [ ] No implementation details (languages, frameworks, APIs)
- [ ] Focused on user value and business needs
- [ ] Written for non-technical stakeholders
- [ ] All mandatory sections completed

### Requirement Completeness
- [ ] No [NEEDS CLARIFICATION] markers remain
- [ ] Requirements are testable and unambiguous  
- [ ] Success criteria are measurable
- [ ] Scope is clearly bounded
- [ ] Dependencies and assumptions identified

---

## Execution Status
*Updated by main() during processing*

- [ ] User description parsed
- [ ] Key concepts extracted
- [ ] Ambiguities marked
- [ ] User scenarios defined
- [ ] Requirements generated
- [ ] Entities identified
- [ ] Review checklist passed

---
