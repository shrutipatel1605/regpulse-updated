"""Prompt injection detection utility.

Checks user input against known injection patterns before sending to LLM.
On detection: raise PotentialInjectionError (400), no credit charge.
"""

from __future__ import annotations

import re

import structlog

from app.exceptions import PotentialInjectionError

logger = structlog.get_logger("regpulse.injection_guard")

INJECTION_PATTERNS: list[re.Pattern[str]] = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"ignore\b.{0,30}\binstructions",
        r"you are now",
        r"new (system |role |persona)",
        r"disregard (your |the )?",
        r"act as (if|a|an)",
        r"(override|bypass|forget) (your |the )?(instructions|rules|constraints)",
        r"<s>",
        r"</s>",
        r"\[INST\]",
        r"\[/INST\]",
        r"DAN mode",
        r"jailbreak",
    ]
]


def check_injection(text: str) -> None:
    """Raise PotentialInjectionError if text matches any injection pattern."""
    for pattern in INJECTION_PATTERNS:
        if pattern.search(text):
            logger.warning(
                "injection_detected",
                pattern=pattern.pattern,
                text_preview=text[:100],
            )
            raise PotentialInjectionError()


def sanitise_for_llm(text: str) -> str:
    """Wrap user input in XML tags for safe LLM consumption."""
    return f"<user_question>{text}</user_question>"
