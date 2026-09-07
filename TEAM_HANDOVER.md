# RegPulse — Team Handover

> **You're here because you're taking over RegPulse.** Read this file first; it points at everything else.
> **Last updated:** 2026-04-14 (Sprint 8 merged at `56d628f`)

---

## 1. TL;DR

RegPulse is a B2B SaaS RAG platform that answers Indian banking compliance questions from RBI's official circulars. **50 build prompts + Sprints 1–8 are shipped.** All pre-launch code is done. **The only remaining path to v1.0.0 is GCP infra (Phases A–C in `PRODUCTION_PLAN.md`).**

| Metric | Value |
|---|---|
| Main branch tip | `56d628f` (Sprint 8 merged) |
| CI on `main` | ✅ backend-lint, ✅ backend-test (106/106), ✅ frontend-build |
| Golden dataset eval | 21/21 PASS |
| Retrieval eval | 8/8 PASS |
| PRD v3 gaps closed | 10/12 (G-10 Sprint 9, G-11 deferred) |
| Endpoints | ~65 across 19 routers |
| Tables | 19 across 5 migrations |
| Frontend routes | 25 |
| Running containers | 6 (`docker compose up --build -d`) |

---

## 2. What to Read, In Order

| # | File | Why |
|---|------|-----|
| 1 | **This file (`TEAM_HANDOVER.md`)** | Orientation. |
| 2 | `README.md` | Quick start, architecture diagram, endpoint inventory. |
| 3 | `MEMORY.md` | Non-negotiable patterns. Read before you write a line of code. |
| 4 | `LEARNINGS.md` | L1–L8 — mistakes the team has already paid for. Prevents repeat offences. |
| 5 | `context.md` | Current state, tech debt, gap closure tracker. |
| 6 | `spec.md` | Living technical spec — schema, every endpoint, RAG pipeline, security model. |
| 7 | `TECHNICAL_DOCS.md` | Deep dive: architecture, component graph, runbook, config reference. |
| 8 | `RegPulse_PRD_v3.md` | Product requirements with gap analysis. |
| 9 | `RegPulse_FSD_v3.md` | Functional spec with gap analysis. |
| 10 | `DEVELOPMENT_PLAN.md` | Multi-sprint roadmap (Sprint 7 ✅, 8 ✅, 9, 10+). |
| 11 | `PRODUCTION_PLAN.md` | GCP deployment plan — Phases A, B, C. **Read before starting infra work.** |
| 12 | `TESTCASES.md` + `UAT_PLAN.md` + `UAT_RESULTS.md` | Test inventory, UAT scenarios, last run results (81/81). |
| 13 | `HANDOVER.md` | Previous session's commit-by-commit log. |

---

## 3. Architecture at a Glance

```
                  ┌──────────────────┐
                  │   rbi.org.in     │
                  └────────┬─────────┘
                           │  daily 02:00 IST
                           ▼
 ┌───────────────────────────────────┐
 │  Scraper (Celery + Redis broker)  │  ── persist_kg, ingest_news, renewal reminders, credit alerts
 └────────────────┬──────────────────┘
                  │ writes directly (TD-01: to be isolated v2)
                  ▼
 ┌────────────────────────────────────────┐         ┌──────────────────┐
 │ PostgreSQL 16 + pgvector (19 tables)   │◀────────│  Memorystore    │
 │   users, circular_documents, chunks,   │         │  Redis 7 (cache) │
 │   questions (w/ question_embedding),   │         └─────────┬────────┘
 │   action_items, kg_*, news_items, ...  │                   │
 └──────────┬─────────────────────────────┘                   │
            │                                                 │
            ▼                                                 │
 ┌───────────────────────────────────────┐                    │
 │ FastAPI backend (/api/v1/, ~65 eps)   │────────────────────┘
 │  auth • account • circulars • Q&A     │
 │  subscriptions • action-items • admin │
 └──────────┬────────────────────────────┘
            │        Anthropic (primary) → GPT-4o (fallback)
            ▼        OpenAI text-embedding-3-large (3072-dim)
 ┌───────────────────────────────────────┐
 │ Next.js 14 frontend (25 routes)       │
 │  Tailwind, TanStack Query, Zustand    │
 └───────────────────────────────────────┘
```

