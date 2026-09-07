"""Work-email validator service.

Blocks free/disposable email providers using a static blocklist and validates
domain MX records via async DNS lookup. Only domain names are logged — never
full email addresses (PII protection).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

import aiodns
import structlog

logger = structlog.get_logger(__name__)

# Blocklist path relative to repo root: config/free_email_blocklist.json
_BLOCKLIST_PATH = Path(__file__).resolve().parents[3] / "config" / "free_email_blocklist.json"


@dataclass(frozen=True, slots=True)
class ValidationResult:
    """Result of a work-email validation check."""

    is_valid: bool
    reason: str
    requires_review: bool = False


class WorkEmailValidator:
    """Validates that an email belongs to a legitimate work domain.

    Checks performed (in order):
    1. Domain extracted and lowercased.
    2. Checked against a frozen set of free/disposable email providers.
    3. Async MX record lookup (3 s timeout) to verify the domain accepts mail.

    Domains that pass the blocklist but have no MX records are flagged with
    ``requires_review=True`` so an admin can approve them later.
    """

    _MX_TIMEOUT: ClassVar[float] = 3.0

    def __init__(self, blocklist_path: Path | None = None) -> None:
        path = blocklist_path or _BLOCKLIST_PATH
        raw: list[str] = json.loads(path.read_text(encoding="utf-8"))
        self._blocked_domains: frozenset[str] = frozenset(d.lower().strip() for d in raw)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def validate(self, email: str) -> ValidationResult:
        """Return a ``ValidationResult`` for the given email address."""
        domain = self._extract_domain(email)
        if not domain:
            return ValidationResult(is_valid=False, reason="Invalid email format")

        # 1. Blocklist check
        if domain in self._blocked_domains:
            logger.info("email_blocked_free_provider", domain=domain)
            return ValidationResult(
                is_valid=False,
                reason="Free/disposable email providers are not allowed",
            )

        # 2. MX record check
        mx_valid = await self._check_mx(domain)
        if mx_valid is None:
            # DNS lookup failed/timed out — flag for admin review
            logger.warning("email_mx_lookup_failed", domain=domain)
            return ValidationResult(
                is_valid=True,
                reason="MX lookup inconclusive; flagged for admin review",
                requires_review=True,
            )
        if not mx_valid:
            logger.info("email_no_mx_records", domain=domain)
            return ValidationResult(
                is_valid=False,
                reason="Domain does not have valid MX records",
            )

        logger.info("email_validated", domain=domain)
        return ValidationResult(is_valid=True, reason="OK")

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_domain(email: str) -> str | None:
        """Extract and lowercase the domain part of an email address."""
        try:
            _, domain = email.rsplit("@", 1)
        except ValueError:
            return None
        domain = domain.lower().strip()
        if not domain or "." not in domain:
            return None
        return domain

    async def _check_mx(self, domain: str) -> bool | None:
        """Query MX records for *domain*. Returns True/False or None on error."""
        resolver = aiodns.DNSResolver(timeout=self._MX_TIMEOUT)
        try:
            records = await resolver.query(domain, "MX")
            return len(records) > 0
        except aiodns.error.DNSError:
            # NXDOMAIN, NOTIMP, etc. — domain doesn't exist or has no MX
            return False
        except Exception:  # noqa: BLE001
            # Timeout or unexpected failure — inconclusive
            return None
