"""Evals-specific conftest — minimal setup for anti-hallucination tests.

Overrides the parent conftest to avoid importing the full app dependencies
that are unnecessary for the eval test suite.
"""

from __future__ import annotations

import os
import sys

# Ensure the backend root (/app in Docker, or the backend dir locally) is on the path
_backend_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _backend_root not in sys.path:
    sys.path.insert(0, _backend_root)

# Set minimal env vars required by app.config.Settings
os.environ.update(
    {
        "DATABASE_URL": "sqlite+aiosqlite://",
        "REDIS_URL": "redis://localhost:6379/15",
        "JWT_PRIVATE_KEY": "test-private-key-not-used",
        "JWT_PUBLIC_KEY": "test-public-key-not-used",
        "OPENAI_API_KEY": "sk-test-fake",
        "ANTHROPIC_API_KEY": "sk-ant-test-fake",
        "RAZORPAY_KEY_ID": "rzp_test_fake",
        "RAZORPAY_KEY_SECRET": "rzp_secret_fake",
        "RAZORPAY_WEBHOOK_SECRET": "whsec_fake",
        "SMTP_HOST": "smtp.test.local",
        "SMTP_PORT": "587",
        "SMTP_USER": "test@test.local",
        "SMTP_PASS": "test-password",
        "SMTP_FROM": "noreply@regpulse.test",
        "FRONTEND_URL": "http://localhost:3000",
        "ENVIRONMENT": "dev",
    }
)
