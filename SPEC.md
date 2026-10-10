**DATAQUERY AI**

Full-Stack AI Data Analyst

Product Requirements • Design System • Architecture • Database • Security • Code Style • Testing

**Implementation Plan and Technical Specification**

Version 1.0 \| MVP target: 1–2 days, with optional enhancements

# Document Purpose

This document defines the scope and implementation approach for DataQuery AI, a web application that lets users upload structured datasets, ask questions in natural language, and receive calculated results, charts, and evidence-grounded explanations. It combines Text-to-SQL or deterministic data operations with Retrieval-Augmented Generation (RAG).

Core principle: use a deterministic query engine for numerical facts; use RAG to retrieve relevant text and documentation; use the LLM to interpret questions, create a validated analysis plan, and explain results using returned evidence.

# 1. Product Requirements Document (PRD)

## 1.1 Product Summary

DataQuery AI is an AI-assisted analytics workspace. A user uploads a CSV or Excel file, optionally adds reference documents such as a PDF data dictionary or business policy, and asks questions in plain English. The system routes the question to structured analysis, document retrieval, or both, then returns an answer with a result table, optional chart, and citations where document evidence is used.

## 1.2 Problem Statement

People often have data but lack the time or skills to write SQL, Python, or complex spreadsheet formulas. Separately, important definitions and business rules may live in documents rather than the dataset itself. DataQuery AI brings numerical analysis and supporting context into one interface.

## 1.3 Target Users

- Students who need to explore academic or project datasets.

- Small business owners reviewing sales, expenses, customers, or inventory.

- Analysts who want to explore data before deeper analysis.

- Non-technical users who need answers without writing code.

## 1.4 Product Goals

- Upload and preview CSV and XLSX files.

- Automatically profile columns, data types, missing values, duplicate rows, and basic statistics.

- Answer natural-language questions with calculations performed by Pandas or DuckDB/SQLite.

- Create basic tables and charts from actual query results.

- Retrieve relevant text from uploaded PDF/TXT reference documents using RAG.

- Support combined questions that require both numerical analysis and document evidence.

- Show source names and page/chunk references for RAG-based answers.

- Handle unsupported questions and failures clearly rather than inventing results.

## 1.5 Scope and Priorities

| **Priority** | **Features**                                                                                                                                                                                                          |
|--------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| P0 — MVP     | CSV upload; basic XLSX upload if time allows; validation; data preview; dataset profiling; natural-language question; validated query plan; deterministic execution; result table; basic chart; loading/error states. |
| P1 — RAG MVP | PDF/TXT upload; text extraction; chunking; embeddings; ChromaDB vector search; document metadata; citations; SQL/RAG routing; answer grounded in retrieved passages.                                                  |
| P2 — Later   | Follow-up questions; conversation persistence; multi-file comparison; PDF reports; user accounts; workspace sharing; advanced hybrid search; background ingestion; query cache.                                       |

## 1.6 User Stories

- As a user, I can upload a dataset and preview its contents before asking questions.

- As a user, I can ask for totals, averages, rankings, counts, filters, and trends in plain English.

- As a user, I can upload documentation and ask what a metric or business rule means.

- As a user, I can ask a combined question that uses a calculation and a policy or definition.

- As a user, I can inspect the table or chart behind an answer.

- As a user, I can see which document and page/chunk support a document-based answer.

- As a user, I receive a clear message if the dataset or documents do not contain enough information.

## 1.7 Functional Requirements

| **ID** | **Requirement**     | **Acceptance condition**                                                                   |
|--------|---------------------|--------------------------------------------------------------------------------------------|
| FR-01  | Dataset upload      | Accept supported CSV/XLSX only; validate extension, file content, size, rows, and columns. |
| FR-02  | Dataset profile     | Return row/column counts, inferred types, missing values, duplicates, and preview.         |
| FR-03  | Question routing    | Classify requests as structured-data, document, combined, or unsupported.                  |
| FR-04  | Structured analysis | Convert question to a constrained plan; validate it; execute with Pandas/DuckDB/SQLite.    |
| FR-05  | RAG ingestion       | Extract PDF/TXT text, split into chunks, embed chunks, and store metadata.                 |
| FR-06  | RAG retrieval       | Retrieve relevant chunks scoped to the active workspace/document set.                      |
| FR-07  | Grounded answer     | Use computed results and/or retrieved passages; avoid unsupported claims.                  |
| FR-08  | Results UI          | Show answer, table, optional chart, and document citations when relevant.                  |
| FR-09  | Errors              | Handle invalid files, unsupported operations, empty results, and provider failures.        |
| FR-10  | Deletion            | Allow removal of uploaded files and their associated metadata/vector entries.              |