**The hard invariant:** RAG answers come ONLY from `circular_documents` / `document_chunks`. News items live beside circulars in `/updates` but are NEVER mixed into the retrieval corpus.

---

## 4. Repo Map (keep this handy)

```
backend/
  app/
    main.py                         # FastAPI entrypoint, lifespan, CORS, middleware
    routers/                        # 19 router files, all mounted at /api/v1/
      account.py                    # DPDP deletion + export (Sprint 7)
      circulars.py                  # library + updates feed (Sprint 8)
      questions.py                  # ask + suggestions + PDF export (Sprint 8)
      subscriptions.py              # Razorpay + auto-renew (Sprint 7)
      action_items.py               # CRUD + stats + is_overdue (Sprint 8)
      admin/prompts.py              # prompt CRUD + sandbox (Sprint 8)
      ...
    services/                       # 11 services
      rag_service.py                # hybrid retrieval + RRF + reranking + KG expansion
      llm_service.py                # Anthropic → GPT-4o fallback, confidence scoring
      pdf_export_service.py         # reportlab + QR codes (Sprint 8)
      embedding_service.py          # OpenAI embeddings w/ SHA256 Redis cache
      kg_service.py, snippet_service.py, circular_library_service.py, ...
    dependencies/
      auth.py                       # JWT + jti blacklist + role checks
      rag.py                        # shared build_rag_service / build_llm_service (Sprint 8)
    schemas/                        # Pydantic request/response models
    models/                         # SQLAlchemy 2.0 Mapped[] ORM
  migrations/
    001_initial_schema.sql          # canonical schema
    002_sprint3_knowledge_graph.sql
    003_sprint4_confidence.sql
    004_sprint5.sql
    005_sprint6_system_user.sql
  scripts/
    seed_demo.py
    backfill_embeddings.py          # chunk embeddings
    backfill_kg.py                  # knowledge graph
    backfill_question_embeddings.py # ⚠️ run once in prod post-deploy (Sprint 8)
  tests/
    unit/                           # 106 tests passing
    evals/                          # golden dataset (21) + retrieval (8)
    integration/                    # Postgres-backed
    load/                           # k6 scenarios

scraper/                            # Celery crawler — NEVER imports backend/
  tasks.py                          # 10 tasks, 6 beat schedules
  crawler/, processor/, uploader/

frontend/                           # Next.js 14, TypeScript strict
  src/app/                          # 25 routes (login, library, ask, history, admin/...)
  src/components/                   # Badge, ConfidenceMeter, Skeleton, AppSidebar, ...
  src/stores/                       # Zustand (auth, theme)
  src/lib/api/                      # axios w/ 401 silent refresh

.github/workflows/
  ci.yml                            # backend-lint, backend-test, frontend-build
  deploy.yml                        # tag-triggered GCP Cloud Run deploy (stub — no infra yet)

docker-compose.yml                  # 6 containers: postgres, redis, backend, frontend, scraper worker, beat
Makefile                            # test-backend, test-frontend, eval, launch_check
```

---

## 5. What's Done vs What's Left

### Shipped (don't touch unless you have a reason)
| Feature | Sprint |
|---|---|
| Auth (OTP + RS256 JWT + jti blacklist + HttpOnly refresh cookie) | 1–3 |
| RAG (vector + BM25 RRF + cross-encoder + KG expansion) | 5, 6 |
| Anti-hallucination (confidence score, consult-expert fallback, citation validation) | 2 |
| Snippet sharing + news ingest + knowledge graph | 3 |
| Dark mode + Confidence Meter UI + skeleton loaders | 4 |
| Admin PDF upload + semantic heatmap | 5 |
| SIGTERM shutdown + system user + scraper embeddings on insert | 6 |
| DPDP deletion + export, auto-renewal, low-credit alerts | 7 |
| Updates tracking, action items stats/overdue, admin sandbox, suggestions, PDF QR | 8 |

