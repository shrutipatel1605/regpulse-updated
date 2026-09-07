#!/usr/bin/env bash
# RegPulse GCP Phase 3C — Cloud Run runtime service account + IAM grants
# Creates a dedicated SA that Cloud Run will use, then grants:
#   - secretmanager.secretAccessor on every REGPULSE_* secret (so the SA can read them at runtime)
#   - cloudsql.client (so the SA can connect to Cloud SQL via the proxy/private IP)
#   - logging.logWriter + monitoring.metricWriter (so structured logs and metrics flow)
# Safe to re-run: all bindings are idempotent.

set -uo pipefail

PROJECT=regpulse-495309
SA_NAME=regpulse-runtime
SA_EMAIL="${SA_NAME}@${PROJECT}.iam.gserviceaccount.com"

echo "==> Creating runtime service account: ${SA_EMAIL}"
if gcloud iam service-accounts describe "${SA_EMAIL}" >/dev/null 2>&1; then
  echo "    (already exists, skipping)"
else
  gcloud iam service-accounts create "${SA_NAME}" \
    --display-name="RegPulse Cloud Run runtime" \
    --description="Runtime identity for backend + frontend Cloud Run services"
fi

echo "==> Granting project-level roles (cloudsql.client, logging.logWriter, monitoring.metricWriter)"
for ROLE in roles/cloudsql.client roles/logging.logWriter roles/monitoring.metricWriter; do
  gcloud projects add-iam-policy-binding "${PROJECT}" \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="${ROLE}" \
    --condition=None \
    --quiet >/dev/null
  echo "    + ${ROLE}"
done

echo "==> Granting secretAccessor on each REGPULSE_* secret"
SECRETS=$(gcloud secrets list --filter="name~REGPULSE_" --format="value(name)")
for SECRET in ${SECRETS}; do
  gcloud secrets add-iam-policy-binding "${SECRET}" \
    --member="serviceAccount:${SA_EMAIL}" \
    --role=roles/secretmanager.secretAccessor \
    --condition=None \
    --quiet >/dev/null
  echo "    + ${SECRET}"
done

echo
echo "==> Phase 3C complete. Runtime SA ready: ${SA_EMAIL}"
echo "==> Next: Phase 4 (build images + deploy Cloud Run, attaching this SA)"
