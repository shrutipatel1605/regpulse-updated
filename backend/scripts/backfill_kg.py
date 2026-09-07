"""Backfill knowledge graph entities/relationships for existing circulars.

This script lives in backend/scripts/ for discoverability but executes
the scraper-side EntityExtractor and persist_kg helper. It walks every
ACTIVE circular_documents row, joins its chunks into a single text blob,
and runs the extractor + upsert. Idempotent — re-running is safe because
both kg_entities and kg_relationships have unique constraints.

Usage (from backend container):
    python scripts/backfill_kg.py [--limit N]

The script depends on the `scraper` package being importable, which is
true inside the scraper container — run it there:
    docker exec regpulse-scraper python /scraper/backfill_kg.py
"""

from __future__ import annotations

import argparse
import sys

import structlog

logger = structlog.get_logger("regpulse.backfill_kg")


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill KG entities/relationships")
    parser.add_argument("--limit", type=int, default=None, help="Max circulars to process")
    parser.add_argument("--dry-run", action="store_true", help="Extract but don't write")
    args = parser.parse_args()

    from sqlalchemy import text  # noqa: PLC0415

    from scraper.db import get_db_session  # noqa: PLC0415
    from scraper.processor.entity_extractor import EntityExtractor  # noqa: PLC0415
    from scraper.tasks import persist_kg  # noqa: PLC0415

    extractor = EntityExtractor()

    with get_db_session() as db:
        sql = """
            SELECT id, circular_number, title
            FROM circular_documents
            WHERE status = 'ACTIVE'
            ORDER BY indexed_at DESC
        """
        if args.limit is not None:
            sql += f" LIMIT {int(args.limit)}"
        rows = db.execute(text(sql)).fetchall()

    print(f"Found {len(rows)} circulars to backfill", file=sys.stderr)

    total_entities = 0
    total_edges = 0
    failed = 0

    for idx, row in enumerate(rows, start=1):
        doc_id, circular_number, title = str(row[0]), row[1], row[2]
        try:
            with get_db_session() as db:
                chunks = db.execute(
                    text("SELECT chunk_text FROM document_chunks " "WHERE document_id = CAST(:id AS uuid) ORDER BY chunk_index"),
                    {"id": doc_id},
                ).fetchall()
                full_text = "\n\n".join(r[0] for r in chunks if r[0])

                if not full_text.strip():
                    print(f"  [{idx}/{len(rows)}] {circular_number or doc_id}: no text, skipping")
                    continue

                entities, triples = extractor.extract(
                    full_text,
                    circular_number=circular_number,
                    title=title,
                )

                if args.dry_run:
                    print(f"  [{idx}/{len(rows)}] {circular_number}: " f"{len(entities)} entities, {len(triples)} triples (dry-run)")
                    continue

                inserted_e, inserted_r = persist_kg(
                    db,
                    entities=entities,
                    triples=triples,
                    source_document_id=doc_id,
                )
                db.commit()
                total_entities += inserted_e
                total_edges += inserted_r
                print(f"  [{idx}/{len(rows)}] {circular_number}: " f"+{inserted_e} entities, +{inserted_r} edges")
        except Exception as exc:  # noqa: BLE001
            failed += 1
            print(f"  [{idx}/{len(rows)}] FAILED: {exc}", file=sys.stderr)

    print(
        f"\nDone. {total_entities} entities, {total_edges} edges, {failed} failures",
        file=sys.stderr,
    )
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
