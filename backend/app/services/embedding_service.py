"""Standalone embedding service for the backend.

IMPORTANT: This module must NEVER import from the scraper/ package.
It is a self-contained async wrapper around the OpenAI embeddings API,
used by the RAG pipeline and library search.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
from typing import TYPE_CHECKING

import structlog
import tiktoken
from openai import RateLimitError
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_random_exponential,
)

from app.config import get_settings

if TYPE_CHECKING:
    import openai
    import redis.asyncio as aioredis

logger: structlog.stdlib.BoundLogger = structlog.get_logger("regpulse.embedding")

_CACHE_PREFIX = "emb:"
_CACHE_TTL = 86400  # 24 hours
_BATCH_SIZE = 100


class EmbeddingService:
    """Async embedding generation with Redis caching and cost logging."""

    def __init__(
        self,
        openai_client: openai.AsyncOpenAI,
        redis: aioredis.Redis,  # type: ignore[type-arg]
    ) -> None:
        self._client = openai_client
        self._redis = redis
        settings = get_settings()
        self._model = settings.EMBEDDING_MODEL
        self._dims = settings.EMBEDDING_DIMS
        self._encoding = tiktoken.get_encoding("cl100k_base")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def generate(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a list of texts.

        Uses Redis cache (sha256 key), batches uncached texts in groups of 100,
        and logs estimated token cost before each API call.
        """
        if not texts:
            return []

        results: list[list[float] | None] = [None] * len(texts)
        uncached_indices: list[int] = []
        uncached_texts: list[str] = []

        # 1. Check cache for each text
        hashes = [self._hash(t) for t in texts]
        cache_keys = [f"{_CACHE_PREFIX}{h}" for h in hashes]

        cached_values = await self._redis.mget(cache_keys)  # type: ignore[union-attr]

        for i, cached in enumerate(cached_values):
            if cached is not None:
                results[i] = json.loads(cached)
            else:
                uncached_indices.append(i)
                uncached_texts.append(texts[i])

        if not uncached_texts:
            logger.debug("embedding_all_cached", count=len(texts))
            return [r for r in results if r is not None]

        # 2. Batch uncached texts and call API
        all_embeddings: list[list[float]] = []
        batches = [uncached_texts[i : i + _BATCH_SIZE] for i in range(0, len(uncached_texts), _BATCH_SIZE)]

        # Log estimated cost
        total_tokens = sum(len(self._encoding.encode(t)) for t in uncached_texts)
        logger.info(
            "embedding_api_call",
            model=self._model,
            texts=len(uncached_texts),
            total_tokens=total_tokens,
            estimated_cost_usd=round(total_tokens * 0.00013 / 1000, 6),
            batches=len(batches),
        )

        # Parallel batch calls
        tasks = [self._embed_batch(batch) for batch in batches]
        batch_results = await asyncio.gather(*tasks)
        for batch_embs in batch_results:
            all_embeddings.extend(batch_embs)

        # 3. Fill results and cache
        pipe = self._redis.pipeline()  # type: ignore[union-attr]
        for idx, emb in zip(uncached_indices, all_embeddings, strict=True):
            results[idx] = emb
            cache_key = cache_keys[idx]
            pipe.setex(cache_key, _CACHE_TTL, json.dumps(emb))
        await pipe.execute()

        return [r for r in results if r is not None]

    async def generate_single(self, text: str) -> list[float]:
        """Convenience wrapper — embed a single text string."""
        result = await self.generate([text])
        return result[0]

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    @retry(
        retry=retry_if_exception_type(RateLimitError),
        wait=wait_random_exponential(min=1, max=60),
        stop=stop_after_attempt(5),
        reraise=True,
    )
    async def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Call OpenAI embeddings API for a single batch with retry on RateLimitError."""
        response = await self._client.embeddings.create(
            input=texts,
            model=self._model,
            dimensions=self._dims,
        )
        return [item.embedding for item in response.data]

    @staticmethod
    def _hash(text: str) -> str:
        """SHA-256 hash of text for cache key."""
        return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------


def get_embedding_service(request: object) -> EmbeddingService:
    """FastAPI dependency returning app.state.embedding_service.

    Usage in routers:
        embedding_svc: EmbeddingService = Depends(get_embedding_service)
    """
    from fastapi import Request

    req: Request = request  # type: ignore[assignment]
    return req.app.state.embedding_service  # type: ignore[no-any-return]
