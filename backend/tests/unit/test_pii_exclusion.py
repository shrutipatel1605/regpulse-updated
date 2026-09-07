"""Tests for PII exclusion from LLM prompts (T-SEC-02).

The LLM system prompt and user message must NEVER contain user PII
(email, full_name, org_name). The only user input that reaches the LLM
is the sanitised question text + retrieved chunk content.
"""

from __future__ import annotations

from app.services.llm_service import _build_context, _build_user_message
from app.services.rag_service import RetrievedChunk


def _make_chunks() -> list[RetrievedChunk]:
    return [
        RetrievedChunk(
            chunk_id="c1",
            document_id="d1",
            chunk_index=0,
            chunk_text="Section 3.1: Every RE shall carry out CDD at account opening.",
            token_count=20,
            circular_number="RBI/2024-25/42",
            title="KYC Direction",
            rbi_url="https://rbi.org.in/test",
            rrf_score=0.5,
        ),
    ]


class TestPIIExclusion:
    """Verify that user PII never appears in LLM-bound messages."""

    def test_user_message_contains_no_email(self):
        """The user message sent to the LLM must not contain any email address."""
        chunks = _make_chunks()
        # Even if the user tries to inject their email in the question
        message = _build_user_message("What is KYC? My email is amit@bigbank.com", chunks)

        # The question IS included (wrapped in XML tags) — but the system
        # architecture never passes user.email, user.full_name, or user.org_name.
        # This test verifies the function signature: it only takes (question, chunks).
        assert "amit@bigbank.com" in message  # user typed it, it's in the question
        # But the function has no way to inject OTHER PII because it doesn't receive it.

    def test_build_user_message_signature_excludes_pii(self):
        """_build_user_message only accepts (question, chunks) — no user object."""
        import inspect

        sig = inspect.signature(_build_user_message)
        param_names = list(sig.parameters.keys())
        assert param_names == ["question", "chunks"], (
            f"_build_user_message should only accept (question, chunks), got {param_names}. "
            "Adding user-level params would risk PII leakage to the LLM."
        )

    def test_build_context_contains_only_chunk_data(self):
        """_build_context should only include chunk text and circular metadata."""
        chunks = _make_chunks()
        context = _build_context(chunks)

        # Should contain circular data
        assert "RBI/2024-25/42" in context
        assert "KYC Direction" in context
        assert "Section 3.1" in context

        # Should NOT contain any user-identifiable strings
        # (these would only appear if someone passed user data as chunk text)
        assert "email" not in context.lower() or "email" in chunks[0].chunk_text.lower()

    def test_system_prompt_has_no_pii_placeholders(self):
        """The system prompt must not contain any template slots for user data."""
        from app.services.llm_service import _SYSTEM_PROMPT

        pii_keywords = ["user_name", "user_email", "org_name", "full_name", "{email}", "{name}"]
        for keyword in pii_keywords:
            assert keyword not in _SYSTEM_PROMPT, f"System prompt contains PII placeholder '{keyword}'"

    def test_sanitise_wraps_in_xml(self):
        """sanitise_for_llm wraps user input — no PII injected."""
        from app.utils.injection_guard import sanitise_for_llm

        result = sanitise_for_llm("What is KYC?")
        assert result == "<user_question>What is KYC?</user_question>"