## 1.8 Non-Functional Requirements

- Numerical answers must come from actual computation, not LLM guesswork.

- Never execute arbitrary LLM-generated Python code.

- Validate every generated query plan and restrict operations to an allowlist.

- Scope document retrieval to the active dataset/workspace.

- Apply upload, row, column, response-size, and execution-time limits.

- Keep secrets on the backend and out of source control.

- Provide readable error messages and consistent API response schemas.

## 1.9 MVP Acceptance Criteria

- A user uploads a known CSV and receives a correct row count and numeric aggregate.

- The app answers a supported question and displays the actual computed result.

- A user uploads a text-based PDF or TXT document and can ask a question answered from retrieved passages.

- A document answer displays source metadata such as filename and page number when available.

- A combined question can use a structured result and retrieved document context, or clearly state if one branch is unsupported.

- Malformed uploads, unknown columns, empty retrieval, and LLM errors do not crash the app.

- The core pipeline is testable without making real LLM API calls.

# 2. Design System

## 2.1 Design Principles

- Professional analytics workspace with a clean, low-clutter layout.

- Make the question, answer, computed data, and source evidence visually distinct.

- Use consistent spacing, typography, colors, and component behavior.

- Always provide loading, empty, success, and error states.

- Prefer clarity over decorative complexity; charts must support the answer.

## 2.2 Visual Tokens

| **Token**      | **Value** | **Usage**                                |
|----------------|-----------|------------------------------------------|
| Primary        | \#2563EB  | Main actions, links, selected navigation |
| Primary hover  | \#1D4ED8  | Hover state                              |
| Background     | \#F8FAFC  | App canvas                               |
| Surface        | \#FFFFFF  | Cards, panels, dialogs                   |
| Text primary   | \#0F172A  | Main content                             |
| Text secondary | \#64748B  | Helper text and metadata                 |
| Border         | \#E2E8F0  | Inputs, dividers, cards                  |
| Success        | \#16A34A  | Successful operations                    |
| Warning        | \#D97706  | Warnings                                 |
| Error          | \#DC2626  | Errors and failed actions                |

## 2.3 Typography and Spacing

- Font: Inter or a system sans-serif stack.

- Page title: 24–30 px; section title: 18–20 px; body: 14–16 px; metadata: 12–14 px.

- Use a 4 px spacing scale: 4, 8, 12, 16, 24, and 32 px.

- Use consistent 8–12 px corner radii for inputs, buttons, and cards.

## 2.4 Main Screens

- Dashboard: upload dataset, upload reference documents, recent workspace/session, suggested questions.

- Dataset workspace: dataset name, summary cards, column metadata, data preview, question input.

- Answer view: plain-English response, result table, chart, calculation details, and export option.

- Sources panel: retrieved snippets with filename and page/chunk metadata.

## 2.5 Reusable Components

Button, Card, FileUploader, DatasetSummary, DataPreviewTable, QuestionInput, ChatMessage, ResultTable, ChartRenderer, SourceCitation, LoadingState, ErrorMessage, EmptyState.

## 2.6 Accessibility

Use semantic elements, visible keyboard focus, labeled inputs, sufficient contrast, text alternatives for charts, and error messages that do not rely on color alone.

# 3. Architecture

## 3.1 Recommended Stack

| **Layer**           | **Technology**                         | **Responsibility**                                                   |
|---------------------|----------------------------------------|----------------------------------------------------------------------|
| Frontend            | React + Vite + Tailwind CSS            | Upload, chat, preview, result table, chart, citations, UI states.    |
| API                 | Python + FastAPI + Pydantic            | Validation, endpoints, orchestration, consistent errors.             |
| Structured analysis | Pandas + DuckDB or SQLite              | Exact calculations, filters, grouping, sorting, aggregations.        |
| LLM                 | Gemini API via google-genai            | Question interpretation, constrained query plan, answer explanation. |
| RAG embeddings      | Sentence Transformers or embedding API | Convert text chunks and questions into vectors.                      |
| Vector store        | ChromaDB                               | Store chunk vectors and metadata; retrieve relevant passages.        |
| Document parsing    | PyMuPDF + standard text parsing        | Extract PDF/TXT content and page metadata.                           |
| Tests               | pytest + HTTPX + frontend test tools   | Unit, API, integration, and UI tests.                                |

## 3.2 High-Level Flow

