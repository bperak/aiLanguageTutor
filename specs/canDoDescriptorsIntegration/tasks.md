# Feature: CanDo Similar-Topics Sorting

Scope: Add a graph-level `:SIMILAR_TOPIC(similarity_score: float)` relation and expose a new sorting mode `sort=similar:<topic>` for CanDo listing.

Repository areas: `backend/app/api/v1/endpoints/cando.py`, `backend/app/services/*`, Neo4j data, `frontend/src/app/cando/page.tsx`, tests in `backend/tests/` and `tests/`.

Notes:
- Use existing Neo4j session plumbing.
- Keep existing `sort=level|topic` unchanged; add `similar:<topic>`.
- If relation is missing, compute ad-hoc similarity from `primaryTopic` text as fallback.

## Tasks

1. T001 - Create contract for similar sort [P]
   - Path: `specs/canDoDescriptorsIntegration/contracts/cando-list.json`
   - Add optional query param `sort` with pattern `^(level|topic|similar:[^?&]+)$`.
   - Document response unchanged; ordering semantics updated.

2. T002 - Contract test: list with sort=similar:<topic> [P]
   - Path: `backend/tests/test_cando_contract.py`
   - Cases: 200 OK, ordered by decreasing `similarity_score` (mock via fixtures), invalid topic → 200 with fallback ordering.

3. T003 - Data model update: add SIMILAR_TOPIC relation [P]
   - Path: `specs/canDoDescriptorsIntegration/data-model.md`
   - Add: `(:CanDoDescriptor)-[:SIMILAR_TOPIC {similarity_score: float}]->(:CanDoDescriptor)`.

4. T004 - Cypher migration to (re)build SIMILAR_TOPIC edges [P]
   - Path: `backend/migrations/007_cando_similar_topic.cypher`
   - Build edges with cosine similarity over topic embeddings or simple Jaccard over tokenized `primaryTopic` (start simple: Jaccard).
   - Ensure `similarity_score` in [0,1]. Limit out-degree to 10 per node.

5. T005 - Service: topic similarity utility [P]
   - Path: `backend/app/services/cando_similarity_service.py`
   - Functions: `compute_similarity(a: str, b: str) -> float` (token Jaccard), `build_edges(session)` (invoked by migration/maintenance).

6. T006 - Backend: extend list endpoint to support sort=similar:<topic>
   - Path: `backend/app/api/v1/endpoints/cando.py`
   - Accept `sort` string; when `similar:<topic>`:
     - If `topic` after colon provided: order by similarity to that topic using graph edges if present; fallback to on-the-fly score `compute_similarity(primaryTopic, topic)`.
     - Cypher example with edges:
       ```
       OPTIONAL MATCH (c)-[r:SIMILAR_TOPIC]->(t:CanDoDescriptor {primaryTopic: $similarTopic})
       WITH c, coalesce(r.similarity_score, 0.0) AS sim
       ORDER BY sim DESC, toString(c.level) ASC
       ```
   - Preserve existing filters, `limit`, `offset`.

7. T007 - Unit tests for similarity utility [P]
   - Path: `backend/tests/test_cando_similarity.py`
   - Cover edge cases (empty, case, punctuation).

8. T008 - Integration tests for sort=similar mode
   - Path: `tests/test_cando_list_similar.py`
   - Seed a tiny graph fixture: 4 CanDo nodes with topics; assert ordering and pagination work.

9. T009 - Frontend: add Similar sort option
   - Path: `frontend/src/app/cando/page.tsx`
   - Add Sort option "Similar to topic…" with an input/select to choose target topic; send `sort=similar:<topic>`.

10. T010 - Docs: update API_REFERENCE.md and GRAMMAR_SERVICE_USAGE_GUIDE.md
    - Note new param and relation; show example requests.

11. T011 - Ops: script to rebuild similarity edges [P]
    - Path: `scripts/rebuild_cando_similarity.ps1`
    - Calls backend admin endpoint or runs Cypher directly in the Neo4j container.

12. T012 - Backend admin endpoint (optional) [P]
    - Path: `backend/app/api/v1/endpoints/admin.py`
    - POST `/admin/cando/rebuild-similar-topic` → runs `build_edges` with auth guard.

## Dependencies
- T001 → T002, T006
- T003 → T004 → T006 → T008
- T005 → T004, T006, T007
- T009 after T006
- T011 after T004; T012 optional but after T005

## Parallelization [P]
- Can run in parallel: T001, T003, T005, T007.
- After T006 lands, T009 can proceed while T008 runs.

## Example Commands
- Backend tests: `cd backend; poetry run pytest -k cando -v`
- Rebuild edges: `pwsh ./scripts/rebuild_cando_similarity.ps1`

## Tasks: CanDoDescriptors Integration

Feature dir: specs/canDoDescriptorsIntegration

T001. Setup env and config [P]
- Ensure .env for Neo4j/Postgres; add flags in backend config: `LESSON_SOURCE_PRECEDENCE`, `GATING_MODE`, `GATING_N`.
- Paths: `backend/app/core/config.py`.

T002. Create Postgres migrations [sequential]
- Tables: `lessons`, `lesson_versions`, `user_lesson_overlays` (JSONB, indexes).
- Paths: `backend/migrations/*.sql` (or Alembic/Poetry migrations if applicable).

