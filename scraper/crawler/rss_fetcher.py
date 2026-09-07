"""RSS fetcher for banking/regulatory news.

Standalone scraper module. NEVER imports from backend/app/.

Pulls items from a small set of vetted sources via RSS only — no HTML
scraping. Each item is normalised to a NewsItemDTO and de-duplicated by
(source, external_id) before insertion.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import feedparser
import structlog

logger: structlog.stdlib.BoundLogger = structlog.get_logger("regpulse.rss")


# ---------------------------------------------------------------------------
# Source registry — RSS feeds only. Public, intended for syndication.
# ---------------------------------------------------------------------------
SOURCE_FEEDS: dict[str, str] = {
    "RBI_PRESS": "https://www.rbi.org.in/pressreleases_rss.xml",
    "BUSINESS_STANDARD": "https://www.business-standard.com/rss/finance-103.rss",
    "LIVEMINT": "https://www.livemint.com/rss/banking",
    "ET_BANKING": "https://economictimes.indiatimes.com/industry/banking/finance/rssfeeds/13358319.cms",
}


@dataclass
class NewsItemDTO:
    source: str
    external_id: str
    title: str
    url: str
    published_at: datetime | None
    summary: str | None
    raw_html_hash: str


def _hash_entry(entry: dict[str, Any]) -> str:
    """Stable hash of the raw entry — used to detect content changes
    even when external_id is reused."""
    payload = (
        entry.get("title", "") + entry.get("link", "") + entry.get("summary", "")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _entry_external_id(source: str, entry: dict[str, Any]) -> str:
    """Derive a stable external id from the feed entry."""
    for key in ("id", "guid", "link"):
        val = entry.get(key)
        if val:
            return f"{source}:{val}"[:500]
    # Fallback: hash the title
    title = entry.get("title", "untitled")
    return f"{source}:{hashlib.sha1(title.encode()).hexdigest()}"[:500]


def _parse_published(entry: dict[str, Any]) -> datetime | None:
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if parsed is None:
        return None
    try:
        return datetime(*parsed[:6], tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


def fetch_source(source_key: str) -> list[NewsItemDTO]:
    """Fetch a single source feed and return normalised items.

    Network errors are swallowed and logged — they should not break the
    Celery task. Returns an empty list on failure.
    """
    url = SOURCE_FEEDS.get(source_key)
    if url is None:
        logger.warning("rss_unknown_source", source=source_key)
        return []

    log = logger.bind(source=source_key, url=url)
    log.info("rss_fetch_start")

    try:
        parsed = feedparser.parse(url)
    except Exception:
        log.exception("rss_fetch_failed")
        return []

    if parsed.bozo:
        log.warning("rss_feed_bozo", reason=str(parsed.get("bozo_exception", "")))

    items: list[NewsItemDTO] = []
    for entry in parsed.entries[:50]:  # cap each feed at 50 items per fetch
        try:
            items.append(
                NewsItemDTO(
                    source=source_key,
                    external_id=_entry_external_id(source_key, entry),
                    title=entry.get("title", "untitled")[:500],
                    url=entry.get("link", "")[:1000],
                    published_at=_parse_published(entry),
                    summary=(entry.get("summary") or "")[:2000] or None,
                    raw_html_hash=_hash_entry(entry),
                )
            )
        except Exception:
            log.exception("rss_entry_parse_failed")
            continue

    log.info("rss_fetch_complete", count=len(items))
    return items


def fetch_all_sources(sources: list[str] | None = None) -> list[NewsItemDTO]:
    """Fetch every configured source and return a flat list."""
    keys = sources if sources is not None else list(SOURCE_FEEDS.keys())
    out: list[NewsItemDTO] = []
    for key in keys:
        out.extend(fetch_source(key))
    return out
