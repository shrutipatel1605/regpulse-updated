# Claude Code Instructions — RegPulse

> **Read `MEMORY.md` and `LEARNINGS.md` before starting any task.**
>
> Sprint exit checklist: (1) re-run golden dataset eval if the sprint touched retrieval/answer code, (2) append new gotchas to `LEARNINGS.md`, (3) `git push origin main`, (4) refresh all 5 docs (README, CLAUDE, MEMORY, spec, context). All four must be green before declaring "done."

## Rules

1. All endpoints at `/api/v1/` — never deviate
2. Never import from `scraper/` in `backend/`
3. Never send PII to the LLM
4. Always validate citations — strip circular numbers not in retrieved chunks
5. Credits deducted only on success — `SELECT FOR UPDATE`
6. Admin routers in `routers/admin/` sub-package
7. Pydantic schemas in `schemas/` — not inline in routers
8. SQLAlchemy models use 2.0 `Mapped[]` annotations — TIMESTAMPTZ columns must declare `DateTime(timezone=True)` or asyncpg will reject naive datetimes
9. Services via `Depends()` — never instantiate in route bodies
10. All errors return `{"success": false, "error": "message", "code": "ERROR_CODE"}`
11. Public snippet sharing must NEVER expose `detailed_interpretation` — only `quick_answer` (truncated) + 1 citation, or the consult-expert fallback
12. RSS news items are stored in `news_items` and surfaced in `/updates`, but they are **never** mixed into the RAG retrieval corpus — RAG-only-from-circulars is invariant
13. After every prompt: update README.md, MEMORY.md, CLAUDE.md, context.md

## Quick Reference

- **Python:** ruff + black (line-length=100), B008 suppressed globally
- **TypeScript:** `strict: true`, ESLint + Prettier
- **Tests:** pytest (backend), Next.js build (frontend)
- **Env:** `.env.example` is the reference; `Settings` class loads all

## Build Progress (50/50 done)

| Prompt | Description | Status |
|--------|-------------|--------|
| 01–04b | Infrastructure: monorepo, schema, config, FastAPI, embedding service | Done |
| 05–10 | Scraper: crawl, PDF, metadata, chunking, Celery, supersession | Done |
| 11–14 | Auth: email validation, OTP, JWT, frontend auth | Done |
| 15–17 | Circular Library: hybrid search API, frontend, detail page | Done |
| 18–23 | RAG Q&A: retrieval, LLM, SSE streaming, caching, ask/history | Done |
| 24–27 | Subscriptions: Razorpay, plans, upgrade/account pages | Done |
| 28–32 | Admin: dashboard, review, prompts, users, circulars, scraper | Done |
| 33–36 | Action items + saved interpretations (backend + frontend) | Done |
| 37–42 | Dashboard, updates, admin UI, analytics, summary services | Done |
| 43–50 | PDF export, CI/CD, Nginx, Makefile, launch checks | Done |

## Phase 2 Roadmap (Sprint 1-8 + Frontend v2)

| Sprint | Description | Status |
|--------|-------------|--------|
| Sprint 1 | Hardening (HTTPOnly cookies, Scraper Embedder), Analytics (PostHog), Landing Page | ✅ Complete (`363b1ef`) |
| Sprint 2 | Anti-Hallucination Guardrails, Golden Dataset Eval Pipeline, k6 Load Tests | ✅ Complete (`1858575`) |
| Sprint 3 | Public Snippet Sharing, RSS/News Ingest, Knowledge Graph + RAG Expansion (flag-gated) | ✅ Complete (`5379c49`/`5d6dec3`/`52375b8`/`516acf9`) |
| Sprint 4 | Premium UI Polish (Confidence Meter UI, Skeleton loaders, Dark mode, SSE jitter fix), A/B UX flag scaffolding + LLM SDK / fallback-model hardening | ✅ Complete (`f6c3a5a` + `fdc784c`) |
| Sprint 5 | Admin Manual PDF Upload, Semantic Clustering Heatmaps | ✅ Complete (`5a8a77b` + CI fixes `33d9b8d`) |
| Sprint 6 | Pre-Launch Hardening: SIGTERM shutdown, system user audit, scraper embeddings on insert, LLM exception tightening, KG expansion GA, retrieval eval, dev Dockerfile | ✅ Complete |
| Sprint 7 | DPDP Compliance (account deletion + data export), subscription auto-renewal, low-credit notifications | ✅ Complete |
| Sprint 8 | Updates feed tracking, action items stats/overdue, admin Q&A sandbox, question suggestions, PDF export w/ QR codes | ✅ Complete |
| Frontend v2 | Terminal-modern redesign — design tokens, AppShell, editorial Ask, list pages, Learnings, Debate, Upgrade, Account | ✅ Complete (`49cde9c`) |
| Phase D.3 | Debate & Annotations API — relational models, CRUD, Dashboard integration | ✅ Complete |
| Post-Build | Real data migration, GCP deployment, Beta launch | ⏳ In Progress |

## Localhost Demo

Status: **Running + UAT passed** (2026-04-14). All 6 containers via `docker compose up --build -d`. UAT: 81/81 tests passed.

