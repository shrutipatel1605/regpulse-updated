#!/usr/bin/env bash
# Poll Cloud SQL + Memorystore readiness. Run repeatedly until both report READY/RUNNABLE.

set -uo pipefail

REGION=asia-south1

echo "== Cloud SQL (regpulse-db) =="
gcloud sql instances describe regpulse-db --format="value(name,state,ipAddresses[0].ipAddress)" 2>/dev/null || echo "(not yet visible)"

echo
echo "== Memorystore Redis (regpulse-redis) =="
gcloud redis instances describe regpulse-redis --region=${REGION} --format="value(name,state,host,port)" 2>/dev/null || echo "(not yet visible)"