### Left (this is the map)
| Track | Scope | Where |
|---|---|---|
| **Phase A** — GCP infra | Cloud SQL+pgvector, Memorystore, Artifact Registry, Secret Manager, VPC connectors | `PRODUCTION_PLAN.md §Phase 2–3` |
| **Phase B** — CI/CD + security | Workload Identity Federation, staging env, custom domain + TLS, `pip audit`/`pnpm audit` | `PRODUCTION_PLAN.md §Phase 4–5` |
| **Phase C** — Data migration + launch | Full RBI scrape, run `backfill_question_embeddings.py`, Cloud Monitoring, tag `v1.0.0` | `PRODUCTION_PLAN.md §Phase 6–8` |
| **Sprint 9** — post-launch hardening | G-10 pybreaker, TD-01/03/09, mobile polish | `DEVELOPMENT_PLAN.md §Sprint 9` |
| **Sprint 10+** — feature roadmap | Conversational threading, team seats, SEBI, enterprise API | `DEVELOPMENT_PLAN.md §Sprint 10+` |

### Operational post-deploy checklist (Phase C)
- [ ] `alembic upgrade head` on Cloud SQL
- [ ] Full RBI scrape (replaces 10-circular demo)
- [ ] `python backend/scripts/backfill_question_embeddings.py` so `/questions/suggestions` works for pre-Sprint 8 rows
- [ ] `backend/scripts/backfill_kg.py` if any circulars predate KG extraction
- [ ] Verify golden eval still 21/21 against real data
- [ ] Cloud Monitoring alert policies (CPU/mem/5xx/SQL connections)
- [ ] Walkthrough: register → OTP → ask → cite → action items → PDF export → scan QR

---

## 6. How to Run It

```bash
# First time (demo mode, no external billing)
cp .env.example .env                 # fill in OPENAI_API_KEY, ANTHROPIC_API_KEY
                                     # set DEMO_MODE=true, dummy Razorpay/SMTP keys
docker compose up --build -d         # 6 containers, schema auto-applied

# Seed a demo dataset
docker exec regpulse-backend python scripts/seed_demo.py

# OR pull real circulars
docker exec regpulse-scraper celery -A celery_app -b redis://redis:6379/1 \
  call scraper.tasks.daily_scrape

# Access
# Frontend:        http://localhost:3000
# API docs:        http://localhost:8000/api/v1/docs
# Demo login:      any work-ish email, OTP 123456
```

### Testing
```bash
# Backend unit tests (106 tests)
cd /tmp && DATABASE_URL="sqlite+aiosqlite:///:memory:" REDIS_URL="redis://localhost:6379/0" \
  JWT_PRIVATE_KEY="test" JWT_PUBLIC_KEY="test" OPENAI_API_KEY="test" ANTHROPIC_API_KEY="test" \
  RAZORPAY_KEY_ID="test" RAZORPAY_KEY_SECRET="test" RAZORPAY_WEBHOOK_SECRET="test" \
  SMTP_HOST="localhost" SMTP_PORT="587" SMTP_USER="test" SMTP_PASS="test" \
  SMTP_FROM="test@test.com" FRONTEND_URL="http://localhost:3000" \
  PYTHONPATH=/home/user/RegPulse/backend pytest /home/user/RegPulse/backend/tests/unit/ -v

# Lint
ruff check backend/ && black --check --line-length 100 backend/

# Frontend
cd frontend && pnpm install && npx tsc --noEmit && npx next lint

# Golden eval (requires real OPENAI + ANTHROPIC keys + running Postgres)
make eval-golden

# Load test
k6 run backend/tests/load/k6_load_test.js
```

