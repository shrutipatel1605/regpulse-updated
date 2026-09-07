# RegPulse

**RBI Regulatory Intelligence Platform** — Instant, cited answers to Indian banking compliance questions, powered by RBI's own circulars.

---

## All 50 Build Prompts Complete

| Phase | Prompt(s) | Description |
|-------|-----------|-------------|
| 1 — Infrastructure | 01–04b | Monorepo, 13-table schema, config, FastAPI bootstrap, embedding service |
| 2 — Scraper | 05–10 | RBI crawler, PDF extract, metadata, chunking, Celery, supersession |
| 3 — Auth | 11–14 | Work-email validation, OTP, RS256 JWT, refresh rotation, frontend auth |
| 4 — Circular Library | 15–17 | Hybrid search API (vector+BM25 RRF), library + detail pages |
| 5 — RAG Q&A | 18–23 | RAG pipeline, LLM service, SSE streaming, caching, ask/history pages |
| 6 — Subscriptions | 24–27 | Razorpay orders/verify/webhook, upgrade + account pages |
| 7 — Admin | 28–32 | Dashboard, review, prompts, users, circulars, scraper (6 sub-routers) |
| 8 — Features | 33–36 | Action items CRUD, saved interpretations CRUD + frontend pages |
| 9 — Frontend | 37–42 | Dashboard, updates feed, admin UI (6 pages), analytics + summary services |
| 10 — Deploy | 43–50 | PDF export, CI/CD, Nginx, Makefile, launch checks |

---

## Phase 2 Roadmap (Multi-Sprint)

| Phase/Sprint | Description | Status |
|--------------|-------------|--------|
| Sprint 1 | Analytics (PostHog), Core Hardening (HTTPOnly cookies, Direct Embedder), Landing Page | ✅ Complete (`363b1ef`) |
| Sprint 2 | Anti-Hallucination Guardrails, Golden Dataset Eval Pipeline, k6 Load Tests | ✅ Complete (`1858575`) |
| Sprint 3 | Public Safe Snippet Sharing, RSS/News Ingest, Knowledge Graph + RAG Expansion (flag-gated) | ✅ Complete (`5379c49`/`5d6dec3`/`52375b8`/`516acf9`) |
| Sprint 4 | Confidence Meter UI, Dark Mode (WCAG-AA), Skeleton loaders, SSE jitter fix, A/B feature-flag scaffolding | ✅ Complete (`f6c3a5a`) |
| Sprint 5 | Admin Manual PDF Upload, Semantic Clustering Heatmaps | ✅ Complete |
| Sprint 6 | Pre-Launch Hardening: SIGTERM shutdown, system user audit log, scraper embeddings on insert, LLM exception tightening, KG expansion GA, retrieval eval | ✅ Complete |
| Sprint 7 | DPDP compliance (account deletion + data export), subscription auto-renewal, low-credit notifications | ✅ Complete |
| Sprint 8 | Updates feed tracking, action items stats/overdue, admin Q&A sandbox, question suggestions, real PDF + QR codes | ✅ Complete (`56d628f`) |
| Frontend v2 | Terminal-modern redesign: design tokens, AppShell, editorial Ask, list pages, Learnings, Debate routes | ✅ Complete (`49cde9c`) |
| Phase D.3 | Debate & Annotations API | ✅ Complete |
| Phase A | GCP infra provisioning (Cloud SQL, Memorystore, Artifact Registry, Secret Manager) | ⏳ Next |
| Phase B | CI/CD hardening (WIF, staging env, security baseline, integration tests) | ⏳ Planned |
| Phase C | Data migration + observability (✅ done) + v1.0.0 launch | ⏳ In Progress |
| Sprint 9 | Circuit breaker (G-10), TD-01/03/09, mobile responsive polish | ⏳ Post-launch |

---

## Architecture

```
rbi.org.in → Scraper (Celery) → PostgreSQL + pgvector ← FastAPI ← Next.js 14
                                    ↕ Redis 7                ↕ LLM
                                                    claude-sonnet / gpt-4o
```

| Layer | Tech |
|-------|------|
| Backend | FastAPI, SQLAlchemy 2.0 async, Pydantic v2, Python 3.11 |
| Frontend | Next.js 14, TypeScript strict, CSS custom-property design tokens, TanStack Query, Zustand |
| Database | PostgreSQL 16 + pgvector (17 tables, ivfflat + GIN indexes) |
| Cache/Queue | Redis 7, Celery |
| LLM | claude-sonnet-4-20250514 with extended thinking (primary), gpt-4o (fallback) |
| Payments | Razorpay (INR) |
| CI/CD | GitHub Actions → Artifact Registry → Cloud Run |
| Reverse Proxy | Nginx with TLS 1.3, HSTS, CSP |

---

## Quick Start (Demo Mode)

```bash
cp .env.example .env              # Fill in OPENAI_API_KEY and ANTHROPIC_API_KEY
                                  # Set DEMO_MODE=true, dummy Razorpay/SMTP keys
docker compose up --build -d      # Start all 6 containers (schema auto-applied)

# Trigger scraper to index RBI circulars (embeddings generated on insert):
docker exec regpulse-scraper celery -A celery_app -b redis://redis:6379/1 call scraper.tasks.daily_scrape
```

| Service | URL |
|---------|-----|
| Register/Login | http://localhost:3000/register |
| Web app | http://localhost:3000 |
| API docs (Swagger) | http://localhost:8000/api/v1/docs |

