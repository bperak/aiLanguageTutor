# Repository Guidelines

## Project Structure & Module Organization
- `backend/`: FastAPI app (`app/main.py`, `app/api/v1`, `app/core`, `app/db.py`).
- `frontend/`: Next.js 14+ app (`src/app`, `src/components`, `src/lib`).
- `validation-ui/`: Streamlit validation tool (`main.py`).
- `tests/` and `backend/tests/`: Pytest suites (`test_*.py`).
- `scripts/`: Utilities (e.g., `scripts/run_tests.ps1`).
- `docker-compose.yml`: Spins up backend, frontend, validation UI, and databases.

## Build, Test, and Development Commands
- Start stack (Docker): `docker-compose up -d` then check `docker-compose ps`.
- Backend dev: `cd backend && poetry install && poetry run uvicorn app.main:app --reload --port 8000`.
- Backend tests: `cd backend && poetry run pytest` or `./scripts/run_tests.ps1` from repo root.
- Frontend dev: `cd frontend && npm install && npm run dev` (http://localhost:3000).
- Lint frontend: `cd frontend && npm run lint`.

## Coding Style & Naming Conventions
- Python: 4-space indent, type hints required for public functions; line length 88.
  - Linting: Ruff (py311). Keep imports sorted; avoid unused imports.
- TypeScript/React: ESLint via `next lint`; components `PascalCase` (e.g., `GrammarPatternCard.tsx`), hooks/utilities `camelCase`.
- Files/dirs: tests `test_*.py`; Next.js routes under `src/app/.../page.tsx`.

## Testing Guidelines
- Framework: Pytest. Place new tests in `tests/` (API/e2e) or `backend/tests/` (unit/integration).
- Naming: `test_<feature>.py`, functions `test_<case>()`.
- Run subsets: `pytest -k <keyword> -v`.
- Aim for 80%+ coverage on new/changed code; add tests for edge cases and failures.

## Commit & Pull Request Guidelines
- Commits: Use a clear, imperative subject (e.g., "Add grammar study API"). The history shows short subjects (e.g., initial setup) with optional detail after a colon.
- Pull Requests must include:
  - Purpose and scope; link related issues.
  - How to test (commands, routes touched).
  - Screenshots/GIFs for UI changes.
  - Checklist: tests pass (`./scripts/run_tests.ps1`), lint clean (Ruff/ESLint), no secrets in diff.

## Security & Configuration Tips
- Secrets: Copy `.env.template` to `.env` and fill keys (OpenAI, Gemini, DB, JWT). Never commit real secrets.
- JWT: Generate with `openssl rand -hex 32` and set `JWT_SECRET_KEY`.
- Datastores: Ensure PostgreSQL and Neo4j env vars match `docker-compose.yml` and backend config.