```text
React UI
  │
  v
FastAPI API
  │
  ├──> Upload and validation service
  │      ├──> CSV/XLSX --> Pandas / DuckDB
  │      └──> PDF/TXT --> extraction --> chunking --> embeddings --> ChromaDB
  │
  └──> Question router
         │
         ├──> Structured question --> query planner --> validator --> data engine
         ├──> Document question   --> vector retrieval --> evidence passages
         └──> Combined question   --> data engine + vector retrieval
                                         │
                                         v
                                 Answer composer / LLM
                                         │
                                         v
                       Answer + table + chart + citations
```

## 3.3 Query Routing Rules

| **Question type**  | **Example**                                                              | **Processing**                                                                      |
|--------------------|--------------------------------------------------------------------------|-------------------------------------------------------------------------------------|
| Structured data    | Which product has the highest revenue?                                   | Generate validated plan and calculate with Pandas/DuckDB/SQL.                       |
| Document knowledge | What does net revenue mean?                                              | Retrieve relevant chunks and answer with source citations.                          |
| Combined           | What was June revenue and how does the policy define recognized revenue? | Run structured analysis and retrieve policy evidence; combine only supported facts. |
| Unsupported        | Predict next year's revenue without sufficient history.                  | Ask for clarification or explain limitations; do not fabricate.                     |

## 3.4 Structured Query Safety

- Prefer a structured JSON analysis plan over free-form Python or SQL.

- Validate allowed operations, column names, operators, sort directions, and result limits.

- Execute only through predefined functions; never use eval() or exec().

- If SQL is generated, parse and validate it, use read-only connections where applicable, and apply execution limits.

- Return computation output separately from the LLM-generated explanation.

## 3.5 RAG Pipeline

- Ingestion: validate document, extract text, preserve source metadata.

- Chunking: split text into overlapping chunks; start with approximately 500–800 tokens and 80–120 tokens overlap, then tune based on evaluation.

- Embedding: embed chunks using a consistent embedding model.

- Indexing: store vectors with workspace_id, document_id, filename, page_number, chunk_index, and ingestion timestamp.

- Retrieval: embed the query and retrieve top-k chunks, scoped to the active workspace.

- Grounded generation: pass the question and retrieved passages to the LLM; require it to acknowledge insufficient evidence.

- Citations: return source metadata with each retrieved passage used in the answer.

- Deletion: remove vectors and source files when a document is deleted.

## 3.6 API Endpoints

| **Method** | **Endpoint**                                       | **Purpose**                                          |
|------------|----------------------------------------------------|------------------------------------------------------|
| GET        | /api/health                                        | Health check.                                        |
| POST       | /api/datasets                                      | Upload CSV/XLSX and create dataset session.          |
| GET        | /api/datasets/{dataset_id}/profile                 | Dataset statistics and schema.                       |
| GET        | /api/datasets/{dataset_id}/preview                 | Return a limited preview.                            |
| POST       | /api/datasets/{dataset_id}/documents               | Upload PDF/TXT reference document and index it.      |
| POST       | /api/datasets/{dataset_id}/ask                     | Route question to structured analysis, RAG, or both. |
| GET        | /api/datasets/{dataset_id}/documents               | List indexed documents.                              |
| DELETE     | /api/datasets/{dataset_id}/documents/{document_id} | Delete document and associated vectors.              |
| DELETE     | /api/datasets/{dataset_id}                         | Delete dataset and related temporary resources.      |

## 3.7 Suggested Backend Structure

```text
backend/
  app/
    main.py
    api/
      health.py
      datasets.py
      ask.py
      documents.py
    core/
      config.py
      errors.py
      security.py
    schemas/
      dataset.py
      query.py
      answer.py
      document.py
    services/
      file_service.py
      profiling_service.py
      query_router.py
      query_planner.py
      query_validator.py
      query_executor.py
      document_service.py
      chunking_service.py
      embedding_service.py
      retrieval_service.py
      answer_service.py
      chart_service.py
  tests/
frontend/
  src/
    components/
      upload/
      dataset/
      chat/
      results/
      sources/
    pages/
    services/api.js
    App.jsx
```

# 4. Database and Storage Design

## 4.1 Storage Strategy

For the MVP, keep uploaded tabular data in temporary server-side files or load it into a controlled in-memory session. Use DuckDB or SQLite for structured querying if needed. Use ChromaDB for document chunks and embeddings. Add PostgreSQL only when persistent user accounts, durable metadata, or multi-user collaboration is required.

## 4.2 Logical Entities

