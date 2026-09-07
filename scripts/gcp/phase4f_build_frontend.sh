#!/usr/bin/env bash
# RegPulse GCP Phase 4F — Build frontend image via Cloud Build.
# Bakes NEXT_PUBLIC_API_URL (points at the deployed backend Cloud Run service).

set -uo pipefail

PROJECT=regpulse-495309
REGION=asia-south1
TAG=${1:-rc1}
IMAGE="${REGION}-docker.pkg.dev/${PROJECT}/regpulse/frontend:${TAG}"

# Pull current backend URL from Cloud Run
BACKEND_URL=$(gcloud run services describe regpulse-backend --region="${REGION}" --format='value(status.url)')
if [[ -z "${BACKEND_URL}" ]]; then
  echo "ERROR: regpulse-backend service not found in ${REGION}. Deploy backend (Phase 4E) first." >&2
  exit 1
fi
API_URL="${BACKEND_URL}/api/v1"

echo "==> Building frontend → ${IMAGE}"
echo "    Backend API URL baked in: ${API_URL}"

gcloud builds submit frontend/ \
  --config=frontend/cloudbuild.yaml \
  --substitutions=_API_URL="${API_URL}",_IMAGE="${IMAGE}" \
  --timeout=20m \
  --quiet

echo
echo "==> Build complete. Image: ${IMAGE}"
gcloud artifacts docker images describe "${IMAGE}" --format="value(image_summary.fully_qualified_digest,image_summary.upload_time)"
