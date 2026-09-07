# RegPulse: Repository Setup & Prompt Improvements Plan

## Context

The RegPulse project has 50 sequential Claude Code prompts designed to build an RBI regulatory intelligence B2B SaaS platform from scratch. The current state is an empty git repo (`RegPulse/RegPulse/`) plus documentation files (PRD, FSD, 50 prompts DOCX, HTML mockup, README, MEMORY.md). The goal is to analyze the prompts and suggest improvements before executing the build.

After thorough analysis of all 50 prompts, the PRD, FSD, and MEMORY.md, I've identified **9 categories of improvements** totaling ~40 actionable items. Below is the consolidated list, prioritized by impact.

---

## Top 10 Highest-Impact Improvements

### 1. Add SQLAlchemy ORM Models Prompt (between Prompt 02 and 03)
**Problem:** Prompt 02 creates raw SQL, Prompt 03 bootstraps FastAPI with async SQLAlchemy, but no prompt defines Python ORM model classes. Every subsequent prompt silently assumes they exist, leading to ad-hoc inconsistent models.
**Fix:** Add a new prompt creating `backend/app/models/` with all table models using SQLAlchemy 2.0 `Mapped[]` annotations, plus `backend/app/schemas/` for Pydantic v2 request/response schemas.

### 2. Move Alembic Setup to Right After Schema (Prompt 02 -> 02.5)
**Problem:** Alembic is Prompt 38 (Phase 9!). This means 36 prompts of running raw SQL manually.
**Fix:** Set up Alembic immediately after the schema definition. Every subsequent prompt uses `alembic upgrade head` as standard.

### 3. Add Auth Frontend Pages (Missing Entirely)
**Problem:** Prompts 11-14 build all auth backend. Prompt 16 jumps straight to the library frontend. No prompt creates `/register`, `/login`, `/verify-otp` pages. These are referenced in the FSD, HTML mockup, and README.
**Fix:** Add a new prompt between 14 and 15 for auth frontend pages.

### 4. Add User Dashboard Page (Missing Entirely)
**Problem:** Multiple prompts reference redirecting to `/dashboard` (Prompts 24, 35), but no prompt builds it. The FSD specifies it shows recent questions, credit balance, quick search.
**Fix:** Add a dashboard prompt after the auth frontend prompt.

### 5. Implement Prompt Injection Defense (Security-Critical)
**Problem:** The FSD (Section 7) specifies input sanitization against prompt injection, but no prompt implements it. The system prompt alone is insufficient defense.
**Fix:** In Prompt 19 or 20: (a) regex detection of injection patterns, (b) input truncation to MAX_QUESTION_CHARS, (c) XML tag wrapping of user input in the prompt, (d) block `DEMO_MODE=true` when `ENVIRONMENT=prod`.

### 6. Add Hybrid Retrieval (BM25 + Vector) to RAG Pipeline
**Problem:** Prompt 15 (library search) uses hybrid FTS+vector, but Prompt 18 (RAG retrieval) uses vector-only. Queries containing specific circular numbers or exact regulatory terms will miss relevant results.
**Fix:** Add BM25/full-text search as parallel retrieval path in Prompt 18 and merge with Reciprocal Rank Fusion.

### 7. Split Testing Across Phases (Not All in Phase 8)
**Problem:** 30 prompts of untested code accumulate before Phase 8. Enormous debugging surface area.
**Fix:** Add mini-test instructions at the end of each phase, or add test prompts after Phases 2, 3, 5, and 7.

### 8. Add Linter/Formatter/Pre-commit in Prompt 01
**Problem:** No prompt sets up ruff, black, isort (Python) or ESLint, Prettier (TS). Each Claude Code session produces differently formatted code.
**Fix:** Add `pyproject.toml` (ruff, black, mypy), `.eslintrc.js`, `.prettierrc`, and `pre-commit-config.yaml` to Prompt 01.

### 9. Create Shared Embedding Service for Backend
**Problem:** Prompt 15 and 18 need `EmbeddingGenerator` which lives in `scraper/processor/embedder.py`. Backend shouldn't import from scraper module.
**Fix:** Create `backend/app/services/embedding_service.py` as a standalone async wrapper around OpenAI embeddings API.

### 10. Add Streaming Responses (SSE) for Q&A
**Problem:** Prompt 20 waits for full LLM response (5-10s perceived wait). Users see nothing during generation.
**Fix:** Implement Server-Sent Events streaming in the Q&A endpoint. Stream tokens as they arrive, validate citations post-stream.

---

## All Improvements by Category

