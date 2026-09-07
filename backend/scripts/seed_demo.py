#!/usr/bin/env python3
"""Seed demo circulars from the golden dataset into the database.

Loads the 5 synthetic circulars from tests/evals/golden_dataset.json,
generates real embeddings via OpenAI, and inserts them into the DB.

Usage (from inside the backend container):
    python scripts/seed_demo.py            # skip existing
    python scripts/seed_demo.py --reseed   # delete + re-insert

Requires: DATABASE_URL, OPENAI_API_KEY set in environment.
"""

from __future__ import annotations

import asyncio
import datetime
import json
import os
import sys
import uuid
from pathlib import Path

# Ensure backend root is importable
_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_root))

# Minimal env defaults for Settings
_DEFAULTS = {
    "REDIS_URL": "redis://redis:6379/0",
    "JWT_PRIVATE_KEY": "not-used",
    "JWT_PUBLIC_KEY": "not-used",
    "ANTHROPIC_API_KEY": "not-used",
    "RAZORPAY_KEY_ID": "rzp_test",
    "RAZORPAY_KEY_SECRET": "rzp_secret",
    "RAZORPAY_WEBHOOK_SECRET": "whsec",
    "SMTP_HOST": "localhost",
    "SMTP_PORT": "587",
    "SMTP_USER": "x",
    "SMTP_PASS": "x",
    "SMTP_FROM": "x@x.com",
    "FRONTEND_URL": "http://localhost:3000",
}
for k, v in _DEFAULTS.items():
    os.environ.setdefault(k, v)

# ---------------------------------------------------------------------------
# Enriched metadata for each golden-dataset circular
# ---------------------------------------------------------------------------
CIRCULAR_METADATA = {
    "RBI/2024-25/42": {
        "issued_date": "2024-08-15",
        "effective_date": "2024-10-01",
        "department": "Department of Regulation",
        "affected_teams": ["Compliance", "Retail Banking", "Operations"],
        "tags": ["KYC", "CDD", "Aadhaar", "V-CIP"],
        "impact_level": "HIGH",
        "ai_summary": (
            "Master Direction consolidating KYC norms including CDD requirements, "
            "periodic updation timelines by risk category, and Video-based Customer "
            "Identification Process (V-CIP) standards for all Regulated Entities."
        ),
    },
    "RBI/2023-24/108": {
        "issued_date": "2023-11-20",
        "effective_date": "2024-01-01",
        "department": "Department of Regulation",
        "affected_teams": ["Digital Lending", "Compliance", "IT"],
        "tags": ["Digital Lending", "LSP", "KFS", "Data Privacy"],
        "impact_level": "HIGH",
        "ai_summary": (
            "Guidelines mandating direct fund flow between borrower and RE, "
            "standardised Key Fact Statement, and data localisation requirements "
            "for Lending Service Providers and Digital Lending Apps."
        ),
    },
    "RBI/2024-25/15": {
        "issued_date": "2024-06-10",
        "effective_date": "2024-09-01",
        "department": "Department of Regulation",
        "affected_teams": ["NBFC Compliance", "Risk Management", "Finance"],
        "tags": ["NBFC", "SBR", "Risk Management", "Ind AS"],
        "impact_level": "HIGH",
        "ai_summary": (
            "Scale Based Regulation framework classifying NBFCs into four layers "
            "with progressive regulatory requirements including mandatory Risk "
            "Management Committee and CRO for Upper Layer entities."
        ),
    },
    "RBI/2023-24/76": {
        "issued_date": "2023-09-05",
        "effective_date": "2023-09-05",
        "department": "Department of Supervision",
        "affected_teams": ["Treasury", "Risk Management", "Board Secretariat"],
        "tags": ["PCA", "Capital Adequacy", "NPA", "CRAR"],
        "impact_level": "MEDIUM",
        "ai_summary": (
            "Prompt Corrective Action framework defining capital and asset quality "
            "thresholds that trigger supervisory restrictions on dividends, branch "
            "expansion, and staff recruitment for Scheduled Commercial Banks."
        ),
    },
    "RBI/2024-25/31": {
        "issued_date": "2024-07-22",
        "effective_date": "2024-10-01",
        "department": "Department of Supervision",
        "affected_teams": ["Fraud Risk", "Audit", "Compliance", "IT Security"],
        "tags": ["Fraud", "XBRL", "EWS", "CRILC", "Forensic Audit"],
        "impact_level": "MEDIUM",
        "ai_summary": (
            "Master Direction on fraud reporting timelines via XBRL-based Central "
            "Fraud Registry, Board and ACB review requirements, and Red Flag Account "
            "monitoring with mandatory forensic audit protocols."
        ),
    },
}


