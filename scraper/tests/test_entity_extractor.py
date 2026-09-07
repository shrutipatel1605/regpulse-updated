"""Unit tests for the entity extractor.

The LLM pass is mocked — we exercise the regex pre-pass, the parsing
of the LLM JSON envelope, validation of allowed enum values, and the
deterministic ordering of outputs. The persistence path is tested
end-to-end via the live backfill smoke test in CI.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from scraper.processor.entity_extractor import (
    ENTITY_TYPES,
    RELATION_TYPES,
    Entity,
    EntityExtractor,
    _regex_pass,
)


# ---------------------------------------------------------------------------
# Regex pre-pass
# ---------------------------------------------------------------------------


class TestRegexPass:
    def test_extracts_circular_numbers(self):
        text = "Per RBI/2023-24/108 and RBI/2024-25/42 the rules apply."
        out = _regex_pass(text)
        nums = {e.canonical_name for e in out if e.entity_type == "CIRCULAR"}
        assert nums == {"RBI/2023-24/108", "RBI/2024-25/42"}

    def test_extracts_section_refs(self):
        text = "See Section 4.1 and Section 35A of the BR Act."
        out = _regex_pass(text)
        secs = {e.canonical_name for e in out if e.entity_type == "SECTION"}
        assert "Section 4.1" in secs
        assert "Section 35A" in secs

    def test_extracts_amounts(self):
        text = "Banks must hold ₹50 crore. Some need Rs. 10 lakh."
        out = _regex_pass(text)
        amounts = {e.canonical_name for e in out if e.entity_type == "AMOUNT"}
        assert any("50 crore" in a for a in amounts)
        assert any("10 lakh" in a for a in amounts)

    def test_extracts_dates(self):
        text = "Effective from 15 January 2026 and reviewed on 30 June 2026."
        out = _regex_pass(text)
        dates = {e.canonical_name for e in out if e.entity_type == "DATE"}
        assert "15 January 2026" in dates
        assert "30 June 2026" in dates

    def test_empty_text_returns_empty(self):
        assert _regex_pass("") == set()

    def test_no_matches_returns_empty(self):
        assert _regex_pass("Just plain text with no targets.") == set()


# ---------------------------------------------------------------------------
# LLM pass parsing (mocked)
# ---------------------------------------------------------------------------


def _mock_anthropic_response(payload: dict) -> MagicMock:
    response = MagicMock()
    block = MagicMock()
    block.text = json.dumps(payload)
    response.content = [block]
    return response


class TestLLMPassParsing:
    def test_parses_valid_envelope(self):
        with patch("scraper.processor.entity_extractor.anthropic.Anthropic") as MockClient:
            instance = MockClient.return_value
            instance.messages.create.return_value = _mock_anthropic_response(
                {
                    "entities": [
                        {
                            "entity_type": "ORG",
                            "canonical_name": "Reserve Bank of India",
                            "aliases": ["RBI"],
                        },
                        {"entity_type": "TEAM", "canonical_name": "Compliance"},
                    ],
                    "triples": [
                        {
                            "subject": "Reserve Bank of India",
                            "predicate": "MENTIONS",
                            "object": "Compliance",
                        }
                    ],
                }
            )
            ext = EntityExtractor()
            ents, triples = ext.extract("dummy text", circular_number="RBI/2024-25/42")

            ent_names = {e.canonical_name for e in ents}
            assert "Reserve Bank of India" in ent_names
            assert "Compliance" in ent_names
            # Anchor circular auto-added
            assert "RBI/2024-25/42" in ent_names

            # The LLM-supplied triple plus auto-MENTIONS edges from the anchor
            preds = {t.predicate for t in triples}
            assert "MENTIONS" in preds

    def test_invalid_entity_type_dropped(self):
        with patch("scraper.processor.entity_extractor.anthropic.Anthropic") as MockClient:
            instance = MockClient.return_value
            instance.messages.create.return_value = _mock_anthropic_response(
                {
                    "entities": [
                        {"entity_type": "BOGUS", "canonical_name": "Junk"},
                        {"entity_type": "ORG", "canonical_name": "RBI"},
                    ],
                    "triples": [],
                }
            )
            ext = EntityExtractor()
            ents, _ = ext.extract("dummy", circular_number=None)
            ent_names = {e.canonical_name for e in ents}
            assert "Junk" not in ent_names
            assert "RBI" in ent_names

    def test_invalid_relation_dropped(self):
        with patch("scraper.processor.entity_extractor.anthropic.Anthropic") as MockClient:
            instance = MockClient.return_value
            instance.messages.create.return_value = _mock_anthropic_response(
                {
                    "entities": [
                        {"entity_type": "ORG", "canonical_name": "RBI"},
                        {"entity_type": "ENTITY_TYPE", "canonical_name": "NBFC"},
                    ],
                    "triples": [
                        {"subject": "RBI", "predicate": "BOGUS", "object": "NBFC"},
                        {"subject": "RBI", "predicate": "APPLIES_TO", "object": "NBFC"},
                    ],
                }
            )
            ext = EntityExtractor()
            _, triples = ext.extract("dummy", circular_number=None)
            preds = {t.predicate for t in triples}
            assert "BOGUS" not in preds
            assert "APPLIES_TO" in preds

    def test_triple_with_unknown_entity_dropped(self):
        with patch("scraper.processor.entity_extractor.anthropic.Anthropic") as MockClient:
            instance = MockClient.return_value
            instance.messages.create.return_value = _mock_anthropic_response(
                {
                    "entities": [{"entity_type": "ORG", "canonical_name": "RBI"}],
                    "triples": [
                        {
                            "subject": "RBI",
                            "predicate": "REFERENCES",
                            "object": "Ghost Entity",
                        }
                    ],
                }
            )
            ext = EntityExtractor()
            _, triples = ext.extract("dummy", circular_number=None)
            assert all(t.obj.canonical_name != "Ghost Entity" for t in triples)

    def test_malformed_json_returns_regex_only(self):
        with patch("scraper.processor.entity_extractor.anthropic.Anthropic") as MockClient:
            instance = MockClient.return_value
            response = MagicMock()
            block = MagicMock()
            block.text = "not json at all"
            response.content = [block]
            instance.messages.create.return_value = response

            ext = EntityExtractor()
            ents, triples = ext.extract(
                "Per RBI/2024-25/42 see Section 5.",
                circular_number="RBI/2024-25/42",
            )
            # Regex pass still produced entities
            ent_names = {e.canonical_name for e in ents}
            assert "RBI/2024-25/42" in ent_names
            assert "Section 5" in ent_names
            # No LLM triples parseable
            assert triples == []

    def test_disabled_returns_empty(self):
        with patch(
            "scraper.processor.entity_extractor.get_scraper_settings"
        ) as MockSettings, patch(
            "scraper.processor.entity_extractor.anthropic.Anthropic"
        ):
            MockSettings.return_value.KG_EXTRACTION_ENABLED = False
            MockSettings.return_value.ANTHROPIC_API_KEY = "fake"
            MockSettings.return_value.LLM_SUMMARY_MODEL = "claude-haiku"
            ext = EntityExtractor()
            ents, triples = ext.extract("anything", circular_number="RBI/2024-25/42")
            assert ents == [] and triples == []


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


class TestDeterministicOrdering:
    def test_entities_sorted_by_type_then_name(self):
        with patch("scraper.processor.entity_extractor.anthropic.Anthropic") as MockClient:
            instance = MockClient.return_value
            instance.messages.create.return_value = _mock_anthropic_response(
                {
                    "entities": [
                        {"entity_type": "TEAM", "canonical_name": "Compliance"},
                        {"entity_type": "ORG", "canonical_name": "RBI"},
                        {"entity_type": "ENTITY_TYPE", "canonical_name": "NBFC"},
                    ],
                    "triples": [],
                }
            )
            ext = EntityExtractor()
            ents, _ = ext.extract("dummy", circular_number=None)
            types_seen = [e.entity_type for e in ents]
            # Sorted: ENTITY_TYPE < ORG < TEAM
            assert types_seen == sorted(types_seen)


def test_enum_constants_match_schema():
    """Sanity check — these must equal the migration's enum values."""
    assert ENTITY_TYPES == {
        "CIRCULAR",
        "SECTION",
        "REGULATION",
        "ENTITY_TYPE",
        "AMOUNT",
        "DATE",
        "TEAM",
        "ORG",
    }
    assert RELATION_TYPES == {
        "SUPERSEDES",
        "REFERENCES",
        "AMENDS",
        "APPLIES_TO",
        "MENTIONS",
        "EFFECTIVE_FROM",
    }


def test_entity_dataclass_is_hashable():
    """Required so set deduplication works."""
    e1 = Entity("ORG", "RBI", aliases=("Reserve Bank",))
    e2 = Entity("ORG", "RBI", aliases=("Reserve Bank",))
    assert hash(e1) == hash(e2)
    assert {e1, e2} == {e1}