### A. Architecture & Design (7 items)
| # | Issue | Prompt(s) | Fix |
|---|-------|-----------|-----|
| A1 | No SQLAlchemy ORM models | 02-03 gap | New prompt: `backend/app/models/` |
| A2 | No Pydantic schema layer | 13,15,20,23,25-29 | Add `backend/app/schemas/` per domain |
| A3 | Scraper has no db.py | 05-10 | Create `scraper/db.py` with sync SQLAlchemy |
| A4 | No scraper connection pooling | 09 | Add pool config to scraper's DB engine |
| A5 | No API versioning (`/api/v1/`) | 03 | Add prefix to all router mountings |
| A6 | No retry/circuit breaker on LLM calls | 19 | Add tenacity + pybreaker for Anthropic/OpenAI |
| A7 | Missing GPT-4o fallback (documented in FSD/MEMORY) | 19 | Add fallback if Anthropic 5xx/timeout |

### B. Prompt Sequencing (6 items)
| # | Issue | Fix |
|---|-------|-----|
| B1 | Alembic at Prompt 38, should be ~02.5 | Move to immediately after schema |
| B2 | Config (04) needed before Bootstrap (03) | Swap order: Config first |
| B3 | EmbeddingGenerator import across module boundary | Shared service in backend |
| B4 | AI Summary (42) needed by scraper pipeline (09) | Move to Phase 2 or make 09 explicit about stub |
| B5 | All testing in Phase 8 | Distribute across phases |
| B6 | Prompt 45 needs Alembic migration (not mentioned clearly) | Explicit `alembic revision` instruction |

### C. Missing Features (8 items)
| # | Feature | Priority |
|---|---------|----------|
| C1 | Auth frontend pages (register, login, verify) | **Critical** |
| C2 | User dashboard page | **Critical** |
| C3 | Admin Q&A sandbox (FSD Section 6.4) | High |
| C4 | Subscription auto-renewal (PRD says auto-renew) | High |
| C5 | User account deletion / data export (DPDP Act) | High |
| C6 | Frontend 429 rate-limit UI with countdown | Medium |
| C7 | Low credits / expiry notification triggers | Medium |
| C8 | Annual billing data model support | Low |

### D. Security Gaps (7 items)
| # | Gap | Fix |
|---|-----|-----|
| D1 | No prompt injection defense | Regex detection + XML tag wrapping + input sanitization |
| D2 | No refresh token rotation | Revoke old, issue new on each `/auth/refresh` |
| D3 | Deactivated users keep valid JWTs | Redis token blacklist (jti with TTL) |
| D4 | CORS vs webhook endpoint | Explicitly exclude webhook from CORS |
| D5 | SQL injection surface in hybrid search | Ensure parameterized queries in Prompt 15 |
| D6 | XSS via admin override rendered in react-markdown | Disable HTML in markdown rendering for overrides |
| D7 | Demo OTP in production | Startup validator: block `DEMO_MODE=true` + `ENVIRONMENT=prod` |

### E. Developer Experience (7 items)
| # | Issue | Fix |
|---|-------|-----|
| E1 | No CLAUDE.md in repo | Create in Prompt 01 pointing to MEMORY.md |
| E2 | "Fresh task context" loses reasoning context | Change to "continue in same session" or add "read existing code first" |
| E3 | No linter/formatter setup | Add ruff, black, ESLint, Prettier to Prompt 01 |
| E4 | No type checking (mypy, TS strict) | Add mypy config + verify `strict: true` in tsconfig |
| E5 | No pre-commit hooks | Add pre-commit config to Prompt 01 |
| E6 | No centralized error handling pattern | Add `backend/app/exceptions.py` with custom exceptions + handler |
| E7 | No consistent dependency injection pattern | Establish convention in Prompt 03 |

### F. Production Readiness (7 items)
| # | Gap | Fix |
|---|-----|-----|
| F1 | No database backup strategy | Add pg_dump cron or Cloud SQL automated backups |
| F2 | No load testing | Add Locust/k6 prompt in Phase 8 |
| F3 | No blue-green/canary deployment | Use Cloud Run revisions (traffic splitting for canary) |
| F4 | No backward-compatible migration guidance | Add instructions for safe migrations |
| F5 | No secrets rotation procedure | Document dual-key JWT rotation |
| F6 | No Cloud Logging retention policy | Set 30d dev, 90d prod via Cloud Logging retention bucket |
| F7 | No LLM API health check in launch script | Add lightweight API call to Prompt 48 |

