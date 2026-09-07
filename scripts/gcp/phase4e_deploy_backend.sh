#!/usr/bin/env bash
# RegPulse GCP Phase 4E — Deploy backend to Cloud Run.
# - Image: backend:rc1 from Artifact Registry
# - Network: VPC Connector for private-IP egress to Cloud SQL + Redis
# - Identity: regpulse-runtime SA (reads secrets, connects to SQL, writes logs/metrics)
# - Secrets: 11 REGPULSE_* values mounted as env vars from Secret Manager
# - Mode: DEMO (ENVIRONMENT=staging is mandatory because config.py blocks DEMO_MODE=true with prod)
# Safe to re-run: creates a new revision, atomic traffic switch.

set -uo pipefail

PROJECT=regpulse-495309
REGION=asia-south1
SERVICE=regpulse-backend
IMAGE_TAG=${1:-rc1}
IMAGE="${REGION}-docker.pkg.dev/${PROJECT}/regpulse/backend:${IMAGE_TAG}"
SA="regpulse-runtime@${PROJECT}.iam.gserviceaccount.com"
FRONTEND_URL_PLACEHOLDER="https://regpulse-frontend-yvigu4ssea-el.a.run.app"  # actual hash-form URL of regpulse-frontend Cloud Run service

# Non-secret env vars (KEY=VALUE pairs; no commas inside values)
ENV_VARS=(
  "ENVIRONMENT=staging"
  "DEMO_MODE=true"
  "FREE_CREDIT_GRANT=999999"
  "FRONTEND_URL=${FRONTEND_URL_PLACEHOLDER}"
  'ADMIN_EMAIL_ALLOWLIST=["amit.das@think360.ai"]'
  "SMTP_HOST=smtp.demo.local"
  "SMTP_PORT=587"
  "SMTP_FROM=noreply@regpulse.in"
  "OTP_MAX_SENDS_PER_HOUR=100"
  "LLM_MODEL=claude-sonnet-4-20250514"
  "LLM_FALLBACK_MODEL=gpt-4o"
  "EMBEDDING_MODEL=text-embedding-3-large"
  # Cross-site cookies needed while frontend + backend are on different *.run.app
  # subdomains (PSL-separated). Switch to lax+secure once custom domains land in Phase 5.
  "COOKIE_SECURE=true"
  "COOKIE_SAMESITE=none"
)
ENV_CSV=$(IFS=,; echo "${ENV_VARS[*]}")

# Secret bindings (env_var_name=secret_name:version)
SECRETS=(
  "DATABASE_URL=REGPULSE_DATABASE_URL:latest"
  "REDIS_URL=REGPULSE_REDIS_URL:latest"
  "JWT_PRIVATE_KEY=REGPULSE_JWT_PRIVATE_KEY:latest"
  "JWT_PUBLIC_KEY=REGPULSE_JWT_PUBLIC_KEY:latest"
  "OPENAI_API_KEY=REGPULSE_OPENAI_API_KEY:latest"
  "ANTHROPIC_API_KEY=REGPULSE_ANTHROPIC_API_KEY:latest"
  "RAZORPAY_KEY_ID=REGPULSE_RAZORPAY_KEY_ID:latest"
  "RAZORPAY_KEY_SECRET=REGPULSE_RAZORPAY_KEY_SECRET:latest"
  "RAZORPAY_WEBHOOK_SECRET=REGPULSE_RAZORPAY_WEBHOOK_SECRET:latest"
  "SMTP_USER=REGPULSE_SMTP_USER:latest"
  "SMTP_PASS=REGPULSE_SMTP_PASS:latest"
)
SECRETS_CSV=$(IFS=,; echo "${SECRETS[*]}")

echo "==> Deploying ${SERVICE} from ${IMAGE}"

gcloud run deploy "${SERVICE}" \
  --image="${IMAGE}" \
  --region="${REGION}" \
  --platform=managed \
  --service-account="${SA}" \
  --vpc-connector=regpulse-connector \
  --vpc-egress=private-ranges-only \
  --port=8000 \
  --memory=1Gi \
  --cpu=1 \
  --min-instances=1 \
  --max-instances=10 \
  --timeout=300 \
  --concurrency=80 \
  --allow-unauthenticated \
  --set-env-vars="${ENV_CSV}" \
  --set-secrets="${SECRETS_CSV}" \
  --labels=app=regpulse,env=production,owner=amit,managed-by=manual \
  --quiet

echo
echo "==> Service URL:"
gcloud run services describe "${SERVICE}" --region="${REGION}" --format='value(status.url)'

echo
echo "==> Health check (give it 10 sec to warm up):"
sleep 10
URL=$(gcloud run services describe "${SERVICE}" --region="${REGION}" --format='value(status.url)')
echo "    curl ${URL}/api/v1/health"
curl -s -o /dev/null -w "HTTP %{http_code} in %{time_total}s\n" "${URL}/api/v1/health" || true
