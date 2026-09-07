#!/usr/bin/env bash
# Retry Cloud SQL creation only — use after diagnosing/fixing the VPC peering.
# Assumes /tmp/regpulse_db_pw exists.

set -uo pipefail

PROJECT=regpulse-495309
REGION=asia-south1
NETWORK=projects/${PROJECT}/global/networks/default
LABELS=app=regpulse,env=production,owner=amit,managed-by=manual

if [[ ! -f /tmp/regpulse_db_pw ]]; then
  echo "ERROR: /tmp/regpulse_db_pw missing." >&2
  exit 1
fi

echo "==> Retry 2C. Cloud SQL (regpulse-db, async)"
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
  --async \
  --quiet
