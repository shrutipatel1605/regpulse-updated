# RegPulse — Implementation & Development Plan

> Master plan covering code gap closure, GCP deployment, tech debt, and feature roadmap.
> Informed by PRD v3.0 / FSD v3.0 gap analysis (12 gaps identified) and PRODUCTION_PLAN.md.
>
> **Last updated:** 2026-04-14 (Sprint 8 landed)

---

## Current State

| Area | Status |
|---|---|
| **Codebase** | 50/50 prompts + Sprints 1–8 + Phase D.1-D.3 complete. ~67 endpoints, 21 tables, 27 frontend routes. |
| **CI** | Green (backend-lint, backend-test, frontend-build). |
| **Eval** | Golden dataset 21/21 PASS, retrieval eval 8/8 PASS |
| **Deploy pipeline** | Staging live on Cloud Run. Scraper Job running daily. |
| **Infra** | GCP resources provisioned (asia-south1). Cloud SQL, Redis, Artifact Registry live. |
| **Audit** | **UX Blocker**: OTP login gate blocks automated agents. **Scraper**: Ingestion bottleneck (Syntax Error in PDF extraction). |
| **Tech debt** | TD-01 (scraper DB isolation), TD-03 (OpenAPI codegen), TD-09 (BACKEND_PUBLIC_URL), **TD-13 (Scraper extraction fix)** |

---

## Plan Overview

```
Sprint 7 ──── DPDP compliance + subscription completion (code, pre-launch legal blocker)
    │
Sprint 8 ──── UX gaps + admin tooling (code, pre-launch quality bar)
    │
Phase A ───── GCP infrastructure provisioning (infra, per PRODUCTION_PLAN.md Phases 2-3)
    │
Phase B ───── CI/CD + staging + security hardening (infra, per PRODUCTION_PLAN.md Phases 4-5)
    │
Phase C ───── Data migration + observability + launch (infra, per PRODUCTION_PLAN.md Phases 6-8)
    │
Sprint 9 ──── Post-launch iteration (reliability, multi-regulator prep)
    │
Sprint 10+ ── Feature roadmap (team seats, conversational Q&A, SEBI/IRDAI)
```

Sprint 7 and Phase A can run **in parallel** — code work is independent of infra provisioning.

---

## Sprint 7: Pre-Launch Legal & Revenue (Code)

**Goal:** Close the 2 DPDP legal blockers and the subscription gaps that affect revenue.

**Duration:** ~1 week

### 7.1 DPDP Account Deletion — Gap G-01 (P0 Legal)

| Item | Detail |
|---|---|
| **Endpoint** | `PATCH /api/v1/account/delete` |
| **Auth** | Requires active user + OTP re-confirmation |
| **Schema** | `users.deletion_requested_at` column already exists |
| **Logic** | (1) Verify OTP, (2) Set `is_active=FALSE`, `deletion_requested_at=now()`, (3) Anonymise PII: `email→'deleted_{uuid}@deleted.regpulse.com'`, `full_name→'Deleted User'`, `org_name→NULL`, `designation→NULL`, (4) Delete: sessions, saved_interpretations, action_items WHERE user_id, (5) Nullify: `questions.user_id`, `analytics_events.user_id`, (6) Send confirmation email to original email before anonymising, (7) Revoke all active sessions + blacklist JTIs |
| **Files to create/edit** | `backend/app/routers/account.py` (new router), `backend/app/schemas/account.py` (new), register router in `main.py` |
| **Test** | Unit test: verify PII is nullified, sessions deleted, questions.user_id set NULL |
| **Frontend** | Add "Delete Account" section to `/account` page with OTP confirmation modal |

### 7.2 DPDP Data Export — Gap G-02 (P0 Legal)