### G. RAG Pipeline Improvements (8 items)
| # | Improvement | Impact |
|---|-------------|--------|
| G1 | Cosine threshold 0.5 too aggressive | Make configurable, start at 0.7 distance (0.3 similarity) |
| G2 | No query expansion/reformulation | LLM-generated alternative phrasings before embedding |
| G3 | Vector-only RAG (no BM25) | Add hybrid retrieval with RRF fusion |
| G4 | Cross-encoder blocks event loop in single thread | Dedicated ProcessPoolExecutor |
| G5 | No chunk deduplication before LLM | Max 2 chunks per document |
| G6 | No answer quality evaluation framework | 50+ golden Q&A pairs + automated scoring |
| G7 | Lossy question normalization | Strip stop-word prefixes for better cache hits |
| G8 | No streaming responses | SSE streaming for perceived latency improvement |

### H. Cost Optimization (5 items)
| # | Item | Savings |
|---|------|---------|
| H1 | Reduce embedding dims to 1536 | 50% storage + search cost |
| H2 | Cross-encoder model in wrong Dockerfile (scraper, should be backend) | ~500MB image size reduction |
| H3 | No token counting before LLM call | Prevents context window overflow |
| H4 | Use cheaper model (Haiku) for summaries | Significant at scale |
| H5 | Compress Redis cached values | Memory savings |

### I. Technical Debt Risks (8 items)
| # | Risk | Mitigation |
|---|------|------------|
| I1 | Tight coupling: scraper writes directly to backend DB | Shared models package or internal API |
| I2 | Monolithic admin router (~800+ lines by Prompt 30) | Split into sub-routers |
| I3 | Scattered index definitions across prompts | Consolidate in schema migration |
| I4 | Hardcoded plan pricing in router code | Move to config table or env vars |
| I5 | Inconsistent service instantiation patterns | Standardize on FastAPI DI |
| I6 | No frontend client state management | Add Zustand in Prompt 01 |
| I7 | Manual API client falls out of sync | Use OpenAPI + openapi-typescript codegen |
| I8 | No graceful shutdown handling | Add SIGTERM handlers for backend + Celery |

---

## Suggested Revised Prompt Sequence

The original 50 prompts should be restructured to ~55 prompts:

```
Phase 1 — Infrastructure (6 prompts, was 4)
  01  Monorepo + linter/formatter/pre-commit + CLAUDE.md
  02  PostgreSQL Schema + Alembic setup (merge original 02 + 38)
  02b SQLAlchemy ORM Models + Pydantic Schemas (NEW)
  03  Config & Secrets Management (was 04, moved earlier)
  04  FastAPI Bootstrap + error handling pattern (was 03, reordered)
  04b Shared Embedding Service for backend (NEW)

Phase 2 — Scraper (6 prompts, unchanged count)
  05-10 (as before, with scraper/db.py added to 09)
  + AI Summary service moved here from Phase 10

Phase 3 — Auth (5 prompts, was 4)
  11-14 (as before, with refresh token rotation in 13, token blacklist in 14)
  14b Auth Frontend Pages: register, login, verify-otp (NEW)

Phase 4 — Circular Library (3 prompts, unchanged)
  15-17 (as before, with hybrid search using parameterized queries)

Phase 5 — Q&A Engine (6 prompts, was 5)
  18  RAG Retrieval + hybrid BM25+vector + chunk dedup (enhanced)
  19  LLM Service + prompt injection defense + GPT-4o fallback (enhanced)
  20  Question API + SSE streaming (enhanced)
  21-22 (as before)
  22b User Dashboard Page (NEW)

Phase 6 — Payments (2 prompts, unchanged)
  23-24 (with subscription auto-renewal consideration)

Phase 7 — Admin Console (6 prompts, unchanged)
  25-30 (split admin.py into sub-routers in 25)

Phase 8 — Testing (6 prompts, was 5)
  31-35 (as before)
  35b Load Testing with Locust/k6 (NEW)

Phase 9 — DevOps (5 prompts, unchanged)
  36-40 (with cross-encoder in backend Dockerfile, not scraper; log retention; blue-green deploy)

Phase 10 — Polish (10 prompts, unchanged)
  41-50 (with DPDP compliance data export, configurable RAG thresholds, Redis compression)
```

---

## Verification Plan

After implementing improvements to the prompts document:
1. Cross-reference every page/route mentioned in README, FSD, and mockup HTML against the prompt list — ensure no missing pages
2. Verify every table in schema Prompt 02 has a corresponding SQLAlchemy model
3. Verify every API endpoint mentioned across prompts has a frontend page that calls it
4. Check that every external dependency (library) mentioned is included in requirements.txt/package.json prompts
5. Run the first 4 prompts as a smoke test to verify the foundation is solid

## Deliverable

A comprehensive improvements document that can be used alongside the existing 50 prompts, organized as:
1. **Pre-build checklist** — things to set up before Prompt 01
2. **Per-prompt amendments** — specific additions/changes to each prompt
3. **New prompts to insert** — full prompt text for the ~5 new prompts
4. **Post-build hardening** — additional steps after Prompt 50
