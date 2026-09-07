"""Unit tests for CircularLibraryService.

DB-dependent tests (list, autocomplete, detail, facets) require PostgreSQL
with pgvector and are in tests/integration/. This file tests pure logic
(RRF fusion, filter building, sort column mapping).
"""

from __future__ import annotations

import uuid

from app.services.circular_library_service import CircularLibraryService


class TestRRFFusion:
    """Test the Reciprocal Rank Fusion algorithm."""

    def test_rrf_fuse_single_source(self) -> None:
        vector_results = [
            {"document_id": uuid.uuid4(), "rank": 0, "snippet": "text1"},
            {"document_id": uuid.uuid4(), "rank": 1, "snippet": "text2"},
        ]
        fused = CircularLibraryService._rrf_fuse(vector_results, [])
        assert len(fused) == 2
        # First result should have higher score (rank 0 vs rank 1)
        assert fused[0]["score"] > fused[1]["score"]

    def test_rrf_fuse_overlapping_results(self) -> None:
        doc_id = uuid.uuid4()
        vector_results = [{"document_id": doc_id, "rank": 0, "snippet": "vec snippet"}]
        fts_results = [{"document_id": doc_id, "rank": 0, "snippet": None}]
        fused = CircularLibraryService._rrf_fuse(vector_results, fts_results)
        assert len(fused) == 1
        # Score should be sum of both RRF contributions: 1/(60+0) + 1/(60+0)
        expected = 2.0 / 60.0
        assert abs(fused[0]["score"] - expected) < 0.0001

    def test_rrf_fuse_disjoint_results(self) -> None:
        id1 = uuid.uuid4()
        id2 = uuid.uuid4()
        vector_results = [{"document_id": id1, "rank": 0, "snippet": "v1"}]
        fts_results = [{"document_id": id2, "rank": 0, "snippet": "f1"}]
        fused = CircularLibraryService._rrf_fuse(vector_results, fts_results)
        assert len(fused) == 2
        # Both should have equal scores (each appears at rank 0 in one source)
        assert fused[0]["score"] == fused[1]["score"]

    def test_rrf_fuse_empty_inputs(self) -> None:
        fused = CircularLibraryService._rrf_fuse([], [])
        assert fused == []

    def test_rrf_ranking_boosted_by_both_sources(self) -> None:
        """Document appearing in both sources should rank higher than one in only one."""
        shared_id = uuid.uuid4()
        only_vec_id = uuid.uuid4()
        only_fts_id = uuid.uuid4()

        vector_results = [
            {"document_id": shared_id, "rank": 0, "snippet": "shared"},
            {"document_id": only_vec_id, "rank": 1, "snippet": "vec only"},
        ]
        fts_results = [
            {"document_id": shared_id, "rank": 0, "snippet": None},
            {"document_id": only_fts_id, "rank": 1, "snippet": None},
        ]

        fused = CircularLibraryService._rrf_fuse(vector_results, fts_results)

        # Shared doc should be first (boosted by both sources)
        assert fused[0]["document_id"] == shared_id
        assert fused[0]["score"] > fused[1]["score"]

    def test_rrf_preserves_snippets(self) -> None:
        doc_id = uuid.uuid4()
        vector_results = [{"document_id": doc_id, "rank": 0, "snippet": "my snippet"}]
        fts_results = [{"document_id": doc_id, "rank": 0, "snippet": None}]
        fused = CircularLibraryService._rrf_fuse(vector_results, fts_results)
        assert fused[0]["snippet"] == "my snippet"

    def test_rrf_many_results_ordering(self) -> None:
        """Test that RRF correctly orders results from many inputs."""
        ids = [uuid.uuid4() for _ in range(10)]
        vector_results = [{"document_id": ids[i], "rank": i, "snippet": None} for i in range(10)]
        fts_results = [{"document_id": ids[9 - i], "rank": i, "snippet": None} for i in range(10)]

        fused = CircularLibraryService._rrf_fuse(vector_results, fts_results)
        assert len(fused) == 10
        # All scores should be positive
        assert all(f["score"] > 0 for f in fused)


class TestFilterBuilding:
    """Test _build_filter_conditions static method."""

    def test_no_filters(self) -> None:
        conditions = CircularLibraryService._build_filter_conditions()
        # The filter builder always includes pending_admin_review = False so
        # unreviewed circulars are hidden from the public library.
        assert len(conditions) == 1

    def test_single_filter(self) -> None:
        conditions = CircularLibraryService._build_filter_conditions(doc_type="CIRCULAR")
        assert len(conditions) == 2  # pending_admin_review + doc_type

    def test_multiple_filters(self) -> None:
        conditions = CircularLibraryService._build_filter_conditions(
            doc_type="CIRCULAR",
            status="ACTIVE",
            impact_level="HIGH",
            department="Regulation",
        )
        assert len(conditions) == 5  # pending_admin_review + 4 filters

    def test_date_filters(self) -> None:
        conditions = CircularLibraryService._build_filter_conditions(
            date_from="2024-01-01",
            date_to="2024-12-31",
        )
        assert len(conditions) == 3  # pending_admin_review + date_from + date_to

    def test_tags_filter(self) -> None:
        conditions = CircularLibraryService._build_filter_conditions(
            tags=["KYC", "AML"],
        )
        assert len(conditions) == 3  # pending_admin_review + one condition per tag


class TestSortColumnMapping:
    """Test _get_sort_column static method."""

    def test_valid_sort_columns(self) -> None:
        from app.models.circular import CircularDocument

        col = CircularLibraryService._get_sort_column("issued_date")
        assert col is CircularDocument.issued_date
        assert CircularLibraryService._get_sort_column("title") is CircularDocument.title
        assert CircularLibraryService._get_sort_column("indexed_at") is CircularDocument.indexed_at

    def test_invalid_sort_column_defaults(self) -> None:
        from app.models.circular import CircularDocument

        # Unknown sort column should default to issued_date
        assert CircularLibraryService._get_sort_column("invalid") is CircularDocument.issued_date