async def main() -> None:
    import openai
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    reseed = "--reseed" in sys.argv

    settings_db_url = os.environ["DATABASE_URL"]
    oai_key = os.environ.get("OPENAI_API_KEY", "")
    if not oai_key or oai_key.startswith("sk-test"):
        print("ERROR: Real OPENAI_API_KEY required for embedding generation")
        sys.exit(1)

    engine = create_async_engine(settings_db_url, echo=False)
    client = openai.AsyncOpenAI(api_key=oai_key)

    # Load golden dataset
    golden_path = _root / "tests" / "evals" / "golden_dataset.json"
    with open(golden_path) as f:
        dataset = json.load(f)

    circulars = dataset["synthetic_circulars"]
    print(f"Seeding {len(circulars)} demo circulars (reseed={reseed})...")

    async with engine.begin() as conn:
        for circ in circulars:
            cn = circ["circular_number"]
            meta = CIRCULAR_METADATA.get(cn, {})

            if reseed:
                # Delete existing circular + cascading chunks
                await conn.execute(
                    text("DELETE FROM document_chunks WHERE document_id IN " "(SELECT id FROM circular_documents WHERE circular_number = :cn)"),
                    {"cn": cn},
                )
                await conn.execute(
                    text("DELETE FROM circular_documents WHERE circular_number = :cn"),
                    {"cn": cn},
                )
            else:
                existing = await conn.execute(
                    text("SELECT id FROM circular_documents WHERE circular_number = :cn"),
                    {"cn": cn},
                )
                if existing.scalar():
                    print(f"  SKIP {cn} (use --reseed to replace)")
                    continue

            doc_id = str(uuid.uuid4())

            await conn.execute(
                text("""
                    INSERT INTO circular_documents (
                        id, circular_number, title, rbi_url, status, doc_type,
                        impact_level, pending_admin_review,
                        issued_date, effective_date, department,
                        affected_teams, tags, ai_summary
                    ) VALUES (
                        :id, :cn, :title, :url, 'ACTIVE', 'MASTER_DIRECTION',
                        :impact_level, FALSE,
                        :issued_date, :effective_date,
                        :department,
                        CAST(:affected_teams AS JSONB), CAST(:tags AS JSONB),
                        :ai_summary
                    )
                """),
                {
                    "id": doc_id,
                    "cn": cn,
                    "title": circ["title"],
                    "url": circ["rbi_url"],
                    "impact_level": meta.get("impact_level", "MEDIUM"),
                    "issued_date": (datetime.date.fromisoformat(meta["issued_date"]) if meta.get("issued_date") else None),
                    "effective_date": (datetime.date.fromisoformat(meta["effective_date"]) if meta.get("effective_date") else None),
                    "department": meta.get("department"),
                    "affected_teams": json.dumps(meta.get("affected_teams", [])),
                    "tags": json.dumps(meta.get("tags", [])),
                    "ai_summary": meta.get("ai_summary"),
                },
            )

            # Generate embeddings
            chunk_texts = circ["chunks"]
            response = await client.embeddings.create(
                input=chunk_texts,
                model="text-embedding-3-large",
                dimensions=3072,
            )
            embeddings = [d.embedding for d in response.data]

            for idx, (chunk_text, embedding) in enumerate(zip(chunk_texts, embeddings, strict=True)):
                emb_str = "[" + ",".join(str(x) for x in embedding) + "]"
                await conn.execute(
                    text("""
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

            print(f"  DONE {cn} — {circ['title']} ({len(chunk_texts)} chunks)")

    await engine.dispose()
    print("Seed complete.")


if __name__ == "__main__":
    asyncio.run(main())
