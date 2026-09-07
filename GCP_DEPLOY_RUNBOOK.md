# GCP Deployment Runbook

**Project**: `regpulse-495309` | **Region**: `asia-south1` | **Billing**: `0130B1-10E7BB-34EF9C`
**Owner**: amit.das@think360.ai | **Last updated**: 2026-05-14

Live, resumable record of the GCP deployment. If you're picking this up in a new session, read this first, check what's done, then continue from the first incomplete phase.

---

## Status

- [x] Phase 0 — Local prereqs (gcloud CLI + auth)
- [x] Phase 1 — APIs enabled on project
- [x] Phase 2 — Data layer (Cloud SQL + Memorystore + budget alert) — `regpulse-db` @ `10.81.0.2`, `regpulse-redis` @ `10.45.36.187:6379`
- [x] Phase 3 — Secrets + JWT keypair (13 secrets in Secret Manager, runtime SA `regpulse-runtime@regpulse-495309.iam.gserviceaccount.com`)
- [x] Phase 4 — First manual Cloud Run deploy (substantially complete; 4H/4I deferred)
  - [x] 4A. Artifact Registry Docker repo (`asia-south1-docker.pkg.dev/regpulse-495309/regpulse`)
  - [x] 4B. VPC Connector (`regpulse-connector`, /28 at 10.8.0.0/28)
  - [x] 4C. Migrations applied (19 tables; ANN indexes deferred — see LEARNINGS LGCP.5)
  - [x] 4D. Backend image: `regpulse/backend:rc2` (sha256:559e4399…)
  - [x] 4E. Backend deployed: `https://regpulse-backend-yvigu4ssea-el.a.run.app` (revision 00004)
  - [x] 4F. Frontend image: `regpulse/frontend:rc1` (sha256:0a1c3fd9…)
  - [x] 4G. Frontend deployed: `https://regpulse-frontend-yvigu4ssea-el.a.run.app` (revision 00001)
  - [ ] 4H. Celery worker GCE — DEFERRED (only needed when leaving DEMO_MODE; scheduled tasks for auto-renewal/low-credit emails)
  - [x] 4I. Scraper Cloud Run Job + Cloud Scheduler
    - Image: `regpulse/scraper:rc1` (sha256:52dc5199…)
    - Job: `regpulse-scraper` (2 vCPU, 2Gi, 1h timeout, VPC connector, runtime SA, eager-mode one-shot)
    - Scheduler: `regpulse-scraper-daily` runs at `30 20 * * *` UTC (= 02:00 IST)
    - One-shot entrypoint: `python -m scraper.run_oneshot daily` (eager-mode bypasses broker)
- [ ] Phase 5 — Custom domain + TLS
- [ ] Phase 6 — GitHub Actions auto-deploy via WIF
- [x] Phase 6.2 — Observability: Scraper Dashboard & Log-based metrics deployed (`scripts/gcp/phase6_setup_observability.sh`)
- [ ] Phase 7 — Smoke test + v1.0.0 cut

## Open items

- `shubhamkadam1802@gmail.com` has `roles/editor` + `roles/iam.devOps` on `regpulse-495309`. Personal Gmail; confirm Think360 contractor (then migrate to work email) or revoke both bindings.

## Conventions

- Resource names: `regpulse-*` prefix
- Standard labels: `app=regpulse,env=production,owner=amit,managed-by=manual` (drop `managed-by=manual` once under Terraform)
- All Cloud SQL and Redis use private IP only (no public endpoint)
- Cost ceiling alerting at $300/mo (50/80/100%)

---

## Phase 0 — Local prereqs (one-time, per laptop)

```bash
brew install --cask google-cloud-sdk
source "$(brew --prefix)/share/google-cloud-sdk/path.zsh.inc"
source "$(brew --prefix)/share/google-cloud-sdk/completion.zsh.inc"

gcloud auth login
gcloud auth application-default login

gcloud config set project regpulse-495309
gcloud config set compute/region asia-south1
gcloud config set compute/zone asia-south1-a
gcloud auth application-default set-quota-project regpulse-495309
```

## Phase 1 — APIs (one-time, per project)

