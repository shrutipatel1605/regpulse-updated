"""Knowledge graph service (Sprint 3 Pillar A).

Read-only helpers backing optional RAG expansion. The graph is populated
by the scraper at index time. Retrieval is feature-flagged off by default
via RAG_KG_EXPANSION_ENABLED — until that flag flips, this service has
no effect on the live `/ask` flow.

Heavy traversal queries stay in pgvector/Postgres — no Neo4j dependency.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger("regpulse.kg")


# Regex copies of the deterministic patterns the scraper uses. Kept here
# (not imported from scraper/) to honour the "no scraper imports in
# backend" rule. They must stay in sync with scraper/processor/entity_extractor.py.
_CIRCULAR_NUMBER_RE = re.compile(r"RBI/\d{4}-\d{2}/\d+")
_SECTION_RE = re.compile(r"\bSection\s+(\d+(?:\.\d+)*[A-Z]?)\b", re.IGNORECASE)


@dataclass
class KGEntityRow:
    id: uuid.UUID
    entity_type: str
    canonical_name: str
    aliases: list[str]


@dataclass
class KGNeighbor:
    entity: KGEntityRow
    relation_type: str
    direction: str  # "OUT" or "IN" relative to the source entity


# ---------------------------------------------------------------------------
# Read API
# ---------------------------------------------------------------------------


async def find_entities_by_name(
    db: AsyncSession,
    *,
    names: list[str],
    entity_types: list[str] | None = None,
) -> list[KGEntityRow]:
    """Look up entities whose canonical_name (case-insensitive) or aliases
    contain any of the given names. Useful for KG lookup driven by chunk text.
    """
    if not names:
        return []

    cleaned = [n.strip() for n in names if n and n.strip()]
    if not cleaned:
        return []

    clauses = ["LOWER(canonical_name) = ANY(:names_lower)"]
    params: dict = {"names_lower": [n.lower() for n in cleaned]}

    if entity_types:
        clauses.append("entity_type::text = ANY(:etypes)")
        params["etypes"] = entity_types

    sql = text(f"SELECT id, entity_type::text, canonical_name, aliases " f"FROM kg_entities WHERE {' AND '.join(clauses)}")
    result = await db.execute(sql, params)
    rows = result.all()
    return [
        KGEntityRow(
            id=row[0],
            entity_type=row[1],
            canonical_name=row[2],
            aliases=list(row[3] or []),
        )
        for row in rows
    ]


async def find_entities_in_text(
    db: AsyncSession,
    chunk_text: str,
) -> list[KGEntityRow]:
    """Run the regex pre-pass on a chunk and look up the matches in kg_entities.

    Cheaper than embedding-based matching and good enough for the v1 expansion
    signal — circular numbers and section refs are deterministic anchors.
    """
    candidates: set[str] = set()
    candidates.update(_CIRCULAR_NUMBER_RE.findall(chunk_text))
    for sec in _SECTION_RE.findall(chunk_text):
        candidates.add(f"Section {sec}")

    if not candidates:
        return []

    return await find_entities_by_name(db, names=list(candidates))


async def get_neighbors(
    db: AsyncSession,
    *,
    entity_id: uuid.UUID,
    depth: int = 1,
    limit: int = 25,
) -> list[KGNeighbor]:
    """Return one- or two-hop neighbours of an entity.

    Depth=1 is the common case (direct relationships). Depth=2 is supported
    for occasional admin/debug usage but is not used by the live RAG path.
    """
    if depth not in (1, 2):
        raise ValueError("depth must be 1 or 2")

    sql_d1 = text("""
        SELECT
            ke.id, ke.entity_type::text, ke.canonical_name, ke.aliases,
            r.relation_type::text, 'OUT' AS direction
        FROM kg_relationships r
        JOIN kg_entities ke ON ke.id = r.target_entity_id
        WHERE r.source_entity_id = CAST(:eid AS uuid)
        UNION ALL
        SELECT
            ke.id, ke.entity_type::text, ke.canonical_name, ke.aliases,
            r.relation_type::text, 'IN' AS direction
        FROM kg_relationships r
        JOIN kg_entities ke ON ke.id = r.source_entity_id
        WHERE r.target_entity_id = CAST(:eid AS uuid)
        LIMIT :limit
        """)

    if depth == 1:
        result = await db.execute(sql_d1, {"eid": str(entity_id), "limit": limit})
    else:
        # Depth-2: union the depth-1 result with neighbours-of-neighbours.
        sql_d2 = text("""
            WITH first_hop AS (
                SELECT target_entity_id AS id FROM kg_relationships
                WHERE source_entity_id = CAST(:eid AS uuid)
                UNION
                SELECT source_entity_id AS id FROM kg_relationships
                WHERE target_entity_id = CAST(:eid AS uuid)
            )
            SELECT
                ke.id, ke.entity_type::text, ke.canonical_name, ke.aliases,
                r.relation_type::text, 'OUT' AS direction
            FROM kg_relationships r
            JOIN kg_entities ke ON ke.id = r.target_entity_id
            WHERE r.source_entity_id IN (SELECT id FROM first_hop)
              AND r.target_entity_id <> CAST(:eid AS uuid)
            LIMIT :limit
            """)
        result = await db.execute(sql_d2, {"eid": str(entity_id), "limit": limit})

    rows = result.all()
    return [
        KGNeighbor(
            entity=KGEntityRow(
                id=row[0],
                entity_type=row[1],
                canonical_name=row[2],
                aliases=list(row[3] or []),
            ),
            relation_type=row[4],
            direction=row[5],
        )
        for row in rows
    ]


async def neighbor_circular_numbers(
    db: AsyncSession,
    *,
    seed_entities: list[KGEntityRow],
    limit_per_seed: int = 5,
) -> set[str]:
    """Return canonical_name values of CIRCULAR-typed neighbours.

    Used by RAG expansion to identify which other circulars the seed
    entities co-occur with. Circular canonical_names are exactly the
    `circular_number` strings that document_chunks rows reference, so
    callers can use them directly to fetch chunks.
    """
    if not seed_entities:
        return set()

    seed_ids = [str(e.id) for e in seed_entities]
    sql = text("""
        SELECT DISTINCT ke.canonical_name
        FROM kg_relationships r
        JOIN kg_entities ke ON ke.id = r.source_entity_id OR ke.id = r.target_entity_id
        WHERE ke.entity_type = 'CIRCULAR'
          AND (
            r.source_entity_id = ANY(CAST(:ids AS uuid[]))
            OR r.target_entity_id = ANY(CAST(:ids AS uuid[]))
          )
        LIMIT :limit
        """)
    result = await db.execute(
        sql,
        {"ids": seed_ids, "limit": limit_per_seed * max(len(seed_ids), 1)},
    )
    return {row[0] for row in result.all()}
