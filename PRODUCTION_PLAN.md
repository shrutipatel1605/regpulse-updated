# RegPulse — Production Deployment Plan

## Current State

| Area | Status |
|------|--------|
| **Codebase** | 50/50 prompts + Sprints 1–8 shipped. All pre-launch code gaps closed (10/12 PRD v3 gaps). |
| **CI** | GitHub Actions all green on `main` at `56d628f` (lint + test + build) |
| **Deploy pipeline** | Stub — `.github/workflows/deploy.yml` written but Cloud Run services not provisioned |
| **Infra** | No GCP resources provisioned, no GitHub environments configured |
| **Branch protection** | Not possible (private repo, free GitHub plan) |
| **Tests** | 106 unit tests passing, 21 golden eval tests, 8 retrieval eval tests, k6 load tests |
| **Secrets management** | `.env` file only, no Secret Manager yet |

---

## Phase 1: Pre-Flight (Local Prep)

### 1.1 Sync local with remote
```
git pull origin main
```

### 1.2 Close stale PR #4
`sprint-3/authentication` — auth was merged via later PRs. Close it.

### 1.3 Resolve known tech debt before deploy

| ID | Issue | Action |
|----|-------|--------|
| TD-02 | No graceful shutdown | ✅ Fixed (Sprint 6) — SIGTERM handlers |
| TD-04 | `admin_audit_log.actor_id` NOT NULL | ✅ Fixed (Sprint 6) — System user seeded |
| TD-01 | Scraper writes directly to backend DB | Acceptable for v1, document as known risk; isolate in Sprint 9+ |
| G-01 | DPDP Account Deletion | ✅ Fixed (Sprint 7) |
| G-02 | DPDP Data Export | ✅ Fixed (Sprint 7) |
| G-09 | PDF export w/ QR codes | ✅ Fixed (Sprint 8) |

---

## Phase 2: Infrastructure Provisioning (GCP asia-south1)

### 2.1 Database
- **Cloud SQL for PostgreSQL 16** with `pgvector` extension
  - Instance: `db-custom-2-4096` (2 vCPU, 4GB) — start small, scale on load
  - High availability: **Yes** (financial/compliance data)
  - Storage: 50GB SSD, auto-scaling enabled
  - Automated backups: 7-day retention, point-in-time recovery
  - Run initial migration: `alembic upgrade head`
  - Enable `pgvector` extension: `CREATE EXTENSION vector;`

### 2.2 Cache
- **Memorystore for Redis** (Basic tier, 1GB)
- Same VPC via VPC Serverless Access connector

### 2.3 Container Registry
- **Artifact Registry** — 1 Docker repo: `asia-south1-docker.pkg.dev/$PROJECT/regpulse`
  - Images: `backend`, `frontend`
  - Cleanup policy: keep last 10 images per tag

### 2.4 Compute (Cloud Run + GCE)

| Service | Platform | CPU | Memory | Min/Max Instances | Port |
|---------|----------|-----|--------|-------------------|------|
| backend | Cloud Run | 1 vCPU | 1 GB | 1 / 10 | 8000 |
| frontend | Cloud Run | 0.5 vCPU | 512 MB | 1 / 10 | 3000 |
| celery worker + beat | GCE e2-small | 0.5 vCPU | 2 GB | 1 (always-on) | — |
| scraper (daily crawl) | Cloud Run Job | 1 vCPU | 1 GB | 0 (triggered) | — |

**Why GCE for Celery?** Cloud Run is request-driven; Celery requires a long-running process to consume from the Redis broker. An `e2-small` instance runs the worker + beat scheduler persistently.

**Why Cloud Run Job for scraper?** The daily crawl is a batch operation triggered by Cloud Scheduler — no persistent process needed.

### 2.5 Networking
- Cloud Run services get built-in HTTPS + load balancing (no separate ALB needed)
- Cloud Run → Cloud SQL via **Cloud SQL Auth Proxy** (built-in Cloud Run connector)
- Cloud Run → Memorystore via **VPC Serverless Access connector**
- GCE instance in same VPC — direct access to Cloud SQL and Memorystore
- Health checks: `/api/v1/health` (backend), `/` (frontend)

### 2.6 DNS
- Cloud DNS (or external Cloudflare) for domain
- Custom domain mapping on Cloud Run services

---

## Phase 3: Secrets & Configuration

### 3.1 Google Secret Manager
Move all `.env` values to Secret Manager:

