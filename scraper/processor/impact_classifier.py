"""Impact level classification for RBI circulars using Claude Haiku.

Standalone scraper module. NEVER imports from backend/app/.
Classifies circulars as HIGH / MEDIUM / LOW impact based on content analysis.

- HIGH: new requirements, penalties, deadlines, mandatory compliance changes
- MEDIUM: amendments to existing directions, clarifications with action needed
- LOW: informational notices, press releases, FAQs, no action required
"""

from __future__ import annotations

import json

import anthropic
import structlog

from scraper.config import get_scraper_settings

logger: structlog.stdlib.BoundLogger = structlog.get_logger("regpulse.impact_classifier")

# ---------------------------------------------------------------------------
# Classification prompt
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """You are an RBI regulatory impact classifier. Given the title, department, \
and a summary/excerpt of an RBI circular, classify its impact level as exactly one of: \
HIGH, MEDIUM, or LOW.

Rules:
- HIGH: introduces new compliance requirements, penalties, mandatory deadlines, \
new regulations, capital adequacy changes, or enforcement actions
- MEDIUM: amends existing directions, issues clarifications requiring action, \
updates operational guidelines, or modifies existing norms
- LOW: informational notices, press releases, FAQs, data releases, \
or communications requiring no action from regulated entities

Respond with ONLY a JSON object: {"impact_level": "HIGH"|"MEDIUM"|"LOW", "reason": "one sentence"}
No other text."""


# ---------------------------------------------------------------------------
# ImpactClassifier
# ---------------------------------------------------------------------------


class ImpactClassifier:
    """Classify RBI circular impact using Claude Haiku."""

    def __init__(self) -> None:
        settings = get_scraper_settings()
        self._client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        self._model = settings.LLM_SUMMARY_MODEL  # claude-haiku-4-5-20251001

    def classify(
        self,
        title: str,
        summary: str = "",
        department: str = "",
    ) -> str:
        """Classify impact level of a circular.

        Args:
            title: Circular title / link text.
            summary: First ~500 chars of extracted text (or full text for short docs).
            department: Department name (e.g. "Department of Regulation").

        Returns:
            One of "HIGH", "MEDIUM", "LOW". Defaults to "MEDIUM" on any error.
        """
        user_msg = f"Title: {title}\nDepartment: {department}\nExcerpt: {summary[:1000]}"

        try:
            response = self._client.messages.create(
                model=self._model,
                max_tokens=150,
                system=_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_msg}],
            )
            raw = response.content[0].text.strip()

            # Claude may occasionally wrap valid JSON in markdown fences
            # or include a short explanation despite the prompt.
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError:
                cleaned = raw

                if cleaned.startswith("```"):
                    lines = cleaned.splitlines()
                    if lines and lines[0].startswith("```"):
                        lines = lines[1:]
                    if lines and lines[-1].strip() == "```":
                        lines = lines[:-1]
                    cleaned = "\n".join(lines).strip()

                try:
                    parsed = json.loads(cleaned)
                except json.JSONDecodeError:
                    # Last resort: extract the first JSON object.
                    start = cleaned.find("{")
                    end = cleaned.rfind("}")

                    if start == -1 or end <= start:
                        raise

                    parsed = json.loads(cleaned[start : end + 1])

            level = str(parsed.get("impact_level", "MEDIUM")).upper()
            reason = str(parsed.get("reason", ""))

            if level not in ("HIGH", "MEDIUM", "LOW"):
                level = "MEDIUM"

            logger.info(
                "impact_classified",
                title=title[:80],
                level=level,
                reason=reason,
                model=self._model,
            )
            return level

        except (json.JSONDecodeError, KeyError, IndexError) as exc:
            logger.warning(
                "impact_classification_parse_error",
                error=str(exc),
                title=title[:80],
                raw_response=raw[:500] if "raw" in locals() else "",
            )
            return "MEDIUM"
        except anthropic.APIError as exc:
            logger.error("impact_classification_api_error", error=str(exc), title=title[:80])
            return "MEDIUM"
        except Exception as exc:
            logger.error("impact_classification_unexpected_error", error=str(exc), title=title[:80])
            return "MEDIUM"
