# PLAN.md — DataQuery AI Build Roadmap

## 1. Overview

DataQuery AI is a full-stack analytics workspace that lets users upload CSV datasets and reference documents, then ask questions in plain English. The core principle: **the deterministic engine (Pandas/DuckDB) owns all numbers**, ChromaDB RAG owns document evidence, and the LLM only interprets questions, produces a validated JSON plan, and explains results using the evidence it receives—it never invents facts. Every numerical answer is computed; every document answer is cited.

---

## 2. Phases

---

### Phase 0 — Project Setup

**Goal:** Runnable skeleton with health endpoint, environment wiring, and tooling configured.

#### Tasks
- Create root `.gitignore` (exclude `.env`, `uploads/`, `data/chroma/`, `__pycache__`, `node_modules`, `dist`)
- Create `.env.example` with all keys from SPEC §5.4 (placeholder values only); `GEMINI_MODEL` must be left **empty** — set it before Phase 2
- Scaffold backend: `backend/` with `requirements.txt` containing **Phase 0 only**: `fastapi`, `uvicorn[standard]`, `pydantic`, `pydantic-settings`, `python-multipart`, `httpx`, `pytest`, `pytest-asyncio`, `ruff` *(Pandas/DuckDB added in Phase 1; google-genai in Phase 2; PyMuPDF, sentence-transformers, chromadb in Phase 3)*
- Create `backend/app/main.py`: FastAPI app, CORS from `FRONTEND_ORIGIN`, mount API routers
- Create `backend/app/core/config.py`: load `.env` with `pydantic-settings`; expose typed settings object
- Create `backend/app/core/errors.py`: global exception handlers; generic client messages, logged detail
- Create `backend/app/api/health.py`: `GET /api/health` → `{"status": "ok"}`
- Scaffold frontend: `cd frontend && npm create vite@latest . -- --template react`; install Tailwind CSS + PostCSS; configure `tailwind.config.js` with design tokens from SPEC §2.2
- Create `frontend/src/services/api.js`: base URL from `VITE_API_URL`; placeholder exports
- Verify: `uvicorn app.main:app --reload` returns 200 on `/api/health`; `npm run dev` renders blank page without console errors

#### Files to Create / Edit
```
.gitignore
.env.example
backend/
  requirements.txt
  app/
    main.py
    core/config.py
    core/errors.py
    api/health.py
frontend/
  package.json
  vite.config.js
  tailwind.config.js
  postcss.config.js
  src/
    App.jsx
    services/api.js
```

#### Tests
- `curl http://localhost:8000/api/health` → `{"status":"ok"}`
- `npm run dev` loads without errors in browser
- `ruff check backend/` returns no errors

#### Done When
- Health endpoint returns 200
- Frontend dev server starts
- `.env` is not committed; `.env.example` has placeholder values only and `GEMINI_MODEL` is empty

#### Status
Done

**Summary:** All tasks complete. Backend installed with FastAPI, Uvicorn, Pydantic, pydantic-settings, python-multipart, httpx, pytest, ruff; 3/3 pytest passing, ruff clean, uvicorn confirmed 200 on /api/health. Frontend scaffolded with React + Vite + Tailwind CSS v4 (@tailwindcss/vite plugin); npm install succeeded, npm run build passed with 0 errors, Vite dev server running at localhost:5173. Local .env created and confirmed ignored by git. No deviations. Nothing carried over.

---

### Phase 1 — P0 MVP: CSV Pipeline (no LLM)

> **Dependencies added this phase** *(add to `requirements.txt`)*: `pandas`, `duckdb`

**Goal:** Upload a CSV, get a profile, preview rows, submit a hard-coded query plan, and see a computed result table and basic chart—all without any LLM call.

