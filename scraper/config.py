"""Pydantic BaseSettings configuration for the scraper service."""

from functools import lru_cache
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings


class ScraperSettings(BaseSettings):
    """Scraper-specific configuration loaded from environment variables."""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    # --- Database (sync driver for Celery workers) ---
    DATABASE_URL: str

    # --- Redis (Celery broker + result backend) ---
    REDIS_URL: str

    # --- OpenAI (embeddings) ---
    OPENAI_API_KEY: str

    # --- Anthropic (AI summaries) ---
    ANTHROPIC_API_KEY: str
    LLM_SUMMARY_MODEL: str = "claude-haiku-4-5-20251001"

    # --- Embeddings ---
    EMBEDDING_MODEL: str = "text-embedding-3-large"
    EMBEDDING_DIMS: int = 3072

    # --- SMTP (admin alerts) ---
    SMTP_HOST: str
    SMTP_PORT: int
    SMTP_USER: str
    SMTP_PASS: str
    SMTP_FROM: str

    # --- Admin ---
    ADMIN_EMAIL_ALLOWLIST: list[str] = []

    # --- Application ---
    ENVIRONMENT: Literal["dev", "staging", "prod"] = "dev"
    DEMO_MODE: bool = False
    SENTRY_DSN: str | None = None

    # --- Sprint 3: RSS / news ingest ---
    RSS_INGEST_ENABLED: bool = True
    NEWS_RELEVANCE_THRESHOLD: float = 0.75
    # CSV of source keys: RBI_PRESS,BUSINESS_STANDARD,LIVEMINT,ET_BANKING
    RSS_SOURCES: str = "RBI_PRESS,BUSINESS_STANDARD,LIVEMINT,ET_BANKING"

    # --- Sprint 3: Knowledge graph ---
    KG_EXTRACTION_ENABLED: bool = True

    # --- PDF extraction ---
    OCR_MAX_PAGES: int = 10  # max pages to OCR per PDF (bounds runtime)

    # ------------------------------------------------------------------
    # Validators
    # ------------------------------------------------------------------

    @field_validator("ADMIN_EMAIL_ALLOWLIST", mode="before")
    @classmethod
    def _parse_admin_allowlist(cls, v: object) -> list[str]:
        if isinstance(v, str):
            return [e.strip() for e in v.split(",") if e.strip()]
        if isinstance(v, list):
            return v
        return []

    def model_post_init(self, __context: object) -> None:
        """Validate invariants after all fields are loaded."""
        # (1) Collect missing required secrets
        _required = [
            "DATABASE_URL",
            "REDIS_URL",
            "OPENAI_API_KEY",
            "ANTHROPIC_API_KEY",
            "SMTP_HOST",
            "SMTP_USER",
            "SMTP_PASS",
            "SMTP_FROM",
        ]
        missing = [k for k in _required if not getattr(self, k, None)]
        if missing:
            raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")

        # (2) DEMO_MODE blocked in production
        if self.DEMO_MODE and self.ENVIRONMENT == "prod":
            raise RuntimeError("DEMO_MODE=true is not allowed when ENVIRONMENT=prod")


@lru_cache
def get_scraper_settings() -> ScraperSettings:
    """Return a cached singleton ScraperSettings instance."""
    return ScraperSettings()  # type: ignore[call-arg]