| Item | Detail |
|---|---|
| **Endpoint** | `GET /api/v1/account/export` |
| **Auth** | Requires active user + OTP re-confirmation |
| **Logic** | Query all user's questions (text, answers, citations, timestamps), saved_interpretations (name, tags), action_items (title, description, status, due_date). Return as JSON with `Content-Disposition: attachment; filename=regpulse_export_{user_id}.json`. No admin-internal or third-party data. |
| **Files to create/edit** | Same `account.py` router, add export schema |
| **Test** | Unit test: verify export contains all user data, excludes admin fields |
| **Frontend** | Add "Export My Data" button to `/account` page |

### 7.3 Subscription Auto-Renewal — Gap G-04 (P1 Revenue)

| Item | Detail |
|---|---|
| **Celery task** | `subscription_renewal_check()` in `scraper/tasks.py`, scheduled daily 08:00 IST via Celery Beat |
| **Logic** | Query users WHERE `plan != 'FREE' AND plan_expires_at < now() + interval '3 days' AND plan_auto_renew=TRUE`. For each: create Razorpay order. v1 limitation: send renewal reminder email (auto-charge requires Razorpay Subscriptions API, deferred). On manual payment: extend `plan_expires_at + 30 days`, add monthly credits. |
| **Endpoint** | `PATCH /api/v1/subscriptions/auto-renew` — toggle `plan_auto_renew` boolean |
| **Schema** | `plan_auto_renew` and `plan_expires_at` columns already exist |
| **Files to edit** | `scraper/tasks.py` (new task), `scraper/celery_app.py` (beat schedule), `backend/app/routers/subscriptions.py` (new endpoint), email template `renewal_reminder.html` |
| **Frontend** | Add auto-renew toggle to `/account` page billing section |

### 7.4 Low-Credit Notifications — Gap G-05 (P1 Revenue)

| Item | Detail |
|---|---|
| **Celery task** | `credit_notifications()` in `scraper/tasks.py`, scheduled daily 09:00 IST |
| **Logic** | Query users WHERE `credit_balance <= 10 AND plan='FREE' AND (last_credit_alert_sent IS NULL OR < now() - interval '7 days')`. Send `low_credits.html` email with upgrade CTA. Update `last_credit_alert_sent`. |
| **In-request trigger** | After credit deduction in `questions.py`, if balance hits 5 or 2: fire `BackgroundTask` to send email |
| **Schema** | `last_credit_alert_sent` column already exists |
| **Files to edit** | `scraper/tasks.py`, `scraper/celery_app.py`, `backend/app/routers/questions.py` (background task hook), email template `low_credits.html` |

### Sprint 7 Exit Criteria

- [ ] `PATCH /account/delete` works end-to-end: OTP → anonymise → sessions revoked
- [ ] `GET /account/export` returns complete JSON of user's data
- [ ] Renewal reminder emails sent for expiring subscriptions
- [ ] Low-credit emails sent at thresholds 10/5/2
- [ ] Auto-renew toggle works on `/account` page
- [ ] All new endpoints have unit tests
- [ ] CI green
- [ ] Golden dataset eval still 21/21 (no regression)

---

## Sprint 8: Pre-Launch UX & Admin Gaps (Code)

**Goal:** Close the remaining UX gaps that affect product quality at launch.

**Duration:** ~1 week

### 8.1 Updates Feed Tracking — Gap G-03 (P2 UX)

| Item | Detail |
|---|---|
| **Endpoints** | `GET /api/v1/circulars/updates` (recent circulars feed, filterable), `POST /api/v1/circulars/updates/mark-seen` (set `last_seen_updates=now()`) |
| **Logic** | Query `circular_documents WHERE indexed_at > now() - interval '{days} days' ORDER BY indexed_at DESC`. Include `unread_count = COUNT WHERE indexed_at > user.last_seen_updates`. |
| **Schema** | `last_seen_updates` column already exists |
| **Frontend** | Add unread badge to Updates nav item (Zustand store). Filter tabs: All / High Impact / This Week. Call mark-seen on page visit. |
| **Files to edit** | `backend/app/routers/circulars.py` (2 new endpoints), `frontend/src/app/(app)/updates/page.tsx`, `frontend/src/stores/` (unread count) |

