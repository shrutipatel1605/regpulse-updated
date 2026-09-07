#!/usr/bin/env bash
# RegPulse GCP Phase 4G — Deploy frontend to Cloud Run.

set -uo pipefail

PROJECT=regpulse-495309
REGION=asia-south1
SERVICE=regpulse-frontend
IMAGE_TAG=${1:-rc1}
IMAGE="${REGION}-docker.pkg.dev/${PROJECT}/regpulse/frontend:${IMAGE_TAG}"

echo "==> Deploying ${SERVICE} from ${IMAGE}"

gcloud run deploy "${SERVICE}" \
  --image="${IMAGE}" \
  --region="${REGION}" \
  --platform=managed \
  --port=3000 \
  --memory=512Mi \
  --cpu=1 \
  --min-instances=1 \
  --max-instances=10 \
  --timeout=60 \
  --concurrency=80 \
  --allow-unauthenticated \
  --labels=app=regpulse,env=production,owner=amit,managed-by=manual \
  --quiet

echo
echo "==> Service URL:"
gcloud run services describe "${SERVICE}" --region="${REGION}" --format='value(status.url)'

echo
echo "==> Smoke test (10 sec warmup):"
sleep 10
URL=$(gcloud run services describe "${SERVICE}" --region="${REGION}" --format='value(status.url)')
echo "    curl ${URL}/"
curl -s -o /dev/null -w "HTTP %{http_code} in %{time_total}s\n" "${URL}/" || true
