#!/usr/bin/env bash
# RegPulse GCP Phase 3B — External API key secrets
# Reads OPENAI_KEY and ANTHROPIC_KEY from env vars (so they never hit disk in this repo).
# Razorpay + SMTP are pushed as DEMO_MODE-compatible placeholders.
#
# Usage:
#   export OPENAI_KEY="sk-..."
#   export ANTHROPIC_KEY="sk-ant-..."
#   bash scripts/gcp/phase3b_external_secrets.sh
#
# Safe to re-run: secrets are versioned (adds a new version each time, never destructive).

set -uo pipefail

LABELS=app=regpulse,env=production,owner=amit,managed-by=manual

if [[ -z "${OPENAI_KEY:-}" ]]; then
  echo "ERROR: OPENAI_KEY not set. Run: export OPENAI_KEY=\"sk-...\"" >&2
  exit 1
fi
if [[ -z "${ANTHROPIC_KEY:-}" ]]; then
  echo "ERROR: ANTHROPIC_KEY not set. Run: export ANTHROPIC_KEY=\"sk-ant-...\"" >&2
  exit 1
fi

create_or_update_secret() {
  local name=$1
  local value=$2
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
}

echo "==> Pushing external API keys to Secret Manager"
create_or_update_secret REGPULSE_OPENAI_API_KEY "$OPENAI_KEY"
create_or_update_secret REGPULSE_ANTHROPIC_API_KEY "$ANTHROPIC_KEY"

echo "==> Pushing DEMO_MODE placeholders (Razorpay + SMTP — not exercised when DEMO_MODE=true)"
create_or_update_secret REGPULSE_RAZORPAY_KEY_ID "rzp_test_demo_placeholder"
create_or_update_secret REGPULSE_RAZORPAY_KEY_SECRET "demo_razorpay_secret_placeholder"
create_or_update_secret REGPULSE_RAZORPAY_WEBHOOK_SECRET "demo_webhook_secret_placeholder"
create_or_update_secret REGPULSE_SMTP_USER "demo_smtp_user"
create_or_update_secret REGPULSE_SMTP_PASS "demo_smtp_pass"

echo
echo "==> Phase 3B complete. Full secret inventory:"
gcloud secrets list --filter="name~REGPULSE_" --format="table(name,createTime)"

echo
echo "==> Reminder: when going to live mode later, run:"
echo "      export OPENAI_KEY=... ANTHROPIC_KEY=... [real Razorpay + SMTP values]"
echo "    then re-run create_or_update_secret for each real value (adds new version, Cloud Run picks up on next revision)."
