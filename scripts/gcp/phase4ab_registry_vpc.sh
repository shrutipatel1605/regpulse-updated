#!/usr/bin/env bash
# RegPulse GCP Phase 4A+4B — Artifact Registry Docker repo + VPC Connector
# 4A: Docker repo for backend/frontend images (asia-south1)
# 4B: Serverless VPC Connector — bridges Cloud Run (outside VPC) to Cloud SQL+Redis (inside VPC private IPs)
# Safe to re-run: idempotent skips.

set -uo pipefail

PROJECT=regpulse-495309
REGION=asia-south1
REPO=regpulse
CONNECTOR=regpulse-connector
LABELS=app=regpulse,env=production,owner=amit,managed-by=manual

echo "==> 4A. Artifact Registry Docker repo: ${REGION}-docker.pkg.dev/${PROJECT}/${REPO}"
if gcloud artifacts repositories describe "${REPO}" --location="${REGION}" >/dev/null 2>&1; then
  echo "    (already exists, skipping)"
else
  gcloud artifacts repositories create "${REPO}" \
    --repository-format=docker \
    --location="${REGION}" \
    --description="RegPulse container images (backend + frontend)" \
    --labels=${LABELS}
fi

echo "==> 4A-extra. Configure docker to authenticate with AR"
gcloud auth configure-docker "${REGION}-docker.pkg.dev" --quiet

echo "==> 4B. VPC Connector: ${CONNECTOR} (async, ~3-5 min)"
if gcloud compute networks vpc-access connectors describe "${CONNECTOR}" --region="${REGION}" >/dev/null 2>&1; then
  echo "    (already exists, skipping)"
else
  # /28 range required for connector; non-overlapping with the private services range we reserved earlier
  gcloud compute networks vpc-access connectors create "${CONNECTOR}" \
    --region="${REGION}" \
    --network=default \
    --range=10.8.0.0/28 \
    --min-instances=2 \
    --max-instances=3 \
    --machine-type=e2-micro \
    --async
fi

echo
echo "==> 4A+4B dispatched. VPC Connector takes 3-5 min."
echo "==> Poll readiness with:"
echo "      gcloud compute networks vpc-access connectors describe ${CONNECTOR} --region=${REGION} --format='value(state)'"
echo "    (want: READY)"
