"""Unit tests for snippet service.

Covers the pure-function payload builder. The DB-coupled bits
(create_snippet, revoke_snippet) are exercised by the live integration
smoke test in CI; the assertions here lock down the redaction guarantee
that the full detailed_interpretation NEVER leaves snippet_service.
"""

from __future__ import annotations

from types import SimpleNamespace

from app.services.snippet_service import (
    CITATION_QUOTE_MAX_CHARS,
    EXPERT_FALLBACK_TEXT,
    QUICK_ANSWER_MAX_WORDS,
    _build_safe_snippet,
    _generate_slug,
    _truncate_words,
)


def _question(
    *,
    quick_answer: str | None = "Banks must update KYC every 2 years for high-risk customers.",
    citations: list | None = None,
    detailed_interpretation: str = "FULL DETAILED ANSWER THAT MUST NEVER APPEAR PUBLICLY",
):
    return SimpleNamespace(
        quick_answer=quick_answer,
        answer_text=detailed_interpretation,
        citations=(
            citations
            if citations is not None
            else [
                {
                    "circular_number": "RBI/2024-25/42",
                    "verbatim_quote": "Section 5.2: Periodic updation of KYC...",
                    "section_reference": "5.2",
                }
            ]
        ),
    )


class TestSlugGeneration:
    def test_generated_slug_length(self) -> None:
        slug = _generate_slug()
        assert 10 <= len(slug) <= 16

    def test_slugs_are_unique(self) -> None:
        slugs = {_generate_slug() for _ in range(100)}
        assert len(slugs) == 100


class TestTruncateWords:
    def test_under_limit_unchanged(self) -> None:
        assert _truncate_words("one two three", 10) == "one two three"

    def test_over_limit_truncated_with_ellipsis(self) -> None:
        text = " ".join(["word"] * 100)
        out = _truncate_words(text, 10)
        assert out.endswith("…")
        assert len(out.split()) == 10

    def test_word_boundary_respected(self) -> None:
        assert _truncate_words("alpha beta gamma delta", 2) == "alpha beta…"


class TestSafeSnippetBuilder:
    def test_normal_question_returns_quick_answer(self) -> None:
        q = _question()
        snippet, top, expert = _build_safe_snippet(q)

        assert snippet == q.quick_answer
        assert expert is False
        assert top is not None
        assert top["circular_number"] == "RBI/2024-25/42"

    def test_detailed_interpretation_never_leaks(self) -> None:
        """Hard guarantee: the full answer text must NEVER appear in the snippet."""
        q = _question()
        snippet, top, _expert = _build_safe_snippet(q)

        assert "FULL DETAILED ANSWER" not in snippet
        if top:
            assert "FULL DETAILED ANSWER" not in str(top)

    def test_zero_citations_triggers_expert_fallback(self) -> None:
        q = _question(citations=[])
        snippet, top, expert = _build_safe_snippet(q)

        assert expert is True
        assert snippet == EXPERT_FALLBACK_TEXT
        assert top is None

    def test_missing_quick_answer_triggers_expert_fallback(self) -> None:
        q = _question(quick_answer=None)
        snippet, _top, expert = _build_safe_snippet(q)

        assert expert is True
        assert snippet == EXPERT_FALLBACK_TEXT

    def test_long_quick_answer_truncated(self) -> None:
        q = _question(quick_answer=" ".join(["regulation"] * 200))
        snippet, _top, _expert = _build_safe_snippet(q)

        assert len(snippet.split()) <= QUICK_ANSWER_MAX_WORDS + 1  # +1 for ellipsis token
        assert snippet.endswith("…")

    def test_long_citation_quote_truncated(self) -> None:
        q = _question(
            citations=[
                {
                    "circular_number": "RBI/2024-25/42",
                    "verbatim_quote": "x" * 500,
                    "section_reference": "5.2",
                }
            ]
        )
        _snippet, top, _expert = _build_safe_snippet(q)

        assert top is not None
        assert len(top["verbatim_quote"]) <= CITATION_QUOTE_MAX_CHARS + 1

    def test_malformed_citations_ignored_gracefully(self) -> None:
        q = _question(citations=["not a dict", None, 42])  # type: ignore[list-item]
        snippet, top, _expert = _build_safe_snippet(q)

        # First entry isn't a dict, so top_citation is None — but quick_answer still flows
        assert top is None
        assert snippet == q.quick_answer

    def test_citation_without_circular_number_dropped(self) -> None:
        q = _question(citations=[{"verbatim_quote": "no circular_number"}])
        _snippet, top, _expert = _build_safe_snippet(q)
        assert top is None