#### Tasks
- `schemas/dataset.py`: Pydantic models — `DatasetMeta`, `ProfileResponse`, `PreviewResponse`, `ErrorResponse`
- `schemas/query.py`: `AnalysisPlan` fields — `operation`, `columns`, `filters`, `group_by`, `agg` (one of `sum|avg|min|max|count`), `sort`, `limit`; `PlanResult`
- `schemas/answer.py`: `AnswerResponse` (answer_text, table, chart_spec, citations)
- `services/file_service.py`: accept upload; validate extension (`.csv` only for now); for CSV — decode as UTF-8/latin-1, reject if null bytes present, then call `pd.read_csv()` to confirm parsability; enforce 10 MB size limit; save to `uploads/<dataset_id>/`; return `dataset_id`
- `services/profiling_service.py`: load CSV with Pandas; compute row count, column count, inferred dtypes, missing-value counts, duplicate row count, numeric summary (min/max/mean); return `ProfileResponse`
- `api/datasets.py`: wire `POST /api/datasets`, `GET /api/datasets/{id}/profile`, `GET /api/datasets/{id}/preview` (first 100 rows), `DELETE /api/datasets/{id}`
- `services/query_validator.py`: define allowlists — operations: `["filter","aggregate","group_by","sort","count","top_n"]`; aggregations: `["sum","avg","min","max","count"]`; operators: `["eq","ne","gt","lt","gte","lte","in"]`; sort directions: `["asc","desc"]`; max result limit: 1000; validate `AnalysisPlan` (including `agg` field) against allowlists and dataset column names; raise structured error on violation
- `services/query_executor.py`: implement each allowlist operation via Pandas (no `eval()`/`exec()`); return rows + column names as dict
- `services/chart_service.py`: infer chart type from result schema (bar for group aggregation, line for time series, scalar for single value); return `chart_spec` dict (type, x, y, data)
- `api/ask.py` (stub): `POST /api/datasets/{id}/ask` — accept `{"question":"..."}`, return placeholder plan result (hardcoded plan for smoke test)
- **Frontend — FileUploader component**: drag-and-drop + click; shows loading, success (dataset_id), error states
- **Frontend — DatasetSummary component**: calls `/profile`; renders row/column count cards, dtype badges, missing value indicators
- **Frontend — DataPreviewTable component**: calls `/preview`; paginated table with fixed header
- **Frontend — ResultTable component**: renders answer table rows; empty state when no data
- **Frontend — ChartRenderer component**: Recharts bar/line/scalar; text alt for accessibility *(Recharts is not in SPEC §3.1 — see §8 Needs Approval)*
- **Frontend — QuestionInput component**: textarea + submit button; loading and error states (wired to stub endpoint)
- **Frontend — Dashboard page**: compose FileUploader → DatasetSummary → DataPreviewTable → QuestionInput → ResultTable + ChartRenderer

#### Files to Create / Edit
```
backend/app/
  schemas/dataset.py
  schemas/query.py
  schemas/answer.py
  services/file_service.py
  services/profiling_service.py
  services/query_validator.py
  services/query_executor.py
  services/chart_service.py
  api/datasets.py
  api/ask.py          ← stub only this phase
frontend/src/
  components/upload/FileUploader.jsx
  components/dataset/DatasetSummary.jsx
  components/dataset/DataPreviewTable.jsx
  components/results/ResultTable.jsx
  components/results/ChartRenderer.jsx
  components/chat/QuestionInput.jsx
  pages/Dashboard.jsx
  App.jsx             ← add routing
```

#### Tests
- `tests/test_file_service.py`: valid CSV accepted; non-text file rejected (null bytes); oversized file rejected; bad extension rejected; `pd.read_csv()` failure rejected
- `tests/test_profiling.py`: upload SPEC §7.6 CSV; assert `row_count=4`, `col_count=3`, correct dtypes
- `tests/test_query_validator.py`: reject unknown column; reject disallowed operation; reject disallowed aggregation; reject limit > 1000
- `tests/test_query_executor.py`: `{operation:"aggregate", columns:["revenue"], agg:"sum"}` → 240000; group_by product sums correct; filter by city works
- `tests/conftest.py`: shared fixtures (sample CSV bytes, tmp upload dir)

#### Done When
- Upload a CSV → correct row count and numeric aggregate returned
- Preview shows ≤ 100 rows
- Validator rejects unknown columns and disallowed operations
- Frontend shows loading / success / error states for upload and preview
- Result table and chart render from a hardcoded plan result

#### Status
Done

**Summary:** All Phase 1 tasks completed. Backend schemas (dataset, query, answer), file service with strict 10 MB CSV validation and encoding checks, disk-backed profiling service, query validator with comprehensive allowlists, query executor with safe Pandas operations (no eval/exec), chart service inferring scalar/bar/line specs, and datasets/ask API endpoints implemented. Frontend components built: FileUploader, DatasetSummary, DataPreviewTable, QuestionInput, ResultTable, ChartRenderer with Recharts, and composed into Dashboard. All 46 pytest tests pass, ruff is clean, npm run build succeeds with zero errors. Deviations: DuckDB deferred as Pandas handles all in-memory operations cleanly without raw SQL; Recharts was approved and used for charting. Nothing carried over.

---

### Phase 2 — LLM Integration (Gemini)