### 8.2 Action Items Stats — Gap G-06 (P2 UX)

| Item | Detail |
|---|---|
| **Endpoint** | `GET /api/v1/action-items/stats` |
| **Logic** | `SELECT status, COUNT(*) FROM action_items WHERE user_id = $1 GROUP BY status`. Include computed `overdue_count = COUNT WHERE due_date < today AND status IN ('PENDING', 'IN_PROGRESS')`. |
| **Frontend** | Use stats in dashboard badge for pending/overdue items |
| **Files to edit** | `backend/app/routers/action_items.py` (1 new endpoint), `frontend/src/app/(app)/dashboard/page.tsx` |

### 8.3 Action Items Overdue Computation — Gap G-12 (P2 UX)

| Item | Detail |
|---|---|
| **Logic** | In the action items list response, add computed `is_overdue` boolean: `due_date IS NOT NULL AND due_date < today AND status != 'COMPLETED'`. |
| **Frontend** | Show overdue badge + days-overdue countdown on action items page |
| **Files to edit** | `backend/app/schemas/action_items.py` (computed field), `backend/app/routers/action_items.py`, `frontend/src/app/(app)/action-items/page.tsx` |

### 8.4 Admin Q&A Sandbox — Gap G-07 (P2 Admin)

| Item | Detail |
|---|---|
| **Endpoint** | `GET /api/v1/admin/test-question?q={question}` |
| **Logic** | Call RAGService + LLMService with active prompt version. Do NOT: create a question record, deduct credits, add to user history. Log as `admin_test=TRUE` in analytics_events. |
| **Files to edit** | `backend/app/routers/admin/prompts.py` (add endpoint alongside prompt management) |

### 8.5 Question Suggestions — Gap G-08 (P2 UX)

| Item | Detail |
|---|---|
| **Endpoint** | `GET /api/v1/questions/suggestions?q={partial_question}` |
| **Logic** | Embed the partial question, query `questions` table by vector similarity (pgvector ANN on question embeddings or cached embeddings). Return top 5 similar past questions (question_text + quick_answer preview). |
| **Note** | Requires question embeddings to be stored. If not currently stored, this can be deferred or implemented using document chunk similarity as a proxy. |
| **Files to edit** | `backend/app/routers/questions.py` (1 new endpoint) |

### 8.6 PDF QR Codes — Gap G-09 (P3 Polish)

| Item | Detail |
|---|---|
| **Logic** | For each citation in the PDF export, generate a QR code pointing to the `rbi_url`. Use `qrcode` Python library. Place QR beside each citation block. |
| **Files to edit** | `backend/app/services/pdf_export_service.py`, add `qrcode` to `requirements.txt` |

### Sprint 8 Exit Criteria

- [ ] Updates page has unread badges and mark-seen behaviour
- [ ] Action items show overdue status and dashboard badge
- [ ] Admin can test prompts via sandbox without creating records
- [ ] Question suggestions work on the ask page
- [ ] PDF exports include QR codes
- [ ] All new endpoints have unit tests
- [ ] CI green
- [ ] Golden dataset eval still 21/21

---

## Phase A: GCP Infrastructure Provisioning

**Goal:** Stand up production GCP environment. Runs **in parallel** with Sprint 7.

**Duration:** ~1 week (manual provisioning; Terraform deferred)

**References:** PRODUCTION_PLAN.md Phases 1–3

### A.1 GCP Project Setup
```bash
gcloud projects create regpulse-prod --name="RegPulse Production"
gcloud services enable \
  run.googleapis.com \
  sqladmin.googleapis.com \
  redis.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com \
  cloudscheduler.googleapis.com \
  compute.googleapis.com \
  iam.googleapis.com
```

### A.2 Provision Data Stores

