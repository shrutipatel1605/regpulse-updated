#!/usr/bin/env bash
# RegPulse GCP Phase 4I-build — Build scraper image via Cloud Build.
# The scraper image runs the same Celery tasks but can be invoked one-shot
# with `python -m scraper.run_oneshot` (eager mode bypasses the broker).

set -uo pipefail

PROJECT=regpulse-495309
REGION=asia-south1
TAG=${1:-rc1}
IMAGE="${REGION}-docker.pkg.dev/${PROJECT}/regpulse/scraper:${TAG}"

echo "==> Submitting build for scraper → ${IMAGE}"
gcloud builds submit scraper/ \
  --tag "${IMAGE}" \
  --timeout=20m \
  --machine-type=E2_HIGHCPU_8 \
  --quiet

echo
echo "==> Build complete. Image: ${IMAGE}"
gcloud artifacts docker images describe "${IMAGE}" --format="value(image_summary.fully_qualified_digest,image_summary.upload_time)"