| **Entity**              | **Important fields**                                                                                                       | **Purpose**                           |
|-------------------------|----------------------------------------------------------------------------------------------------------------------------|---------------------------------------|
| Dataset                 | id, owner_id/session_id, filename, storage_key, file_type, file_size_bytes, row_count, schema_json, created_at, expires_at | Metadata for uploaded tabular data.   |
| Document                | id, dataset_id, filename, storage_key, file_type, status, page_count, created_at, expires_at                               | Metadata for each reference document. |
| QueryHistory (optional) | id, dataset_id, question, route_type, status, duration_ms, created_at                                                      | History of questions and outcomes.    |
| Conversation (optional) | id, dataset_id, title, created_at, updated_at                                                                              | Groups messages into a session.       |
| Message (optional)      | id, conversation_id, role, content, result_metadata_json, created_at                                                       | Stores user and assistant messages.   |
| Vector chunk metadata   | chunk_id, dataset_id, document_id, text, embedding, page_number, chunk_index                                               | Indexed in ChromaDB for retrieval.    |

## 4.3 Data Isolation

- Every dataset and document must belong to a session or authenticated owner.

- Every vector search must filter by dataset_id/workspace_id.

- Do not retrieve chunks from other datasets or users.

- Deleting a dataset must delete its files, document metadata, and vectors.

- Set retention rules for temporary uploads and derived artifacts.

# 5. Security and Privacy

## 5.1 Upload Safety

- Allow only documented file types; verify file contents rather than trusting filename or MIME type.

- Set configurable limits, for example 10 MB per dataset and 10 MB per document for the MVP; tune based on hosting constraints.

- Set row, column, page, chunk, and processing-time limits.

- Use server-generated storage names and store uploads outside public static directories.

- Handle malformed files safely and clean temporary files after expiry.

- Do not execute spreadsheet macros or formulas.

- Protect CSV exports against spreadsheet formula injection.

## 5.2 LLM and RAG Safety

- Store API keys only in backend environment variables; commit only placeholder values in .env.example.

- Treat uploaded text as untrusted data, not as instructions that can override system rules.

- Never let retrieved documents authorize arbitrary tools or operations.

- Use structured outputs and strict schema validation for query plans and routing decisions.

- Do not execute LLM-generated Python code.

- Limit input length, output tokens, retries, and provider spend.

- Avoid sending unnecessary sensitive data to external AI services.

- If retrieved evidence is insufficient, state that limitation instead of guessing.

## 5.3 API Security

- Configure CORS to the actual frontend origin.

- Validate request bodies with Pydantic.

- Add rate limiting before public deployment.

- Implement authentication and ownership checks before multi-user release.

- Return generic client-facing errors; log technical details privately.

- Use HTTPS in production.

- Never rely on CORS as an authentication mechanism.

## 5.4 Environment Configuration

```env
GEMINI_API_KEY=
GEMINI_MODEL=
DATABASE_URL=
CHROMA_PERSIST_DIRECTORY=./data/chroma
MAX_UPLOAD_SIZE_MB=10
FRONTEND_ORIGIN=http://localhost:5173
```

Keep .env, uploaded datasets, vector-store files, logs, and temporary artifacts out of Git. The example environment file must contain placeholders only.

# 6. Code Style and Development Standards

## 6.1 Python

- Follow PEP 8 and use Ruff for linting/formatting.

- Use type hints for service functions and API schemas.

- Use Pydantic models for request and response contracts.

- Keep route handlers thin; put business logic in services.

- Use descriptive names and straightforward control flow.

- Use structured logging rather than print statements in application code.

- Centralize error handling and avoid leaking stack traces to clients.

## 6.2 React

- Use functional components and hooks.

- Keep API calls in a dedicated service module.

- Separate reusable components from page-level components.

- Handle loading, error, empty, and success states.

- Use ESLint and Prettier.

- Never place secret API keys in frontend variables.

## 6.3 Git and Reviews

Use small commits with clear intent. Example messages:

```text
chore: initialize frontend and backend
feat: add dataset upload and profiling
feat: add validated structured query execution
feat: index reference documents for RAG
feat: add SQL and RAG question routing
test: cover query safety and retrieval isolation
docs: add setup and deployment instructions
```

# 7. Testing Strategy

## 7.1 Unit Tests

- CSV/XLSX parsing, type inference, missing values, duplicate detection.

- Query-plan validation, column allowlist, filter validation, and result limits.

- Chunking behavior and metadata preservation.

- Document filtering and citation formatting.

- Chart selection from result schema.

- Dataset/document deletion and vector cleanup.

## 7.2 API Tests

- Valid and invalid dataset uploads.

- Valid and invalid document uploads.

- Profile and preview endpoints.

- Structured questions return expected computed values.

- Document questions return citations from the correct dataset.

- Unknown dataset/document IDs return safe errors.