| Resource | Spec | Command Pattern |
|---|---|---|
| Cloud SQL | PostgreSQL 16, db-custom-2-4096, HA, 50GB SSD, asia-south1 | `gcloud sql instances create regpulse-db ...` |
| pgvector | Extension on Cloud SQL | `CREATE EXTENSION vector;` via psql |
| Memorystore | Redis, Basic 1GB, asia-south1 | `gcloud redis instances create regpulse-cache ...` |
| Artifact Registry | Docker repo, asia-south1 | `gcloud artifacts repositories create regpulse ...` |

### A.3 Provision Secrets
- Create all `REGPULSE_*` secrets in Secret Manager (see PRODUCTION_PLAN.md Phase 3.1)
- Generate production RSA keypair for JWT
- Set `ENVIRONMENT=prod`, `DEMO_MODE=false`, `FRONTEND_URL=https://regpulse.in`

### A.4 Networking
- Create VPC Serverless Access connector for Cloud Run → Memorystore
- Configure Cloud SQL Auth Proxy connector for Cloud Run → Cloud SQL
- Create VPC for GCE instance (celery worker)

### A.5 Exit Criteria
- [ ] Cloud SQL instance running, pgvector enabled, migrations applied
- [ ] Memorystore Redis instance running
- [ ] Artifact Registry repo created
- [ ] All secrets stored in Secret Manager
- [ ] VPC connectors configured

---

## Phase B: CI/CD + Security Hardening

**Goal:** Automated deployment pipeline, staging environment, security baseline.

**Duration:** ~1 week (after Phase A)

**References:** PRODUCTION_PLAN.md Phases 4–5

### B.1 Workload Identity Federation
```bash
# Create WIF pool + provider for GitHub Actions
gcloud iam workload-identity-pools create github-pool ...
gcloud iam workload-identity-pools providers create-oidc github-provider ...
# Create service account with Cloud Run deployer + Artifact Registry writer roles
gcloud iam service-accounts create github-deploy ...
```

### B.2 First Manual Deploy
```bash
# Build and push images
docker build -t asia-south1-docker.pkg.dev/$PROJECT/regpulse/backend:v0.1.0 backend/
docker push ...
# Deploy Cloud Run services
gcloud run deploy regpulse-backend --image=... --region=asia-south1 ...
gcloud run deploy regpulse-frontend --image=... --region=asia-south1 ...
# Deploy GCE celery worker
gcloud compute instances create-with-container regpulse-celery ...
# Create Cloud Run Job for scraper + Cloud Scheduler trigger
gcloud run jobs create regpulse-scraper ...
gcloud scheduler jobs create http scraper-daily ...
```

### B.3 Staging Environment
- Separate Cloud Run services with `-staging` suffix
- Separate Secret Manager secrets: `REGPULSE_STAGING_*`
- deploy.yml: push to main → staging auto-deploy; v* tag → production

### B.4 Security Hardening
- Custom domain mapping with Google-managed TLS
- Verify slowapi works behind Cloud Run's `X-Forwarded-For`
- Enable AUTH on Memorystore
- Add `pip audit` + `pnpm audit` to CI
- Cloud Armor policy (defer to post-beta if acceptable)

### B.5 Integration Test Job
- Add CI job: `docker compose up` → run tests against real Postgres + Redis → tear down
- Catches issues SQLite-based unit tests miss (e.g., pgvector queries, Redis-specific behaviour)

### B.6 Exit Criteria
- [ ] `git tag v0.1.0 && git push --tags` triggers full deploy to production Cloud Run
- [ ] Staging deploys automatically on push to main
- [ ] Custom domain with TLS working
- [ ] Integration tests passing in CI

---

## Phase C: Data Migration + Observability + Launch

**Goal:** Real data, monitoring, and launch checklist.

**Duration:** ~1 week (after Phase B)

**References:** PRODUCTION_PLAN.md Phases 6–8

