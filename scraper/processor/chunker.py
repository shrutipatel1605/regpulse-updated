"""Sentence-aware text chunker for RBI circulars.

Standalone scraper module. NEVER imports from backend/app/.
Splits extracted circular text into overlapping chunks suitable for
embedding and RAG retrieval. Uses tiktoken cl100k_base for accurate
token counting.

Key design decisions:
- Page markers ("--- Page N ---") are stripped before chunking — they must
  NOT appear in chunk text or count toward token budgets.
- Sentence-aware splitting preserves semantic boundaries.
- 512-token max per chunk, 64-token overlap between consecutive chunks.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import structlog
import tiktoken

logger: structlog.stdlib.BoundLogger = structlog.get_logger("regpulse.chunker")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DEFAULT_MAX_TOKENS = 512
_DEFAULT_OVERLAP_TOKENS = 64

# Page marker pattern from PDFExtractor — strip these before chunking
_PAGE_MARKER_RE = re.compile(r"---\s*Page\s+\d+\s*---")

# Sentence boundary pattern: split on period/question/exclamation followed by
# whitespace (or end of string), but not on common abbreviations
_SENTENCE_SPLIT_RE = re.compile(
    r"(?<=[.?!])\s+(?=[A-Z\d(\"'])"  # Sentence end followed by capital/digit/quote
    r"|(?<=\n)\s*(?=\d+\.?\s)"  # Numbered list items: "1. ...", "2 ..."
    r"|(?<=\n)\s*(?=[(\[a-z]+[)\]])"  # Lettered list items: "(a) ...", "(i) ..."
    r"|\n{2,}",  # Double newline (paragraph break)
)


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class TextChunk:
    """A single text chunk ready for embedding."""

    chunk_index: int
    text: str
    token_count: int


# ---------------------------------------------------------------------------
# Token counting
# ---------------------------------------------------------------------------

# Lazy-loaded encoder (expensive to initialise, reuse across calls)
_encoder: tiktoken.Encoding | None = None
_encoder_failed = False


def _get_encoder() -> tiktoken.Encoding | None:
    """Get the cl100k_base tiktoken encoder (cached).

    Returns None if the encoder cannot be loaded (e.g. network-restricted
    environments where tiktoken BPE data is unavailable).
    """
    global _encoder, _encoder_failed  # noqa: PLW0603
    if _encoder is not None:
        return _encoder
    if _encoder_failed:
        return None
    try:
        _encoder = tiktoken.get_encoding("cl100k_base")
        return _encoder
    except Exception:
        _encoder_failed = True
        logger.warning("tiktoken_unavailable", fallback="char_estimate")
        return None


def count_tokens(text: str) -> int:
    """Count tokens using tiktoken cl100k_base encoding.

    Falls back to character-based estimate (~4 chars/token for English)
    when tiktoken BPE data is unavailable.
    """
    enc = _get_encoder()
    if enc is not None:
        return len(enc.encode(text))
    # Fallback: ~4 chars per token for English text (conservative estimate)
    return max(1, len(text) // 4)


# ---------------------------------------------------------------------------
# TextChunker
# ---------------------------------------------------------------------------


class TextChunker:
    """Split circular text into overlapping chunks for embedding.

    - Strips page markers before processing.
    - Splits on sentence boundaries.
    - Each chunk is ≤ max_tokens (default 512).
    - Consecutive chunks overlap by overlap_tokens (default 64).
    - Token counting uses tiktoken cl100k_base (same as OpenAI embeddings).
    """

    def __init__(
        self,
        max_tokens: int = _DEFAULT_MAX_TOKENS,
        overlap_tokens: int = _DEFAULT_OVERLAP_TOKENS,
    ) -> None:
        self.max_tokens = max_tokens
        self.overlap_tokens = overlap_tokens

    def chunk(self, raw_text: str) -> list[TextChunk]:
        """Split raw_text into overlapping chunks.

        Args:
            raw_text: Full text from PDFExtractor (may include "--- Page N ---" markers).

        Returns:
            List of TextChunk with chunk_index, text, and token_count.
        """
        # Step 1: Strip page markers
        clean_text = self._strip_page_markers(raw_text)

        # Step 2: Normalise whitespace
        clean_text = self._normalise_whitespace(clean_text)

        if not clean_text.strip():
            return []

        # Step 3: Split into sentences
        sentences = self._split_sentences(clean_text)

        if not sentences:
            return []

        # Step 4: Merge sentences into chunks respecting token budget
        chunks = self._merge_into_chunks(sentences)

        logger.info(
            "chunking_complete",
            input_chars=len(raw_text),
            clean_chars=len(clean_text),
            sentence_count=len(sentences),
            chunk_count=len(chunks),
            avg_tokens=round(
                sum(c.token_count for c in chunks) / len(chunks), 1
            )
            if chunks
            else 0,
        )

        return chunks

    # ------------------------------------------------------------------
    # Private methods
    # ------------------------------------------------------------------

    @staticmethod
    def _strip_page_markers(text: str) -> str:
        """Remove '--- Page N ---' markers and surrounding blank lines."""
        text = _PAGE_MARKER_RE.sub("", text)
        # Collapse multiple blank lines left by marker removal
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text

    @staticmethod
    def _normalise_whitespace(text: str) -> str:
        """Normalise whitespace while preserving paragraph structure."""
        lines: list[str] = []
        for line in text.split("\n"):
            stripped = line.strip()
            lines.append(stripped)
        # Rejoin — preserve double newlines as paragraph breaks
        result = "\n".join(lines)
        # Collapse runs of 3+ newlines to 2
        result = re.sub(r"\n{3,}", "\n\n", result)
        return result.strip()

    @staticmethod
    def _split_sentences(text: str) -> list[str]:
        """Split text into sentence-like segments.

        Uses regex-based splitting on sentence boundaries, numbered items,
        and paragraph breaks. Preserves the text content of each segment.
        """
        # Split on sentence boundaries
        parts = _SENTENCE_SPLIT_RE.split(text)
        sentences: list[str] = []
        for part in parts:
            stripped = part.strip()
            if stripped:
                sentences.append(stripped)
        return sentences

    def _merge_into_chunks(self, sentences: list[str]) -> list[TextChunk]:
        """Merge sentences into chunks with overlap.

        Greedy forward pass: accumulate sentences until adding the next would
        exceed max_tokens. Then start a new chunk, rewinding by overlap_tokens
        worth of sentences.
        """
        chunks: list[TextChunk] = []

        # Pre-compute token counts for each sentence
        sentence_tokens: list[int] = [count_tokens(s) for s in sentences]

        chunk_idx = 0
        start = 0  # Index of first sentence in current chunk

        while start < len(sentences):
            # Greedily add sentences until we exceed the budget
            current_tokens = 0
            end = start

            while end < len(sentences):
                added = sentence_tokens[end]
                # Account for space/separator between sentences (~1 token)
                separator_cost = 1 if end > start else 0
                if current_tokens + added + separator_cost > self.max_tokens and end > start:
                    break
                current_tokens += added + separator_cost
                end += 1

            # Handle single sentence exceeding max_tokens — include it anyway
            if end == start:
                end = start + 1
                current_tokens = sentence_tokens[start]

            # Build chunk text
            chunk_text = " ".join(sentences[start:end])
            token_count = count_tokens(chunk_text)

            chunks.append(
                TextChunk(
                    chunk_index=chunk_idx,
                    text=chunk_text,
                    token_count=token_count,
                )
            )
            chunk_idx += 1

            # If we've consumed all sentences, done
            if end >= len(sentences):
                break

            # Find overlap start: rewind from end to find where overlap begins
            overlap_start = end
            overlap_sum = 0
            while overlap_start > start:
                overlap_start -= 1
                overlap_sum += sentence_tokens[overlap_start] + 1
                if overlap_sum >= self.overlap_tokens:
                    break

            # Next chunk starts at overlap_start (rewind for overlap)
            start = overlap_start if overlap_start > start else end

        return chunks
