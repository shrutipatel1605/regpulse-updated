#!/usr/bin/env bash
# RegPulse GCP Phase 4C (reset) — drop the regpulse DB and re-run migrations cleanly.
# Use this when migrations have partially applied and the DB needs a fresh start.
# DESTRUCTIVE for the regpulse DB (acceptable here: schema only, no data yet).

set -uo pipefail

INSTANCE=regpulse-db

echo "==> Dropping 'regpulse' database (schema-only state, no data loss)"
if gcloud sql databases describe regpulse --instance=${INSTANCE} >/dev/null 2>&1; then
  gcloud sql databases delete regpulse --instance=${INSTANCE} --quiet
fi

echo "==> Recreating 'regpulse' database"
gcloud sql databases create regpulse --instance=${INSTANCE}

echo "==> Running migrations"
bash scripts/gcp/phase4c_migrations.sh