```
projects/$PROJECT/secrets/REGPULSE_DATABASE_URL
projects/$PROJECT/secrets/REGPULSE_REDIS_URL
projects/$PROJECT/secrets/REGPULSE_JWT_PRIVATE_KEY
projects/$PROJECT/secrets/REGPULSE_JWT_PUBLIC_KEY
projects/$PROJECT/secrets/REGPULSE_OPENAI_API_KEY
projects/$PROJECT/secrets/REGPULSE_ANTHROPIC_API_KEY
projects/$PROJECT/secrets/REGPULSE_RAZORPAY_KEY_ID
projects/$PROJECT/secrets/REGPULSE_RAZORPAY_KEY_SECRET
projects/$PROJECT/secrets/REGPULSE_RAZORPAY_WEBHOOK_SECRET
projects/$PROJECT/secrets/REGPULSE_SMTP_USER
projects/$PROJECT/secrets/REGPULSE_SMTP_PASS
```

Secrets are mounted as environment variables in Cloud Run revisions and via the GCE metadata/startup script.

### 3.2 GitHub Secrets (for deploy workflow)
```
GCP_PROJECT_ID
GCP_WORKLOAD_IDENTITY_PROVIDER
GCP_SERVICE_ACCOUNT
```

Uses **Workload Identity Federation** — no long-lived service account keys.

### 3.3 Generate production RSA keypair for JWT
```bash
openssl genrsa -out jwt_private.pem 2048
openssl rsa -in jwt_private.pem -pubout -out jwt_public.pem
```

### 3.4 Production env values
```
ENVIRONMENT=prod
DEMO_MODE=false
FRONTEND_URL=https://regpulse.in
ADMIN_EMAIL_ALLOWLIST=amit@yourcompany.com
FREE_CREDIT_GRANT=5
```

---

## Phase 4: CI/CD Hardening

### 4.1 Complete the deploy workflow
The deploy workflow (`.github/workflows/deploy.yml`) uses:
- `google-github-actions/auth@v2` (Workload Identity Federation)
- `google-github-actions/setup-gcloud@v2`
- `google-github-actions/deploy-cloudrun@v2`

Build + push images to Artifact Registry, deploy Cloud Run services on `v*` tags.

### 4.2 Add staging environment
- Separate Cloud Run services with `-staging` suffix
- Deploy on push to `main` (auto), prod only on `v*` tags (manual)
- Separate Secret Manager secrets: `REGPULSE_STAGING_*`

### 4.3 Add integration test job to CI
- Spin up docker-compose in GitHub Actions
- Run tests against real Postgres + Redis (not SQLite mocks)
- This catches issues the SQLite-based unit tests miss

### 4.4 Upgrade GitHub plan (recommended)
- Enables branch protection on `main` (require PR reviews, passing CI)
- Enables required status checks

---

## Phase 5: Security Hardening

| Item | Action | Priority |
|------|--------|----------|
| HTTPS everywhere | Cloud Run provides built-in HTTPS with Google-managed TLS certificates | **Critical** |
| Custom domain TLS | Google-managed SSL certificate via Cloud Run domain mapping | **Critical** |
| CORS | Set `FRONTEND_URL=https://regpulse.in` (exact origin) | **Critical** |
| Rate limiting | Confirm slowapi works behind Cloud Run (use `X-Forwarded-For`) | **High** |
| Cloud Armor | Attach via external HTTPS LB for WAF rules (defer if direct Cloud Run URLs acceptable for beta) | **High** |
| Razorpay webhook | Restrict via Cloud Armor rules or application-level IP check | **Medium** |
| DB encryption | Cloud SQL encryption at rest (enabled by default) | **Medium** |
| Redis AUTH | Enable AUTH on Memorystore | **Medium** |
| Dependency audit | `pip audit` + `pnpm audit` in CI | **Medium** |
| CSP headers | Add `Content-Security-Policy` in Next.js config | **Medium** |

---

## Phase 6: Observability

### 6.1 Logging
- Backend already uses `structlog` (JSON) — Cloud Run stdout auto-ingested into **Cloud Logging**
- No log group configuration needed (zero-config; structlog JSON is auto-parsed)

### 6.2 Monitoring
- **Cloud Monitoring alert policies:**
  - Cloud Run CPU/Memory utilization > 80%
  - Cloud Run 5xx rate > 1%
  - Cloud SQL connections > 80% of max
  - Cloud Run instance count < minimum
