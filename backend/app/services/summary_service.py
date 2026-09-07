"""Summary service — generate AI summaries for circulars.

Uses Claude Haiku (LLM_SUMMARY_MODEL) for cost efficiency.
Summaries require admin approval before public display.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog

from app.config import get_settings

if TYPE_CHECKING:
    import anthropic

logger = structlog.get_logger("regpulse.summary")

_SUMMARY_PROMPT = (
    "Summarize this RBI circular in 3-4 sentences for banking compliance "
    "professionals. Focus on: what changed, who is affected, key deadlines, "
    "and required actions. Be factual — do not add interpretation beyond "
    "what the text states.\n\nCircular text:\n{text}"
)


class SummaryService:
    """Generate AI summaries for circular documents."""

    def __init__(self, anthropic_client: anthropic.AsyncAnthropic) -> None:
        self._client = anthropic_client
        self._settings = get_settings()

    async def generate_summary(self, circular_text: str) -> str:
        """Generate a summary using Claude Haiku.

        Returns summary text. Caller is responsible for storing it
        and setting pending_admin_review=True.
        """
        prompt = _SUMMARY_PROMPT.format(text=circular_text[:8000])

        try:
            response = await self._client.messages.create(
                model=self._settings.LLM_SUMMARY_MODEL,
                max_tokens=512,
                messages=[{"role": "user", "content": prompt}],
            )
            summary = response.content[0].text.strip()
            logger.info("summary_generated", length=len(summary))
            return summary

        except Exception:
            logger.error("summary_generation_failed", exc_info=True)
            return "Summary generation failed. Please review manually."