```bash
gcloud services enable \
  compute.googleapis.com \
  run.googleapis.com \
  sqladmin.googleapis.com \
  sql-component.googleapis.com \
  redis.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com \
  cloudbuild.googleapis.com \
  iamcredentials.googleapis.com \
  cloudresourcemanager.googleapis.com \
  vpcaccess.googleapis.com \
  servicenetworking.googleapis.com \
  cloudscheduler.googleapis.com \
  cloudbilling.googleapis.com
```

## Phase 2 — Data layer + budget alert

```bash
# 2A. VPC private services peering (one-time)
gcloud compute addresses create regpulse-private-services \
  --global --purpose=VPC_PEERING --prefix-length=16 \
  --network=default \
  --description="Private services access for Cloud SQL + Memorystore"

gcloud services vpc-peerings connect \
  --service=servicenetworking.googleapis.com \
  --ranges=regpulse-private-services --network=default

# 2B. Postgres root password (temp; moves to Secret Manager in Phase 3)
openssl rand -base64 32 | tr -d '/+=' | head -c 32 > /tmp/regpulse_db_pw && chmod 600 /tmp/regpulse_db_pw

# 2C/2D/2E — run as one script (terminal paste of multi-line gcloud commands is unreliable on macOS zsh)
bash scripts/gcp/phase2_resume.sh

# Notes baked into the script:
#   - `gcloud beta sql instances create` (GA track doesn't expose --labels for SQL)
#   - `--edition=ENTERPRISE` (this project's Cloud SQL default is Enterprise Plus, which rejects custom tiers)
#   - All three commands dispatch and return; provisioning runs async

# 2F. Poll until ready (SQL=RUNNABLE, Redis=READY) — re-run every 2-3 min
bash scripts/gcp/phase2_poll.sh
```

When both report ready, capture the connection coordinates and proceed to Phase 3.

```bash
# Record for Phase 3 (paste into a scratch note)
SQL_PRIVATE_IP=$(gcloud sql instances describe regpulse-db --format="value(ipAddresses[0].ipAddress)")
SQL_CONNECTION_NAME=$(gcloud sql instances describe regpulse-db --format="value(connectionName)")
REDIS_HOST=$(gcloud redis instances describe regpulse-redis --region=asia-south1 --format="value(host)")
REDIS_PORT=$(gcloud redis instances describe regpulse-redis --region=asia-south1 --format="value(port)")
REDIS_AUTH=$(gcloud redis instances get-auth-string regpulse-redis --region=asia-south1)
echo "SQL=$SQL_PRIVATE_IP CONN=$SQL_CONNECTION_NAME REDIS=$REDIS_HOST:$REDIS_PORT AUTH=$REDIS_AUTH"
```

## Phase 3 — Secrets + JWT keypair

Split into three sub-steps:

```bash
# 3A. Internal secrets (DB URL, Redis URL, JWT keys, passwords) — fully automated
bash scripts/gcp/phase3a_internal_secrets.sh

# 3B. External API keys (OpenAI, Anthropic, Razorpay, SMTP) — needs values from you
# Script generated after values are provided

# 3C. Cloud Run runtime service account + IAM grants — automated after 3B
# Script generated after 3B completes
```

## Phase 4 — First manual Cloud Run deploy (TODO)

Artifact Registry repo → Cloud Build images → Cloud Run services (backend, frontend) → GCE e2-small for Celery → Cloud Run Job + Cloud Scheduler for scraper.

## Phase 5 — Custom domain + TLS (TODO)

Decide final domain. Cloud Run domain mapping → DNS update at registrar → wait for managed cert.

## Phase 6 — GitHub Actions auto-deploy (TODO)

Workload Identity Federation pool + provider → deploy service account → GitHub repo secrets → wire `.github/workflows/deploy.yml` to fire on `v*` tags.

## Phase 7 — Smoke test + v1.0.0 (TODO)

Full end-to-end: register → OTP → ask → cited answer → action items. Razorpay test payment + webhook. Scraper trigger. Admin login. Rate limits. LLM fallback. k6 load. Tag `v1.0.0`.
