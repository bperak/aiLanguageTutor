# Feature Specification: Interactive CanDo Lessons (Aligned with /specify → /plan → /implement)

**Feature Branch**: `001-and-plan-and`  
**Created**: 2025-10-08  
**Status**: Draft  
**Input**: User description: "and /plan  and /implement  sections"

## Execution Flow (main)
```
1. Parse user description from Input
   → We need interactive CanDo lessons aligned with /specify, /plan, /implement
2. Extract key concepts from description
   → CanDo lessons, interactive flows, alignment with internal process
3. For each unclear aspect:
   → [NEEDS CLARIFICATION: lesson assessment rubric, minimal viable interaction depth, persistence rules]
4. Fill User Scenarios & Testing section
5. Generate Functional Requirements (testable)
6. Identify Key Entities (data involved)
7. Run Review Checklist
8. Return: SUCCESS (spec ready for planning)
```

---

## User Scenarios & Testing *(mandatory)*

### Primary User Story
As a learner, I want to start an interactive lesson from a CanDo descriptor, practice through guided and open dialogue with feedback, and see my progress so that I learn the objective and advance to the next phase.

### Acceptance Scenarios
1. **Given** a CanDo page, **When** I click Start lesson, **Then** I see lesson objective, opening turns, and a chat input to reply.
2. **Given** a running lesson, **When** I send a message, **Then** I receive an AI reply with feedback and a next prompt within 20s.
3. **Given** sufficient correct turns, **When** I meet advancement criteria, **Then** I can advance to next phase and my mastery is updated.
4. **Given** an AI delay, **When** response exceeds timeout, **Then** I see a non-blocking status and partial content (never blank failures).

### Edge Cases
- Empty or ambiguous CanDo metadata → lesson still starts with generic objective and topic.
- Network hiccup/AI timeout → user sees “Generating…” and can retry without losing state.
- User reloads page → the latest lesson state is reconstructed from the server session [NEEDS CLARIFICATION: persistence window].

## Requirements *(mandatory)*

### Functional Requirements
- **FR-001**: System MUST allow starting a lesson from a CanDo (`POST /api/v1/cando/lessons/start`).
- **FR-002**: System MUST support turn-by-turn interaction (`POST /api/v1/cando/lessons/turn`).
- **FR-003**: System MUST provide structured feedback per turn (accuracy/naturalness/hints).
- **FR-004**: System MUST expose a lesson objective and opening turns upon start.
- **FR-005**: System MUST persist/update mastery for the CanDo after each turn.
- **FR-006**: System MUST enforce a max response latency (default 20–35s) and return a graceful partial result on timeout.
- **FR-007**: UI MUST show “Generating…” state and disable send/Generate while awaiting response.
- **FR-008**: UI MUST render dialogue turns, feedback, and phase controls; user can advance phase when criteria met.
- **FR-009**: System SHOULD record session transcript for later review [NEEDS CLARIFICATION: retention period].
- **FR-010**: System SHOULD support provider/model configuration per environment (e.g., gpt‑5 primary, gpt‑4o fallback).

### Key Entities *(include if feature involves data)*
- **LessonSession**: sessionId, canDoId, phase, objective, createdAt, lastTurnAt
- **DialogueTurn**: turnId, sessionId, speaker(ai|user), message, feedback?, corrections?, hints?, ts
- **MasteryEdge (graph)**: (User)-[:MASTERED {p, updatedAt}]->(CanDoDescriptor)

---

## Review & Acceptance Checklist
*GATE: Automated checks run during main() execution*

### Content Quality
- [ ] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

### Requirement Completeness
- [ ] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous  
- [x] Success criteria are measurable
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified

---

## Execution Status
*Updated by main() during processing*

- [x] User description parsed
- [x] Key concepts extracted
- [x] Ambiguities marked
- [x] User scenarios defined
- [x] Requirements generated
- [x] Entities identified
- [ ] Review checklist passed
