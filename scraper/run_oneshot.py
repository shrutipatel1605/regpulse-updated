"""One-shot scraper entrypoint for Cloud Run Job.

Sets Celery to eager mode so .delay() calls run synchronously in this process —
no Celery worker needed. Used for scheduled/on-demand scrapes triggered by
Cloud Scheduler against a Cloud Run Job.

Run with: python -m scraper.run_oneshot [daily|priority|news]
- daily (default): full crawl of all RBI sections
- priority: Circulars + Master Directions only
- news: RSS news ingest
"""

from __future__ import annotations

import sys

import structlog

from scraper.celery_app import app

# Force synchronous execution — no Celery worker required.
app.conf.task_always_eager = True
app.conf.task_eager_propagates = True

# Import tasks AFTER the eager-mode flip so any task-level decorators see it.
from scraper.tasks import daily_scrape, ingest_news, priority_scrape  # noqa: E402

logger = structlog.get_logger("regpulse.oneshot")


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else "daily"
    logger.info("oneshot_starting", mode=mode)

    if mode == "daily":
        daily_scrape()
    elif mode == "priority":
        priority_scrape()
    elif mode == "news":
        ingest_news()
    else:
        logger.error("oneshot_unknown_mode", mode=mode)
        return 2

    logger.info("oneshot_done", mode=mode)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