> **Dependencies added this phase** *(add to `requirements.txt`)*: `google-genai`

**Goal:** Replace the hardcoded stub with a real Gemini-powered question-to-plan-to-answer pipeline; return a plain-English explanation grounded in computed results.

#### Tasks
- `core/config.py`: add `GEMINI_API_KEY` and `GEMINI_MODEL` settings; `GEMINI_MODEL` must be **required** (no default) — startup fails with a clear error if unset
- `services/query_planner.py`: call Gemini with dataset schema + question; request **structured JSON output** (`AnalysisPlan` schema); system prompt forbids inventing columns or operations not in the allowlist
- `services/query_router.py` (stub): classify question as `structured | document | combined | unsupported`; for Phase 2 always route to `structured`
- `services/answer_service.py`: receive computed result + question; call Gemini to generate explanation grounded in the result only; include `answer_text`, pass through `table` and `chart_spec`
- `api/ask.py`: full flow — route → plan → validate → execute → explain; return `AnswerResponse`; handle LLM timeout, bad JSON, and validation failure gracefully
- **Frontend — ChatMessage component**: render question bubble + answer card (text + table + chart); show "Computed by data engine" badge
- Wire `QuestionInput` → `ChatMessage` in Dashboard; replace stub

#### Files to Create / Edit
```
backend/app/
  core/config.py          ← extend
  services/query_planner.py
  services/query_router.py
  services/answer_service.py
  api/ask.py              ← full implementation
frontend/src/
  components/chat/ChatMessage.jsx
  pages/Dashboard.jsx     ← wire ChatMessage
```

#### Tests
- `tests/test_query_planner.py`: mock Gemini; assert valid `AnalysisPlan` JSON is parsed and validated; assert disallowed op in response is caught
- `tests/test_ask_api.py`: mock planner + executor; full `/ask` round-trip returns `AnswerResponse`; Gemini timeout returns 503; bad JSON from Gemini returns 422
- `tests/test_answer_service.py`: mocked explanation references only provided computed values

#### Done When
- Question → Gemini plan → validator → Pandas execution → grounded explanation round-trip works
- Bad/disallowed plans are caught before execution
- LLM failures return structured errors, not stack traces
- "Computed by data engine" is visible in the UI; LLM explanation references only computed values

#### Status
Not started

---

### Phase 3 — P1 RAG: Document Pipeline

> **Dependencies added this phase** *(add to `requirements.txt`)*: `pymupdf`, `sentence-transformers`, `chromadb`

**Goal:** Upload PDF/TXT reference documents, chunk and embed them into ChromaDB, and route document/combined questions to retrieval with citations.

#### Tasks
- `schemas/document.py`: `DocumentMeta`, `Citation`, extend `AnswerResponse` with `citations: list[Citation]`
- `services/document_service.py`: validate file — PDFs: check `%PDF-` header bytes; TXT: decode as UTF-8/latin-1, reject if null bytes present; enforce 10 MB limit; extract text with PyMuPDF (PDF) or plain read (TXT); preserve page metadata; save to `uploads/<dataset_id>/docs/`
- `services/chunking_service.py`: split into ~600-token chunks with ~100-token overlap; attach `dataset_id`, `document_id`, `filename`, `page_number`, `chunk_index`
- `services/embedding_service.py`: embed chunks with `sentence-transformers/all-MiniLM-L6-v2` (local, no API key); expose `embed_text(text) -> list[float]`
- `services/retrieval_service.py`: init ChromaDB `PersistentClient`; `index_chunks()` → upsert; `retrieve(query, dataset_id, top_k=5)` always filter by `dataset_id`; `delete_document()` → remove vectors
- `api/documents.py`: wire `POST /api/datasets/{id}/documents`, `GET /api/datasets/{id}/documents`, `DELETE /api/datasets/{id}/documents/{doc_id}`
- `services/query_router.py`: implement full routing — `structured | document | combined | unsupported`; for `unsupported` return safe explanation without fabricating
- `api/ask.py`: extend for `document` and `combined` routes; for `combined` run both branches and merge; always scope retrieval to `dataset_id`
- `services/answer_service.py`: for RAG answers pass retrieved passages to Gemini; instruct it to cite only them; return `citations` list
- **Frontend — SourceCitation component**: render filename, page/chunk number, snippet text
- **Frontend — Sources panel**: list all citations below answer card
- Wire document upload to UI (tab or second uploader); show indexed document list

