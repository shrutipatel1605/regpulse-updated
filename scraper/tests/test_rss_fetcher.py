"""Unit tests for the RSS fetcher.

These tests are pure: they don't hit the network. We monkey-patch
feedparser.parse to return canned dict objects so we can lock down
the normalisation, dedup ID derivation, and graceful error handling.
"""

from __future__ import annotations

import time
from unittest.mock import patch

from scraper.crawler import rss_fetcher
from scraper.crawler.rss_fetcher import (
    _entry_external_id,
    _hash_entry,
    _parse_published,
    fetch_source,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mk_entry(**overrides):
    base = {
        "title": "RBI extends UPI limit",
        "link": "https://example.com/rbi/upi",
        "id": "press-12345",
        "summary": "<p>Some HTML summary</p>",
        "published_parsed": time.struct_time((2026, 4, 1, 9, 30, 0, 0, 0, 0)),
    }
    base.update(overrides)
    return base


class _FakeFeed:
    def __init__(self, entries, bozo=False):
        self.entries = entries
        self.bozo = bozo
        self.bozo_exception = None


# ---------------------------------------------------------------------------
# external_id derivation
# ---------------------------------------------------------------------------


class TestExternalId:
    def test_uses_id_when_present(self):
        e = _mk_entry()
        assert _entry_external_id("RBI_PRESS", e) == "RBI_PRESS:press-12345"

    def test_falls_back_to_link(self):
        e = _mk_entry(id=None)
        e.pop("id")
        assert "https://example.com/rbi/upi" in _entry_external_id("RBI_PRESS", e)

    def test_falls_back_to_title_hash(self):
        e = {"title": "Just a title"}
        out = _entry_external_id("LIVEMINT", e)
        assert out.startswith("LIVEMINT:")
        # The hash is deterministic
        assert out == _entry_external_id("LIVEMINT", e)

    def test_capped_length(self):
        e = {"id": "x" * 1000, "title": "t"}
        assert len(_entry_external_id("ET_BANKING", e)) <= 500


# ---------------------------------------------------------------------------
# published_at parsing
# ---------------------------------------------------------------------------


class TestParsePublished:
    def test_valid_struct_time(self):
        dt = _parse_published(_mk_entry())
        assert dt is not None
        assert dt.year == 2026 and dt.month == 4 and dt.day == 1

    def test_missing_returns_none(self):
        assert _parse_published({"title": "x"}) is None

    def test_uses_updated_parsed_fallback(self):
        e = {
            "title": "x",
            "updated_parsed": time.struct_time((2026, 1, 15, 12, 0, 0, 0, 0, 0)),
        }
        dt = _parse_published(e)
        assert dt is not None
        assert dt.month == 1 and dt.day == 15


# ---------------------------------------------------------------------------
# Hash stability
# ---------------------------------------------------------------------------


class TestHashEntry:
    def test_same_content_same_hash(self):
        e = _mk_entry()
        assert _hash_entry(e) == _hash_entry(_mk_entry())

    def test_changed_summary_changes_hash(self):
        e1 = _mk_entry()
        e2 = _mk_entry(summary="<p>different</p>")
        assert _hash_entry(e1) != _hash_entry(e2)


# ---------------------------------------------------------------------------
# fetch_source
# ---------------------------------------------------------------------------


class TestFetchSource:
    def test_unknown_source_returns_empty(self):
        assert fetch_source("UNKNOWN_FEED") == []

    def test_normalises_entries(self):
        entries = [_mk_entry(), _mk_entry(id="press-67890", title="Second story")]
        with patch.object(rss_fetcher.feedparser, "parse", return_value=_FakeFeed(entries)):
            items = fetch_source("RBI_PRESS")
        assert len(items) == 2
        assert items[0].source == "RBI_PRESS"
        assert items[0].title == "RBI extends UPI limit"
        assert items[0].external_id == "RBI_PRESS:press-12345"
        assert items[1].external_id == "RBI_PRESS:press-67890"

    def test_caps_at_50_per_feed(self):
        entries = [_mk_entry(id=f"press-{i}", title=f"Story {i}") for i in range(80)]
        with patch.object(rss_fetcher.feedparser, "parse", return_value=_FakeFeed(entries)):
            items = fetch_source("RBI_PRESS")
        assert len(items) == 50

    def test_network_failure_returns_empty(self):
        with patch.object(
            rss_fetcher.feedparser,
            "parse",
            side_effect=RuntimeError("connection refused"),
        ):
            assert fetch_source("RBI_PRESS") == []

    def test_malformed_entry_skipped(self):
        # An entry that triggers an exception during normalization should be skipped
        good = _mk_entry()
        bad = {"title": None, "link": object()}  # type: ignore[dict-item]
        with patch.object(
            rss_fetcher.feedparser, "parse", return_value=_FakeFeed([bad, good])
        ):
            items = fetch_source("RBI_PRESS")
        # Bad entry is dropped, good one remains
        assert len(items) >= 1
        assert any(it.title == "RBI extends UPI limit" for it in items)
