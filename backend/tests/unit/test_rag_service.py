"""Unit tests for RAG service — RRF fusion, deduplication, utilities."""

from __future__ import annotations

import uuid

from app.services.rag_service import (
    RAGService,
    RetrievedChunk,
    _hash_question,
    _normalise_question,
)


def _make_chunk(**overrides) -> RetrievedChunk:
    defaults = {
        "chunk_id": str(uuid.uuid4()),
        "document_id": str(uuid.uuid4()),
        "chunk_index": 0,
        "chunk_text": "Test chunk text",
        "token_count": 50,
        "circular_number": "RBI/2024-25/01",
        "title": "Test Circular",
        "rbi_url": "https://rbi.org.in/test",
    }
    defaults.update(overrides)
    return RetrievedChunk(**defaults)


class TestNormalisation:
    def test_normalise_strips_and_lowercases(self) -> None:
        result = _normalise_question("  What are KYC  requirements?  ")
        assert result == "what are kyc requirements?"

    def test_hash_deterministic(self) -> None:
        h1 = _hash_question("hello")
        h2 = _hash_question("hello")
        assert h1 == h2
        assert len(h1) == 64


class TestRRFFusion:
    def test_fuse_single_source(self) -> None:
        chunks = [_make_chunk() for _ in range(3)]
        fused = RAGService._rrf_fuse(chunks, [])
        assert len(fused) == 3
        assert fused[0].rrf_score >= fused[1].rrf_score

    def test_fuse_overlap_boosts_score(self) -> None:
        shared_id = str(uuid.uuid4())
        c1 = _make_chunk(chunk_id=shared_id)
        c2 = _make_chunk(chunk_id=shared_id)
        c_other = _make_chunk()

        fused = RAGService._rrf_fuse([c1, c_other], [c2])
        # shared_id should have higher score
        shared = [c for c in fused if c.chunk_id == shared_id]
        assert len(shared) == 1
        assert shared[0].rrf_score > 1.0 / 60  # More than single source

    def test_fuse_empty(self) -> None:
        assert RAGService._rrf_fuse([], []) == []


class TestDeduplication:
    def test_max_per_doc(self) -> None:
        doc_id = str(uuid.uuid4())
        chunks = [
            _make_chunk(
                chunk_id=str(uuid.uuid4()),
                document_id=doc_id,
                chunk_index=i,
            )
            for i in range(5)
        ]
        result = RAGService._deduplicate(chunks, max_per_doc=2)
        assert len(result) == 2

    def test_different_docs_preserved(self) -> None:
        chunks = [_make_chunk() for _ in range(5)]  # Different doc_ids
        result = RAGService._deduplicate(chunks, max_per_doc=2)
        assert len(result) == 5


class TestRetrievedChunk:
    def test_to_dict(self) -> None:
        chunk = _make_chunk()
        d = chunk.to_dict()
        assert "chunk_id" in d
        assert "document_id" in d
        assert "circular_number" in d

    def test_get_circular_numbers(self) -> None:
        rag = RAGService.__new__(RAGService)
        chunks = [
            _make_chunk(circular_number="RBI/2024-25/01"),
            _make_chunk(circular_number="RBI/2024-25/02"),
            _make_chunk(circular_number="RBI/2024-25/01"),  # duplicate
            _make_chunk(circular_number=None),
        ]
        numbers = rag.get_circular_numbers(chunks)
        assert numbers == {"RBI/2024-25/01", "RBI/2024-25/02"}
