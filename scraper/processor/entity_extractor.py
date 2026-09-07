"""Entity + relationship extractor for RBI circulars (Sprint 3 Pillar A).

Standalone scraper module. NEVER imports from backend/app/.

Two-pass extraction:
1. Deterministic regex pre-pass — circular numbers, section refs, ₹
   amounts, dates. These are free, fast, and deterministic.
2. LLM pass — Haiku extracts entities (orgs, teams, regulations) and
   subject–predicate–object triples constrained to the allowed
   relation types. Run once per circular at scrape time, not per query.

Output is sorted and lowercase-canonical so the same input always
produces the same Entity/Triple sets.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

import anthropic
import structlog

from scraper.config import get_scraper_settings

logger: structlog.stdlib.BoundLogger = structlog.get_logger("regpulse.entity_extractor")


# ---------------------------------------------------------------------------
# Allowed enum values — must match kg_entity_type_enum / kg_relation_type_enum
# ---------------------------------------------------------------------------
ENTITY_TYPES = {
    "CIRCULAR",
    "SECTION",
    "REGULATION",
    "ENTITY_TYPE",
    "AMOUNT",
    "DATE",
    "TEAM",
    "ORG",
}
RELATION_TYPES = {
    "SUPERSEDES",
    "REFERENCES",
    "AMENDS",
    "APPLIES_TO",
    "MENTIONS",
    "EFFECTIVE_FROM",
}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Entity:
    entity_type: str
    canonical_name: str
    aliases: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class Triple:
    subject: Entity
    predicate: str
    obj: Entity


# ---------------------------------------------------------------------------
# Regex pre-pass
# ---------------------------------------------------------------------------

_CIRCULAR_NUMBER_RE = re.compile(r"RBI/\d{4}-\d{2}/\d+")
_SECTION_RE = re.compile(r"\bSection\s+(\d+(?:\.\d+)*[A-Z]?)\b", re.IGNORECASE)
_AMOUNT_RE = re.compile(
    r"(?:₹|Rs\.?\s*|INR\s*)([\d,]+(?:\.\d+)?\s*(?:crore|lakh|thousand|million|billion)?)",
    re.IGNORECASE,
)
_DATE_RE = re.compile(
    r"\b(\d{1,2}\s+(?:January|February|March|April|May|June|July|August|"
    r"September|October|November|December)\s+\d{4})\b",
    re.IGNORECASE,
)


def _regex_pass(text: str) -> set[Entity]:
    """Find deterministic entities — circular numbers, sections, amounts, dates."""
    entities: set[Entity] = set()

    for match in _CIRCULAR_NUMBER_RE.findall(text):
        entities.add(Entity(entity_type="CIRCULAR", canonical_name=match))

    for match in _SECTION_RE.findall(text):
        entities.add(
            Entity(entity_type="SECTION", canonical_name=f"Section {match}")
        )

    for match in _AMOUNT_RE.findall(text):
        cleaned = match.strip()
        entities.add(Entity(entity_type="AMOUNT", canonical_name=f"₹{cleaned}"))

    for match in _DATE_RE.findall(text):
        entities.add(Entity(entity_type="DATE", canonical_name=match))

    return entities


# ---------------------------------------------------------------------------
# LLM pass
# ---------------------------------------------------------------------------


_LLM_SYSTEM_PROMPT = """You are an entity extractor for RBI banking circulars.

Extract two things from the provided circular text:
1. ENTITIES — banking organisations, regulator bodies, regulated-entity \
types (NBFC, Cooperative Bank, Payment Bank...), regulation names, and \
internal teams (Compliance, Risk, KYC...).
2. TRIPLES — subject-predicate-object relationships between the entities.

Constraints:
- entity_type MUST be one of: ORG, REGULATION, ENTITY_TYPE, TEAM
- relation_type MUST be one of: SUPERSEDES, REFERENCES, AMENDS, \
APPLIES_TO, MENTIONS, EFFECTIVE_FROM
- canonical_name should be the most formal/long form. Add common short \
forms in aliases.
- DO NOT extract circular numbers, section refs, amounts, or dates — those \
are handled separately.
- DO NOT speculate. If a relationship is not explicit in the text, omit it.
- Return ONLY a JSON object. No prose, no markdown fences.