T003. Neo4j schema for lessons/pragmatics [P]
- Add `(:Lesson)` and `(:PragmaticPattern)` nodes; edges `[:COVERS]`, `[:USES_PRAGMA]`.
- Path: `resources/add_core_relationships.py` (or new script).

T004. Contracts: finalize JSON Schemas [P]
- Validate and lock schemas:
  - `specs/canDoDescriptorsIntegration/contracts/lesson-plan.json`
  - `specs/canDoDescriptorsIntegration/contracts/exercises.json`
  - Add `manifest.json` and `pragmatic_patterns.json` schemas.

T010. Contract tests for LessonPlan [P][TDD]
- Validate example lesson JSON against schema.
- Path: `tests/test_lesson_plan_contract.py`.

T011. Contract tests for Exercises [P][TDD]
- Validate example exercises JSON against schema.
- Path: `tests/test_exercises_contract.py`.

T020. Parser: compile example blocks → JSON [P]
- Implement `scripts/parse_cando_example.py` to extract named blocks from `resources/canDoDescriptorExample.txt` into:
  - `resources/compiled/cando/JFまるごと_13/lesson_plan.json`
  - `.../exercises.json`, `.../sample_dialog.json`, `.../stages.json`, `.../pragmatic_patterns.json`, `.../illustration_prompts.json`.

T021. Illustration generator reads compiled prompts [P]
- Update `scripts/generate_lesson_illustrations.py` to accept `--prompts resources/compiled/.../illustration_prompts.json`.

T022. Media wiring for compiled plan [P]
- Extend `scripts/wire_lesson_media.py` to read/write compiled `lesson_plan.json` (not only the txt block).

T030. Backend: ActivateCanDo service [sequential]
- Graph-first precedence with compiled fallback; attach media; emit `lesson_activated`.
- Paths: `backend/app/services/lexical_lessons_service.py` (new) and `backend/app/api/v1/endpoints/lexical.py`.

T031. Backend: GenerateExercises service [sequential]
- Respect phases (completion gate default; score gate optional); use pragmatic patterns and stages.
- Path: `backend/app/services/lexical_lessons_service.py`.

T032. Backend: GradeResponse service [P]
- Rubric (coverage, cohesion, language), hints, next_actions, event logging.
- Path: `backend/app/services/ai_conversation_practice.py` or new scorer module.

T033. Backend: UpdateMastery service [P]
- Implement p-update and status buckets; write edge in Neo4j.
- Path: `backend/app/services/grammar_progress_service.py` or new mastery module.

T034. Backend: RecommendNext service [P]
- Combine PREREQ graph, mastery p, textbook paths; return 3–5 candidates.
- Path: `backend/app/services/lexical_lessons_service.py`.

T040. Persist compiled lessons to Postgres [sequential]
- Write base lesson into `lesson_versions`; store manifest; link lesson_id to graph `(:Lesson)`.
- Paths: `backend/app/services/lexical_lessons_service.py` + DAO in `backend/app/db.py`.

T041. Import PragmaticPatterns to Neo4j [P]
- From compiled `pragmatic_patterns.json`; create nodes and `[:USES_PRAGMA]`.
- New script under `resources/`.

T050. API endpoints & OpenAPI [sequential]
- Endpoints for: ActivateCanDo, GenerateExercises, GradeResponse, UpdateMastery, RecommendNext.
- Path: `backend/app/api/v1/endpoints/lexical.py`; update `openapi.json`.

T060. Integration tests [P]
- E2E: ActivateCanDo returns lesson with media; GenerateExercises phases advance by completion.
- Paths: `tests/test_knowledge_api.py`, `tests/test_lexical_endpoints.py`.

T070. Performance & observability [P]
- Enforce p95 latency: ActivateCanDo ≤ 500 ms; GenerateExercises ≤ 1200 ms (excluding image gen); add metrics/logs.
- Paths: middleware/logging & tests.

T080. Docs & quickstart [P]
- Verify `specs/.../quickstart.md` steps; README pointers.

T090. MCP Playwright E2E scenarios [P]
- Add MCP test flows for: ActivateCanDo, GenerateExercises, media wiring (manifest exists), latency smoke.
- Paths: `tests/mcp/scenarios/activate_cando.json`, `tests/mcp/scenarios/generate_exercises.json`, `tests/mcp/scenarios/wire_media.json`, `tests/mcp/scenarios/perf_smoke.json`.
- Add `tests/mcp/README.md` describing how to run with playwright-mcp in this repo.

Dependencies & Parallelization
- Run T001–T004 first.
- Then T010–T011 (contract tests) in parallel.
- T020–T022 can run in parallel after contracts.
- Backend services T030–T034 sequential (shared files); others [P].
- Persistence/import (T040–T041) after T030–T034.
- Endpoints T050 after services.
- Integration, perf, docs (T060–T080) in parallel.

Example commands
- Parser: `python scripts/parse_cando_example.py --file resources/canDoDescriptorExample.txt --can-do-id "JFまるごと:13"`
- Illustrations: `python scripts/generate_lesson_illustrations.py`
- Wire media: `python scripts/wire_lesson_media.py`



