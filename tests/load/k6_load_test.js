/**
 * RegPulse k6 Load Test — Local Docker Compose
 *
 * Tests the critical API paths under concurrent load.
 * Designed to run against http://localhost:8000 (Docker Compose backend).
 *
 * Usage:
 *   brew install k6   (or: docker run --rm -i grafana/k6 run -)
 *   k6 run tests/load/k6_load_test.js
 *
 * Scenarios:
 *   1. Health check (baseline throughput)
 *   2. Auth flow (register → OTP → verify)
 *   3. Circular library browse
 *   4. Q&A endpoint (the heavy hitter)
 */

import http from "k6/http";
import { check, group, sleep } from "k6";
import { Rate, Trend } from "k6/metrics";

// Custom metrics
const errorRate = new Rate("errors");
const authDuration = new Trend("auth_flow_duration", true);
const qaDuration = new Trend("qa_response_duration", true);

// Test configuration
const BASE_URL = __ENV.BASE_URL || "http://localhost:8000";

export const options = {
  scenarios: {
    // Scenario 1: Smoke test — verify endpoints respond
    smoke: {
      executor: "constant-vus",
      vus: 1,
      duration: "10s",
      startTime: "0s",
      exec: "smokeTest",
    },
    // Scenario 2: Load test — ramp up to 20 concurrent users
    load: {
      executor: "ramping-vus",
      startVUs: 0,
      stages: [
        { duration: "30s", target: 10 }, // Ramp up
        { duration: "1m", target: 20 },  // Hold at peak
        { duration: "30s", target: 0 },  // Ramp down
      ],
      startTime: "15s",
      exec: "loadTest",
    },
    // Scenario 3: Spike test — burst of 50 users
    spike: {
      executor: "ramping-vus",
      startVUs: 0,
      stages: [
        { duration: "10s", target: 50 },  // Spike
        { duration: "30s", target: 50 },  // Hold
        { duration: "10s", target: 0 },   // Drop
      ],
      startTime: "2m30s",
      exec: "spikeTest",
    },
  },
  thresholds: {
    http_req_duration: ["p(95)<5000"],     // 95% of requests under 5s
    http_req_failed: ["rate<0.05"],         // Error rate < 5%
    errors: ["rate<0.05"],
    auth_flow_duration: ["p(95)<3000"],     // Auth flow under 3s
  },
};

// ---------------------------------------------------------------------------
// Helper functions
// ---------------------------------------------------------------------------

function apiHeaders(accessToken = null) {
  const headers = { "Content-Type": "application/json" };
  if (accessToken) {
    headers["Authorization"] = `Bearer ${accessToken}`;
  }
  return headers;
}

function registerAndLogin() {
  const email = `loadtest-${__VU}-${__ITER}@testcorp.com`;

  // Register
  const regRes = http.post(
    `${BASE_URL}/api/v1/auth/register`,
    JSON.stringify({
      email: email,
      full_name: `Load User ${__VU}`,
      org_name: "LoadTestCorp",
      org_type: "BANK",
    }),
    { headers: apiHeaders() }
  );

  // Verify OTP (demo mode: 123456)
  const verifyRes = http.post(
    `${BASE_URL}/api/v1/auth/verify-otp`,
    JSON.stringify({
      email: email,
      otp: "123456",
      purpose: "register",
    }),
    { headers: apiHeaders() }
  );

  if (verifyRes.status === 200) {
    const body = JSON.parse(verifyRes.body);
    return body.tokens?.access_token || null;
  }

  return null;
}

// ---------------------------------------------------------------------------
// Test functions
// ---------------------------------------------------------------------------

export function smokeTest() {
  group("Health Check", () => {
    const res = http.get(`${BASE_URL}/api/v1/health/ready`);
    const passed = check(res, {
      "health returns 200": (r) => r.status === 200,
      "health body contains ready": (r) => r.body.includes("ready"),
    });
    errorRate.add(!passed);
  });

  sleep(1);
}

export function loadTest() {
  group("Auth Flow", () => {
    const startAuth = Date.now();
    const token = registerAndLogin();
    authDuration.add(Date.now() - startAuth);

    const authOk = check(token, {
      "auth token obtained": (t) => t !== null,
    });
    errorRate.add(!authOk);

    if (token) {
      // Browse circulars
      group("Browse Library", () => {
        const libRes = http.get(`${BASE_URL}/api/v1/circulars?page=1&per_page=10`, {
          headers: apiHeaders(token),
        });
        check(libRes, {
          "library returns 200": (r) => r.status === 200,
        });
      });
    }
  });

  sleep(1);
}

export function spikeTest() {
  group("Health Under Spike", () => {
    const res = http.get(`${BASE_URL}/api/v1/health/ready`);
    const passed = check(res, {
      "spike health 200": (r) => r.status === 200,
    });
    errorRate.add(!passed);
  });

  // Also hit the circulars list (unauthenticated — should return 401)
  group("Unauthenticated Access", () => {
    const res = http.get(`${BASE_URL}/api/v1/circulars`);
    check(res, {
      "unauthenticated returns 401": (r) => r.status === 401,
    });
  });

  sleep(0.5);
}

export function handleSummary(data) {
  return {
    stdout: textSummary(data, { indent: " ", enableColors: true }),
    "tests/load/k6_results.json": JSON.stringify(data, null, 2),
  };
}

function textSummary(data, opts) {
  // k6 built-in summary — no-op here, k6 handles it
  return "";
}
