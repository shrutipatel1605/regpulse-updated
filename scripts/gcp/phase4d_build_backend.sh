#!/usr/bin/env bash
# RegPulse GCP Phase 4D — Build backend image via Cloud Build and push to Artifact Registry.
# ~3-5 min on Cloud Build's default machine; logs stream live to terminal.

set -uo pipefail

PROJECT=regpulse-495309
REGION=asia-south1
REPO=regpulse
TAG=${1:-rc1}
IMAGE="${REGION}-docker.pkg.dev/${PROJECT}/${REPO}/backend:${TAG}"

echo "==> Submitting build for backend → ${IMAGE}"
gcloud builds submit backend/ \
  --tag "${IMAGE}" \
  --timeout=15m \
  --quiet

echo
echo "==> Build complete. Image: ${IMAGE}"
echo "==> Verifying image in Artifact Registry:"
gcloud artifacts docker images describe "${IMAGE}" --format="value(image_summary.fully_qualified_digest,image_summary.upload_time)"