**Demo credentials:** Any work-looking email + OTP `123456`. 5 free credits granted on registration.

---

## API (~65 endpoints at /api/v1/)

| Group | Endpoints |
|-------|-----------|
| Auth | register, login, verify-otp, refresh, logout |
| Account (Sprint 7) | delete (DPDP anonymise), export (DPDP JSON download), me |
| Circulars | list, search, autocomplete, detail, departments, tags, doc-types, **updates** (Sprint 8), **updates/mark-seen** (Sprint 8) |
| Questions | ask (SSE+JSON), history, detail, export (**PDF + QR codes**, Sprint 8), feedback, **suggestions** (Sprint 8) |
| Subscriptions | plans, order, verify, webhook, plan info, history, **auto-renew toggle** (Sprint 7) |
| Action Items | list (with `is_overdue`), create, update, delete, **stats** (Sprint 8) |
| Saved | list, create, detail, update, delete |
| Snippets (Sprint 3) | create, list, public get, og image, revoke |
| News (Sprint 3) | list, detail |
| Admin | dashboard, review (3), prompts (3 + **test-question sandbox** Sprint 8), users (2), circulars (3), scraper (2), news (2), uploads (3), heatmap (2) |
| Debates (D.3) | list, create thread, list replies, create reply, update stance |
| Health | liveness, readiness |

---

## Tests

```bash
make test-backend    # 64 unit tests (pytest)
make test-frontend   # 22 routes (tsc + eslint + next build)
make test            # Both
```

### Anti-Hallucination Evaluation

```bash
make eval   # or: python -m pytest tests/evals/ -v
```

30 synthetic test cases across 4 categories:
- **12 factual** — direct citation questions with ground truth
- **3 multi-circular** — cross-reference questions requiring multiple sources
- **8 out-of-scope** — questions the system must refuse (SEBI, tax, crypto, etc.)
- **5 injection** — prompt manipulation attempts that must be blocked

### Load Testing

```bash
brew install k6
k6 run tests/load/k6_load_test.js   # Runs against local Docker Compose
```

3 scenarios: smoke (1 VU), load (ramp to 20 VU), spike (burst to 50 VU).

### Retrieval-Level Eval (Sprint 6)

```bash
# Requires running Postgres + real OPENAI_API_KEY:
RAG_KG_EXPANSION_ENABLED=true pytest backend/tests/evals/test_retrieval.py -v
```

6 retrieval queries + out-of-scope check + embedding population verification.

### Sprint 3 Features

- **Public snippet sharing**: any signed-in user can share a redacted preview of any of their answers via `/s/[slug]`. The full `detailed_interpretation` is enforced never to leave the snippet service. Open Graph image rendered server-side via Pillow.
- **RSS news ingest**: Celery beat task `ingest_news` runs every 30 min, pulls from RBI Press, Business Standard, LiveMint, ET Banking via RSS only. Items are embedded and linked to active circulars by cosine similarity above `NEWS_RELEVANCE_THRESHOLD` (default 0.75). Surfaced in `/updates` under a "Market News" tab. Never mixed into the RAG corpus.
- **Knowledge graph**: each circular indexed by the scraper runs a regex pre-pass (circular numbers, sections, amounts, dates) plus a Claude Haiku LLM pass for orgs/regulations/teams + relationship triples. Stored in `kg_entities` + `kg_relationships`. KG-driven RAG expansion is now **enabled by default** (`RAG_KG_EXPANSION_ENABLED=true`) as of Sprint 6, validated via the retrieval eval.
- **Backfill**: `python /scraper/backfill_kg.py` (run inside the scraper container) walks every active circular and populates the KG.

## Launch Check

```bash
./scripts/launch_check.sh http://localhost:8000 http://localhost:3000
```

---

---

## Production Deployment

**All pre-launch code work is complete.** Remaining path to v1.0.0:

1. **Phase A (~1 week) — GCP infra**: Cloud SQL + pgvector, Memorystore Redis, Artifact Registry, Secret Manager, VPC connectors.
2. **Phase B (~1 week) — CI/CD hardening**: Workload Identity Federation, staging env, custom domain + TLS, `pip audit` / `pnpm audit` in CI.
3. **Phase C (~1 week) — Data migration + launch**: Full RBI scrape, `scripts/backfill_question_embeddings.py`, Cloud Monitoring alerts, pre-launch smoke tests, tag `v1.0.0`.

See `PRODUCTION_PLAN.md` for the full GCP deployment roadmap, `TEAM_HANDOVER.md` for the one-page index, and `DEVELOPMENT_PLAN.md` for the multi-sprint roadmap.

- Cloud Run (backend, frontend), GCE e2-small (celery worker + beat), Cloud Run Job (scraper)
- Cloud SQL PostgreSQL 16 + pgvector, Memorystore Redis
- Google-managed TLS, Cloud Armor (optional WAF)
- CI/CD via GitHub Actions with Workload Identity Federation (tag-triggered deploy)
- Estimated cost: ~$173/month (asia-south1)

**Post-deploy action:** run `python scripts/backfill_question_embeddings.py` once in production so pre-Sprint 8 questions become ANN-searchable for `/questions/suggestions`.

---

*RegPulse is not a legal advisory service. Answers are AI-generated from indexed RBI circulars and should be verified at rbi.org.in.*