### C.1 Data Migration & Ingestion Audit
- Run full scraper against live rbi.org.in.
- **Audit Observation (2026-05-15)**: Scraper identifies ~600 documents but only 10 successfully index. Logs show "Syntax Error" from `pdftotext`.
- **Action**: Fix poppler/pdftotext extraction in scraper container (TD-13).
- Verify: circulars indexed, embeddings populated, KG entities extracted.
- Run `backfill_kg.py` if needed for any circulars that missed KG extraction.
- Verify golden dataset eval passes against real data.

### C.2 Observability
- Cloud Monitoring alert policies:
  - Cloud Run CPU/Memory > 80%
  - Cloud Run 5xx rate > 1%
  - Cloud SQL connections > 80%
- Email notification channel for critical alerts
- Verify structlog JSON auto-parsed in Cloud Logging

### C.3 Pre-Launch Testing Checklist
- [ ] Full pipeline: register → verify OTP → ask question → get cited answer → action items
- [ ] Subscription: create order → Razorpay payment → webhook → credits added
- [ ] DPDP: account deletion works end-to-end; data export returns complete JSON
- [ ] Auto-renew toggle + renewal reminder email
- [ ] Low-credit notification email
- [ ] Scraper: manual run → circulars indexed → searchable in library
- [ ] Admin: login → dashboard → review queue → approve summary → upload PDF → view heatmap
- [ ] Snippet sharing: create → public URL works → OG image renders
- [ ] Auth edge cases: expired token refresh, concurrent sessions, logout
- [ ] Rate limiting: verify 429 responses under load
- [ ] LLM fallback: disable Anthropic key → verify GPT-4o fallback fires
- [ ] Dark mode: toggle works, WCAG-AA contrast verified
- [ ] Empty state: new user with no circulars indexed
- [ ] Load test: k6 against production (smoke scenario only)

### C.4 Launch
- Tag `v1.0.0`
- Monitor Cloud Logging + Monitoring for 48h
- Rotate demo credentials
- Announce beta launch

### C.5 Exit Criteria
- [ ] All pre-launch tests passing
- [ ] Monitoring alerts configured and tested
- [ ] Real RBI circulars indexed (not demo data)
- [ ] v1.0.0 deployed and accessible at custom domain

---

## Phase D: Frontend v2 Backend Integration

**Goal:** Replace `RP_DATA` mock fixtures in the V2 frontend with live backend endpoints.

### D.1 Pulse Dashboard API
- **Endpoint:** `GET /api/v1/dashboard/pulse`
- **Logic:** Aggregate global metrics (total circulars, superseded this week, questions asked), serve the semantic heatmap to regular users, and provide an activity stream (who asked what, what was recently saved).

### D.2 Team Learnings API
- **Endpoint:** `GET / POST / PUT / DELETE /api/v1/learnings`
- **Logic:** New model `Learning` bridging a User, a Question or Circular, tags, and a one-line takeaway. Support "Notify Team" workflows.

### D.3 Debate & Annotations API
- **Endpoint:** `GET / POST /api/v1/debates`
- **Logic:** New model `DebateThread` for threaded discussions linked to circulars or citations. Upvote/downvote tracking and OPEN/RESOLVED status.

### D.4 Market Ticker Feed
- **Endpoint:** `GET /api/v1/news/ticker`
- **Logic:** Adapt the existing RSS news ingest items into a scrolling ticker format for the AppShell top bar.

---

## Sprint 9: Post-Launch Hardening (Post-Launch, ~2 weeks)

**Goal:** Address reliability gaps and tech debt surfaced by real usage.

### 9.1 Circuit Breaker — Gap G-10 (P3 Reliability)

| Item | Detail |
|---|---|
| **Current** | Simple try/catch fallback from Anthropic to GPT-4o |
| **Improvement** | Implement proper circuit breaker with `pybreaker`: `fail_max=3`, `reset_timeout=60`. When circuit open, skip Anthropic entirely for 60s → reduces latency during outages. |
| **Files** | `backend/app/services/llm_service.py`, add `pybreaker` to `requirements.txt` |

