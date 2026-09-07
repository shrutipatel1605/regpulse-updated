#!/usr/bin/env bash
# RegPulse GCP Phase 4C — Apply database migrations against Cloud SQL via Auth Proxy
# - Starts Cloud SQL Auth Proxy locally (uses Google's network — works even with private-IP-only instances)
# - Applies migrations 001-005 in order against the `regpulse` database
# - Verifies pgvector extension is enabled
# - Stops the proxy
# Safe to re-run: migrations use CREATE TABLE IF NOT EXISTS / idempotent patterns where possible.

set -uo pipefail

PROJECT=regpulse-495309
REGION=asia-south1
INSTANCE=regpulse-db
INSTANCE_CONN="${PROJECT}:${REGION}:${INSTANCE}"
LOCAL_PORT=5433  # avoid clashing with any local pg on 5432

if [[ ! -f /tmp/regpulse_db_pw ]]; then
  echo "ERROR: /tmp/regpulse_db_pw missing." >&2
  exit 1
fi

cleanup() {
  if [[ -n "${PROXY_PID:-}" ]] && kill -0 "${PROXY_PID}" 2>/dev/null; then
    echo "==> Stopping Cloud SQL Auth Proxy (PID ${PROXY_PID})"
    kill "${PROXY_PID}" 2>/dev/null || true
    wait "${PROXY_PID}" 2>/dev/null || true
  fi
}
trap cleanup EXIT

echo "==> Starting Cloud SQL Auth Proxy on localhost:${LOCAL_PORT} for ${INSTANCE_CONN}"
cloud-sql-proxy --port="${LOCAL_PORT}" "${INSTANCE_CONN}" >/tmp/regpulse_proxy.log 2>&1 &
PROXY_PID=$!
sleep 6  # let proxy authenticate + establish

if ! kill -0 "${PROXY_PID}" 2>/dev/null; then
  echo "ERROR: Cloud SQL Auth Proxy failed to start. Log:" >&2
  cat /tmp/regpulse_proxy.log >&2
  exit 1
fi

export PGPASSWORD="$(cat /tmp/regpulse_db_pw)"
PSQL_OPTS="-h localhost -p ${LOCAL_PORT} -U postgres -d regpulse -v ON_ERROR_STOP=1"

echo "==> Smoke test: SELECT version()"
psql ${PSQL_OPTS} -tA -c "SELECT version();" | head -1

echo "==> Enabling pgvector extension"
psql ${PSQL_OPTS} -c "CREATE EXTENSION IF NOT EXISTS vector;"

echo "==> Applying migrations in order"
for migration in backend/migrations/001_initial_schema.sql \
                 backend/migrations/002_sprint3_knowledge_graph.sql \
                 backend/migrations/003_sprint4_confidence.sql \
                 backend/migrations/004_sprint5.sql \
                 backend/migrations/005_sprint6_system_user.sql; do
  echo "    -> $migration"
  psql ${PSQL_OPTS} -f "$migration" 2>&1 | grep -vE '^(CREATE|ALTER|INSERT|GRANT|COMMENT|SET|BEGIN|COMMIT|NOTICE)' || true
done

echo "==> Verification"
echo "    Tables in regpulse DB:"
psql ${PSQL_OPTS} -tA -c "SELECT table_name FROM information_schema.tables WHERE table_schema='public' ORDER BY table_name;" | sed 's/^/      /'

echo
echo "==> Phase 4C complete. Migrations applied."
