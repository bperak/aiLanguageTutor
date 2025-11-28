# Lexical Features Integration

This document summarizes the integration of the lexical visualization, lessons, and readability features into the AI Language Tutor.

## Overview
- 2D/3D lexical network visualization using `react-force-graph` and `react-force-graph-3d`.
- Lesson seeding by 6 difficulty levels (Lee levels mapped via `:DifficultyLevel.numeric_level`).
- AI‑generated lexical exercises with level‑appropriate prompts and optional readability analysis.
- Optional Japanese readability scoring via `jreadability` (+ `fugashi`) with graceful fallback when not installed.

## Backend
- Endpoints (v1)
  - `GET /api/v1/lexical/graph?center=<word>&depth=1|2&limit=`
    - Returns a small ego‑graph around the center `:Word` for visualization.
  - `GET /api/v1/lexical/lessons/seed?level=1&count=12`
    - Picks random words at the selected level with translation for lesson seeds.
  - `POST /api/v1/lexical/lessons/generate?word=<kanji|hiragana>&level=1&provider=openai|gemini&model=...&analyze_readability=true`
    - Generates a level‑appropriate lexical exercise around a target word using AI (OpenAI or Gemini). Includes related vocabulary from the graph. Optionally attaches readability analysis.
  - `POST /api/v1/lexical/readability?text=...`
    - Analyzes Japanese readability via `jreadability` if available.
- Services
  - `backend/app/services/lexical_lessons_service.py`
    - Word seeding by level, neighbor extraction, prompt construction, AI generation, readability annotation.
  - `backend/app/services/readability_service.py`
    - Optional jreadability wrapper with JP text extraction and level interpretation.
- Registration
  - `backend/app/api/v1/api.py` includes `lexical` router.

## Frontend
- Pages
  - `src/app/lexical/graph/page.tsx`
    - Center word input, depth control (1–2), 2D/3D toggle.
    - Color scheme: by Domain, POS, or Level.
    - Neighbor expansion on node click (incremental fetch+merge).
    - Fetches `/lexical/graph` and renders force graph.
  - `src/app/lexical/lessons/page.tsx`
    - Level selector, seed word dropdown, “Generate Lesson” button. Displays generated content and readability.
- Components
  - `src/components/lexical/LexicalGraph3D.tsx` – 3D graph with camera focus and neighbor expansion on click.
  - `src/components/lexical/LexicalGraph2D.tsx` – 2D graph variant with the same behaviors.
  - Visual styling: node color by Domain/POS/Level; link width and alpha scale by `synonym_strength/weight`.
- Navigation
  - Added links to `Lexical Graph` and `Lexical Lessons` in `NavBar`.

## Configuration
- Frontend env: set `NEXT_PUBLIC_API_BASE_URL` to backend base URL.
- AI providers: backend reads `OPENAI_API_KEY` and/or `GEMINI_API_KEY` from `.env` (see existing config).
- Readability (optional): install `jreadability` and `fugashi` to enable scoring.
- Auth: logging lesson attempts requires a signed-in user (JWT). The UI will try to log attempts; failures are ignored when unauthenticated.

## Data Expectations
- Neo4j contains `:Word` nodes and `:SYNONYM_OF` relationships (Lee + NetworkX importers already in repo).
- `:Word-[:HAS_DIFFICULTY]->(:DifficultyLevel {numeric_level: 1..6})` defines the 6 levels used for seeding.

## Notes & Limits
- Graph endpoint is tuned for small ego‑graphs (hundreds of edges). For very dense nodes, increase server‑side limits cautiously.
- Lesson generation prompts are concise and level‑aware; you can refine them in `LexicalLessonsService._build_exercise_prompt`.
- Readability gracefully returns `available=false` if dependencies are missing; no runtime crash.
- Lesson attempts are recorded as messages in a `lesson` conversation session for analytics/personalization.

## Next Steps (Optional)
- Add neighbor expansion on node click (re‑query with new center).
- Enrich colors by `:SemanticDomain`/POS and link width by `synonym_strength`.
- Persist lessons and attempts in Postgres for personalization.
- Add collocations and example sentences to support additional exercise types.