#### Files to Create / Edit
```
backend/app/
  schemas/document.py
  services/document_service.py
  services/chunking_service.py
  services/embedding_service.py
  services/retrieval_service.py
  api/documents.py
  services/query_router.py    ← full implementation
  services/answer_service.py  ← extend for RAG
  api/ask.py                  ← extend for document + combined
frontend/src/
  components/sources/SourceCitation.jsx
  components/upload/DocumentUploader.jsx
  pages/Dashboard.jsx         ← add doc upload + sources panel
```

#### Tests
- `tests/test_document_service.py`: valid PDF accepted (`%PDF-` header); PDF with wrong header rejected; valid TXT accepted; TXT with null bytes rejected; oversized rejected
- `tests/test_chunking.py`: chunk count and overlap correct; metadata fields present on every chunk
- `tests/test_retrieval_isolation.py`: index chunk under dataset A; retrieve with dataset B → empty; delete document → retrieve returns nothing
- `tests/test_rag_api.py`: mock embedding + Gemini; document question returns non-empty `citations` with correct filename; combined question returns table + citations

#### Done When
- PDF/TXT upload → chunked → indexed in ChromaDB
- Document question returns cited passages with filename and page/chunk
- Retrieval is scoped: cross-dataset retrieval returns nothing
- Combined question returns computed table + document citation
- Deletion removes vectors; subsequent retrieval returns nothing

#### Status
Not started

---

### Phase 4 — Security Hardening, Gap Tests, README, Deployment

> **Deployment scope:** Docker Compose (backend + frontend). Cloud hosting (e.g. Fly.io, Railway) is a stretch goal — mark it out of scope if time is short and note it in the README limitations.

**Goal:** Close security gaps, fill any test coverage gaps, write the README, and produce a deployable build.

#### Tasks
- `core/security.py`: centralize file-validation helpers used across phases; add CSV export formula-injection sanitization (prefix dangerous cells with `'`); enforce configurable row/column/page/chunk limits via settings
- Restrict CORS `allow_origins` to `[settings.FRONTEND_ORIGIN]` (no `*`) — confirm this is set from Phase 0
- Apply `max_tokens`, `timeout`, and retry limits on all Gemini calls in `query_planner.py` and `answer_service.py`
- Add rate-limiting middleware (`slowapi`) on upload and ask endpoints *(needs approval — see §8)*
- **Gap tests** — write any tests not covered in Phases 1-3:
  - `tests/test_integration.py`: end-to-end upload SPEC §7.6 CSV → ask "total revenue" → assert 240000 (mocked Gemini planner)
  - `tests/test_delete_cascade.py`: dataset delete removes files + vectors
  - Prompt-injection TXT embedded in document does not affect routing or plan
- `frontend/src/components/`: audit all components; add `LoadingState.jsx`, `ErrorMessage.jsx`, `EmptyState.jsx` where missing
- Confirm no API keys appear in `vite.config.js` or built JS bundle (`grep -r "GEMINI" dist/`)
- Write `README.md`: setup steps, required env vars (note `GEMINI_MODEL` must be set), architecture text diagram, test commands, known limitations, screenshots
- Verify `DELETE /api/datasets/{id}` cascades: removes uploaded file, all doc files, all Chroma vectors for `dataset_id`
- Frontend production build: `npm run build`; confirm no secrets in `dist/`
- **Deployment:** create `docker-compose.yml` with `backend` and `frontend` services; document how to run locally with Docker; note cloud deployment as stretch goal in README

#### Files to Create / Edit
```
backend/
  app/core/security.py
  tests/
    conftest.py
    test_upload_security.py
    test_query_validator.py
    test_retrieval_isolation.py
    test_api.py
    test_integration.py
frontend/src/components/
  LoadingState.jsx
  ErrorMessage.jsx
  EmptyState.jsx
README.md
docker-compose.yml
```

#### Tests
- `pytest backend/tests/ -v` — all tests (Phases 1-4) pass with zero real API calls
- Manual smoke: upload SPEC §7.6 CSV; ask "What is total revenue?"; assert 240000 displayed
- `npm run build` succeeds; `grep -r "GEMINI" dist/` returns nothing
- `docker-compose up` → both services healthy; health endpoint returns 200

#### Done When
- Full pytest suite passes with mocked LLM
- Security gap tests pass (injection sanitization, delete cascade, prompt-injection)
- README covers setup, required env vars (inc. `GEMINI_MODEL`), architecture, test commands, and limitations
- No secrets or uploaded files in version control
- Deletion removes all associated data (files + vectors)
- `docker-compose up` starts both services successfully