**Note on local tests:** run from `/tmp` or anywhere outside the repo root. `pydantic-settings` auto-loads `.env` and chokes on the full `.env` because of extra vars (L7.3).

---

## 7. Hard Rules (these will bite you if you forget)

From `CLAUDE.md` rules, `MEMORY.md` patterns, and `LEARNINGS.md` incidents:

1. **All endpoints at `/api/v1/`** — never deviate.
2. **Never import from `scraper/` in `backend/`** — and vice versa.
3. **Never send PII to the LLM** — no name, email, org_name.
4. **Always validate citations** — strip circular numbers not in retrieved chunks.
5. **Credits deducted only on success** — `SELECT FOR UPDATE`, atomic.
6. **Admin routers in `routers/admin/`** sub-package.
7. **Pydantic schemas in `schemas/`** — not inline in routers.
8. **SQLAlchemy models use 2.0 `Mapped[]`** — TIMESTAMPTZ columns declare `DateTime(timezone=True)`.
9. **Services via `Depends()`** — never instantiate in route bodies.
10. **All errors return `{"success": false, "error": "message", "code": "ERROR_CODE"}`.**
11. **Snippet sharing must NEVER expose `detailed_interpretation`** — only quick_answer (truncated) + 1 citation.
12. **RSS news items are NEVER mixed into RAG retrieval.** Invariant.
13. **Route ordering:** static paths (`/foo/stats`) registered BEFORE `/{id}` param routes (L8.1).
14. **pgvector SQL is Postgres-only** — dialect-guard for SQLite unit tests (L8.2).
15. **User-mutating routes** use explicit `UPDATE ... WHERE id=:id` instead of attribute-set on a dependency-injected ORM user (L7.1).
16. **reportlab `Paragraph` text** must go through `pdf_export_service._escape()` (L8.4).
17. **Never ship a handover that says "CI green" if tests are red** (L8.5).

---

## 8. Team Handover Checklist

For the outgoing contributor:
- [x] All pre-launch code gaps closed (10/12; G-10 to Sprint 9, G-11 deferred)
- [x] CI green on `main` at `56d628f`
- [x] Docs refreshed (CLAUDE, MEMORY, context, spec, README, PRD v3, FSD v3, TECHNICAL_DOCS, LEARNINGS, DEVELOPMENT_PLAN, PRODUCTION_PLAN, HANDOVER, this file)
- [x] Test suite passes: 106 unit / 21 golden eval / 8 retrieval eval
- [x] Sprint 8 UAT spot-checks (PDF export, suggestions, admin sandbox, updates feed, action items stats)

For the incoming team:
- [ ] Pull `main` and verify `docker compose up --build -d` works end-to-end
- [ ] Read `MEMORY.md` and `LEARNINGS.md`
- [ ] Provision GCP per `PRODUCTION_PLAN.md §Phase A`
- [ ] After deploy: run `backfill_question_embeddings.py` and `backfill_kg.py` as needed
- [ ] Tag `v1.0.0` only after the Phase C smoke-test checklist is green

---

## 9. Who to Ask / Where to Look

| Question | Source |
|---|---|
| "How does the RAG pipeline work?" | `spec.md §4`, `TECHNICAL_DOCS.md §8` |
| "What schema columns does table X have?" | `backend/migrations/001_initial_schema.sql` (canonical) |
| "What endpoint does feature Y live at?" | `spec.md §3` or visit `/api/v1/docs` in a running instance |
| "Why did we pick tech X?" | `RegPulse_PRD_v3.md` (product) or `RegPulse_FSD_v3.md` (implementation) |
| "What's planned for the next sprint?" | `DEVELOPMENT_PLAN.md` |
| "How do I deploy?" | `PRODUCTION_PLAN.md` |
| "Why does this break?" | `LEARNINGS.md` (L1–L8) before anything else |
| "Is this done or planned?" | `context.md` (current inventory + gap tracker) |

---

*RegPulse is not a legal advisory service. Answers are AI-generated from indexed RBI circulars and must be verified at rbi.org.in.*
