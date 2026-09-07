"""Embedding generation for document chunks.

Standalone scraper module. NEVER imports from backend/app/.
Batches text chunks and calls OpenAI text-embedding-3-large for vector output.
"""

from __future__ import annotations

import structlog

from scraper.config import get_scraper_settings

logger: structlog.stdlib.BoundLogger = structlog.get_logger("regpulse.embedder")


class Embedder:
    """Generate embeddings for text chunks using OpenAI API.

    Batches chunks (max 100 per request), calls the configured embedding
    model, and returns dense vectors suitable for pgvector storage.
    """

    def __init__(self) -> None:
        import openai

        settings = get_scraper_settings()
        self._client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        self._model = settings.EMBEDDING_MODEL
        self._dims = settings.EMBEDDING_DIMS

    def embed_chunks(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a list of text chunks.

        Args:
            texts: List of chunk texts to embed.

        Returns:
            List of embedding vectors (float arrays of length EMBEDDING_DIMS).
        """
        if not texts:
            return []

        logger.info(
            "generating_embeddings",
            count=len(texts),
            model=self._model,
            dims=self._dims,
        )

        embeddings: list[list[float]] = []
        batch_size = 100
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            response = self._client.embeddings.create(
                input=batch,
                model=self._model,
                dimensions=self._dims,
            )
            embeddings.extend([data.embedding for data in response.data])

        return embeddings
