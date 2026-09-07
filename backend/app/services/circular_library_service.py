"""Circular Library Service — hybrid search, filtering, autocomplete.

Provides:
- list_circulars: paginated listing with filters and sorting
- hybrid_search: vector similarity + BM25 full-text search with RRF fusion
- autocomplete: prefix/fuzzy matching on title and circular_number
- get_detail: single circular with chunks
- get_departments / get_tags: facet data for filter dropdowns

IMPORTANT: This module must NEVER import from the scraper/ package.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

import structlog
from sqlalchemy import desc, func, literal_column, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.circular import CircularDocument, CircularStatus, DocumentChunk

if TYPE_CHECKING:
    from app.services.embedding_service import EmbeddingService

logger = structlog.get_logger("regpulse.circular_library")

# RRF constant (standard value from literature)
_RRF_K = 60


class CircularLibraryService:
    """Service layer for the Circular Library API."""

    def __init__(
        self,
        db: AsyncSession,
        embedding_service: EmbeddingService | None = None,
    ) -> None:
        self._db = db
        self._embedding_service = embedding_service

    # ------------------------------------------------------------------
    # List with filters + pagination
    # ------------------------------------------------------------------

    async def list_circulars(
        self,
        *,
        doc_type: str | None = None,
        status: str | None = None,
        impact_level: str | None = None,
        department: str | None = None,
        regulator: str | None = None,
        tags: list[str] | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        sort_by: str = "issued_date",
        sort_order: str = "desc",
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[CircularDocument], int]:
        """Return filtered, paginated circular list and total count."""
        query = select(CircularDocument)
        count_query = select(func.count(CircularDocument.id))

        # Apply filters
        query, count_query = self._apply_filters(
            query,
            count_query,
            doc_type=doc_type,
            status=status,
            impact_level=impact_level,
            department=department,
            regulator=regulator,
            tags=tags,
            date_from=date_from,
            date_to=date_to,
        )

        # Sorting
        sort_column = self._get_sort_column(sort_by)
        if sort_order == "desc":
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(sort_column)

        # Pagination
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        # Execute
        total_result = await self._db.execute(count_query)
        total = total_result.scalar() or 0

        result = await self._db.execute(query)
        circulars = list(result.scalars().all())

        return circulars, total

    # ------------------------------------------------------------------
    # Hybrid search (vector + BM25 with RRF)
    # ------------------------------------------------------------------

    async def hybrid_search(
        self,
        *,
        query: str,
        doc_type: str | None = None,
        status: str | None = "ACTIVE",
        impact_level: str | None = None,
        department: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[dict], int]:
        """Hybrid search combining vector similarity and BM25 full-text search.

        Returns list of dicts with circular data + relevance_score + snippet,
        and total count.
        """
        if self._embedding_service is None:
            logger.warning("hybrid_search_no_embedding_service")
            return await self._fallback_fts_search(
                query=query,
                doc_type=doc_type,
                status=status,
                impact_level=impact_level,
                department=department,
                date_from=date_from,
                date_to=date_to,
                page=page,
                page_size=page_size,
            )

        # 1. Generate query embedding
        query_embedding = await self._embedding_service.generate_single(query)

        # 2. Vector search — find top chunks by cosine similarity
        vector_results = await self._vector_search(
            query_embedding,
            doc_type=doc_type,
            status=status,
            impact_level=impact_level,
            department=department,
            date_from=date_from,
            date_to=date_to,
            top_k=50,
        )

        # 3. BM25 full-text search
        fts_results = await self._fts_search(
            query,
            doc_type=doc_type,
            status=status,
            impact_level=impact_level,
            department=department,
            date_from=date_from,
            date_to=date_to,
            top_k=50,
        )

        # 4. RRF fusion
        fused = self._rrf_fuse(vector_results, fts_results)

        # 5. Paginate
        total = len(fused)
        offset = (page - 1) * page_size
        page_results = fused[offset : offset + page_size]

        # 6. Hydrate with full circular data
        if not page_results:
            return [], 0

        doc_ids = [r["document_id"] for r in page_results]
        score_map = {r["document_id"]: r for r in page_results}

        stmt = select(CircularDocument).where(CircularDocument.id.in_(doc_ids))
        result = await self._db.execute(stmt)
        circulars = {c.id: c for c in result.scalars().all()}

        hydrated = []
        for doc_id in doc_ids:
            circ = circulars.get(doc_id)
            if circ is None:
                continue
            info = score_map[doc_id]
            hydrated.append(
                {
                    "circular": circ,
                    "relevance_score": round(info["score"], 4),
                    "snippet": info.get("snippet"),
                }
            )

        return hydrated, total

    # ------------------------------------------------------------------
    # Autocomplete
    # ------------------------------------------------------------------

    async def autocomplete(self, q: str, limit: int = 10) -> list[CircularDocument]:
        """Prefix/trigram autocomplete on title and circular_number."""
        pattern = f"%{q}%"
        stmt = (
            select(CircularDocument)
            .where(
                CircularDocument.status == CircularStatus.ACTIVE,
                CircularDocument.pending_admin_review.is_(False),
                func.concat(
                    CircularDocument.title,
                    " ",
                    func.coalesce(CircularDocument.circular_number, ""),
                ).ilike(pattern),
            )
            .order_by(CircularDocument.issued_date.desc())
            .limit(limit)
        )
        result = await self._db.execute(stmt)
        return list(result.scalars().all())

    # ------------------------------------------------------------------
    # Detail
    # ------------------------------------------------------------------

    async def get_detail(self, circular_id: UUID) -> CircularDocument | None:
        """Get a single circular with its chunks."""
        stmt = select(CircularDocument).options(selectinload(CircularDocument.chunks)).where(CircularDocument.id == circular_id)
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    # ------------------------------------------------------------------
    # Facet helpers
    # ------------------------------------------------------------------

    async def get_departments(self) -> list[str]:
        """Return distinct department values."""
        stmt = (
            select(CircularDocument.department)
            .where(
                CircularDocument.department.is_not(None),
                CircularDocument.pending_admin_review.is_(False),
            )
            .distinct()
            .order_by(CircularDocument.department)
        )
        result = await self._db.execute(stmt)
        return [row[0] for row in result.all()]

    async def get_tags(self) -> list[str]:
        """Return distinct tag values across all circulars."""
        # Unnest JSONB array and get distinct values
        stmt = text(
            "SELECT DISTINCT jsonb_array_elements_text(tags) AS tag "
            "FROM circular_documents "
            "WHERE tags IS NOT NULL AND jsonb_array_length(tags) > 0 "
            "AND pending_admin_review = FALSE "
            "ORDER BY tag"
        )
        result = await self._db.execute(stmt)
        return [row[0] for row in result.all()]

    async def get_doc_types(self) -> list[str]:
        """Return distinct doc_type values."""
        stmt = (
            select(CircularDocument.doc_type).where(CircularDocument.pending_admin_review.is_(False)).distinct().order_by(CircularDocument.doc_type)
        )
        result = await self._db.execute(stmt)
        return [row[0] for row in result.all()]

    # ------------------------------------------------------------------
    # Internal: Vector search
    # ------------------------------------------------------------------

    async def _vector_search(
        self,
        query_embedding: list[float],
        *,
        doc_type: str | None = None,
        status: str | None = None,
        impact_level: str | None = None,
        department: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        top_k: int = 50,
    ) -> list[dict]:
        """Find documents by cosine similarity on chunk embeddings."""
        embedding_str = "[" + ",".join(str(v) for v in query_embedding) + "]"

        # Build a query that joins chunks → documents and returns
        # document_id, best cosine distance, and best chunk text
        stmt = (
            select(
                DocumentChunk.document_id,
                func.min(
                    DocumentChunk.embedding.cosine_distance(
                        func.cast(
                            literal_column(f"'{embedding_str}'"),
                            DocumentChunk.embedding.type,
                        )
                    )
                ).label("min_distance"),
                # Get the chunk text of the best match using a window function workaround
            )
            .join(CircularDocument, CircularDocument.id == DocumentChunk.document_id)
            .where(DocumentChunk.embedding.is_not(None))
            .group_by(DocumentChunk.document_id)
        )

        # Apply document-level filters
        stmt = self._apply_doc_filters_to_join(
            stmt,
            doc_type=doc_type,
            status=status,
            impact_level=impact_level,
            department=department,
            date_from=date_from,
            date_to=date_to,
        )

        stmt = stmt.order_by("min_distance").limit(top_k)
        result = await self._db.execute(
            stmt,
        )
        rows = result.all()

        # For snippets, fetch best chunk text per document
        results = []
        if rows:
            doc_ids = [row[0] for row in rows]
            distance_map = {row[0]: row[1] for row in rows}

            # Get best chunk per document for snippet
            snippet_stmt = text("""
                SELECT DISTINCT ON (dc.document_id)
                    dc.document_id,
                    dc.chunk_text
                FROM document_chunks dc
                WHERE dc.document_id = ANY(:doc_ids)
                    AND dc.embedding IS NOT NULL
                ORDER BY dc.document_id,
                    dc.embedding <=> cast(:emb AS vector)
            """)
            snippet_result = await self._db.execute(snippet_stmt, {"doc_ids": doc_ids, "emb": embedding_str})
            snippet_map = {row[0]: row[1] for row in snippet_result.all()}

            for rank, doc_id in enumerate(doc_ids):
                cosine_dist = distance_map[doc_id]
                similarity = 1.0 - float(cosine_dist)
                chunk_text = snippet_map.get(doc_id, "")
                snippet = chunk_text[:300] if chunk_text else None
                results.append(
                    {
                        "document_id": doc_id,
                        "rank": rank,
                        "similarity": similarity,
                        "snippet": snippet,
                    }
                )

        return results

    # ------------------------------------------------------------------
    # Internal: BM25 full-text search
    # ------------------------------------------------------------------

    async def _fts_search(
        self,
        query: str,
        *,
        doc_type: str | None = None,
        status: str | None = None,
        impact_level: str | None = None,
        department: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        top_k: int = 50,
    ) -> list[dict]:
        """PostgreSQL full-text search on circular title + circular_number."""
        ts_query = func.plainto_tsquery("english", query)
        ts_vector = func.to_tsvector(
            "english",
            func.concat(
                CircularDocument.title,
                " ",
                func.coalesce(CircularDocument.circular_number, ""),
            ),
        )
        rank = func.ts_rank(ts_vector, ts_query)

        stmt = select(
            CircularDocument.id.label("document_id"),
            rank.label("fts_rank"),
        ).where(ts_vector.bool_op("@@")(ts_query))

        stmt = self._apply_doc_filters_direct(
            stmt,
            doc_type=doc_type,
            status=status,
            impact_level=impact_level,
            department=department,
            date_from=date_from,
            date_to=date_to,
        )

        stmt = stmt.order_by(desc("fts_rank")).limit(top_k)
        result = await self._db.execute(stmt)
        rows = result.all()

        return [
            {
                "document_id": row[0],
                "rank": rank_idx,
                "fts_rank": float(row[1]),
                "snippet": None,
            }
            for rank_idx, row in enumerate(rows)
        ]

    # ------------------------------------------------------------------
    # Internal: Fallback FTS-only search (when no embedding service)
    # ------------------------------------------------------------------

    async def _fallback_fts_search(
        self,
        *,
        query: str,
        doc_type: str | None = None,
        status: str | None = None,
        impact_level: str | None = None,
        department: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[dict], int]:
        """FTS-only search fallback when embedding service is unavailable."""
        fts_results = await self._fts_search(
            query,
            doc_type=doc_type,
            status=status,
            impact_level=impact_level,
            department=department,
            date_from=date_from,
            date_to=date_to,
            top_k=200,
        )

        total = len(fts_results)
        offset = (page - 1) * page_size
        page_results = fts_results[offset : offset + page_size]

        if not page_results:
            return [], 0

        doc_ids = [r["document_id"] for r in page_results]
        score_map = {r["document_id"]: r for r in page_results}

        stmt = select(CircularDocument).where(CircularDocument.id.in_(doc_ids))
        result = await self._db.execute(stmt)
        circulars = {c.id: c for c in result.scalars().all()}

        hydrated = []
        for doc_id in doc_ids:
            circ = circulars.get(doc_id)
            if circ is None:
                continue
            info = score_map[doc_id]
            hydrated.append(
                {
                    "circular": circ,
                    "relevance_score": round(info.get("fts_rank", 0.0), 4),
                    "snippet": None,
                }
            )

        return hydrated, total

    # ------------------------------------------------------------------
    # Internal: RRF fusion
    # ------------------------------------------------------------------

    @staticmethod
    def _rrf_fuse(
        vector_results: list[dict],
        fts_results: list[dict],
    ) -> list[dict]:
        """Reciprocal Rank Fusion of vector and FTS results.

        merged_score = Σ 1/(K + rank_i) where K = 60
        """
        scores: dict[UUID, dict] = {}

        for item in vector_results:
            doc_id = item["document_id"]
            rrf_score = 1.0 / (_RRF_K + item["rank"])
            if doc_id not in scores:
                scores[doc_id] = {
                    "document_id": doc_id,
                    "score": 0.0,
                    "snippet": item.get("snippet"),
                }
            scores[doc_id]["score"] += rrf_score
            if item.get("snippet") and not scores[doc_id].get("snippet"):
                scores[doc_id]["snippet"] = item["snippet"]

        for item in fts_results:
            doc_id = item["document_id"]
            rrf_score = 1.0 / (_RRF_K + item["rank"])
            if doc_id not in scores:
                scores[doc_id] = {
                    "document_id": doc_id,
                    "score": 0.0,
                    "snippet": item.get("snippet"),
                }
            scores[doc_id]["score"] += rrf_score

        # Sort by fused score descending
        fused = sorted(scores.values(), key=lambda x: x["score"], reverse=True)
        return fused

    # ------------------------------------------------------------------
    # Internal: Filter helpers
    # ------------------------------------------------------------------

    def _apply_filters(self, query, count_query, **kwargs):  # type: ignore[no-untyped-def]  # noqa: ANN001, ANN003
        """Apply common filters to both data and count queries."""
        filters = self._build_filter_conditions(**kwargs)
        for condition in filters:
            query = query.where(condition)
            count_query = count_query.where(condition)
        return query, count_query

    def _apply_doc_filters_to_join(self, stmt, **kwargs):  # type: ignore[no-untyped-def]  # noqa: ANN001, ANN003
        """Apply document-level filters to a query that already joins CircularDocument."""
        filters = self._build_filter_conditions(**kwargs)
        for condition in filters:
            stmt = stmt.where(condition)
        return stmt

    def _apply_doc_filters_direct(self, stmt, **kwargs):  # type: ignore[no-untyped-def]  # noqa: ANN001, ANN003
        """Apply filters directly on CircularDocument table."""
        filters = self._build_filter_conditions(**kwargs)
        for condition in filters:
            stmt = stmt.where(condition)
        return stmt

    @staticmethod
    def _build_filter_conditions(  # noqa: ANN205
        *,
        doc_type: str | None = None,
        status: str | None = None,
        impact_level: str | None = None,
        department: str | None = None,
        regulator: str | None = None,
        tags: list[str] | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
    ):
        """Build a list of SQLAlchemy filter conditions."""
        conditions = [CircularDocument.pending_admin_review.is_(False)]
        if doc_type:
            conditions.append(CircularDocument.doc_type == doc_type)
        if status:
            conditions.append(CircularDocument.status == status)
        if impact_level:
            conditions.append(CircularDocument.impact_level == impact_level)
        if department:
            conditions.append(CircularDocument.department.ilike(f"%{department}%"))
        if regulator:
            conditions.append(CircularDocument.regulator == regulator)
        if tags:
            # Check if any of the requested tags are in the JSONB array
            for tag in tags:
                conditions.append(CircularDocument.tags.op("@>")(func.cast(f'["{tag}"]', CircularDocument.tags.type)))
        if date_from:
            conditions.append(CircularDocument.issued_date >= date_from)
        if date_to:
            conditions.append(CircularDocument.issued_date <= date_to)
        return conditions

    @staticmethod
    def _get_sort_column(sort_by: str):  # noqa: ANN205
        """Map sort_by string to a model column."""
        column_map = {
            "issued_date": CircularDocument.issued_date,
            "indexed_at": CircularDocument.indexed_at,
            "title": CircularDocument.title,
            "circular_number": CircularDocument.circular_number,
            "updated_at": CircularDocument.updated_at,
        }
        return column_map.get(sort_by, CircularDocument.issued_date)


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------


def get_circular_library_service(
    request: object,
    db: object,
) -> CircularLibraryService:
    """FastAPI dependency returning CircularLibraryService.

    Usage in routers:
        svc: CircularLibraryService = Depends(get_circular_library_service)
    """
    from fastapi import Request as FastAPIRequest

    req: FastAPIRequest = request  # type: ignore[assignment]
    from sqlalchemy.ext.asyncio import AsyncSession as AsyncSess

    db_session: AsyncSess = db  # type: ignore[assignment]

    embedding_svc = getattr(req.app.state, "embedding_service", None)
    return CircularLibraryService(db=db_session, embedding_service=embedding_svc)
