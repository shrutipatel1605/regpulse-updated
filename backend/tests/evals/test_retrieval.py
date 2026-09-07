"""Retrieval-level integration eval for RegPulse RAG pipeline (TD-11).

Tests RAGService.retrieve() with real Postgres + real embeddings (no LLM mock).
Seeds the golden dataset circulars into the DB, generates actual embeddings,
then verifies top-K recall and KG-expansion behaviour.

Requires:
- Running Postgres with pgvector (docker compose)
- Valid OPENAI_API_KEY for embedding generation
- DATABASE_URL pointing to the compose Postgres

Usage:
    # KG expansion off (default):
    pytest backend/tests/evals/test_retrieval.py -v

    # KG expansion on:
    RAG_KG_EXPANSION_ENABLED=true pytest backend/tests/evals/test_retrieval.py -v
"""

from __future__ import annotations

import asyncio
import json
import os
import uuid
from pathlib import Path
from typing import Any

import pytest

# ---------------------------------------------------------------------------
# Env setup — must happen before any app imports
# ---------------------------------------------------------------------------

_BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
_GOLDEN_DATASET = Path(__file__).parent / "golden_dataset.json"

# Ensure backend root is importable
import sys  # noqa: E402

if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

# Minimal env vars required by Settings (some may already be set by docker compose)
_DEFAULTS = {
    "REDIS_URL": "redis://localhost:6379/0",
    "JWT_PRIVATE_KEY": "test-private-key-not-used",
    "JWT_PUBLIC_KEY": "test-public-key-not-used",
    "ANTHROPIC_API_KEY": "sk-ant-test-fake",
    "RAZORPAY_KEY_ID": "rzp_test_fake",
    "RAZORPAY_KEY_SECRET": "rzp_secret_fake",
    "RAZORPAY_WEBHOOK_SECRET": "whsec_fake",
    "SMTP_HOST": "smtp.test.local",
    "SMTP_PORT": "587",
    "SMTP_USER": "test@test.local",
    "SMTP_PASS": "test-password",
    "SMTP_FROM": "noreply@regpulse.test",
    "FRONTEND_URL": "http://localhost:3000",
    "ENVIRONMENT": "dev",
}

for key, val in _DEFAULTS.items():
    os.environ.setdefault(key, val)

# DATABASE_URL and OPENAI_API_KEY are required from the environment
if not os.environ.get("DATABASE_URL"):
    pytest.skip(
        "DATABASE_URL not set — run via docker compose or set it manually",
        allow_module_level=True,
    )
if not os.environ.get("OPENAI_API_KEY") or os.environ["OPENAI_API_KEY"].startswith("sk-test"):
    pytest.skip(
        "Real OPENAI_API_KEY required for embedding generation",
        allow_module_level=True,
    )

# ---------------------------------------------------------------------------
# Imports (after env is configured)
# ---------------------------------------------------------------------------

from sqlalchemy import text as sa_text  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine  # noqa: E402

from app.config import get_settings  # noqa: E402
from app.services.embedding_service import EmbeddingService  # noqa: E402
from app.services.rag_service import RAGService  # noqa: E402

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _load_golden_dataset() -> dict[str, Any]:
    with open(_GOLDEN_DATASET) as f:
        return json.load(f)


DATASET = _load_golden_dataset()


