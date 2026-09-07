"""RegPulse Backend — FastAPI application entry point.

Configures: CORS (webhook excluded), Request-ID middleware, structlog JSON
logging, slowapi rate limiting, async DB/Redis connectivity check, cross-encoder
model load, Anthropic + OpenAI client init, and all routers at /api/v1/.
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from concurrent.futures import ProcessPoolExecutor
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text

from app.cache import redis_client
from app.config import get_settings
from app.db import engine
from app.exceptions import (
    RegPulseException,
    generic_exception_handler,
    regpulse_exception_handler,
)
from app.rate_limit import limiter
from app.routers.account import router as account_router
from app.routers.action_items import router as action_items_router
from app.routers.admin import router as admin_router
from app.routers.auth import router as auth_router
from app.routers.circulars import router as circulars_router
from app.routers.dashboard import router as dashboard_router
from app.routers.debates import router as debates_router
from app.routers.learnings import router as learnings_router
from app.routers.news import router as news_router
from app.routers.questions import router as questions_router
from app.routers.saved import router as saved_router
from app.routers.snippets import router as snippets_router
from app.routers.subscriptions import router as subscriptions_router

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------
settings = get_settings()

# ---------------------------------------------------------------------------
# structlog configuration — JSON lines for every log
# ---------------------------------------------------------------------------
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

# Silence noisy third-party loggers
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

logger: structlog.stdlib.BoundLogger = structlog.get_logger("regpulse")

# ---------------------------------------------------------------------------
# Cross-encoder loader (runs in subprocess to avoid blocking)
# ---------------------------------------------------------------------------
_CROSS_ENCODER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
_CROSS_ENCODER_LOAD_TIMEOUT = 30  # seconds


def _load_cross_encoder():  # type: ignore[no-untyped-def]  # noqa: ANN202
    """Load cross-encoder in a child process so the event loop is never blocked."""
    from sentence_transformers import CrossEncoder

    return CrossEncoder(_CROSS_ENCODER_MODEL)


# ---------------------------------------------------------------------------
# Lifespan — startup / shutdown
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    log = logger.bind(event="startup")

    # 1. Log masked config
    log.info(
        "config_loaded",
        environment=settings.ENVIRONMENT,
        llm_model=settings.LLM_MODEL,
        embedding_model=settings.EMBEDDING_MODEL,
        embedding_dims=settings.EMBEDDING_DIMS,
        demo_mode=settings.DEMO_MODE,
        frontend_url=settings.FRONTEND_URL,
    )

    # 2. DB connectivity check + pgvector status
    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
            result = await conn.execute(text("SELECT extname FROM pg_extension WHERE extname = 'vector'"))
            pgvector_loaded = result.scalar() is not None
        log.info("db_connected", pgvector=pgvector_loaded)
    except Exception:
        log.error("db_connection_failed", exc_info=True)

    # 3. Redis connectivity check
    try:
        await redis_client.ping()
        log.info("redis_connected")
    except Exception:
        log.error("redis_connection_failed", exc_info=True)

    # 4. Load cross-encoder (skip in demo mode — download can hang in Docker)
    if settings.DEMO_MODE:
        app.state.cross_encoder = None
        log.info("cross_encoder_skipped_demo_mode")
    else:
        loop = asyncio.get_running_loop()
        try:
            with ProcessPoolExecutor(max_workers=1) as pool:
                app.state.cross_encoder = await asyncio.wait_for(
                    loop.run_in_executor(pool, _load_cross_encoder),
                    timeout=_CROSS_ENCODER_LOAD_TIMEOUT,
                )
            log.info("cross_encoder_loaded", model=_CROSS_ENCODER_MODEL)
        except Exception:
            app.state.cross_encoder = None
            log.warning(
                "cross_encoder_load_failed",
                model=_CROSS_ENCODER_MODEL,
                timeout=_CROSS_ENCODER_LOAD_TIMEOUT,
            )

    # 5. Init LLM clients → app.state
    import anthropic
    import openai

    app.state.anthropic_client = anthropic.AsyncAnthropic(
        api_key=settings.ANTHROPIC_API_KEY,
    )
    app.state.openai_client = openai.AsyncOpenAI(
        api_key=settings.OPENAI_API_KEY,
    )
    log.info("llm_clients_initialized")

    # 6. Init EmbeddingService → app.state
    from app.services.embedding_service import EmbeddingService

    app.state.embedding_service = EmbeddingService(
        openai_client=app.state.openai_client,
        redis=redis_client,
    )
    log.info(
        "embedding_service_initialized",
        model=settings.EMBEDDING_MODEL,
        dims=settings.EMBEDDING_DIMS,
    )

    # Register SIGTERM handler for graceful shutdown (ECS/Docker sends SIGTERM)
    shutdown_event = asyncio.Event()
    loop = asyncio.get_running_loop()

    def _sigterm_handler() -> None:
        logger.info("sigterm_received, starting graceful shutdown")
        shutdown_event.set()

    loop.add_signal_handler(__import__("signal").SIGTERM, _sigterm_handler)

    yield

    # Shutdown — drain in-flight requests (uvicorn handles this),
    # then close DB pool and Redis connection.
    log = logger.bind(event="shutdown")
    log.info("shutdown_starting")
    await engine.dispose()
    log.info("db_pool_closed")
    await redis_client.aclose()
    log.info("redis_closed")
    logger.info("shutdown_complete")


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------
app = FastAPI(
    title="RegPulse API",
    description="RBI Regulatory Intelligence Platform",
    version="0.1.0",
    docs_url="/api/v1/docs",
    openapi_url="/api/v1/openapi.json",
    lifespan=lifespan,
)

# --- Rate limiter ---
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]

# --- Exception handlers ---
app.add_exception_handler(RegPulseException, regpulse_exception_handler)  # type: ignore[arg-type]
app.add_exception_handler(Exception, generic_exception_handler)  # type: ignore[arg-type]

# ---------------------------------------------------------------------------
# CORS middleware — exclude /api/v1/subscriptions/webhook
# ---------------------------------------------------------------------------
_WEBHOOK_PATH = "/api/v1/subscriptions/webhook"


class CORSMiddlewareExcludingWebhook(CORSMiddleware):
    """Standard CORS but skips the Razorpay webhook endpoint."""

    async def __call__(self, scope, receive, send) -> None:  # type: ignore[override, no-untyped-def]  # noqa: ANN001
        if scope.get("type") == "http" and scope.get("path") == _WEBHOOK_PATH:
            # Bypass CORS — let the request through without CORS headers
            from starlette.types import ASGIApp

            app: ASGIApp = self.app
            await app(scope, receive, send)
            return
        await super().__call__(scope, receive, send)


app.add_middleware(
    CORSMiddlewareExcludingWebhook,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Request-ID middleware
# ---------------------------------------------------------------------------


@app.middleware("http")
async def request_id_middleware(request: Request, call_next) -> Response:  # type: ignore[no-untyped-def]  # noqa: ANN001
    """Attach a UUID request ID to every request; include in response header."""
    request_id = str(uuid.uuid4())
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(request_id=request_id)

    start = time.perf_counter()
    response: Response = await call_next(request)
    duration_ms = round((time.perf_counter() - start) * 1000, 2)

    response.headers["X-Request-ID"] = request_id
    logger.info(
        "request_completed",
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        duration_ms=duration_ms,
    )
    return response


# ---------------------------------------------------------------------------
# Routers — all at /api/v1/
# ---------------------------------------------------------------------------
app.include_router(account_router, prefix="/api/v1/account")
app.include_router(auth_router, prefix="/api/v1/auth")
app.include_router(circulars_router, prefix="/api/v1/circulars")
app.include_router(questions_router, prefix="/api/v1/questions")
app.include_router(subscriptions_router, prefix="/api/v1/subscriptions")
app.include_router(action_items_router, prefix="/api/v1/action-items")
app.include_router(saved_router, prefix="/api/v1/saved")
app.include_router(snippets_router, prefix="/api/v1/snippets")
app.include_router(news_router, prefix="/api/v1/news")
app.include_router(dashboard_router, prefix="/api/v1/dashboard")
app.include_router(learnings_router, prefix="/api/v1/learnings")
app.include_router(debates_router, prefix="/api/v1/debates")
app.include_router(admin_router, prefix="/api/v1/admin")


# ---------------------------------------------------------------------------
# Health endpoints (directly on app, still under /api/v1/)
# ---------------------------------------------------------------------------
@app.get("/api/v1/health")
async def health_check() -> dict:
    """Liveness probe."""
    return {"status": "healthy", "service": "regpulse-api"}


@app.get("/api/v1/health/ready")
async def readiness_check() -> dict:
    """Readiness probe — checks DB and Redis connectivity."""
    errors: list[str] = []
    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception:
        errors.append("database")

    try:
        await redis_client.ping()
    except Exception:
        errors.append("redis")

    if errors:
        return {"status": "degraded", "service": "regpulse-api", "unhealthy": errors}
    return {"status": "ready", "service": "regpulse-api"}
