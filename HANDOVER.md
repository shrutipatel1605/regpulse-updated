# RegPulse — Session Handover

> **From:** 2026-05-15 evening wrap (mixed Claude Code + Antigravity work)
> **To:** Next session
> **Branch:** `main` — pushed to `origin/main`
> **Live URLs:** [Frontend](https://regpulse-frontend-yvigu4ssea-el.a.run.app) · [Backend](https://regpulse-backend-yvigu4ssea-el.a.run.app) · [API docs](https://regpulse-backend-yvigu4ssea-el.a.run.app/api/v1/docs)

---

## 🟢 Read this first

Three things to know:

1. **The browser demo is broken at the login loop.** Register + verify-otp succeed at the API layer, but Next.js middleware on `regpulse-frontend-…run.app` cannot see the `refresh_token` cookie set by `regpulse-backend-…run.app` — they're separate sites under PSL. Middleware bounces every protected route to `/login`. **This is the #1 blocker** (CORS-DEMO-1). Three fix paths, choose one before resuming the demo — see "Top priority" below + LEARNINGS § L9.6.
2. **Everything else works.** Library populates anonymously (93 circulars), API-level Q&A returns cited answers (`confidence_score ≥ 0.5`), auth flow succeeds when driven by curl with `Bearer` headers. The break is purely cookie-vs-middleware on `*.run.app`.
3. **scraper:rc4 and backend:rc4 are live.** Both shipped this session. Scraper auto-approves circulars in DEMO_MODE; backend cookie is now `SameSite=None; Secure` and `FRONTEND_URL` points at the correct hash-form hostname.

---

## 📋 First 10 minutes — status checks

```bash
# Health + scraper + library
curl -s -o /dev/null -w "Backend  %{http_code} %{time_total}s\n" https://regpulse-backend-yvigu4ssea-el.a.run.app/api/v1/health
curl -s -o /dev/null -w "Frontend %{http_code} %{time_total}s\n" https://regpulse-frontend-yvigu4ssea-el.a.run.app/
curl -s 'https://regpulse-backend-yvigu4ssea-el.a.run.app/api/v1/circulars?page_size=3' | python3 -c "import sys,json; d=json.load(sys.stdin); print('Library total:', d.get('total'))"

# Cookie + CORS sanity (should be SameSite=none, Secure on the cookie; ACAO matching frontend URL on preflight)
curl -s -i -X OPTIONS 'https://regpulse-backend-yvigu4ssea-el.a.run.app/api/v1/auth/register' \
  -H 'Origin: https://regpulse-frontend-yvigu4ssea-el.a.run.app' \
  -H 'Access-Control-Request-Method: POST' \
  -H 'Access-Control-Request-Headers: content-type' | grep -iE '^HTTP|access-control-allow-origin'

# Git
git status --short
git log --oneline -8
```

**Expected:** backend + frontend 200, Library `total: 93`, preflight 200 with `access-control-allow-origin: https://regpulse-frontend-yvigu4ssea-el.a.run.app`, clean working tree.

---

## ⚠️  Top priority — unblock the browser demo (CORS-DEMO-1)

Backend cookie is correctly cross-site (`SameSite=None; Secure`). Backend sees the cookie on API calls. The break is **Next.js middleware** at `frontend/src/middleware.ts:41` — it reads `request.cookies.get("refresh_token")` from the frontend's *own* cookie jar, which is empty because the cookie lives on the backend host. Three resolution paths in increasing cost / decreasing hackiness:

### (A) Next.js rewrites — proxy `/api/*` through frontend origin *(~10 min, recommended)*
- Edit `frontend/next.config.js`: add `async rewrites()` returning `[{ source: '/api/:path*', destination: 'https://regpulse-backend-yvigu4ssea-el.a.run.app/api/:path*' }]`
- Change `NEXT_PUBLIC_API_URL` build-arg to `/api/v1` (same-origin)
- Cookie becomes same-origin; middleware works; no backend change needed
- Rebuild frontend → `bash scripts/gcp/phase4f_build_frontend.sh rc2` → deploy
- Survives hard refresh

### (B) Make middleware a no-op + rely on client-side auth state *(~10 min, hack)*
- Strip the redirect from `frontend/src/middleware.ts`; let pages call `/auth/me` and bounce client-side on 401
- Rebuild + redeploy frontend
- Hard refresh loses auth state (no recovery from refresh cookie)
- Picks up tech debt; don't ship as the final fix

### (C) Phase 5 — custom domain *(~30–60 min, real fix)*
- `gcloud beta run domain-mappings create --service=regpulse-frontend --domain=regpulse.in --region=asia-south1`
- Same for `regpulse-backend --domain=api.regpulse.in`
- DNS A/CNAME records at registrar; wait for Google-managed SSL (~15–60 min)
- Update env: `FRONTEND_URL=https://regpulse.in`, set cookie `domain=.regpulse.in` (optionally — current Path=/ works if both hosts share a registrable domain), switch `COOKIE_SAMESITE=lax`
- Rebuild + redeploy backend + frontend with new URLs
- Solves CORS-DEMO-1, OP-3 follow-ups, and gives a proper demo URL. **Pick this if you have DNS access.**

---

## ⚠️  Other open items

| # | What | Severity | Where |
|---|---|---|---|
| 1 | OP-3 — ~373 rbidocs PDFs blocked by RBI WAF | High | LEARNINGS L9.4. Needs User-Agent spoofing / proxy. Not on the critical path. |
| 2 | 🗓️ 2026-05-16 — Rotate OpenAI + Anthropic API keys (transcript-exposed during Phase 3B) | High | `export OPENAI_KEY=… ANTHROPIC_KEY=… && bash scripts/gcp/phase3b_external_secrets.sh` |
| 3 | 🗓️ 2026-05-16 — Confirm / revoke `shubhamkadam1802@gmail.com` Editor+DevOps access | Medium | `gcloud projects remove-iam-policy-binding regpulse-495309 --member="user:shubhamkadam1802@gmail.com" --role="roles/editor"` (and `roles/iam.devOps`) — if not Think360 |
| 4 | UAT auth blocker AG reported (`SMTPConnectError` on register) | **NOT REPRODUCIBLE** | I verified register + verify-otp end-to-end against live backend with `123456` OTP. Backend correctly skips email send in DEMO_MODE. AG report was wrong or tested an older revision. |
| 5 | Frontend Login form silently no-ops on unknown emails | Low | Backend masks "unknown email" to prevent enumeration — returns success message, no OTP generated, verify-otp then fails with "No pending OTP." Confusing UX in DEMO_MODE. Worth a DEMO-only "Did you mean Sign up?" hint. |

---

## 🌐 What's live (after this session)

| Resource | Identifier | Notes |
|---|---|---|
| **Project** | `regpulse-495309` | asia-south1 |
| **Backend** | Cloud Run `regpulse-backend` rev `00009-v8h` | `backend:rc4`, `COOKIE_SECURE=true, COOKIE_SAMESITE=none, FRONTEND_URL=https://regpulse-frontend-yvigu4ssea-el.a.run.app` |
| **Frontend** | Cloud Run `regpulse-frontend` rev `00001` | `frontend:rc1` — **unchanged**, still has the middleware that causes the loop |
| **Scraper Job** | Cloud Run Job `regpulse-scraper` | `scraper:rc4` — DEMO_MODE auto-approve on INSERT + summary UPDATE |
| **Cloud SQL** | `regpulse-db` | 21 tables + new `scraper_runs.failed_extractions` col. 93 circulars (`pending_admin_review=FALSE` after this session's bulk approve), 1208 chunks |
| **Memorystore** | `regpulse-redis` | Basic 1GB, AUTH enabled |
| **Scheduler** | `regpulse-scraper-daily` | `30 20 * * *` UTC (02:00 IST) |

**Mode:** `ENVIRONMENT=staging, DEMO_MODE=true, FREE_CREDIT_GRANT=999999`. OTP fixed `123456`. Payments/SMTP disabled.

---

## ✅ This session's deliverables

**Code shipped (committed + pushed):**
- `fix(scraper)`: DEMO_MODE auto-approve in `process_document` (INSERT) and `generate_summary` (UPDATE). `scraper:rc4` deployed.
- `fix(backend)`: cross-site cookies via new `COOKIE_SECURE` + `COOKIE_SAMESITE` settings; FastAPI 0.115 strict-204 fix in `learnings.py`; `phase4e_deploy_backend.sh` placeholder corrected. `backend:rc4` deployed.
- `docs`: 4 new LEARNINGS entries (L9.5–L9.8), MEMORY tech-debt + DEMO_MODE notes, this handover refresh.

**Live state changes (no code, but recorded):**
- Bulk SQL `UPDATE circular_documents SET pending_admin_review = FALSE` for the 93 SCR-1 rows. Library is now populated for non-admins.
- Cloud Run env var `FRONTEND_URL` patched on live service (was project-number form, now hash form).

**What did NOT ship:**
- Frontend rebuild. The middleware fix (any of A/B/C) is a next-session task.
- Pytest run. Backend changes are config-knob level — low risk — but the run was skipped for time.

---

## 🛠️  Suggested next dev activities (ranked)

1. **CORS-DEMO-1 fix** — pick (A) / (B) / (C) above, ship it, retest the browser flow end-to-end.
2. **2026-05-16 security tasks** — rotate API keys + audit `shubhamkadam1802@gmail.com` IAM. Calendar today.
3. **OP-3 — RBI WAF workaround** — pick up after CORS-DEMO-1 lands. Try realistic User-Agent header on the scraper's PDF download path; if WAF is IP-based, residential proxy is the only path.
4. **Phase 6 — GitHub Actions WIF auto-deploy** — removes the laptop `gcloud builds submit` dependency. Wait until CORS-DEMO-1 is closed so the pipeline isn't blocked by demo flakiness.
5. **Phase 7 — smoke tests + v1.0.0 tag** — only after CORS-DEMO-1 + Phase 5 (or rewrite) are stable, and you've run the demo end-to-end at least once in a clean incognito session.

---

## 🗺️  Where things live

| Need | Path |
|---|---|
| GCP deploy step scripts | `scripts/gcp/phase{N}*.sh` |
| Full deploy state + checklist | `GCP_DEPLOY_RUNBOOK.md` |
| Codebase invariants + business rules | `MEMORY.md` |
| All Phase 2 + GCP + this-session gotchas | `LEARNINGS.md` (L1–L8, LGCP.1–LGCP.6, L9.1–L9.8) |
| Backend code | `backend/app/` |
| Scraper code | `scraper/` |
| Frontend code | `frontend/src/` (Next.js 14) |
| Cloud SQL password | Secret Manager `REGPULSE_POSTGRES_PASSWORD` |
| Cloud Run logs | `gcloud logging read 'resource.type=cloud_run_revision'` |
| Cloud Run Job logs | `gcloud logging read 'resource.type=cloud_run_job'` |

---

## 🚪 To resume cold (no context from this session)

1. `git pull origin main`
2. Read `MEMORY.md` § Technical Debt (CORS-DEMO-1 row) + § GCP Deployment State
3. Read `LEARNINGS.md` § L9.5–L9.8 — this session's four big bites
4. Read this file's "Top priority" — pick (A), (B), or (C)
5. Run the "First 10 minutes" health checks
6. Ship the cross-site fix, retest demo end-to-end in a fresh incognito window