#### Status
Not started

---

## 3. DO

- Follow the stack, API endpoints, and folder structure in SPEC.md exactly.
- Use a JSON `AnalysisPlan` validated against an allowlist (operations, columns, operators, sort directions, result limits).
- Compute every number with Pandas/DuckDB — never with the LLM.
- Scope every ChromaDB query by `dataset_id`.
- Return consistent `AnswerResponse` and `ErrorResponse` schemas (Pydantic) from every endpoint.
- Keep all secrets in `.env` only; commit only `.env.example` with placeholders.
- Add loading, empty, success, and error states to every UI component.
- Use the design tokens from SPEC §2.2 in `tailwind.config.js`.
- Write tests that run without real Gemini calls (mock the LLM client).
- Use the commit message style from SPEC §6.3 (`chore:`, `feat:`, `test:`, `docs:`).

---

## 4. DO NOT

- Do not use `eval()`, `exec()`, or run LLM-generated Python/SQL directly.
- Do not let the LLM invent numbers, column names, or citations.
- Do not commit `.env`, `uploads/`, `data/chroma/`, logs, or any user file.
- Do not hardcode API keys anywhere in source code.
- Do not trust file extensions or MIME types alone — for PDFs check the `%PDF-` header; for CSV/TXT verify text decodability and absence of null bytes, then parse.
- Do not add libraries outside SPEC §3.1 without asking first.
- Do not build everything in one go — stop and wait for approval after each phase.

---

## 5. IGNORE (Out of Scope)

- **P2 features:** follow-up questions, conversation persistence, multi-file comparison, PDF export, user accounts, workspace sharing, advanced hybrid search, background ingestion, query cache.
- PostgreSQL and any authentication/authorization system.
- Optional entities: `QueryHistory`, `Conversation`, `Message`.
- XLSX support — defer until CSV pipeline works end-to-end.

---

## 6. Risks and Assumptions

| # | Risk / Unclear Item | Assumption Made |
|---|---------------------|-----------------|
| 1 | SPEC says "DuckDB or SQLite" — which to use? | Default to Pandas for in-memory ops; add DuckDB for complex group/sort. Avoid SQLite to prevent any raw SQL execution path. |
| 2 | "Sentence Transformers or embedding API" — local vs. remote? | Use local `all-MiniLM-L6-v2` so tests never need a remote key. If Gemini embeddings are wanted later, add an env flag. |
| 3 | Session vs. persistent dataset IDs — no auth in MVP | Generate a UUID per upload; store in server-side dict keyed by `dataset_id`; no user session. Files expire on server restart unless a persist path is configured. |
| 4 | SPEC has `GEMINI_MODEL=` with no default value | `GEMINI_MODEL` is required with no default; `config.py` raises a startup error if unset. User fills it in `.env` before Phase 2. |
| 5 | ChromaDB in-process vs. server mode | Use in-process `PersistentClient` for MVP simplicity. |
| 6 | XLSX listed under P0 "if time allows" | Treating XLSX as a Phase 4 stretch goal. Phase 1 is CSV-only. |
| 7 | No explicit rate-limit library mentioned | Will use `slowapi`; will flag before adding. |
| 8 | Frontend test tooling not specified beyond "frontend test tools" | Will use Vitest + React Testing Library; will flag before adding. |
| 9 | `CHROMA_PERSIST_DIRECTORY` default path `./data/chroma` is relative | Will resolve relative to `backend/`; documented in README. |
| 10 | Delete endpoint cascade scope not fully specified | Will cascade: uploaded file + all document files + all Chroma vectors for that `dataset_id`. |

---

## 7. Rules for Later Phases

- **Implement one phase at a time.** Do not begin the next phase until you explicitly approve the current one.
- After completing each phase, update only the Status line and add a short summary under that phase: what was built, any deviations, and anything that carries over.
- If a task turns out to be much larger than 60 minutes, split it and note the split here before continuing.

---

## 8. Needs My Approval Before Use

The following libraries are **not listed in SPEC §3.1**. They will not be installed until you explicitly approve them:

| Library | Used for | Phase |
|---------|----------|-------|
| `pydantic-settings` | Load `.env` into typed config | 0 |
| `React Router` (`react-router-dom`) | Client-side routing between pages | 1 |
| `Recharts` | Bar/line charts in frontend | 1 |
| `slowapi` | Rate limiting on FastAPI endpoints | 4 |
| `Vitest` + `@testing-library/react` | Frontend unit tests | 4 |