@pytest.fixture(scope="module")
def event_loop():
    """Module-scoped event loop for async fixtures."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="module")
def settings():
    return get_settings()


@pytest.fixture(scope="module")
def async_engine(settings):
    return create_async_engine(settings.DATABASE_URL, echo=False)


@pytest.fixture(scope="module")
def embedding_service(settings):
    import openai
    import redis.asyncio as aioredis

    client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    redis_client = aioredis.from_url(settings.REDIS_URL)
    return EmbeddingService(openai_client=client, redis=redis_client)


@pytest.fixture(scope="module")
def seeded_circulars(async_engine, embedding_service, event_loop):
    """Seed golden dataset circulars + chunks with real embeddings into Postgres.

    Returns a dict mapping circular_number -> document_id for assertions.
    """
    circulars = DATASET["synthetic_circulars"]
    circular_map: dict[str, str] = {}

    async def _seed():
        async with async_engine.begin() as conn:
            for circ in circulars:
                doc_id = str(uuid.uuid4())
                circular_map[circ["circular_number"]] = doc_id

                # Check if circular already seeded (idempotent)
                existing = await conn.execute(
                    sa_text("SELECT id FROM circular_documents WHERE circular_number = :cn"),
                    {"cn": circ["circular_number"]},
                )
                if existing.scalar():
                    # Already seeded — fetch the existing doc_id
                    circular_map[circ["circular_number"]] = str(existing.scalar())
                    continue

                # Insert circular_documents row
                await conn.execute(
                    sa_text("""
                        INSERT INTO circular_documents (
                            id, circular_number, title, rbi_url, status, doc_type
                        ) VALUES (
                            :id, :cn, :title, :url, 'ACTIVE', 'Circular'
                        )
                    """),
                    {
                        "id": doc_id,
                        "cn": circ["circular_number"],
                        "title": circ["title"],
                        "url": circ["rbi_url"],
                    },
                )

                # Generate real embeddings for chunks
                embeddings = await embedding_service.generate(circ["chunks"])

                # Insert document_chunks with embeddings
                for idx, (chunk_text, embedding) in enumerate(zip(circ["chunks"], embeddings, strict=True)):
                    emb_str = "[" + ",".join(str(x) for x in embedding) + "]"
                    await conn.execute(
                        sa_text("""
                            INSERT INTO document_chunks (
                                id, document_id, chunk_index, chunk_text,
                                token_count, embedding
                            ) VALUES (
                                :id, :doc_id, :idx, :text, :tokens,
                                CAST(:emb AS vector)
                            )
                        """),
                        {
                            "id": str(uuid.uuid4()),
                            "doc_id": doc_id,
                            "idx": idx,
                            "text": chunk_text,
                            "tokens": len(chunk_text.split()),
                            "emb": emb_str,
                        },
                    )

    # Re-fetch the actual IDs in case they already existed
    async def _fetch_ids():
        async with async_engine.connect() as conn:
            for cn in circular_map:
                row = await conn.execute(
                    sa_text("SELECT id FROM circular_documents WHERE circular_number = :cn"),
                    {"cn": cn},
                )
                val = row.scalar()
                if val:
                    circular_map[cn] = str(val)

    event_loop.run_until_complete(_seed())
    event_loop.run_until_complete(_fetch_ids())
    return circular_map


# ---------------------------------------------------------------------------
# Retrieval query helpers
# ---------------------------------------------------------------------------

RETRIEVAL_QUERIES = [
    {
        "id": "RET_001",
        "question": "What is the KYC updation frequency for high-risk customers?",
        "expected_circulars": {"RBI/2024-25/42"},
        "description": "Factual: KYC updation policy (single circular)",
    },
    {
        "id": "RET_002",
        "question": "How should loan disbursements be handled in digital lending?",
        "expected_circulars": {"RBI/2023-24/108"},
        "description": "Factual: Digital lending rules",
    },
    {
        "id": "RET_003",
        "question": "What are the NBFC classification layers under SBR framework?",
        "expected_circulars": {"RBI/2024-25/15"},
        "description": "Factual: NBFC scale-based regulation",
    },
    {
        "id": "RET_004",
        "question": "When is the PCA framework triggered for banks?",
        "expected_circulars": {"RBI/2023-24/76"},
        "description": "Factual: PCA thresholds",
    },
    {
        "id": "RET_005",
        "question": "What is the fraud reporting timeline for banks?",
        "expected_circulars": {"RBI/2024-25/31"},
        "description": "Factual: Fraud risk management",
    },
    {
        "id": "RET_006",
        "question": "What are KYC requirements and risk management for NBFCs?",
        "expected_circulars": {"RBI/2024-25/42", "RBI/2024-25/15"},
        "description": "Multi-circular: KYC + NBFC regulation",
    },
]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestRetrieval:
    """Integration tests for RAGService.retrieve() with real Postgres + embeddings."""

    @pytest.mark.parametrize(
        "query",
        RETRIEVAL_QUERIES,
        ids=[q["id"] for q in RETRIEVAL_QUERIES],
    )
    @pytest.mark.asyncio
    async def test_retrieval_recall(
        self,
        query,
        seeded_circulars,
        async_engine,
        embedding_service,
        settings,
    ):
        """Verify that retrieve() returns chunks from the expected circular(s)."""
        import redis.asyncio as aioredis

        redis_client = aioredis.from_url(settings.REDIS_URL)

        async with AsyncSession(async_engine) as session:
            rag = RAGService(
                db=session,
                embedding_service=embedding_service,
                redis=redis_client,
                cross_encoder=None,  # skip reranking in eval
            )
            chunks = await rag.retrieve(query["question"])

        # At least 1 chunk must be returned
        assert len(chunks) > 0, f"No chunks returned for: {query['question']}"

        # Check that at least one expected circular appears in the results
        returned_circulars = {c.circular_number for c in chunks if c.circular_number}
        overlap = returned_circulars & query["expected_circulars"]

        assert overlap, f"Expected at least one of {query['expected_circulars']} in results, " f"got {returned_circulars}"

    @pytest.mark.asyncio
    async def test_out_of_scope_returns_few_or_no_chunks(
        self,
        seeded_circulars,
        async_engine,
        embedding_service,
        settings,
    ):
        """Out-of-scope question should return 0-1 chunks (low recall = correct)."""
        import redis.asyncio as aioredis

        redis_client = aioredis.from_url(settings.REDIS_URL)

        async with AsyncSession(async_engine) as session:
            rag = RAGService(
                db=session,
                embedding_service=embedding_service,
                redis=redis_client,
                cross_encoder=None,
            )
            chunks = await rag.retrieve("What is the recipe for chicken tikka masala?")

        # Should return very few chunks or empty
        assert len(chunks) <= 2, f"Out-of-scope question returned {len(chunks)} chunks — expected ≤2"

    @pytest.mark.asyncio
    async def test_embeddings_populated(self, seeded_circulars, async_engine):
        """Verify all seeded chunks have non-null embeddings (TD-08 verification)."""
        async with async_engine.connect() as conn:
            result = await conn.execute(
                sa_text("""
                    SELECT count(*) FILTER (WHERE embedding IS NULL) AS null_count,
                           count(*) AS total
                    FROM document_chunks
                    WHERE document_id = ANY(:doc_ids)
                """),
                {"doc_ids": list(seeded_circulars.values())},
            )
            row = result.one()
            assert row[0] == 0, f"{row[0]} of {row[1]} chunks have NULL embeddings"
            assert row[1] > 0, "No chunks found in DB"
