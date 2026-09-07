#!/usr/bin/env bash
# RegPulse GCP Phase 4I — Cloud Scheduler trigger for the scraper Cloud Run Job.
# Schedule: 20:30 UTC daily = 02:00 IST (matches local Celery beat schedule).

set -uo pipefail

PROJECT=regpulse-495309
REGION=asia-south1
JOB=regpulse-scraper
SCHEDULER_JOB=regpulse-scraper-daily
SA="regpulse-runtime@${PROJECT}.iam.gserviceaccount.com"
JOB_URI="https://${REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${PROJECT}/jobs/${JOB}:run"

if gcloud scheduler jobs describe "${SCHEDULER_JOB}" --location="${REGION}" >/dev/null 2>&1; then
  echo "==> Updating existing scheduler job ${SCHEDULER_JOB}"
  ACTION=update
else
  echo "==> Creating scheduler job ${SCHEDULER_JOB} (20:30 UTC daily = 02:00 IST)"
  ACTION=create
fi

gcloud scheduler jobs ${ACTION} http "${SCHEDULER_JOB}" \
  --location="${REGION}" \
  --schedule="30 20 * * *" \
  --time-zone="UTC" \
  --uri="${JOB_URI}" \
  --http-method=POST \
  --oauth-service-account-email="${SA}" \
  --oauth-token-scope="https://www.googleapis.com/auth/cloud-platform" \
  --description="Daily RBI scrape: triggers regpulse-scraper Cloud Run Job" \
  --quiet

echo
echo "==> Scheduler ready. Next run:"
gcloud scheduler jobs describe "${SCHEDULER_JOB}" --location="${REGION}" --format='value(scheduleTime,state)' 2>&1
