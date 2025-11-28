# Tasks: Interactive CanDo Lessons

**Input**: Design documents from `/specs/001-and-plan-and/`  
**Prerequisites**: plan.md (required)

## Phase 3.1: Setup
- [ ] T001 Create contracts directory `specs/001-and-plan-and/contracts/` with two files: `cando-lessons-start.json`, `cando-lessons-turn.json`
- [ ] T002 [P] Add backend env knobs (if missing) for AI timeouts and models in `backend/app/core/config.py`

## Phase 3.2: Tests First (TDD)
- [ ] T003 Contract test [P] POST `/api/v1/cando/lessons/start` in `backend/tests/test_cando_lessons_start_contract.py`
- [ ] T004 Contract test [P] POST `/api/v1/cando/lessons/turn` in `backend/tests/test_cando_lessons_turn_contract.py`
- [ ] T005 Integration test [P] interactive flow in `tests/test_cando_interactive_flow.py`

## Phase 3.3: Core Implementation (ONLY after tests are failing)
- [ ] T006 Add `start_lesson` endpoint in `backend/app/api/v1/endpoints/cando.py` → returns objective, opening turns, sessionId
- [ ] T007 Add `turn_lesson` endpoint in `backend/app/api/v1/endpoints/cando.py` → accepts sessionId + user message; returns ai turn + feedback
- [ ] T008 Create service `backend/app/services/cando_lesson_session_service.py` for minimal in-memory sessions (id → state)
- [ ] T009 Use `AIConversationPractice` to generate scenario/turns; map to CanDo context
- [ ] T010 Update `backend/app/services/mastery_service.py` usage from turn endpoint to upsert mastery
- [ ] T011 Error handling: timeouts and partial returns (20–35s) in both endpoints

## Phase 3.4: Frontend Integration
- [ ] T012 Update `frontend/src/app/cando/[canDoId]/page.tsx` to show Start Lesson button, objectives, opening turns, chat box, send/disable while generating
- [ ] T013 Render AI feedback and allow phase advance when conditions met

## Phase 3.5: Polish
- [ ] T014 [P] Unit tests for session service in `backend/tests/test_cando_lesson_session_service.py`
- [ ] T015 [P] Update docs: `API_REFERENCE.md` and `USER_MANUAL.md` (lesson flow)
- [ ] T016 Add Playwright E2E: start → send a turn → see AI turn in `tests/e2e/test_cando_lesson_chat.py`

## Dependencies
- T003–T005 (tests) MUST fail before starting T006–T011.
- T008 precedes T006/T007 wiring; T009 consumes conversation service; T010 depends on endpoints returning user/score.
- T012–T013 after endpoints are functional.
- Polish (T014–T016) after core integration.

## Parallel Example
```
# After tests created and failing, run these in parallel (different files):
- T008 service file creation
- T009 mapping to AIConversationPractice
- T011 shared error handling helpers
```

## Notes
- Keep endpoints under `/api/v1/cando/lessons/*` to remain consistent.
- Avoid long-hanging requests; return partial content with clear status on timeout.
