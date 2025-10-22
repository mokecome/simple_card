# Repository Guidelines

## Project Structure & Module Organization
- `backend/`: FastAPI app with `api/v1/` routers, `services/` business logic (OCR, classification, tasks), `models/` SQLAlchemy ORM, and `schemas/` Pydantic contracts.
- `frontend/`: React app (`src/` components, pages, API clients) built with `react-scripts`; production assets emit to `build/`.
- Root utilities: `scripts/` helpers, `start.sh`, `init_db.py`, and runtime artifacts under `output/` and `uploads/`.
- Keep architectural docs in `docs/`; operational notes (e.g., `USAGE_GUIDE.md`) remain at repo root.

## Build, Test, and Development Commands
- Backend dev server: `python main.py` (runs FastAPI on port 8006 with automatic schema sync).
- Frontend dev server: `cd frontend && npm start` (React app on port 1002 with proxy configured to backend).
- Integrated launch: `./start.sh` frees dev ports and starts both services with background logs.
- Frontend build: `cd frontend && npm run build` to emit optimized assets in `frontend/build/`.
- Dependency sync: `pip install -r backend/requirements.txt` and `cd frontend && npm install`.

## Coding Style & Naming Conventions
- Python: follow PEP8 (4 spaces), use type hints, and name services/routers with snake_case (`card_service`, `ocr.router`).
- React: prefer PascalCase for components, camelCase for helpers, keep hooks stateless, and centralize requests in `frontend/src/api/`.
- Store config in environment variables—copy patterns from `backend/core/config.py`; avoid committing secrets.

## Testing Guidelines
- Backend: place pytest suites under `backend/tests/` (folder pending). Use FastAPI TestClient and SQLite in-memory fixtures for CRUD and OCR parsing.
- Frontend: `npm test` triggers `react-scripts test` (Testing Library). Name files `*.test.js` beside the component under test.
- Validate critical flows—card CRUD, OCR upload, classification—before sending a PR.

## Commit & Pull Request Guidelines
- Commits follow `<type>: <summary>` (`fix: 修復OCR批量識別`, `style: 優化圖片預覽`). Keep scope focused and stick to the comment language (Chinese or English) already used.
- In pull requests, describe the change, link issues, list manual checks (`python main.py`, `npm start`), and add screenshots for UI updates.
- Tag backend/frontend maintainers when both stacks change, and call out schema or API updates explicitly.

## Security & Configuration Tips
- Populate `.env` with OCR and OpenAI keys before running services; see `backend/core/config.py` for required fields.
- Keep `output/card_images/` and `uploads/` git-ignored and scrub sample data of PII prior to commits.