- `DEMO_MODE=true` — fixed OTP `123456`, no email/payment, no cross-encoder
- LLM: Claude Sonnet + extended thinking (10k budget) primary, GPT-4o fallback
- Auth: HttpOnly cookie refresh tokens, RS256 JWT, jti blacklist
- RAG: vector+BM25 RRF fusion, cross-encoder rerank (skipped in demo), KG expansion ON by default
- Anti-hallucination: confidence scoring (0-1.0), "Consult Expert" fallback at < 0.5
- Migrations: `001`–`005` (initial → Sprint 6 system user)
- Evals: golden dataset 21/21, retrieval 8/8, k6 load tests (smoke/load/spike)
- Key Sprint features: snippet sharing (`/s/[slug]`), RSS news (69 items), KG (95 entities), Confidence Meter UI, dark mode (WCAG-AA), skeleton loaders, admin PDF upload, semantic heatmaps, DPDP compliance, auto-renewal, low-credit alerts
- **Frontend v2 ("terminal-modern")**: design tokens (paper/ink/amber palette, serif editorial, mono data), AppShell with TopBar + Sidebar + Ticker + CommandPalette + TweaksPanel, editorial Ask brief with SSE, 2-col library, dtable list pages, Learnings + Debate new routes, 3-col Upgrade, DPDP Account panel. 27 routes. Design source in `files/design-v2/`.
- See `UAT_RESULTS.md` for full test results, `PRODUCTION_PLAN.md` for GCP deploy

## Next Steps (Post-Sprint 8)

Sprint 7 resolved G-01 (DPDP deletion), G-02 (DPDP export), G-04 (auto-renewal), G-05 (low-credit notifications). Sprint 8 resolved G-03 (updates tracking), G-06 (action stats), G-07 (admin sandbox), G-08 (suggestions), G-09 (PDF QR), G-12 (overdue). See `DEVELOPMENT_PLAN.md` for the unified implementation plan.

### Pre-Launch (GCP Phases A–C)
| Phase | Work |
|-------|------|
| Phase A | GCP infra provisioning: Cloud SQL, Memorystore, Artifact Registry, Secret Manager |
| Phase B | CI/CD hardening: WIF, staging env, security baseline, integration tests |
| Phase C | Data migration (in-progress), observability (✅ done), pre-launch testing, v1.0.0 launch |

### Post-Launch (Sprint 9+)
| Phase | Work |
|-------|------|
| Sprint 9 | pybreaker circuit breaker, TD-01/TD-03/TD-09, mobile responsive polish |
| Sprint 10–12 | Conversational Q&A, team seats, shared interpretations |
| Sprint 13–15 | Multi-regulator (SEBI), cross-regulator RAG, email digests |
| Sprint 16–18 | Enterprise API, batch export, circular version diff |

### Remaining Tech Debt
| Size | Items |
|------|-------|
| Medium | TD-01 (scraper DB isolation), TD-03 (OpenAPI codegen), TD-09 (BACKEND_PUBLIC_URL) |

### PRD v2.0 → v3.0 Gap Summary (12 gaps)
| Priority | Gaps |
|----------|------|
| ~~**Before Launch**~~ | ~~G-01 (DPDP deletion), G-02 (DPDP export)~~ — ✅ Sprint 7 |
| ~~**Sprint 7**~~ | ~~G-04 (auto-renewal), G-05 (low-credit emails)~~ — ✅ Sprint 7 |
| ~~**Sprint 8**~~ | ~~G-03 (updates tracking), G-06 (action stats), G-07 (admin sandbox), G-08 (suggestions), G-09 (PDF QR), G-12 (overdue)~~ — ✅ Sprint 8 |
| **Sprint 9** | G-10 (circuit breaker) |
| **Deferred** | G-11 (query expansion — KG expansion serves same purpose) |

## File Reference

| File | Purpose |
|------|---------|
| `TEAM_HANDOVER.md` | **Start here** if you're new — one-page orientation + reading order |
| `MEMORY.md` | Architecture, schema, business rules, patterns |
| `context.md` | Project state — inventory, verification results |
| `spec.md` | Full technical spec — schema, API, RAG pipeline, security |
| `README.md` | External docs — build progress, API ref, setup |
| `LEARNINGS.md` | Phase 2 mistakes, root causes, and prevention rules — read before any sprint |
| `TESTCASES.md` | Complete test inventory — functional, technical, eval, load, stress |
| `PRODUCTION_PLAN.md` | GCP deployment roadmap and cost estimates |
| `DEVELOPMENT_PLAN.md` | Unified implementation plan — gap closure, infra, roadmap |
| `RegPulse_PRD_v4.md` | Product requirements v4.0 — Frontend v2 + Learnings/Debates/Annotations |
| `RegPulse_FSD_v4.md` | Functional specification v4.0 — schema, endpoints, design system |
| `RegPulse_PRD_v3.md` | Product requirements v3.0 (superseded by v4.0) |
| `RegPulse_FSD_v3.md` | Functional specification v3.0 (superseded by v4.0) |
| `TECHNICAL_DOCS.md` | Full technical documentation — architecture, DB, API, RAG, security, runbook |
| `UAT_PLAN.md` | 208 manual UAT test scenarios across 28 categories |
| `UAT_RESULTS.md` | Automated UAT results — 81/81 passed (2026-04-14) |
| `HANDOVER.md` | Session handover — what was done, what's next, environment state |
| `HANDOVER_DESIGN_V2.md` | Frontend v2 redesign handover — chunks, design source, constraints |
| `GCP_DEPLOY_RUNBOOK.md` | Live GCP deployment state — phase status, resource IDs, resumable scripts |