### 9.2 Tech Debt TD-01: Scraper DB Isolation

| Item | Detail |
|---|---|
| **Current** | Scraper writes directly to backend database via synchronous SQLAlchemy |
| **Improvement** | Add a thin internal API on the backend that the scraper calls to write documents. Alternatively, use a message queue (Redis pub/sub) for scraper → backend document ingestion. |
| **Risk** | Breaking change to scraper pipeline. Requires careful migration. |
| **Recommendation** | Defer until real usage proves this is causing issues (concurrent access, schema drift). Document the boundary clearly. |

### 9.3 Tech Debt TD-03: OpenAPI Codegen

| Item | Detail |
|---|---|
| **Current** | Manual `api.ts` client in frontend |
| **Improvement** | Generate TypeScript client from FastAPI's OpenAPI schema using `openapi-typescript-codegen` or `@hey-api/openapi-ts`. Eliminates drift between backend and frontend API types. |
| **Files** | `frontend/src/lib/api.ts` (replace), add codegen script to `Makefile` |

### 9.4 Tech Debt TD-09: BACKEND_PUBLIC_URL

| Item | Detail |
|---|---|
| **Current** | `BACKEND_PUBLIC_URL` unset in demo; OG images for snippets use localhost fallback |
| **Fix** | Set `BACKEND_PUBLIC_URL=https://api.regpulse.in` (or whatever the Cloud Run backend URL is) in Secret Manager |

### 9.5 Mobile Responsive Polish

| Item | Detail |
|---|---|
| **Current** | Desktop-first layout; some pages may not render well on mobile |
| **Improvement** | Audit all 25 routes for Tailwind responsive breakpoints. Priority: landing page, ask, library, history. |

### Sprint 9 Exit Criteria
- [ ] Circuit breaker implemented with fail tracking
- [ ] TD-03 resolved (OpenAPI codegen) OR explicitly deferred with rationale
- [ ] TD-09 resolved (BACKEND_PUBLIC_URL set in production)
- [ ] Top 5 mobile-critical pages responsive

---

## Sprint 10+: Feature Roadmap (Quarterly)

Prioritised by user-facing impact. Each sprint is ~2 weeks.

### Q3 2026 — Collaboration & Conversation

| Sprint | Feature | PRD Ref | Effort |
|---|---|---|---|
| 10 | **Conversational Q&A Threading** — `parent_question_id` on questions table, context window management, frontend thread UI | US-13 | Large |
| 11 | **Team Seats & Workspaces** — org model, role-based access (viewer/editor/admin), shared question history, shared action items | US-14 | Large |
| 12 | **Share Interpretation with Team** — workspace-scoped sharing, comment threads on saved interpretations | Roadmap | Medium |

### Q4 2026 — Multi-Regulator Expansion

| Sprint | Feature | PRD Ref | Effort |
|---|---|---|---|
| 13 | **SEBI Circular Scraper** — new crawler for sebi.gov.in, map to existing schema (regulator='SEBI'), department/tag taxonomy for SEBI | Roadmap | Large |
| 14 | **Multi-Regulator RAG** — regulator-scoped retrieval, cross-regulator questions ("how do RBI and SEBI KYC norms differ?"), regulator filter in library | Roadmap | Medium |
| 15 | **Email Digests** — weekly regulatory summary via Celery Beat, personalised by user's department/tags, subscription-gated | Roadmap | Medium |

### Q1 2027 — Enterprise & Scale

| Sprint | Feature | PRD Ref | Effort |
|---|---|---|---|
| 16 | **Enterprise API Access** — API key management, rate-limited REST API for programmatic Q&A, usage metering | Roadmap | Large |
| 17 | **Batch Export** — bulk PDF export, Excel export for action items, scheduled report generation | Roadmap | Medium |
| 18 | **Version Diff / Compare Circulars** — store circular version history, side-by-side diff rendering | Roadmap | Medium |

---

## Dependency Map

