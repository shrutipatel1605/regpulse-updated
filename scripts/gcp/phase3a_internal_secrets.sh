#!/usr/bin/env bash
# RegPulse GCP Phase 3A — Internal secrets (DB, Redis, JWT)
# - Creates the `regpulse` database inside the Cloud SQL instance
# - Generates a production JWT RSA-2048 keypair (saved to /tmp, pushed to Secret Manager)
# - Pushes DATABASE_URL, REDIS_URL, JWT keys, Postgres password, Redis AUTH to Secret Manager
# Safe to re-run: secrets are versioned (each run adds a new version, no destruction).

set -uo pipefail

PROJECT=regpulse-495309
REGION=asia-south1
LABELS=app=regpulse,env=production,owner=amit,managed-by=manual

if [[ ! -f /tmp/regpulse_db_pw ]]; then
  echo "ERROR: /tmp/regpulse_db_pw missing — Phase 2B was not run on this laptop." >&2
  exit 1
fi

echo "==> Fetching connection coordinates"
SQL_IP=$(gcloud sql instances describe regpulse-db --format='value(ipAddresses[0].ipAddress)')
REDIS_HOST=$(gcloud redis instances describe regpulse-redis --region=${REGION} --format='value(host)')
REDIS_PORT=$(gcloud redis instances describe regpulse-redis --region=${REGION} --format='value(port)')
REDIS_AUTH=$(gcloud redis instances get-auth-string regpulse-redis --region=${REGION} --format='value(authString)')
DB_PASSWORD=$(cat /tmp/regpulse_db_pw)

echo "    SQL=${SQL_IP}  REDIS=${REDIS_HOST}:${REDIS_PORT}"

echo "==> Creating 'regpulse' database in Cloud SQL"
if gcloud sql databases describe regpulse --instance=regpulse-db >/dev/null 2>&1; then
  echo "    (already exists, skipping)"
else
  gcloud sql databases create regpulse --instance=regpulse-db
fi

echo "==> Generating JWT RSA-2048 keypair"
openssl genrsa -out /tmp/regpulse_jwt_private.pem 2048 2>/dev/null
openssl rsa -in /tmp/regpulse_jwt_private.pem -pubout -out /tmp/regpulse_jwt_public.pem 2>/dev/null
chmod 600 /tmp/regpulse_jwt_private.pem /tmp/regpulse_jwt_public.pem

DATABASE_URL="postgresql+asyncpg://postgres:${DB_PASSWORD}@${SQL_IP}:5432/regpulse"
REDIS_URL="redis://default:${REDIS_AUTH}@${REDIS_HOST}:${REDIS_PORT}/0"

create_or_update_secret() {
  local name=$1
  local source=$2  # either "string:VALUE" or "file:PATH"
  local data_arg

  if [[ "$source" == string:* ]]; then
    local value="${source#string:}"
    if gcloud secrets describe "$name" >/dev/null 2>&1; then
      printf '%s' "$value" | gcloud secrets versions add "$name" --data-file=- >/dev/null
      echo "    + new version → $name"
    else
      printf '%s' "$value" | gcloud secrets create "$name" \
        --replication-policy=automatic \
        --labels=${LABELS} \
        --data-file=- >/dev/null
      echo "    + created     → $name"
    fi
  elif [[ "$source" == file:* ]]; then
    local path="${source#file:}"
    if gcloud secrets describe "$name" >/dev/null 2>&1; then
      gcloud secrets versions add "$name" --data-file="$path" >/dev/null
      echo "    + new version → $name"
    else
      gcloud secrets create "$name" \
        --replication-policy=automatic \
        --labels=${LABELS} \
        --data-file="$path" >/dev/null
      echo "    + created     → $name"
    fi
  fi
}

echo "==> Pushing internal secrets to Secret Manager"
create_or_update_secret REGPULSE_DATABASE_URL "string:${DATABASE_URL}"
create_or_update_secret REGPULSE_REDIS_URL "string:${REDIS_URL}"
create_or_update_secret REGPULSE_POSTGRES_PASSWORD "string:${DB_PASSWORD}"
create_or_update_secret REGPULSE_REDIS_AUTH_STRING "string:${REDIS_AUTH}"
create_or_update_secret REGPULSE_JWT_PRIVATE_KEY "file:/tmp/regpulse_jwt_private.pem"
create_or_update_secret REGPULSE_JWT_PUBLIC_KEY "file:/tmp/regpulse_jwt_public.pem"

echo
echo "==> Phase 3A complete. Secrets created/updated:"
gcloud secrets list --filter="name~REGPULSE_" --format="table(name,createTime,labels)"

echo
echo "==> Next: Phase 3B (external API keys — provide values via separate script)"
