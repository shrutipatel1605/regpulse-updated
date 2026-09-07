#!/usr/bin/env bash
# RegPulse GCP Phase 2 — Cloud SQL + Memorystore + budget alert
# Assumes 2A (VPC peering) and 2B (password file at /tmp/regpulse_db_pw) already done.
# Safe to re-run: already-exists errors are loud and clear, nothing is destructive.

set -uo pipefail

PROJECT=regpulse-495309
REGION=asia-south1
NETWORK=projects/${PROJECT}/global/networks/default
BILLING_ACCOUNT=0130B1-10E7BB-34EF9C
LABELS=app=regpulse,env=production,owner=amit,managed-by=manual

if [[ ! -f /tmp/regpulse_db_pw ]]; then
  echo "ERROR: /tmp/regpulse_db_pw missing — re-run Phase 2B first." >&2
  exit 1
fi

echo "==> 2C. Cloud SQL (regpulse-db, async)"
gcloud beta sql instances create regpulse-db \
  --database-version=POSTGRES_16 \
  --edition=ENTERPRISE \
  --tier=db-custom-2-4096 \
  --region=${REGION} \
  --availability-type=REGIONAL \
  --storage-size=50GB \
  --storage-type=SSD \
  --storage-auto-increase \
  --backup-start-time=18:30 \
  --backup-location=${REGION} \
  --enable-point-in-time-recovery \
  --retained-backups-count=7 \
  --network=${NETWORK} \
  --no-assign-ip \
  --root-password="$(cat /tmp/regpulse_db_pw)" \
  --labels=${LABELS} \
  --async

echo "==> 2D. Memorystore Redis (regpulse-redis, async)"
gcloud redis instances create regpulse-redis \
  --size=1 \
  --region=${REGION} \
  --tier=basic \
  --redis-version=redis_7_2 \
  --network=${NETWORK} \
  --enable-auth \
  --labels=${LABELS} \
  --async \
  --quiet

echo '==> 2E. Budget alert ($300/mo, 50/80/100% thresholds)'
gcloud billing budgets create \
  --billing-account=${BILLING_ACCOUNT} \
  --display-name="RegPulse monthly cap" \
  --budget-amount=300 \
  --threshold-rule=percent=50 \
  --threshold-rule=percent=80 \
  --threshold-rule=percent=100 \
  --filter-projects=projects/${PROJECT}

echo
echo "==> Phase 2 commands dispatched. Cloud SQL ~10-15 min, Redis ~5 min."
echo "==> Poll with: bash scripts/gcp/phase2_poll.sh"
