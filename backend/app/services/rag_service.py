"""RAG Service — hybrid retrieval pipeline for Q&A.

Pipeline:
1. Normalise + SHA256 hash question
2. Redis answer cache check
3. Embed question via EmbeddingService
4. PARALLEL: pgvector cosine ANN + PostgreSQL FTS
5. RRF fusion
6. Deduplicate (max RAG_MAX_CHUNKS_PER_DOC per document)
7. Cosine threshold filter
8. Cross-encoder rerank → top RAG_TOP_K_FINAL
9. Return ranked chunks or empty (no-answer)

IMPORTANT: This module must NEVER import from the scraper/ package.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from typing import TYPE_CHECKING

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings

if TYPE_CHECKING:
    import redis.asyncio as aioredis

    from app.services.embedding_service import EmbeddingService

logger = structlog.get_logger("regpulse.rag")

_RRF_K = 60
_ANSWER_CACHE_PREFIX = "ans:"
_ANSWER_CACHE_TTL = 86400  # 24h


def _normalise_question(text: str) -> str:
    """Normalise question for cache key: lowercase, strip, collapse whitespace."""
    return " ".join(text.lower().strip().split())


def _hash_question(text: str) -> str:
    """SHA-256 hash of normalised question."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _rerank_chunks(
    model_name: str,
    query: str,
    chunk_texts: list[str],
) -> list[float]:
    """Run cross-encoder reranking in a subprocess (CPU-bound).

    This function is designed to be called via ProcessPoolExecutor
    to avoid blocking the async event loop.
    """
    from sentence_transformers import CrossEncoder

    model = CrossEncoder(model_name)
    pairs = [[query, ct] for ct in chunk_texts]
    scores = model.predict(pairs)
    return [float(s) for s in scores]


class RetrievedChunk:
    """A chunk retrieved and ranked by the RAG pipeline."""

    __slots__ = (
        "chunk_id",
        "document_id",
        "chunk_index",
        "chunk_text",
        "token_count",
        "circular_number",
        "title",
        "rbi_url",
        "rrf_score",
        "rerank_score",
    )

    def __init__(
        self,
        *,
        chunk_id: str,
        document_id: str,
        chunk_index: int,
        chunk_text: str,
        token_count: int,
        circular_number: str | None,
        title: str,
        rbi_url: str,
        rrf_score: float = 0.0,
        rerank_score: float = 0.0,
    ) -> None:
        self.chunk_id = chunk_id
        self.document_id = document_id
        self.chunk_index = chunk_index
        self.chunk_text = chunk_text
        self.token_count = token_count
        self.circular_number = circular_number
        self.title = title
        self.rbi_url = rbi_url
        self.rrf_score = rrf_score
        self.rerank_score = rerank_score

    def to_dict(self) -> dict:
        return {
            "chunk_id": self.chunk_id,
            "document_id": self.document_id,
            "chunk_index": self.chunk_index,
            "chunk_text": self.chunk_text,
            "token_count": self.token_count,
            "circular_number": self.circular_number,
            "title": self.title,
            "rbi_url": self.rbi_url,
        }


