# RegPulse --- Technical Documentation

> Version 3.0 | 2026-04-14 | Covers 50 build prompts + Sprints 1--8 (all pre-launch code complete)

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Repository Structure](#2-repository-structure)
3. [Architecture](#3-architecture)
4. [Database](#4-database)
5. [Backend (FastAPI)](#5-backend-fastapi)
6. [Scraper (Celery)](#6-scraper-celery)
7. [Frontend (Next.js)](#7-frontend-nextjs)
8. [RAG Pipeline](#8-rag-pipeline)
9. [Anti-Hallucination System](#9-anti-hallucination-system)
10. [Authentication & Security](#10-authentication--security)
11. [Infrastructure & Deployment](#11-infrastructure--deployment)
12. [Configuration Reference](#12-configuration-reference)
13. [Testing & Evaluation](#13-testing--evaluation)
14. [Operational Runbook](#14-operational-runbook)

---

## 1. System Overview

RegPulse is a B2B SaaS platform for Indian banking professionals. It provides RAG-powered Q&A over RBI (Reserve Bank of India) circulars with cited answers, action item generation, and regulatory change tracking.

**Tech Stack:**

| Layer | Technology |
|---|---|
| Backend API | Python 3.11, FastAPI, SQLAlchemy 2.0 async, Pydantic v2 |
| Frontend | Next.js 14, TypeScript strict, Tailwind CSS, TanStack Query, Zustand |
| Database | PostgreSQL 16 + pgvector extension |
| Cache / Queue | Redis 7, Celery 5.x, Celery Beat |
| LLM (primary) | Anthropic claude-sonnet-4-20250514 (extended thinking, 10k budget) |
| LLM (fallback) | OpenAI GPT-4o |
| LLM (lightweight) | Claude Haiku (summaries, impact classification, KG extraction, cluster labels) |
| Embeddings | OpenAI text-embedding-3-large (3072-dim) |
| Reranker | ms-marco-MiniLM-L-6-v2 (sentence-transformers) |
| Payments | Razorpay (INR) |
| Analytics | PostHog (self-hosted compatible) |
| CI/CD | GitHub Actions -> GCP Artifact Registry -> Cloud Run |

---

## 2. Repository Structure

```
RegPulse/
├── backend/                    # FastAPI application
│   ├── app/
│   │   ├── config.py          # Pydantic Settings (singleton via @lru_cache)
│   │   ├── db.py              # SQLAlchemy async engine + session factory
│   │   ├── main.py            # FastAPI app, lifespan, SIGTERM handler
│   │   ├── exceptions.py      # 7 exception subclasses
│   │   ├── models/            # SQLAlchemy 2.0 Mapped[] ORM models
│   │   │   ├── user.py        # User, Session
│   │   │   ├── circular.py    # CircularDocument, DocumentChunk
│   │   │   ├── question.py    # Question, ActionItem, SavedInterpretation
│   │   │   ├── subscription.py # SubscriptionEvent
│   │   │   ├── admin.py       # PromptVersion, AdminAuditLog, AnalyticsEvent, ManualUpload, QuestionCluster
│   │   │   ├── scraper.py     # ScraperRun
│   │   │   ├── kg.py          # KGEntity, KGRelationship
│   │   │   ├── news.py        # NewsItem
│   │   │   ├── snippet.py     # PublicSnippet
│   │   │   └── debate.py      # DebateThread, DebateReply (Phase D.3)
│   │   ├── schemas/           # Pydantic request/response schemas
│   │   ├── routers/
│   │   │   ├── auth.py        # /auth/* (register, login, verify-otp, refresh, logout)
│   │   │   ├── circulars.py   # /circulars/* (list, search, detail, departments, tags, doc-types)
│   │   │   ├── questions.py   # /questions/* (ask SSE/JSON, history, detail, export, feedback)
│   │   │   ├── subscriptions.py # /subscriptions/* (plans, order, verify, webhook, plan, history)
│   │   │   ├── action_items.py # /action-items/* (CRUD)
│   │   │   ├── saved.py       # /saved/* (CRUD)
│   │   │   ├── snippets.py    # /snippets/* (create, list, public get, og image, revoke)
│   │   │   ├── news.py        # /news/* (list, detail)
│   │   │   ├── debates.py     # /debates/* (list, detail, reply, stance) (Phase D.3)
│   │   │   └── admin/         # Admin sub-package
│   │   │       ├── dashboard.py  # Stats + heatmap
│   │   │       ├── review.py     # Thumbs-down review queue
│   │   │       ├── prompts.py    # Prompt version management
│   │   │       ├── users.py      # User management + credit adjustment
│   │   │       ├── circulars.py  # Summary approval + metadata edit
│   │   │       ├── scraper.py    # Scraper controls
│   │   │       ├── news.py       # News management
│   │   │       └── uploads.py    # Manual PDF upload
│   │   ├── services/          # Business logic (injected via Depends)
│   │   │   ├── embedding_service.py  # OpenAI embeddings with Redis cache
│   │   │   ├── rag_service.py        # Hybrid retrieval + KG expansion + reranking
│   │   │   ├── llm_service.py        # Anthropic + GPT-4o fallback, injection guard, confidence scoring
│   │   │   ├── subscription_service.py # Razorpay integration
│   │   │   ├── snippet_service.py    # Safe snippet creation (truncation + safety invariant)
│   │   │   ├── kg_service.py         # Knowledge graph queries for RAG expansion
│   │   │   ├── pdf_export_service.py # PDF compliance brief (reportlab) + per-citation QR codes (qrcode[pil]) — Sprint 8
│   │   │   ├── otp_service.py        # OTP generation + verification via Redis
│   │   │   ├── email_validator.py    # Domain blocklist + MX check
│   │   │   └── summary_service.py    # AI summary generation via Haiku
│   │   └── utils/
│   │       ├── jwt_utils.py   # RS256 sign/verify, blacklist
│   │       ├── credit_utils.py # Atomic credit deduction (SELECT FOR UPDATE)
│   │       └── injection_guard.py # 20+ regex patterns
│   ├── migrations/
│   │   ├── 001_initial_schema.sql
│   │   ├── 002_sprint3_knowledge_graph.sql
│   │   ├── 003_sprint4_confidence.sql
│   │   ├── 004_sprint5.sql
│   │   └── 005_sprint6_system_user.sql
│   ├── tests/
│   │   ├── unit/              # 64+ pytest unit tests
│   │   └── evals/             # Golden dataset + retrieval evals
│   ├── Dockerfile             # Multi-stage: production (uvicorn) + dev (pytest)
│   ├── requirements.txt
│   └── requirements-dev.txt
│
├── scraper/                   # Celery worker + beat scheduler
│   ├── celery_app.py          # Celery config + beat schedule (4 schedules)
│   ├── tasks.py               # 8 tasks: daily_scrape, priority_scrape, process_document,
│   │                          #   process_uploaded_pdf, generate_summary, send_staleness_alerts,
│   │                          #   ingest_news, run_question_clustering
│   ├── config.py              # ScraperSettings (separate from backend config)
│   ├── db.py                  # Synchronous SQLAlchemy (scraper writes directly)
│   ├── crawler/
│   │   ├── rbi_crawler.py     # URL diff against rbi.org.in
│   │   └── rss_fetcher.py     # RSS feed ingestion
│   ├── extractor/
│   │   ├── pdf_extractor.py   # pdfplumber + pytesseract OCR fallback
│   │   ├── metadata_extractor.py # Regex + taxonomy extraction
│   │   └── constants.py       # Department codes, team keywords, supersession patterns
│   ├── processor/
│   │   ├── text_chunker.py    # Token-aware chunking
│   │   ├── embedding_generator.py # OpenAI batch embedding
│   │   ├── impact_classifier.py   # Haiku impact classification
│   │   ├── entity_extractor.py    # KG entity + relationship extraction
│   │   └── supersession_resolver.py # Supersession detection + staleness
│   ├── Dockerfile             # Includes tesseract + poppler for OCR
│   └── requirements.txt
│
├── frontend/                  # Next.js 14 application
│   ├── src/
│   │   ├── app/
│   │   │   ├── (marketing)/page.tsx    # Landing page
│   │   │   ├── (auth)/                 # Login, register, verify
│   │   │   ├── (app)/                  # Authenticated routes (25 pages)
│   │   │   ├── s/[slug]/page.tsx       # Public snippet view
│   │   │   └── admin/                  # 6 admin pages + uploads + heatmap
│   │   ├── components/        # Shared UI components
│   │   ├── hooks/             # TanStack Query hooks + useFeatureFlag
│   │   ├── lib/
│   │   │   └── api.ts         # Axios client (withCredentials: true)
│   │   └── stores/
│   │       └── authStore.ts   # Zustand (access token in memory only)
│   ├── Dockerfile             # Next.js standalone build on port 3000
│   └── tailwind.config.ts     # darkMode: "class", custom WCAG-AA palette
│
├── docker-compose.yml         # 6 services: postgres, redis, backend, scraper, celery-beat, frontend
├── nginx.conf                 # TLS 1.3, HSTS, CSP, rate limiting zones
├── Makefile                   # test, eval, lint, build targets
├── .github/workflows/
│   ├── ci.yml                 # Lint + test + build (on push/PR)
│   └── deploy.yml             # GCP deploy (on v* tag)
│
├── PRODUCTION_PLAN.md         # GCP deployment roadmap
├── CLAUDE.md                  # AI assistant instructions
├── MEMORY.md                  # Architecture & patterns reference
├── spec.md                    # Full technical specification
├── context.md                 # Current project state
├── LEARNINGS.md               # Phase 2 gotchas & prevention rules
├── TESTCASES.md               # Complete test inventory
├── RegPulse_PRD_v3.md         # Product Requirements Document v3.0
├── RegPulse_FSD_v3.md         # Functional Specification Document v3.0
└── .env.example               # Environment variable reference
```

---

## 3. Architecture

### 3.1 Component Diagram

```
rbi.org.in ─────┐
                │
RSS Feeds ──────┤
                ▼
     ┌──────────────────┐     ┌────────────────┐
     │  Scraper (Celery) │────▶│  PostgreSQL 16  │
     │  Worker + Beat    │     │  + pgvector     │
     └──────────────────┘     └───────┬────────┘
                                      │
     ┌──────────────────┐             │
     │  FastAPI Backend  │◀────────────┘
     │  (uvicorn)        │─────▶ Redis 7
     └────────┬─────────┘      (cache, OTP,
              │                 JWT blacklist,
              ▼                 task broker)
     ┌──────────────────┐
     │  Next.js 14       │
     │  Frontend          │
     └──────────────────┘
              │
              ▼
     ┌──────────────────┐
     │   Browser         │
     └──────────────────┘
```

### 3.2 Data Flow: Question Answering

```
User Question
     │
     ▼
  Injection Guard (20+ regex patterns)
     │ PASS
     ▼
  Normalise + SHA256 ──▶ Redis Cache HIT? ──▶ Return cached (free)
     │ MISS
     ▼
  Embed Question (OpenAI, Redis-cached)
     │
     ├──▶ pgvector cosine ANN (async)
     ├──▶ PostgreSQL FTS (async)
     └──▶ KG Expansion (if enabled)
              │
              ▼
  Reciprocal Rank Fusion (merge + dedup)
     │
     ▼
  Cross-encoder Rerank (ProcessPoolExecutor)
     │
     ▼
  Insufficient Context Guard (< 2 chunks?)
     │ >= 2 chunks
     ▼
  LLM Call (Anthropic, GPT-4o fallback)
     │
     ▼
  Citation Validation (strip hallucinated refs)
     │
     ▼
  Confidence Scoring (3 signals)
     │
     ├──▶ confidence >= 0.5 → Full answer
     └──▶ confidence < 0.5  → "Consult Expert" fallback
              │
              ▼
  INSERT question + Deduct Credit (SELECT FOR UPDATE)
     │
     ▼
  Cache in Redis (24h TTL) + SSE/JSON Response
```

### 3.3 Service Dependency Graph

```
Routers
  └──▶ Services (via FastAPI Depends)
         ├── EmbeddingService ──▶ OpenAI API + Redis
         ├── RAGService ──▶ EmbeddingService + KGService + PostgreSQL
         ├── LLMService ──▶ Anthropic API / OpenAI API
         ├── OTPService ──▶ Redis + SMTP
         ├── SubscriptionService ──▶ Razorpay API
         ├── SnippetService ──▶ PostgreSQL + Pillow (OG images)
         ├── KGService ──▶ PostgreSQL (kg_entities, kg_relationships)
         ├── PDFExportService ──▶ reportlab + qrcode[pil] (Sprint 8)
         └── SummaryService ──▶ Anthropic API (Haiku)
```

---

## 4. Database

### 4.1 PostgreSQL 16 + pgvector

- **19 tables** across 5 migration files.
- **pgvector** extension for 3072-dimensional embeddings (ivfflat index, lists=100).
- **GIN indexes** on tsvector (full-text search), JSONB columns (citations, tags).
- **Schema auto-applied** via `docker-entrypoint-initdb.d` volume mounts.

### 4.2 Migration Files

| File | Contents |
|---|---|
| `001_initial_schema.sql` | 13 core tables (users, sessions, circulars, chunks, questions, action_items, saved_interpretations, prompts, subscriptions, scraper_runs, audit_log, analytics, pending_domain_reviews) |
| `002_sprint3_knowledge_graph.sql` | kg_entities, kg_relationships, news_items, public_snippets |
| `003_sprint4_confidence.sql` | questions.confidence_score, questions.consult_expert |
| `004_sprint5.sql` | manual_uploads, question_clusters, circular_documents.upload_source, questions.cluster_id |
| `005_sprint6_system_user.sql` | System user (UUID 00000000-0000-0000-0000-000000000001) for audit log |

### 4.3 Key Constraints

- All `TIMESTAMPTZ` columns use `DateTime(timezone=True)` in SQLAlchemy to avoid asyncpg naive datetime rejection.
- `users.credit_balance` protected by `SELECT FOR UPDATE` during deduction.
- `public_snippets` enforces the safety invariant: only `quick_answer` (truncated) + 1 citation leaves the system.
- `questions.user_id` is nullable (set NULL on DPDP deletion).

### 4.4 Connection Configuration

- **Backend:** `postgresql+asyncpg://` (async driver). Pool size conditional (skipped for SQLite in tests).
- **Scraper:** `postgresql://` (synchronous psycopg2). `pool_size=5`.
- **Invariant:** Scraper and backend share the same database. This is a known tech debt (TD-01) accepted for v1.

---

## 5. Backend (FastAPI)

### 5.1 Application Lifecycle

`backend/app/main.py`:
- **Lifespan:** on startup, loads cross-encoder model (skipped in DEMO_MODE), initialises Redis connection, registers SIGTERM handler.
- **SIGTERM handler:** Sets a shutdown flag, allows in-flight requests to complete (15s grace period), then exits.
- **CORS:** Origin restricted to `FRONTEND_URL`. Razorpay webhook endpoint excluded.
- **Rate limiting:** slowapi with per-endpoint limits (auth: 5-10/hr, questions: 10/min).

### 5.2 Router Organisation

All routes prefixed `/api/v1/`. ~65 endpoints across 19 router files.

| Router | Prefix | Endpoints |
|---|---|---|
| auth.py | /auth | register, login, verify-otp, refresh, logout |
| account.py (Sprint 7) | /account | request-deletion-otp, delete (DPDP), export (DPDP) |
| circulars.py | /circulars | list, search, autocomplete, detail, departments, tags, doc-types, **updates** (Sprint 8), **updates/mark-seen** (Sprint 8) |
| questions.py | /questions | ask (SSE+JSON), history, detail, export (**PDF + QR**, Sprint 8), feedback, **suggestions** (Sprint 8) |
| subscriptions.py | /subscriptions | plans, order, verify, webhook, plan, history, **auto-renew** (Sprint 7) |
| action_items.py | /action-items | list (**w/ is_overdue**), **stats** (Sprint 8), create, update, delete |
| saved.py | /saved | list, create, detail, update, delete |
| snippets.py | /snippets | create, list, public get, og image, revoke |
| news.py | /news | list, detail |
| admin/dashboard.py | /admin | dashboard stats, heatmap, heatmap refresh |
| admin/review.py | /admin/questions | review queue, override |
| admin/prompts.py | /admin/prompts | list, create, activate, **test-question** (Sprint 8) |
| admin/users.py | /admin/users | list, update, add-credits |
| admin/circulars.py | /admin/circulars | pending-summaries, approve, edit metadata |
| admin/scraper.py | /admin/scraper | run history, manual trigger |
| admin/uploads.py | /admin/pdf | manual PDF upload |
| admin/news.py | /admin/news | list with dismissed, update status |
| debates.py (D.3) | /debates | list, detail, reply, stance |

**Shared helpers:** `app/dependencies/rag.py` exposes `build_rag_service(request, db, redis)` and `build_llm_service(request)`. Used by `routers/questions.py` (Q&A + suggestions) and `routers/admin/prompts.py` (sandbox). Never inline these in new routers.

### 5.3 Error Response Format

All errors return:
```json
{"success": false, "error": "Human-readable message", "code": "ERROR_CODE"}
```

Exception classes in `app/exceptions.py`: `InsufficientCreditsError`, `CircularNotFoundError`, `QuestionNotFoundError`, `PotentialInjectionError`, `ServiceUnavailableError`, `RateLimitExceededError`, `AuthenticationError`.

### 5.4 Auth Chain

```
get_current_user (JWT decode + blacklist check)
  └── require_active (is_active=True)
       └── require_verified (email_verified=True)
            ├── require_admin (is_admin=True)
            └── require_credits (credit_balance >= 1)
```

---

## 6. Scraper (Celery)

### 6.1 Task Inventory

| Task | Schedule | Description |
|---|---|---|
| `daily_scrape` | Daily 02:00 IST | Full crawl of all RBI sections |
| `priority_scrape` | Every 4h (06-22 UTC) | Circulars + Master Directions only |
| `process_document` | On-demand (chained) | Full pipeline: extract -> chunk -> embed -> store -> classify -> KG -> summary |
| `process_uploaded_pdf` | On-demand | Manual upload pipeline (same as above + upload status tracking) |
| `generate_summary` | On-demand (chained) | Haiku summary + pending_admin_review=TRUE |
| `send_staleness_alerts` | On-demand | Email users with stale saved interpretations |
| `ingest_news` | Every 30 min | RSS feed fetch + embedding + circular linking |
| `run_question_clustering` | Daily 03:00 IST | K-means on question embeddings + Haiku labels |

### 6.2 Scraper Pipeline Detail

1. **URL Diff:** `RBICrawler` fetches rbi.org.in section pages, extracts document URLs, diffs against `circular_documents.rbi_url` to find new documents.
2. **PDF Download:** `PDFExtractor` downloads PDF, returns bytes.
3. **Text Extraction:** `pdfplumber` primary, `pytesseract` OCR fallback for scanned documents.
4. **Metadata Extraction:** `MetadataExtractor` applies regex patterns from `constants.py` taxonomy. Extracts circular_number, department, dates, action_deadline, affected_teams.
5. **Chunking:** `TextChunker` splits by token count (configurable, ~500 tokens/chunk with overlap).
6. **Embedding:** `EmbeddingGenerator` calls OpenAI text-embedding-3-large in batches (max 100 chunks/call). Embeddings populated on INSERT (Sprint 6 fix).
7. **Storage:** `scraper/db.py` writes `circular_documents` + `document_chunks` rows.
8. **Impact Classification:** `ImpactClassifier` calls Claude Haiku with the first 2000 tokens. Returns HIGH/MEDIUM/LOW.
9. **Supersession Resolution:** `SupersessionResolver` pattern-matches supersession language, updates old circular status, triggers staleness detection.
10. **AI Summary:** `generate_summary` Celery task calls Haiku for 3-sentence summary. Sets `pending_admin_review=TRUE`.
11. **KG Extraction:** `EntityExtractor` runs regex + Haiku LLM pass. Writes to `kg_entities` + `kg_relationships`.

### 6.3 Important Constraints

- Scraper uses **synchronous** SQLAlchemy (`scraper/db.py`). Never uses `await`.
- Scraper has its own `ScraperSettings` (`scraper/config.py`). Never imports from `backend/app/config`.
- Scraper writes directly to the backend database (known tech debt TD-01).
- Celery worker must consume both `celery` and `scraper` queues: `-Q celery,scraper`.

---

## 7. Frontend (Next.js)

### 7.1 State Management

| State Type | Solution |
|---|---|
| Server state (API data) | TanStack Query (with cache invalidation) |
| Client state (auth, UI) | Zustand stores |
| Access token | Zustand memory only --- NEVER localStorage |
| Refresh token | httpOnly cookie (set by backend, never touched by JS) |

### 7.2 Auth Flow

1. User enters email -> POST /auth/register or /auth/login.
2. OTP entry -> POST /auth/verify-otp. Backend returns access token in body + sets httpOnly refresh cookie.
3. `authStore.setAuth(user, accessToken)` stores in Zustand memory.
4. All API calls use `axios` with `withCredentials: true` (sends cookie automatically).
5. On 401: attempt silent refresh via POST /auth/refresh (cookie sent automatically). If refresh fails: redirect to /login.
6. Frontend NEVER touches `document.cookie`.

### 7.3 SSE Streaming

The `/ask` page uses `fetch` + `ReadableStream` (not `EventSource`) for SSE:
- Processes `event: token`, `event: citations`, `event: done`, `event: error`.
- rAF-buffered rendering (Sprint 4): tokens accumulated in a buffer, flushed to DOM on each `requestAnimationFrame` to prevent jank during fast token delivery.

### 7.4 Dark Mode

- Tailwind `darkMode: "class"` configuration.
- System preference detection on first load (`prefers-color-scheme: dark`).
- User toggle persisted in `localStorage`.
- WCAG-AA compliant colour palette.
- PostHog event: `dark_mode_toggled`.

### 7.5 Key Pages (25 routes)

**Public:** Landing (/), Register, Login, Verify, Public Snippet (/s/[slug]).

**Authenticated:** Dashboard, Library (list + detail), Ask, History (list + detail), Updates, Saved, Action Items, Account, Upgrade.

**Admin:** Dashboard, Review, Prompts, Circulars, Users, Scraper, Uploads, Heatmap.

---

## 8. RAG Pipeline

### 8.1 Retrieval Parameters

| Parameter | Default | Description |
|---|---|---|
| `RAG_COSINE_THRESHOLD` | 0.4 | Minimum cosine similarity to include a chunk |
| `RAG_TOP_K_INITIAL` | 12 | Chunks retrieved per search path (vector + FTS) |
| `RAG_TOP_K_FINAL` | 6 | Chunks kept after cross-encoder reranking |
| `RAG_MAX_CHUNKS_PER_DOC` | 2 | Max chunks from a single circular |
| `RAG_KG_EXPANSION_ENABLED` | true | Include KG-related chunks in retrieval |
| `RAG_KG_BOOST_WEIGHT` | 0.1 | Weight for KG-expanded chunks in RRF scoring |

### 8.2 Reciprocal Rank Fusion

For each candidate chunk appearing in multiple search paths:
```
rrf_score = sum(1 / (60 + rank_in_path))
```

Chunks are deduplicated by ID, keeping the highest RRF score. Then limited to `RAG_MAX_CHUNKS_PER_DOC` per circular to prevent single-document domination.

### 8.3 KG-Driven RAG Expansion

When enabled, the RAG service:
1. Extracts entity mentions from the user's question (regex + lookup in `kg_entities`).
2. Queries `kg_relationships` for related entities.
3. Fetches document_chunks linked to related circulars.
4. Adds these chunks to the candidate pool with `RAG_KG_BOOST_WEIGHT` applied to their RRF scores.

### 8.4 Question Embeddings (Sprint 8)

After the LLM produces an answer, `routers/questions.py::_maybe_embed_question()` calls `EmbeddingService.generate_single(question_text)` and assigns the result to `questions.question_embedding` before INSERT. The same string was embedded by `RAGService.retrieve()` earlier in the request, so EmbeddingService's Redis cache (keyed by SHA256) turns this into a cache hit — no duplicate OpenAI API call.

`GET /questions/suggestions` embeds the partial query and issues:

```sql
SELECT id, question_text, quick_answer
FROM questions
WHERE user_id = :user_id
  AND question_embedding IS NOT NULL
  AND streaming_completed = TRUE
ORDER BY question_embedding <=> CAST(:vec AS vector)
LIMIT :limit
```

Constraints: scope to the current user (avoids leaking other users' queries), short-circuit for `len(q) < 5`, fall through to empty list when `db.bind.dialect.name != 'postgresql'` (SQLite unit tests don't support `vector`).

Legacy rows: `scripts/backfill_question_embeddings.py` batches NULL rows through EmbeddingService. Idempotent, safe to re-run. **Operational note:** run once per environment after Phase C deploy.

This improves recall for cross-circular questions (e.g., "NBFC lending norms" retrieves circulars linked via the NBFC entity graph).

### 8.4 Cross-Encoder Reranking

- Model: `ms-marco-MiniLM-L-6-v2` (sentence-transformers).
- Runs in `ProcessPoolExecutor` to avoid blocking the async event loop.
- 30-second timeout. On timeout: fall back to RRF-scored order.
- Skipped entirely in `DEMO_MODE` (avoids HuggingFace model download).

---

## 9. Anti-Hallucination System

### 9.1 Three-Layer Defense

| Layer | When | Action |
|---|---|---|
| **Injection Guard** | Before any LLM call | 20+ regex patterns detect prompt injection. 400 response, no credit charge. |
| **Insufficient Context Guard** | After retrieval, before LLM | < 2 chunks -> "Consult Expert" fallback. No LLM call, no credit charge. |
| **Confidence Scoring** | After LLM response | 3-signal composite. < 0.5 -> "Consult Expert" fallback. |

### 9.2 Citation Validation

Every `citation.circular_number` in the LLM response is validated against the set of circular numbers actually present in the retrieved chunks. Any hallucinated circular number is stripped. This is a hard invariant --- the system will never show a citation that wasn't in the retrieval context.

### 9.3 Confidence Scoring

Three signals combined into a 0.0--1.0 score:
1. **LLM self-reported confidence** (from extended thinking output).
2. **Citation survival ratio** (valid citations after stripping / total citations before stripping).
3. **Retrieval depth** (number of unique documents in top-K chunks).

Score < 0.5 OR zero valid citations -> `consult_expert=TRUE`.

### 9.4 Golden Dataset Evaluation

`tests/evals/test_hallucination.py` --- 21 test cases (originally 30, refined to 21):
- **Factual:** Direct citation questions with ground truth.
- **Multi-circular:** Cross-reference questions.
- **Out-of-scope:** Questions the system must refuse (SEBI, tax, crypto, etc.).
- **Injection:** Prompt manipulation attempts.

Run: `make eval` or `pytest tests/evals/ -v`.

### 9.5 Retrieval-Level Evaluation

`backend/tests/evals/test_retrieval.py` --- 8 tests:
- 6 retrieval recall queries (specific circulars must appear in results).
- 1 out-of-scope query (should return empty or low-relevance results).
- 1 embedding population verification (all chunks have non-null embeddings).

Requires real PostgreSQL + `OPENAI_API_KEY`.

---

## 10. Authentication & Security

### 10.1 Auth Mechanisms

| Mechanism | Implementation |
|---|---|
| OTP | 6-digit, Redis-stored, 10-min TTL, 5 attempts max, 3 sends/hr |
| JWT (access) | RS256, 30-min TTL (configurable), payload: sub, admin, jti, iat, exp |
| JWT (refresh) | 30-day TTL (configurable), httpOnly SameSite=lax cookie, bcrypt-hashed in DB |
| Token rotation | Every /auth/refresh revokes old session, issues new pair |
| Blacklist | Redis key `jti_blacklist:{jti}` with TTL = remaining token lifetime |
| Email validation | 250+ domain blocklist + async MX record check |
| Honeypot | Registration form hidden field. Non-empty -> flag `bot_suspect=TRUE`, fake 202 |

### 10.2 LLM Security

- **PII isolation:** User name, email, org_name are NEVER sent to any LLM. Stripped in the service layer before prompt construction.
- **Prompt injection:** 20+ regex patterns checked before every LLM call. Detected -> 400, no credit, logged.
- **User input isolation:** Wrapped in `<user_question>` XML tags. System prompt instructs model to ignore instructions inside tags.
- **DEMO_MODE guard:** Startup validator raises RuntimeError if `DEMO_MODE=true AND ENVIRONMENT=prod`.

### 10.3 Infrastructure Security

| Control | Implementation |
|---|---|
| TLS | Google-managed certificates on Cloud Run (prod); Nginx TLS 1.3 (self-hosted) |
| HSTS | `max-age=31536000; includeSubDomains; preload` |
| CSP | Restricts to own domain + Razorpay + rbi.org.in + Sentry DSN |
| CORS | Origin restricted to `FRONTEND_URL` |
| Rate limiting | slowapi with `X-Forwarded-For` trust |
| Webhook auth | Razorpay HMAC-SHA256 signature verification |
| Secrets | GCP Secret Manager (prod), `.env` file (dev) |

---

## 11. Infrastructure & Deployment

### 11.1 Local Development (Docker Compose)

6 containers:

| Service | Image | Port | Notes |
|---|---|---|---|
| postgres | pgvector/pgvector:pg16 | 5432 | Schema auto-applied via initdb.d |
| redis | redis:7-alpine | 6379 | |
| backend | ./backend/Dockerfile | 8000 | uvicorn, 1 worker |
| scraper | ./scraper/Dockerfile | --- | Celery worker, -Q celery,scraper |
| celery-beat | ./scraper/Dockerfile | --- | Celery beat scheduler |
| frontend | ./frontend/Dockerfile | 3000 | Next.js standalone |

```bash
cp .env.example .env   # Fill in API keys, set DEMO_MODE=true
docker compose up --build -d
```

### 11.2 Production (GCP asia-south1)

See `PRODUCTION_PLAN.md` for full roadmap.

| Component | GCP Service |
|---|---|
| Backend | Cloud Run (1 vCPU, 1GB, min-instances=1) |
| Frontend | Cloud Run (0.5 vCPU, 512MB, min-instances=1) |
| Celery worker + beat | GCE e2-small (always-on) |
| Scraper (daily crawl) | Cloud Run Job (triggered by Cloud Scheduler) |
| Database | Cloud SQL PostgreSQL 16 + pgvector |
| Cache | Memorystore Redis (Basic 1GB) |
| Registry | Artifact Registry |
| Secrets | Secret Manager |
| CI/CD | GitHub Actions with Workload Identity Federation |
| Observability | Cloud Monitoring Dashboard & Log-based metrics (deployed via `phase6_setup_observability.sh`) |

Estimated cost: ~$173/month.

### 11.3 CI/CD Pipeline

**ci.yml** (on push/PR to main):
1. `backend-lint`: ruff check
2. `backend-test`: pytest with SQLite + mock Redis
3. `frontend-build`: tsc --noEmit + next lint + next build

**deploy.yml** (on v* tag):
1. Authenticate via Workload Identity Federation
2. Build + push backend and frontend images to Artifact Registry
3. Deploy to Cloud Run (backend + frontend services)

---

## 12. Configuration Reference

See `backend/app/config.py` for the authoritative `Settings` class.

### 12.1 Required Variables

`DATABASE_URL`, `REDIS_URL`, `JWT_PRIVATE_KEY`, `JWT_PUBLIC_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`, `RAZORPAY_WEBHOOK_SECRET`, `SMTP_HOST`, `SMTP_USER`, `SMTP_PASS`, `SMTP_FROM`, `FRONTEND_URL`

### 12.2 Key Defaults

| Variable | Default | Notes |
|---|---|---|
| `DEMO_MODE` | false | Fixed OTP 123456, skip reranker, skip email/payment |
| `LLM_MODEL` | claude-sonnet-4-20250514 | Must be Anthropic model |
| `LLM_FALLBACK_MODEL` | gpt-4o | Must be OpenAI model (startup validator enforces) |
| `EMBEDDING_DIMS` | 3072 | Set to 1536 to halve storage |
| `RAG_KG_EXPANSION_ENABLED` | true | KG-driven retrieval expansion |
| `FREE_CREDIT_GRANT` | 5 | Credits given on registration |

### 12.3 DEMO_MODE Behaviour

When `DEMO_MODE=true` (blocked in prod):
- OTP fixed to `123456` --- no email sent.
- Work email validation skipped (any email accepted).
- Cross-encoder reranker skipped (no HuggingFace model download).
- Razorpay/SMTP use dummy keys.
- `OTP_MAX_SENDS_PER_HOUR` should be raised above default 3 for testing.

---

## 13. Testing & Evaluation

### 13.1 Test Inventory

| Suite | Count | Command | Notes |
|---|---|---|---|
| Backend unit tests | 64+ | `make test-backend` | pytest, SQLite + mocks |
| Frontend build check | 22 routes | `make test-frontend` | tsc + eslint + next build |
| Golden dataset eval | 21 tests | `make eval` | Anti-hallucination evaluation |
| Retrieval eval | 8 tests | `pytest backend/tests/evals/test_retrieval.py` | Requires real Postgres + OpenAI key |
| k6 load test | 3 scenarios | `k6 run tests/load/k6_load_test.js` | Smoke (1 VU), Load (20 VU), Spike (50 VU) |

### 13.2 Running Tests

```bash
# Unit tests (no external dependencies)
make test

# Golden dataset eval (requires running backend)
make eval

# Retrieval eval (requires running Postgres + OPENAI_API_KEY)
RAG_KG_EXPANSION_ENABLED=true pytest backend/tests/evals/test_retrieval.py -v

# Load test (requires running Docker Compose)
k6 run tests/load/k6_load_test.js
```

### 13.3 Linting

```bash
# Backend
ruff check backend/     # Lint (B008 suppressed globally)
black --check backend/  # Format (line-length=100)

# Frontend
cd frontend && pnpm lint   # ESLint
cd frontend && pnpm tsc --noEmit  # TypeScript strict
```

---

## 14. Operational Runbook

### 14.1 Starting the Platform (Local)

```bash
cp .env.example .env              # Fill in OPENAI_API_KEY, ANTHROPIC_API_KEY, set DEMO_MODE=true
docker compose up --build -d      # Start all 6 containers
# Wait for health checks (postgres + redis)
# Schema auto-applied on first postgres start

# Seed demo data (optional):
docker exec regpulse-backend python scripts/seed_demo.py

# Trigger initial scraper run:
docker exec regpulse-scraper celery -A celery_app -b redis://redis:6379/1 call scraper.tasks.daily_scrape

# Verify:
curl http://localhost:8000/api/v1/health
open http://localhost:3000
```

### 14.2 Triggering a Manual Scraper Run

```bash
# From host:
docker exec regpulse-scraper celery -A celery_app -b redis://redis:6379/1 call scraper.tasks.daily_scrape

# Or via admin UI: POST /api/v1/admin/scraper/trigger (requires admin JWT)
```

### 14.3 Backfilling Knowledge Graph

```bash
docker exec regpulse-scraper python /scraper/backfill_kg.py
```

### 14.4 Monitoring Celery Tasks

```bash
# Watch worker logs:
docker logs -f regpulse-scraper

# Watch beat logs:
docker logs -f regpulse-celery-beat
```

### 14.5 Database Backup (Local)

```bash
docker exec regpulse-postgres pg_dump -U regpulse regpulse > backup_$(date +%Y%m%d).sql
```

### 14.6 Launch Check

```bash
./scripts/launch_check.sh http://localhost:8000 http://localhost:3000
```

### 14.7 Common Issues

| Issue | Cause | Fix |
|---|---|---|
| `asyncpg.exceptions.DataError: cannot cast type timestamp without time zone` | SQLAlchemy column missing `DateTime(timezone=True)` | Add `DateTime(timezone=True)` to all TIMESTAMPTZ columns |
| Scraper tasks not executing | Worker not consuming `scraper` queue | Ensure `-Q celery,scraper` flag on worker |
| HuggingFace model download hang in Docker | SSL timeout behind Docker Desktop | Set `DEMO_MODE=true` to skip reranker |
| JWT PEM key truncated | Multiline PEM in .env | Use `\n` literals, not real newlines |
| `ADMIN_EMAIL_ALLOWLIST` parse error | pydantic-settings v2 expects JSON | Config has CSV+JSON validator; use either format |
| Frontend 401 loops | Refresh token expired or cookie not sent | Check `withCredentials: true` in axios; verify cookie domain |

---

*--- RegPulse Technical Documentation v3.0 ---*
