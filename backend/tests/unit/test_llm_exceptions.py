"""Tests for LLM exception handling tightening (TD-10, Sprint 6).

Verifies that:
- TypeError / AttributeError propagate (not swallowed by API error handlers)
- Anthropic API errors trigger the OpenAI fallback path
- OpenAI fallback errors re-raise cleanly
- Streaming path handles API errors and parse failures correctly
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import anthropic
import openai
import pytest

from app.services.llm_service import LLMService
from app.services.rag_service import RetrievedChunk

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_chunks(n: int = 3) -> list[RetrievedChunk]:
    """Build N synthetic chunks for test use."""
    return [
        RetrievedChunk(
            chunk_id=f"chunk-{i}",
            document_id=f"doc-{i}",
            chunk_index=i,
            chunk_text=f"Section {i}: Test content about RBI circular {i}.",
            token_count=20,
            circular_number=f"RBI/2024-25/{40 + i}",
            title=f"Test Circular {i}",
            rbi_url=f"https://rbi.org.in/test/{i}",
            rrf_score=0.5,
        )
        for i in range(n)
    ]


def _mock_anthropic_client() -> AsyncMock:
    client = AsyncMock(spec=anthropic.AsyncAnthropic)
    client.messages = AsyncMock()
    client.messages.create = AsyncMock()
    client.messages.stream = MagicMock()
    return client


def _mock_openai_client() -> AsyncMock:
    client = AsyncMock(spec=openai.AsyncOpenAI)
    client.chat = MagicMock()
    client.chat.completions = MagicMock()
    client.chat.completions.create = AsyncMock()
    return client


def _valid_llm_response() -> str:
    return json.dumps(
        {
            "quick_answer": "Test answer",
            "detailed_interpretation": "Detailed test",
            "risk_level": "LOW",
            "confidence_score": 0.9,
            "consult_expert": False,
            "affected_teams": ["Compliance"],
            "citations": [
                {
                    "circular_number": "RBI/2024-25/40",
                    "verbatim_quote": "Test content",
                    "section_reference": "Section 0",
                }
            ],
            "recommended_actions": [],
        }
    )


# ---------------------------------------------------------------------------
# Tests: Exception propagation (TD-10 core guarantee)
# ---------------------------------------------------------------------------


class TestExceptionPropagation:
    """TypeError and AttributeError must NOT be caught by the API error handlers."""

    @pytest.mark.asyncio
    async def test_typeerror_in_anthropic_call_propagates(self):
        """A TypeError inside _call_anthropic must not fall through to fallback."""
        anthro = _mock_anthropic_client()
        oai = _mock_openai_client()

        # Simulate a programming bug: TypeError raised inside the Anthropic call
        anthro.messages.create.side_effect = TypeError("unexpected keyword argument 'bad_kwarg'")

        service = LLMService(anthropic_client=anthro, openai_client=oai)
        chunks = _make_chunks()

        with pytest.raises(TypeError, match="bad_kwarg"):
            await service.generate(question="What is KYC?", chunks=chunks)

        # OpenAI should NOT have been called — the error should propagate
        oai.chat.completions.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_attributeerror_propagates(self):
        """An AttributeError (e.g., response missing .content) must propagate."""
        anthro = _mock_anthropic_client()
        oai = _mock_openai_client()

        anthro.messages.create.side_effect = AttributeError("'NoneType' has no attribute 'content'")

        service = LLMService(anthropic_client=anthro, openai_client=oai)
        chunks = _make_chunks()

        with pytest.raises(AttributeError, match="content"):
            await service.generate(question="What is KYC?", chunks=chunks)

        oai.chat.completions.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_keyerror_propagates(self):
        """A KeyError in the Anthropic call path must propagate."""
        anthro = _mock_anthropic_client()
        oai = _mock_openai_client()

        anthro.messages.create.side_effect = KeyError("missing_field")

        service = LLMService(anthropic_client=anthro, openai_client=oai)
        chunks = _make_chunks()

        with pytest.raises(KeyError, match="missing_field"):
            await service.generate(question="What is KYC?", chunks=chunks)


# ---------------------------------------------------------------------------
# Tests: API error → fallback (should still work)
# ---------------------------------------------------------------------------


class TestAPIErrorFallback:
    """Anthropic API errors should trigger the OpenAI fallback path."""

    @pytest.mark.asyncio
    async def test_anthropic_api_error_triggers_openai_fallback(self):
        """When Anthropic returns an API error, fallback to OpenAI."""
        anthro = _mock_anthropic_client()
        oai = _mock_openai_client()

        # Anthropic fails with API error
        anthro.messages.create.side_effect = anthropic.APIConnectionError(request=MagicMock())

        # OpenAI succeeds
        oai_response = MagicMock()
        oai_response.choices = [MagicMock()]
        oai_response.choices[0].message.content = _valid_llm_response()
        oai.chat.completions.create.return_value = oai_response

        service = LLMService(anthropic_client=anthro, openai_client=oai)
        chunks = _make_chunks()

        result, model_used = await service.generate(question="What is KYC?", chunks=chunks)

        # OpenAI was called as fallback
        oai.chat.completions.create.assert_called_once()
        assert model_used == "gpt-4o"

    @pytest.mark.asyncio
    async def test_anthropic_timeout_triggers_fallback(self):
        """Anthropic timeout should trigger OpenAI fallback."""
        anthro = _mock_anthropic_client()
        oai = _mock_openai_client()

        anthro.messages.create.side_effect = anthropic.APITimeoutError(request=MagicMock())

        oai_response = MagicMock()
        oai_response.choices = [MagicMock()]
        oai_response.choices[0].message.content = _valid_llm_response()
        oai.chat.completions.create.return_value = oai_response

        service = LLMService(anthropic_client=anthro, openai_client=oai)
        chunks = _make_chunks()

        result, model_used = await service.generate(question="What is KYC?", chunks=chunks)
        assert model_used == "gpt-4o"

    @pytest.mark.asyncio
    async def test_both_apis_fail_raises(self):
        """When both Anthropic and OpenAI fail, the error is re-raised."""
        anthro = _mock_anthropic_client()
        oai = _mock_openai_client()

        anthro.messages.create.side_effect = anthropic.APIConnectionError(request=MagicMock())
        oai.chat.completions.create.side_effect = openai.APIConnectionError(request=MagicMock())

        service = LLMService(anthropic_client=anthro, openai_client=oai)
        chunks = _make_chunks()

        with pytest.raises(openai.APIConnectionError):
            await service.generate(question="What is KYC?", chunks=chunks)

    @pytest.mark.asyncio
    async def test_openai_typeerror_propagates_not_caught(self):
        """A TypeError in the OpenAI fallback path must propagate, not be caught."""
        anthro = _mock_anthropic_client()
        oai = _mock_openai_client()

        # Anthropic fails with API error → triggers fallback
        anthro.messages.create.side_effect = anthropic.APIConnectionError(request=MagicMock())
        # OpenAI has a programming bug
        oai.chat.completions.create.side_effect = TypeError("bad openai kwarg")

        service = LLMService(anthropic_client=anthro, openai_client=oai)
        chunks = _make_chunks()

        with pytest.raises(TypeError, match="bad openai kwarg"):
            await service.generate(question="What is KYC?", chunks=chunks)


# ---------------------------------------------------------------------------
# Tests: Streaming exception handling
# ---------------------------------------------------------------------------


class TestStreamingExceptions:
    """Streaming path should handle API errors but not swallow programming bugs."""

    @pytest.mark.asyncio
    async def test_stream_parse_failure_emits_safe_fallback(self):
        """When the streamed response is not valid JSON, emit safe fallback citations."""
        anthro = _mock_anthropic_client()
        oai = _mock_openai_client()

        # Mock the stream context manager to yield non-JSON text
        mock_stream = AsyncMock()
        mock_event = MagicMock()
        mock_event.type = "content_block_delta"
        mock_event.delta = MagicMock()
        mock_event.delta.text = "This is not JSON at all"

        async def _aiter_events():
            yield mock_event

        # ``__aiter__`` on a MagicMock is invoked with ``self`` as the first
        # positional arg; wrap the generator in a lambda so the extra arg is
        # absorbed.
        mock_stream.__aiter__ = lambda _self: _aiter_events()

        stream_cm = MagicMock()
        stream_cm.__aenter__ = AsyncMock(return_value=mock_stream)
        stream_cm.__aexit__ = AsyncMock(return_value=False)
        anthro.messages.stream.return_value = stream_cm

        service = LLMService(anthropic_client=anthro, openai_client=oai)
        chunks = _make_chunks()

        events = []
        async for event_type, data in service.generate_stream(question="What is KYC?", chunks=chunks):
            events.append((event_type, json.loads(data)))

        # Should have token event(s) + a citations event with safe fallback
        citation_events = [e for e in events if e[0] == "citations"]
        assert len(citation_events) == 1
        citations_data = citation_events[0][1]
        assert citations_data["consult_expert"] is True
        assert citations_data["citations"] == []