- **Custom metrics** (via Cloud Monitoring or Prometheus):
  - LLM latency (p50, p95, p99)
  - RAG retrieval quality (empty results rate)
  - Credit deductions/hour
  - Scraper success/failure rate

### 6.3 Alerting
- Cloud Monitoring notification channels → email/Slack for critical alerts
- PagerDuty or Opsgenie for on-call (later)

---

## Phase 7: Data & Compliance

| Item | Action |
|------|--------|
| **Backups** | Cloud SQL automated backups (7-day retention), test restore procedure |
| **Migration plan** | Script to seed initial circulars — run scraper against RBI once infra is up. Also run `python backend/scripts/backfill_question_embeddings.py` once post-deploy so the /questions/suggestions endpoint has data for pre-Sprint 8 rows. |
| **DPDP Act compliance** | ✅ Implemented (Sprint 7) — `POST /account/request-deletion-otp`, `PATCH /account/delete`, `GET /account/export`. Verify end-to-end in Phase C smoke tests. |
| **Data retention** | Define policy: how long to keep questions, analytics events, audit logs |
| **Audit trail** | `admin_audit_log` already exists — verify it covers all admin mutations |

---

## Phase 8: Testing Checklist (Pre-Launch)

- [ ] Full pipeline: register → verify OTP → ask question → get cited answer → action items
- [ ] Subscription: create order → Razorpay payment → webhook → credits added
- [ ] Scraper: manual run → circulars indexed → searchable in library
- [ ] Admin: login → dashboard → review queue → approve summary
- [ ] Auth edge cases: expired token refresh, concurrent sessions, logout
- [ ] Rate limiting: verify 429 responses under load
- [ ] LLM fallback: disable Anthropic key → verify GPT-4o fallback fires
- [ ] Empty state: new user with no circulars indexed
- [ ] Load test: 50 concurrent users (k6)

---

## Recommended Deployment Order

```
1. Create GCP project, enable APIs (Cloud Run, Cloud SQL, Memorystore, Artifact Registry, Secret Manager, Cloud Scheduler)
2. Provision Cloud SQL instance, enable pgvector extension
3. Provision Memorystore Redis instance
4. Create Artifact Registry Docker repo
5. Store secrets in Secret Manager
6. Build and push Docker images to Artifact Registry (manual first deploy)
7. Deploy Cloud Run services (backend + frontend)
8. Provision GCE e2-small for celery worker + beat
9. Create Cloud Run Job + Cloud Scheduler trigger for daily scraper crawl
10. Run alembic migrations
11. Run initial scraper crawl to seed circulars
12. Smoke test all endpoints
13. Map custom domain to Cloud Run services (Google-managed TLS)
14. Set up Workload Identity Federation for GitHub Actions
15. Complete deploy workflow, tag v0.1.0 for first automated deploy
```

---

## Terraform Modules (future)

The following modules will be authored in a follow-up sprint:

```
terraform/
  cloud-run.tf          # backend + frontend services
  cloud-sql.tf          # PostgreSQL 16 + pgvector
  memorystore.tf        # Redis
  artifact-registry.tf  # Docker repo
  secret-manager.tf     # All REGPULSE_* secrets
  iam-wif.tf            # Workload Identity Federation for GitHub Actions
  cloud-scheduler.tf    # Daily scraper trigger
  compute-celery.tf     # GCE e2-small for celery worker + beat
```

---

## Cost Estimate (Monthly, asia-south1)

| Resource | Spec | ~Cost |
|----------|------|-------|
| Cloud SQL PostgreSQL | db-custom-2-4096, HA, 50GB SSD | $75 |
| Memorystore Redis | Basic tier, 1GB | $35 |
| Cloud Run backend | 1 vCPU / 1GB, min-instances=1 | $25 |
| Cloud Run frontend | 0.5 vCPU / 512MB, min-instances=1 | $12 |
| GCE e2-small (celery) | 0.5 vCPU / 2GB, always-on | $15 |
| Artifact Registry | Storage + transfer | $3 |
| Cloud Armor (if used) | 1 policy | $8 |
| Cloud Logging/Monitoring | Within free tier | $0 |
| **Total** | | **~$173/mo** |

Note: `min-instances=1` is deliberate — scale-to-zero adds cold-start latency to `/api/v1/ask` SSE which the anti-hallucination/confidence UX depends on.

Plus variable costs: OpenAI embeddings (~$0.13/1M tokens), Anthropic LLM calls (~$3/1M input tokens), SMTP (free tier for low volume).