class RAGService:
    """Hybrid retrieval service for the Q&A pipeline."""

    def __init__(
        self,
        db: AsyncSession,
        embedding_service: EmbeddingService,
        redis: aioredis.Redis,  # type: ignore[type-arg]
        cross_encoder: object | None = None,
    ) -> None:
        self._db = db
        self._embedding = embedding_service
        self._redis = redis
        self._cross_encoder = cross_encoder
        self._settings = get_settings()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def check_cache(self, question: str) -> dict | None:
        """Check Redis answer cache. Returns cached answer dict or None."""
        normalised = _normalise_question(question)
        cache_key = f"{_ANSWER_CACHE_PREFIX}{_hash_question(normalised)}"
        cached = await self._redis.get(cache_key)
        if cached:
            logger.info("answer_cache_hit", question_hash=cache_key)
            return json.loads(cached)
        return None

    async def cache_answer(self, question: str, answer: dict) -> None:
        """Store answer in Redis cache."""
        normalised = _normalise_question(question)
        cache_key = f"{_ANSWER_CACHE_PREFIX}{_hash_question(normalised)}"
        await self._redis.setex(cache_key, _ANSWER_CACHE_TTL, json.dumps(answer))

    async def retrieve(self, question: str) -> list[RetrievedChunk]:
        """Full hybrid retrieval pipeline. Returns ranked chunks."""
        settings = self._settings
        top_k_initial = settings.RAG_TOP_K_INITIAL
        top_k_final = settings.RAG_TOP_K_FINAL
        max_per_doc = settings.RAG_MAX_CHUNKS_PER_DOC

        # 1. Embed question
        query_embedding = await self._embedding.generate_single(question)

        # 2. Retrieval: vector + FTS
        # Both searches use the same AsyncSession, so they must run
        # sequentially to avoid concurrent AsyncSession operations.
        vector_results = await self._vector_search(
            query_embedding,
            top_k=top_k_initial,
        )

        fts_results = await self._fts_search(
            question,
            top_k=top_k_initial,
        )

        logger.info(
            "retrieval_results",
            vector_count=len(vector_results),
            fts_count=len(fts_results),
        )

        # 3. RRF fusion
        fused = self._rrf_fuse(vector_results, fts_results)

        if not fused:
            logger.info("retrieval_empty")
            return []

        # 4. Deduplicate: max chunks per document
        deduped = self._deduplicate(fused, max_per_doc)

        # 4.5. Optional knowledge graph expansion (Sprint 3 Pillar A)
        # Default OFF — feature-flagged via RAG_KG_EXPANSION_ENABLED.
        if settings.RAG_KG_EXPANSION_ENABLED and deduped:
            try:
                deduped = await self._kg_expand(deduped, max_per_doc=max_per_doc)
            except Exception:
                logger.warning("kg_expansion_failed", exc_info=True)

        # 5. Cosine threshold filter
        filtered = [c for c in deduped if c.rrf_score > 0]

        if not filtered:
            return []

        # 6. Cross-encoder rerank
        if self._cross_encoder is not None:
            reranked = await self._cross_encoder_rerank(question, filtered)
        else:
            reranked = filtered

        # 7. Top-K final
        final = reranked[:top_k_final]

        logger.info(
            "retrieval_complete",
            initial_fused=len(fused),
            after_dedup=len(deduped),
            after_filter=len(filtered),
            final_count=len(final),
        )

        return final

    def get_circular_numbers(self, chunks: list[RetrievedChunk]) -> set[str]:
        """Extract unique circular numbers from retrieved chunks."""
        return {c.circular_number for c in chunks if c.circular_number}

    # ------------------------------------------------------------------
    # Internal: Vector search
    # ------------------------------------------------------------------

    async def _vector_search(
        self,
        query_embedding: list[float],
        top_k: int,
    ) -> list[RetrievedChunk]:
        """pgvector cosine ANN search on active circulars."""
        embedding_str = "[" + ",".join(str(v) for v in query_embedding) + "]"

        stmt = text("""
            SELECT
                dc.id AS chunk_id,
                dc.document_id,
                dc.chunk_index,
                dc.chunk_text,
                dc.token_count,
                cd.circular_number,
                cd.title,
                cd.rbi_url,
                dc.embedding <=> cast(:emb AS vector) AS cosine_dist
            FROM document_chunks dc
            JOIN circular_documents cd ON cd.id = dc.document_id
            WHERE cd.status = 'ACTIVE'
                AND dc.embedding IS NOT NULL
            ORDER BY cosine_dist
            LIMIT :top_k
        """)

        result = await self._db.execute(stmt, {"emb": embedding_str, "top_k": top_k})
        rows = result.all()

        chunks = []
        for row in rows:
            chunks.append(
                RetrievedChunk(
                    chunk_id=str(row[0]),
                    document_id=str(row[1]),
                    chunk_index=row[2],
                    chunk_text=row[3],
                    token_count=row[4],
                    circular_number=row[5],
                    title=row[6],
                    rbi_url=row[7],
                )
            )
        return chunks

    # ------------------------------------------------------------------
    # Internal: FTS search
    # ------------------------------------------------------------------

    async def _fts_search(
        self,
        question: str,
        top_k: int,
    ) -> list[RetrievedChunk]:
        """PostgreSQL full-text search on chunk text, filtered to active docs."""
        stmt = text("""
            SELECT
                dc.id AS chunk_id,
                dc.document_id,
                dc.chunk_index,
                dc.chunk_text,
                dc.token_count,
                cd.circular_number,
                cd.title,
                cd.rbi_url,
                ts_rank(
                    to_tsvector('english', dc.chunk_text),
                    plainto_tsquery('english', :query)
                ) AS fts_rank
            FROM document_chunks dc
            JOIN circular_documents cd ON cd.id = dc.document_id
            WHERE cd.status = 'ACTIVE'
                AND to_tsvector('english', dc.chunk_text)
                    @@ plainto_tsquery('english', :query)
            ORDER BY fts_rank DESC
            LIMIT :top_k
        """)

        result = await self._db.execute(stmt, {"query": question, "top_k": top_k})
        rows = result.all()

        chunks = []
        for row in rows:
            chunks.append(
                RetrievedChunk(
                    chunk_id=str(row[0]),
                    document_id=str(row[1]),
                    chunk_index=row[2],
                    chunk_text=row[3],
                    token_count=row[4],
                    circular_number=row[5],
                    title=row[6],
                    rbi_url=row[7],
                )
            )
        return chunks

    # ------------------------------------------------------------------
    # Internal: RRF fusion
    # ------------------------------------------------------------------

    @staticmethod
    def _rrf_fuse(
        vector_results: list[RetrievedChunk],
        fts_results: list[RetrievedChunk],
    ) -> list[RetrievedChunk]:
        """Reciprocal Rank Fusion: merged_score = sum(1/(K + rank_i))."""
        scores: dict[str, RetrievedChunk] = {}

        for rank, chunk in enumerate(vector_results):
            key = chunk.chunk_id
            if key not in scores:
                scores[key] = chunk
                chunk.rrf_score = 0.0
            scores[key].rrf_score += 1.0 / (_RRF_K + rank)

        for rank, chunk in enumerate(fts_results):
            key = chunk.chunk_id
            if key not in scores:
                scores[key] = chunk
                chunk.rrf_score = 0.0
            scores[key].rrf_score += 1.0 / (_RRF_K + rank)

        return sorted(scores.values(), key=lambda c: c.rrf_score, reverse=True)

    # ------------------------------------------------------------------
    # Internal: Deduplication
    # ------------------------------------------------------------------

    @staticmethod
    def _deduplicate(
        chunks: list[RetrievedChunk],
        max_per_doc: int,
    ) -> list[RetrievedChunk]:
        """Keep at most max_per_doc chunks per document_id."""
        doc_counts: dict[str, int] = defaultdict(int)
        result = []
        for chunk in chunks:
            if doc_counts[chunk.document_id] < max_per_doc:
                result.append(chunk)
                doc_counts[chunk.document_id] += 1
        return result

    # ------------------------------------------------------------------
    # Internal: Knowledge graph expansion (Sprint 3 Pillar A, opt-in)
    # ------------------------------------------------------------------

    async def _kg_expand(
        self,
        chunks: list[RetrievedChunk],
        *,
        max_per_doc: int,
    ) -> list[RetrievedChunk]:
        """Pull additional chunks from circulars that are graph-connected
        to the entities present in the top retrieved chunks.

        New chunks are added with a small RRF-score boost so they sit
        below organic hits but can still rank above noise. The expansion
        is best-effort: any failure short-circuits to returning the input
        unchanged.
        """
        from app.services.kg_service import (
            find_entities_in_text,
            neighbor_circular_numbers,
        )

        boost = float(self._settings.RAG_KG_BOOST_WEIGHT)
        top_chunks = chunks[:3]  # only seed from the very top hits
        seed_text = " ".join(c.chunk_text for c in top_chunks)

        seed_entities = await find_entities_in_text(self._db, seed_text)
        if not seed_entities:
            return chunks

        circular_numbers = await neighbor_circular_numbers(self._db, seed_entities=seed_entities)
        # Drop circulars already represented in the result set
        already = {c.circular_number for c in chunks if c.circular_number}
        new_circulars = [n for n in circular_numbers if n not in already]
        if not new_circulars:
            return chunks

        # Pull up to `max_per_doc` chunks per neighbour circular
        stmt = text("""
            SELECT
                dc.id, dc.document_id, dc.chunk_index, dc.chunk_text,
                dc.token_count, cd.circular_number, cd.title, cd.rbi_url
            FROM document_chunks dc
            JOIN circular_documents cd ON cd.id = dc.document_id
            WHERE cd.status = 'ACTIVE'
              AND cd.circular_number = ANY(:numbers)
              AND dc.embedding IS NOT NULL
            ORDER BY dc.chunk_index
            LIMIT :hard_limit
            """)
        result = await self._db.execute(
            stmt,
            {
                "numbers": new_circulars,
                "hard_limit": max_per_doc * len(new_circulars),
            },
        )
        rows = result.all()
        if not rows:
            return chunks

        added: list[RetrievedChunk] = []
        for row in rows:
            chunk = RetrievedChunk(
                chunk_id=str(row[0]),
                document_id=str(row[1]),
                chunk_index=row[2],
                chunk_text=row[3],
                token_count=row[4],
                circular_number=row[5],
                title=row[6],
                rbi_url=row[7],
                rrf_score=boost,
            )
            added.append(chunk)

        logger.info(
            "kg_expansion_applied",
            seed_entities=len(seed_entities),
            new_circulars=len(new_circulars),
            added_chunks=len(added),
        )
        return chunks + added

    # ------------------------------------------------------------------
    # Internal: Cross-encoder rerank
    # ------------------------------------------------------------------

    async def _cross_encoder_rerank(
        self,
        question: str,
        chunks: list[RetrievedChunk],
    ) -> list[RetrievedChunk]:
        """Rerank using cross-encoder in a subprocess."""
        chunk_texts = [c.chunk_text for c in chunks]

        try:
            loop = asyncio.get_running_loop()
            with ProcessPoolExecutor(max_workers=1) as pool:
                scores = await asyncio.wait_for(
                    loop.run_in_executor(
                        pool,
                        _rerank_chunks,
                        "cross-encoder/ms-marco-MiniLM-L-6-v2",
                        question,
                        chunk_texts,
                    ),
                    timeout=30,
                )

            for chunk, score in zip(chunks, scores, strict=True):
                chunk.rerank_score = score

            return sorted(chunks, key=lambda c: c.rerank_score, reverse=True)

        except Exception:
            logger.warning("cross_encoder_rerank_failed", exc_info=True)
            return chunks
