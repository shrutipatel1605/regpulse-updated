#!/usr/bin/env bash
# RegPulse Launch Check — verify all services are healthy before go-live.
# Usage: ./scripts/launch_check.sh [BASE_URL]

set -e

BASE_URL="${1:-http://localhost:8000}"
FRONTEND_URL="${2:-http://localhost:3000}"
PASS=0
FAIL=0

check() {
    local name="$1"
    local url="$2"
    local expected_status="${3:-200}"

    status=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "$url" 2>/dev/null || echo "000")

    if [ "$status" = "$expected_status" ]; then
        echo "  [PASS] $name ($status)"
        PASS=$((PASS + 1))
    else
        echo "  [FAIL] $name (got $status, expected $expected_status)"
        FAIL=$((FAIL + 1))
    fi
}

echo "=================================================="
echo "RegPulse Launch Check"
echo "Backend: $BASE_URL"
echo "Frontend: $FRONTEND_URL"
echo "=================================================="
echo ""

echo "--- Backend Health ---"
check "Liveness probe" "$BASE_URL/api/v1/health"
check "Readiness probe" "$BASE_URL/api/v1/health/ready"

echo ""
echo "--- API Endpoints ---"
check "Circulars list" "$BASE_URL/api/v1/circulars"
check "Departments facet" "$BASE_URL/api/v1/circulars/departments"
check "Tags facet" "$BASE_URL/api/v1/circulars/tags"
check "Subscription plans" "$BASE_URL/api/v1/subscriptions/plans"
check "API docs" "$BASE_URL/api/v1/docs"

echo ""
echo "--- Frontend ---"
check "Landing page" "$FRONTEND_URL"
check "Library page" "$FRONTEND_URL/library"

echo ""
echo "--- Auth (expect 401/403) ---"
check "Questions (no auth)" "$BASE_URL/api/v1/questions" "403"
check "Admin dashboard (no auth)" "$BASE_URL/api/v1/admin/dashboard" "403"

echo ""
echo "=================================================="
echo "Results: $PASS passed, $FAIL failed"
echo "=================================================="

if [ "$FAIL" -gt 0 ]; then
    echo "LAUNCH CHECK FAILED"
    exit 1
else
    echo "ALL CHECKS PASSED"
    exit 0
fi
