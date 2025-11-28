## Quickstart: CanDo-driven lessons

Prerequisites
- .env configured (Neo4j URI/USER/PASSWORD; Postgres in docker-compose if used). Do not commit secrets.
- Python venv activated; `pip install pillow python-dotenv neo4j`.

1) Parse example and compile JSON
- Source: `resources/canDoDescriptorExample.txt` (LessonPlan, Exercises, Dialog, Stages, PragmaticPatterns, IllustrationPrompts).
- Create a small parser (planned: `scripts/parse_cando_example.py`) to extract named blocks and write to:
  - `resources/compiled/cando/JFまるごと_13/lesson_plan.json`
  - `resources/compiled/cando/JFまるごと_13/exercises.json`
  - `resources/compiled/cando/JFまるごと_13/sample_dialog.json`
  - `resources/compiled/cando/JFまるごと_13/stages.json`
  - `resources/compiled/cando/JFまるごと_13/pragmatic_patterns.json`
  - `resources/compiled/cando/JFまるごと_13/illustration_prompts.json`

2) Generate illustrations (core assets)
- Run: `python scripts/generate_lesson_illustrations.py`
- Output: `images/lessons/cando/JFまるごと_13/*.png` + `manifest.json`.

3) Wire media into LessonPlan
- Run: `python scripts/wire_lesson_media.py`
- This injects `illustrations[]` and per-section `media` into the LessonPlan block in the example (and in compiled JSON once parser is in place).

4) Import to Neo4j (structure)
- Ensure CanDoDescriptor nodes imported (`resources/can_do_import.py`).
- Create `(:Lesson {lesson_id, version})` and `(:Lesson)-[:COVERS]->(:CanDoDescriptor)`.
- Optionally add `(:PragmaticPattern)` and link `[:USES_PRAGMA]` using `pragmatic_patterns.json`.

5) Store lesson JSON in Postgres (content)
- Tables: lessons, lesson_versions, user_lesson_overlays (JSONB).
- Insert base `lesson_plan.json`, `exercises.json`, `manifest.json` into `lesson_versions`.

6) Service behavior
- ActivateCanDo: Graph-first by default; fill gaps from compiled (feature flag `LESSON_SOURCE_PRECEDENCE`).
- GenerateExercises: use completion gate by default (configurable N per phase); optional score gate.
- Personalization: apply JSON Patch overlay pinned to base version; auto‑rebase with conflict log.

7) API smoke tests
- GET /api/lessons/activate?can_do_id=JFまるごと:13 → returns LessonPlan JSON with media refs.
- POST /api/lessons/exercises → returns ExerciseBundle JSON (phase-aware).

Notes
- Images: serve statically or via CDN; manifests contain refs only.
- Safety: sanitize prompts; avoid brand text in images; no PII in JSON.


