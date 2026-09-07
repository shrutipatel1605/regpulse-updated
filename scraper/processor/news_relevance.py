"""News-to-circular relevance scorer.

For each fetched news item we embed `title + summary` and compare against
recent circular embeddings via pgvector cosine similarity. The closest
circular above NEWS_RELEVANCE_THRESHOLD is the linked_circular.

Standalone scraper module. NEVER imports from backend/app/.
"""

from __future__ import annotations

import structlog
from sqlalchemy import text
from sqlalchemy.orm import Session

from scraper.config import get_scraper_settings
from scraper.processor.embedder import Embedder

logger: structlog.stdlib.BoundLogger = structlog.get_logger("regpulse.news_relevance")


def score_and_link(
    session: Session,
    *,
    title: str,
    summary: str | None,
    embedder: Embedder | None = None,
) -> tuple[float | None, str | None]:
    """Return (relevance_score, linked_circular_id_str_or_None).

    The score is the maximum cosine similarity (1 - distance) between the
    embedded news text and the embeddings of any active document_chunks.
    Linking only happens above the configured threshold.
    """
    settings = get_scraper_settings()
    text_to_embed = title if not summary else f"{title}\n\n{summary}"

    if not text_to_embed.strip():
        return None, None

    # Reuse the existing scraper embedder
    embedder = embedder or Embedder()
    try:
        vectors = embedder.embed_chunks([text_to_embed])
    except Exception:
        logger.exception("news_embed_failed")
        return None, None

    if not vectors or not vectors[0]:
        # Embedder unavailable / returned empty — gracefully degrade.
        return None, None

    vec_literal = "[" + ",".join(f"{v:.6f}" for v in vectors[0]) + "]"

    # Top-1 nearest active circular by max chunk similarity.
    # We project chunk-level → document-level by MAX over chunks per doc.
    sql = text(
        """
        SELECT
            cd.id::text AS document_id,
            MAX(1 - (dc.embedding <=> CAST(:vec AS vector))) AS sim
        FROM document_chunks dc
        JOIN circular_documents cd ON cd.id = dc.document_id
        WHERE cd.status = 'ACTIVE'
        GROUP BY cd.id
        ORDER BY sim DESC
        LIMIT 1
        """
    )

    try:
        row = session.execute(sql, {"vec": vec_literal}).first()
    except Exception:
        logger.exception("news_similarity_query_failed")
        return None, None

    if row is None:
        return None, None

    document_id, sim = row
    score = float(sim) if sim is not None else None

    if score is None:
        return None, None

    if score >= settings.NEWS_RELEVANCE_THRESHOLD:
        logger.info(
            "news_linked_to_circular",
            document_id=document_id,
            score=round(score, 4),
            threshold=settings.NEWS_RELEVANCE_THRESHOLD,
        )
        return score, document_id

    logger.info(
        "news_below_threshold",
        score=round(score, 4),
        threshold=settings.NEWS_RELEVANCE_THRESHOLD,
    )
    return score, None
