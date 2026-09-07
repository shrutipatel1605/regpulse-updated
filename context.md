# RegPulse — Project Status

> **Phase 2 complete + GCP MVP live in DEMO_MODE + Phase D (collaboration) shipped. SCR-1 (scraper PDF extraction) resolved 2026-05-15. Demo Q&A works end-to-end at the API layer. Next critical path: CORS-DEMO-1 (cross-site middleware loop blocks browser login) → Phase 7 launch.**

---

## Current State (2026-05-15)

- **Branch:** `main` — Phase D.1/D.2/D.3 + SCR-1 fix + DEMO auto-approve + cross-site cookie fix all on `main`. `backend:rc4` (rev `00009-v8h`), `scraper:rc4` deployed 2026-05-15.
- **CI:** All 3 jobs green on `main` (backend-lint, backend-test, frontend-build)
- **Live:** GCP MVP deployed 2026-05-14, hardened 2026-05-15 — Cloud Run backend rev `00009-v8h` + frontend rev `00001` (unchanged, has the middleware bug) + scraper Job, all in `staging + DEMO_MODE=true`
- **UAT:** 81/81 automated tests passed on Sprint 7 state; Sprint 8 + Phase D added more unit coverage
- **Golden eval:** 21/21 PASS | **Retrieval eval:** 8/8 PASS
- **Frontend:** 27 routes (Dashboard, /learnings, /debate now backed by real APIs)
- **Backend:** ~70 endpoints, 12 services, 21 tables, 5 SQL migrations + 2 Alembic
- **LEARNINGS.md:** L1–L8 (Phase 2) + LGCP.1–LGCP.6 (GCP deploy)

**🔥 Top blocker:** CORS-DEMO-1 — browser login loops because Next.js middleware on `regpulse-frontend-…run.app` can't read the `refresh_token` cookie scoped to `regpulse-backend-…run.app` (different PSL sites). Fix paths (A/B/C) documented in `HANDOVER.md`. Recommendation: (A) Next.js rewrites OR (C) Phase 5 custom domain.

---

## Inventory

**Backend:** 12 services, ~70 endpoints, 21 tables, 5 SQL migrations + 2 Alembic
- Phase D.1: Pulse Dashboard API + frontend wire-up (`fee0f76` / `959bfef`)
- Phase D.2: Team Learnings API + `learning.py` model + frontend (`a3013c5` / `25ab3ac`)
- Phase D.3: Debates API — `debate.py` model, `routers/debates.py`, `schemas/debates.py`, Alembic `1066cb96e57c`

**Frontend:** 27 routes, terminal-modern v2 design system, PostHog analytics
- Phase D wire-up: `useDebates` hook, Dashboard `DebateCard`, `/debate` page fully on live DB

**Scraper:** 10 Celery tasks, 6 beat schedules. Container layout fixed in `aed8425`. PDF extraction still broken (SCR-1).

**Infra:** GCP Phases 1–6 done (provisioning → deploy → observability). Phase 4H, 5, 6 (CI/CD), 7 still deferred.

---

## Tech Debt & Follow-ups (open)

| ID | Issue | Plan |
|---|---|---|
| **CORS-DEMO-1** | **Browser login loop — Next.js middleware can't see cross-site cookie** | `*.run.app` sites are PSL-separated. Fix paths in HANDOVER + LEARNINGS L9.6. Top priority. |
| ~~SCR-1~~ | ~~PDF extraction failing~~ | ✅ Resolved (`16ba70c` + `scraper:rc4`). 93 circulars / 1,208 chunks. |
| TD-01 | Scraper writes directly to backend DB | API isolation in Sprint 9+ |
| TD-03 | Manual api.ts client | OpenAPI codegen (Sprint 9) |
| TD-09 | `BACKEND_PUBLIC_URL` unset in demo | Set when custom domain (Phase 5) lands |
| G-10 | Simple try/catch LLM fallback — no circuit-open tracking | `pybreaker` in requirements.txt; wire in Sprint 9 |
| OP-1 | `questions.question_embedding` NULL for pre-Sprint 8 rows | Run `scripts/backfill_question_embeddings.py` once in production |
| OP-2 | Admin sandbox doesn't swap `PromptVersion` at LLM call time | Wire `PromptVersion.prompt_text` through `LLMService` in Sprint 9 |

Resolved: ~~TD-02/04/05/06/07/08/10/11/12~~ (Sprints 1–6); G-01–G-09, G-12 (Sprints 7–8); scraper `ModuleNotFoundError` (`aed8425`).

---

## PRD Gap Status (10/12 resolved)

| Status | Gaps |
|--------|------|
| ✅ Sprint 7 | G-01 (DPDP deletion), G-02 (DPDP export), G-04 (auto-renewal), G-05 (low-credit) |
| ✅ Sprint 8 | G-03 (updates tracking), G-06 (action stats), G-07 (admin sandbox), G-08 (suggestions), G-09 (PDF QR), G-12 (overdue) |
| Sprint 9 | G-10 (circuit breaker) |
| Deferred | G-11 (KG expansion serves same purpose) |

---

## Critical Path to v1.0.0

Pre-launch code work is complete. GCP MVP is live in DEMO_MODE; API-level Q&A returns cited answers. Remaining path to v1.0.0:

1. **CORS-DEMO-1 fix** — Next.js rewrites OR Phase 5 custom domain. Without this the browser demo loops on login. ~10 min (rewrites) or ~30-60 min (custom domain). See HANDOVER § Top priority.
2. **2026-05-16 security tasks** — rotate exposed API keys + audit `shubhamkadam1802@gmail.com` IAM access.
3. **OP-3 — RBI WAF workaround** — recover the ~373 lost PDFs after CORS-DEMO-1 clears.
4. **Phase 6 — GitHub Actions auto-deploy via WIF** — 1.5–2 hr.
5. **Phase 7 — Smoke tests + v1.0.0 tag** — full UAT pass against GCP staging, then cut release.

ANN-index recovery (`halfvec(3072)` migration) parked until `circular_documents` row count exceeds ~1000 and end-to-end latency becomes measurably slow.
