"""Celery application configuration for the RegPulse scraper.

Standalone scraper module. NEVER imports from backend/app/.
Uses Redis as both broker and result backend.
"""

from __future__ import annotations

import os

from celery import Celery
from celery.schedules import crontab

# Read REDIS_URL from environment directly to avoid loading full ScraperSettings
# at import time (which can fail if .env has format issues during development).
_REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

app = Celery(
    "regpulse_scraper",
    broker=_REDIS_URL,
    backend=_REDIS_URL,
)

# ---------------------------------------------------------------------------
# Celery configuration
# ---------------------------------------------------------------------------

app.conf.update(
    # Serialisation
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    # Timezone
    timezone="UTC",
    enable_utc=True,
    # Reliability
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    # Limits
    task_soft_time_limit=300,  # 5 minutes soft limit
    task_time_limit=360,  # 6 minutes hard limit
    # Graceful shutdown — finish current task before exiting (TD-02)
    worker_max_tasks_per_child=None,
    worker_cancel_long_running_tasks_on_connection_loss=False,
    # Result expiry
    result_expires=3600,  # 1 hour
    # Task routes
    task_routes={
        "scraper.tasks.daily_scrape": {"queue": "scraper"},
        "scraper.tasks.priority_scrape": {"queue": "scraper"},
        "scraper.tasks.process_document": {"queue": "scraper"},
        "scraper.tasks.generate_summary": {"queue": "scraper"},
        "scraper.tasks.send_staleness_alerts": {"queue": "scraper"},
        "scraper.tasks.ingest_news": {"queue": "scraper"},
        "scraper.tasks.process_uploaded_pdf": {"queue": "scraper"},
        "scraper.tasks.run_question_clustering": {"queue": "scraper"},
        "scraper.tasks.subscription_renewal_check": {"queue": "scraper"},
        "scraper.tasks.credit_notifications": {"queue": "scraper"},
    },
)

# ---------------------------------------------------------------------------
# Celery Beat schedule
# ---------------------------------------------------------------------------

app.conf.beat_schedule = {
    # Daily full crawl at 02:00 IST (20:30 UTC previous day)
    "daily-scrape-0200-ist": {
        "task": "scraper.tasks.daily_scrape",
        "schedule": crontab(hour=20, minute=30),
        "args": (),
    },
    # Priority crawl every 4h from 06:00–22:00 UTC (Circulars + Master Directions)
    "priority-scrape-every-4h": {
        "task": "scraper.tasks.priority_scrape",
        "schedule": crontab(hour="6,10,14,18,22", minute=0),
        "args": (),
    },
    # Sprint 3: RSS news ingest every 30 minutes
    "ingest-news-every-30-min": {
        "task": "scraper.tasks.ingest_news",
        "schedule": crontab(minute="*/30"),
        "args": (),
    },
    # Sprint 5: Question clustering daily at 03:00 UTC
    "question-clustering-daily": {
        "task": "scraper.tasks.run_question_clustering",
        "schedule": crontab(hour=3, minute=0),
        "args": (30,),
    },
    # Sprint 7: Subscription renewal check daily at 08:00 IST (02:30 UTC)
    "subscription-renewal-0800-ist": {
        "task": "scraper.tasks.subscription_renewal_check",
        "schedule": crontab(hour=2, minute=30),
        "args": (),
    },
    # Sprint 7: Low-credit notifications daily at 09:00 IST (03:30 UTC)
    "credit-notifications-0900-ist": {
        "task": "scraper.tasks.credit_notifications",
        "schedule": crontab(hour=3, minute=30),
        "args": (),
    },
}

# Auto-discover tasks from scraper.tasks module
app.autodiscover_tasks(["scraper"])

# ---------------------------------------------------------------------------
# Graceful shutdown signal (TD-02) — log when SIGTERM is received
# ---------------------------------------------------------------------------
from celery.signals import worker_shutting_down  # noqa: E402


@worker_shutting_down.connect
def _on_worker_shutting_down(sig, how, exitcode, **kwargs):  # type: ignore[no-untyped-def]  # noqa: ANN001, ANN003
    import structlog

    logger = structlog.get_logger("regpulse.celery")
    logger.info(
        "celery_worker_shutting_down",
        signal=sig,
        how=how,
        exitcode=exitcode,
    )