```
Sprint 7 (DPDP + subscriptions) ─────────┐
                                          │
Phase A (GCP infra) ──────── parallel ────┤
                                          │
                                          ▼
                                    Phase B (CI/CD + security)
                                          │
Sprint 8 (UX gaps) ── can start ──────────┤
 during Phase A/B                         │
                                          ▼
                                    Phase C (data + launch)
                                          │
                                          ▼
                                    v1.0.0 LAUNCH
                                          │
                                          ▼
                                    Sprint 9 (post-launch hardening)
                                          │
                                          ▼
                                    Sprint 10+ (roadmap)
```

**Critical path:** Sprint 7 (DPDP) → Phase B (CI/CD) → Phase C (launch). DPDP is a legal blocker; nothing ships to production without it.

**Parallelisation:** Phase A (infra) runs in parallel with Sprint 7 (code). Sprint 8 can overlap with Phase B.

---

## Gap Closure Tracker

| Gap | Description | Sprint | Status |
|---|---|---|---|
| G-01 | DPDP Account Deletion | Sprint 7 | ✅ Complete |
| G-02 | DPDP Data Export | Sprint 7 | ✅ Complete |
| G-03 | Updates Feed unread tracking | Sprint 8 | ✅ Complete |
| G-04 | Subscription auto-renewal | Sprint 7 | ✅ Complete |
| G-05 | Low-credit notifications | Sprint 7 | ✅ Complete |
| G-06 | Action items /stats | Sprint 8 | ✅ Complete |
| G-07 | Admin Q&A sandbox | Sprint 8 | ✅ Complete |
| G-08 | Question suggestions | Sprint 8 | ✅ Complete |
| G-09 | PDF QR codes | Sprint 8 | ✅ Complete |
| G-10 | pybreaker circuit breaker | Sprint 9 | Planned |
| G-11 | Query expansion | Deferred | KG expansion serves same purpose |
| G-12 | Action items overdue | Sprint 8 | ✅ Complete |
| D.1 | Pulse Dashboard API | Phase D | ✅ Complete |
| D.2 | Team Learnings API | Phase D | ✅ Complete |
| D.3 | Debate & Annotations API | Phase D | ✅ Complete |
| D.4 | Market Ticker Feed | Phase D | Planned |

---

## Cost Summary

### Development Effort

| Phase | Duration | Parallel? |
|---|---|---|
| Sprint 7 | ~1 week | Yes (with Phase A) |
| Sprint 8 | ~1 week | Yes (with Phase B) |
| Phase A | ~1 week | Yes (with Sprint 7) |
| Phase B | ~1 week | After Phase A |
| Phase C | ~1 week | After Phase B + Sprints 7-8 |
| **Total to launch** | **~3–4 weeks** | With parallelisation |

### Infrastructure (Monthly)

| Resource | Cost |
|---|---|
| Cloud SQL PostgreSQL (HA) | $75 |
| Memorystore Redis | $35 |
| Cloud Run backend | $25 |
| Cloud Run frontend | $12 |
| GCE e2-small (celery) | $15 |
| Artifact Registry | $3 |
| Cloud Armor (if used) | $8 |
| **Total** | **~$173/mo** |

Plus variable: OpenAI embeddings (~$0.13/1M tokens), Anthropic LLM (~$3/1M input tokens), SMTP (free tier).

---

## Document References

| Document | Purpose |
|---|---|
| `PRODUCTION_PLAN.md` | GCP infrastructure provisioning detail (Phases 2–8) |
| `RegPulse_PRD_v3.md` | Product requirements with gap analysis (Section 12) |
| `RegPulse_FSD_v3.md` | Functional specification with gap analysis (Section 16) |
| `TECHNICAL_DOCS.md` | Full technical documentation |
| `LEARNINGS.md` | Phase 2 gotchas — read before any sprint |
| `TESTCASES.md` | Complete test inventory |

---

*--- RegPulse Development Plan v1.0 ---*