Output schema:
{
  "entities": [
    {"entity_type": "ORG", "canonical_name": "Reserve Bank of India", "aliases": ["RBI"]}
  ],
  "triples": [
    {"subject": "Reserve Bank of India", "predicate": "APPLIES_TO", "object": "NBFC"}
  ]
}"""


class EntityExtractor:
    """Two-pass entity + relationship extractor."""

    def __init__(self) -> None:
        settings = get_scraper_settings()
        self._enabled = settings.KG_EXTRACTION_ENABLED
        self._client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        self._model = settings.LLM_SUMMARY_MODEL

    def extract(
        self,
        circular_text: str,
        *,
        circular_number: str | None = None,
        title: str | None = None,
    ) -> tuple[list[Entity], list[Triple]]:
        """Run both passes and return (entities, triples), sorted for determinism.

        Returns empty lists if KG_EXTRACTION_ENABLED is false.
        """
        if not self._enabled:
            logger.info("kg_extraction_disabled")
            return [], []

        if not circular_text or not circular_text.strip():
            return [], []

        # Pass 1 — regex
        regex_entities = _regex_pass(circular_text)

        # Always include the source circular itself if we know its number
        if circular_number:
            regex_entities.add(
                Entity(entity_type="CIRCULAR", canonical_name=circular_number)
            )

        # Pass 2 — LLM
        llm_entities, llm_triples = self._llm_pass(
            circular_text=circular_text,
            title=title or "",
            anchor_circular=circular_number,
        )

        all_entities = regex_entities | set(llm_entities)
        # Deterministic ordering
        sorted_entities = sorted(
            all_entities, key=lambda e: (e.entity_type, e.canonical_name.lower())
        )
        sorted_triples = sorted(
            llm_triples,
            key=lambda t: (
                t.subject.entity_type,
                t.subject.canonical_name.lower(),
                t.predicate,
                t.obj.canonical_name.lower(),
            ),
        )

        logger.info(
            "kg_extraction_complete",
            circular_number=circular_number,
            entity_count=len(sorted_entities),
            triple_count=len(sorted_triples),
        )
        return sorted_entities, sorted_triples

    def _llm_pass(
        self,
        *,
        circular_text: str,
        title: str,
        anchor_circular: str | None,
    ) -> tuple[list[Entity], list[Triple]]:
        # Cap input to keep token cost predictable
        excerpt = circular_text[:6000]
        user_msg = f"Title: {title}\n\nCircular text:\n{excerpt}"

        try:
            response = self._client.messages.create(
                model=self._model,
                max_tokens=1500,
                temperature=0,
                system=_LLM_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_msg}],
            )
            raw = response.content[0].text.strip()
            # Strip accidental code fences
            if raw.startswith("```"):
                raw = re.sub(r"^```(?:json)?\n?|\n?```$", "", raw)
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            logger.warning("kg_llm_parse_error", error=str(exc))
            return [], []
        except anthropic.APIError as exc:
            logger.warning("kg_llm_api_error", error=str(exc))
            return [], []
        except Exception:
            logger.exception("kg_llm_unexpected_error")
            return [], []

        # Parse entities
        entity_lookup: dict[str, Entity] = {}
        for raw_ent in parsed.get("entities", []):
            if not isinstance(raw_ent, dict):
                continue
            etype = str(raw_ent.get("entity_type", "")).upper()
            name = str(raw_ent.get("canonical_name", "")).strip()
            if not name or etype not in ENTITY_TYPES:
                continue
            aliases_raw = raw_ent.get("aliases") or []
            aliases = tuple(
                sorted({str(a).strip() for a in aliases_raw if str(a).strip()})
            )
            ent = Entity(entity_type=etype, canonical_name=name, aliases=aliases)
            entity_lookup[name.lower()] = ent

        # Parse triples (skip any referencing unknown entities)
        triples: list[Triple] = []
        for raw_t in parsed.get("triples", []):
            if not isinstance(raw_t, dict):
                continue
            subj_name = str(raw_t.get("subject", "")).strip().lower()
            obj_name = str(raw_t.get("object", "")).strip().lower()
            pred = str(raw_t.get("predicate", "")).upper().strip()

            if pred not in RELATION_TYPES:
                continue
            subj = entity_lookup.get(subj_name)
            obj = entity_lookup.get(obj_name)
            if subj is None or obj is None:
                continue
            triples.append(Triple(subject=subj, predicate=pred, obj=obj))

        # If we have an anchor circular, add MENTIONS edges from it to every
        # entity the LLM extracted. These are the highest-quality edges
        # because they're grounded in the document.
        if anchor_circular:
            anchor = Entity(entity_type="CIRCULAR", canonical_name=anchor_circular)
            for ent in entity_lookup.values():
                triples.append(Triple(subject=anchor, predicate="MENTIONS", obj=ent))

        return list(entity_lookup.values()), triples