- Provider failures do not crash the application.

## 7.3 Integration Tests

1. Upload a small deterministic CSV.

2. Ask a numerical question and compare the result with a known expected value.

3. Upload a test document containing a known fact.

4. Ask a document question and verify that the correct source chunk is retrieved.

5. Ask a combined question and verify that both the computed result and retrieved evidence appear.

6. Verify that a document from another dataset is never returned.

## 7.4 Mocking Policy

All normal pytest suites must mock Gemini calls. Mock embedding generation as well where it would otherwise require a remote service. Use a deterministic fake embedding or a local embedding model for retrieval tests. Real provider checks, if desired, must be separate, manually invoked smoke tests and must not run in the default test suite.

## 7.5 Security Tests

- Reject unsupported extensions, oversized files, and malformed inputs.

- Reject invalid or dangerous query plans.

- Confirm that arbitrary code cannot be executed.

- Test prompt-injection text embedded in uploaded documents.

- Confirm retrieval is scoped to the active dataset.

- Confirm secrets are not included in frontend builds or logs.

- Confirm deletion removes associated files and vector entries.

## 7.6 Sample Acceptance Dataset

```csv
product,city,revenue
Laptop,Delhi,80000
Phone,Mumbai,50000
Laptop,Mumbai,70000
Phone,Delhi,40000
```

Expected values: total revenue = 240000; Laptop revenue = 150000; Phone revenue = 90000; highest-revenue product = Laptop; row count = 4.

## 7.7 Evaluation Metrics

| **Metric**            | **What it checks**                                                    |
|-----------------------|-----------------------------------------------------------------------|
| Numerical correctness | Computed result matches expected result.                              |
| Query-plan validity   | Generated plan uses allowed operations and existing columns.          |
| Retrieval relevance   | Retrieved chunks contain useful evidence for the question.            |
| Citation correctness  | Displayed sources actually support the answer.                        |
| Groundedness          | Answer does not claim facts unsupported by results or retrieved text. |
| Latency               | Time spent on parsing, retrieval, query execution, and generation.    |

# 8. Two-Day Implementation Roadmap

## Day 1 — Structured Data Analysis

1. Set up React/Vite/Tailwind and FastAPI.

2. Implement CSV upload, validation, preview, and dataset profiling.

3. Implement a constrained question-to-query-plan flow.

4. Validate plans and execute supported calculations with Pandas/DuckDB/SQLite.

5. Return structured results and render a table.

6. Test a small known dataset end-to-end.

Day 1 exit criterion: a user can upload a CSV, ask a numerical question, and receive the correct calculated result.

## Day 2 — RAG, Visualization, and Release

1. Add PDF/TXT upload and safe text extraction.

2. Implement chunking, embeddings, and ChromaDB indexing.

3. Add document-only and combined SQL/RAG question routing.

4. Return source citations and render basic charts.

5. Add tests for retrieval isolation, query validation, and failure handling.

6. Deploy, write the README, and verify the hosted application.

Day 2 exit criterion: a user can ask a numerical question and a document question, and the app returns accurate calculations or evidence-grounded answers respectively.

Scope warning: a polished two-day build is possible only with a narrow feature set and familiar tools. If RAG ingestion or deployment takes longer than expected, keep the core CSV analysis and a single-document RAG workflow; defer authentication, persistent chat, multi-document comparison, and advanced hybrid search.

# 9. Definition of Done

- CSV upload and preview work.

- Numerical answers are computed by the data engine.

- Document questions retrieve relevant passages and show source references.

- Combined questions use both pipelines when appropriate, or explain limitations.

- Generated query plans are validated and no arbitrary code is executed.

- Default automated tests run without real Gemini calls.

- Uploads and retrieval are scoped and can be deleted.

- Secrets and user data files are excluded from version control.

- README contains setup, environment variables, architecture, test commands, limitations, and screenshots.

# 10. Recommended Build Order

1. Upload CSV and profile data.

2. Implement deterministic calculations and result tables.

3. Add LLM question interpretation with structured output.

4. Add chart rendering.

5. Add PDF/TXT ingestion and RAG retrieval.

6. Add routing for SQL-only, RAG-only, and combined questions.

7. Add citations, security checks, and tests.

8. Deploy and document the MVP.

# Final Recommendation

Build DataQuery AI as a hybrid analytics application, not as a chatbot that tries to use RAG for every task. The strongest design is: deterministic computation for numbers, vector retrieval for contextual documents, and an LLM that routes requests and explains results using the evidence it receives. This architecture is practical to demonstrate, easier to test, and gives the project a clear technical story for interviews.
