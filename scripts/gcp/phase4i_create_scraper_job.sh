#!/usr/bin/env bash
# RegPulse GCP Phase 4I — Create Cloud Run Job for the scraper.
# Same image, but the Job override runs `python -m scraper.run_oneshot daily`
# which sets celery to eager mode and executes the full pipeline in-process.

set -uo pipefail

PROJECT=regpulse-495309
REGION=asia-south1
JOB=regpulse-scraper
IMAGE_TAG=${1:-rc1}
IMAGE="${REGION}-docker.pkg.dev/${PROJECT}/regpulse/scraper:${IMAGE_TAG}"
SA="regpulse-runtime@${PROJECT}.iam.gserviceaccount.com"

ENV_VARS=(
  "ENVIRONMENT=staging"
  "DEMO_MODE=true"
  'ADMIN_EMAIL_ALLOWLIST=["amit.das@think360.ai"]'
  "SMTP_HOST=smtp.demo.local"
  "SMTP_PORT=587"
  "SMTP_FROM=noreply@regpulse.in"
)
ENV_CSV=$(IFS=,; echo "${ENV_VARS[*]}")

SECRETS=(
  "DATABASE_URL=REGPULSE_DATABASE_URL:latest"
  "REDIS_URL=REGPULSE_REDIS_URL:latest"
  "OPENAI_API_KEY=REGPULSE_OPENAI_API_KEY:latest"
  "ANTHROPIC_API_KEY=REGPULSE_ANTHROPIC_API_KEY:latest"
  "SMTP_USER=REGPULSE_SMTP_USER:latest"
  "SMTP_PASS=REGPULSE_SMTP_PASS:latest"
)
SECRETS_CSV=$(IFS=,; echo "${SECRETS[*]}")

if gcloud run jobs describe "${JOB}" --region="${REGION}" >/dev/null 2>&1; then
  echo "==> Updating existing job ${JOB}"
  ACTION=update
else
  echo "==> Creating job ${JOB}"
  ACTION=create
fi

gcloud run jobs ${ACTION} "${JOB}" \
  --image="${IMAGE}" \
  --region="${REGION}" \
  --service-account="${SA}" \
  --vpc-connector=regpulse-connector \
  --vpc-egress=private-ranges-only \
  --memory=2Gi \
  --cpu=2 \
  --task-timeout=3600 \
  --max-retries=1 \
  --parallelism=1 \
  --tasks=1 \
  --command="python" \
  --args="-m,scraper.run_oneshot,daily" \
  --set-env-vars="${ENV_CSV}" \
  --set-secrets="${SECRETS_CSV}" \
  --labels=app=regpulse,env=production,owner=amit,managed-by=manual \
  --quiet

echo
echo "==> Job ready. Trigger manually with:"
echo "      gcloud run jobs execute ${JOB} --region=${REGION} --wait"
