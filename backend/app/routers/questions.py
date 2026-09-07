"""Questions router — ask, history, detail, feedback.

POST /questions — ask a question (SSE streaming or JSON)
GET  /questions — paginated history
GET  /questions/{id} — question detail
PATCH /questions/{id}/feedback — submit feedback
"""

from __future__ import annotations

import json
import time
import uuid

import structlog
from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import desc, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache import get_redis
from app.db import get_db
from app.dependencies.auth import require_credits, require_verified_user
from app.dependencies.rag import build_llm_service, build_rag_service
from app.models.question import Question
from app.models.user import User
from app.schemas.questions import (
    FeedbackRequest,
    QuestionDetail,
    QuestionListResponse,
    QuestionRequest,
    QuestionResponse,
    QuestionSuggestionItem,
    QuestionSuggestionListResponse,
    QuestionSummary,
)
from app.services.email_service import EmailService
from app.services.llm_service import LLMService
from app.services.rag_service import RAGService
from app.utils.credit_utils import deduct_credit

router = APIRouter(tags=["questions"])
logger = structlog.get_logger("regpulse.questions")


async def _maybe_embed_question(request: Request, text: str) -> list[float] | None:
    """Embed ``text`` via app.state.embedding_service; return None on failure.

    Suggestions depend on ``questions.question_embedding`` being populated,
    but an embedding failure must never block a Q&A response. EmbeddingService
    is Redis-cached by SHA256 — this usually hits the cache already warmed by
    ``RAGService.retrieve()`` earlier in the request.
    """
    svc = getattr(request.app.state, "embedding_service", None)
    if svc is None:
        return None
    try:
        return await svc.generate_single(text)
    except Exception:
        logger.warning("question_embedding_failed", exc_info=True)
        return None


# ---------------------------------------------------------------------------
# POST /questions — ask a question
# ---------------------------------------------------------------------------


@router.post("", response_model=None)
async def ask_question(
    body: QuestionRequest,
    request: Request,
    user: User = Depends(require_credits),
    db: AsyncSession = Depends(get_db),
    redis: object = Depends(get_redis),
) -> QuestionResponse | StreamingResponse:
    """Ask a regulatory question.

    If Accept: text/event-stream, returns SSE stream.
    Otherwise returns full JSON response.
    """
    start_time = time.perf_counter()

    rag = build_rag_service(request, db, redis)
    llm = build_llm_service(request)

    question_text = body.question.strip()

    # 1. Check answer cache
    cached = await rag.check_cache(question_text)
    if cached:
        logger.info("question_cache_hit")
        return QuestionResponse(
            data=QuestionDetail(**cached),
            credit_balance=user.credit_balance,  # No deduction for cache hit
        )

    # 2. Retrieve relevant chunks
    chunks = await rag.retrieve(question_text)

    if not chunks:
        # No relevant chunks found — return no-answer, no credit charge
        no_answer = Question(
            id=uuid.uuid4(),
            user_id=user.id,
            question_text=question_text,
            answer_text="I couldn't find relevant RBI circulars to answer this question.",
            quick_answer="No relevant circulars found.",
            risk_level=None,
            credit_deducted=False,
            streaming_completed=True,
            latency_ms=int((time.perf_counter() - start_time) * 1000),
        )
        db.add(no_answer)
        await db.commit()
        await db.refresh(no_answer)

        return QuestionResponse(
            data=QuestionDetail.model_validate(no_answer),
            credit_balance=user.credit_balance,
        )

    # 3. Check if SSE requested
    accept = request.headers.get("accept", "")
    if "text/event-stream" in accept:
        return StreamingResponse(
            _stream_response(
                request=request,
                question_text=question_text,
                chunks=chunks,
                llm=llm,
                rag=rag,
                db=db,
                user=user,
                start_time=start_time,
            ),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    # 4. Non-streaming: call LLM directly
    llm_response, model_used = await llm.generate(question_text, chunks)
    latency_ms = int((time.perf_counter() - start_time) * 1000)

    # 4b. Embed the question so /questions/suggestions can ANN-search it.
    # EmbeddingService is Redis-cached on SHA256 — this is a cache hit after
    # RAG.retrieve() embedded the same string a moment ago.
    question_embedding = await _maybe_embed_question(request, question_text)

    # 5. Create question record + deduct credit atomically
    question = Question(
        id=uuid.uuid4(),
        user_id=user.id,
        question_text=question_text,
        question_embedding=question_embedding,
        answer_text=llm_response.get("detailed_interpretation"),
        quick_answer=llm_response.get("quick_answer"),
        risk_level=llm_response.get("risk_level"),
        confidence_score=llm_response.get("confidence_score"),
        consult_expert=bool(llm_response.get("consult_expert", False)),
        affected_teams=llm_response.get("affected_teams", []),
        citations=llm_response.get("citations", []),
        recommended_actions=llm_response.get("recommended_actions", []),
        chunks_used=[c.to_dict() for c in chunks],
        model_used=model_used,
        credit_deducted=True,
        streaming_completed=True,
        latency_ms=latency_ms,
    )
    db.add(question)
    new_balance = await deduct_credit(db, user.id)
    await db.commit()
    await db.refresh(question)

    # 5b. Low-credit notification at thresholds 5 or 2
    if new_balance in (5, 2):
        try:
            email_svc = EmailService()
            await email_svc.send_low_credits_email(user.email, new_balance)
        except Exception:
            logger.warning("low_credit_email_failed", user_id=str(user.id))

    # 6. Cache the answer
    await rag.cache_answer(
        question_text,
        {
            "id": str(question.id),
            "question_text": question.question_text,
            "answer_text": question.answer_text,
            "quick_answer": question.quick_answer,
            "risk_level": question.risk_level,
            "confidence_score": question.confidence_score,
            "consult_expert": question.consult_expert,
            "affected_teams": question.affected_teams,
            "citations": question.citations,
            "recommended_actions": question.recommended_actions,
            "model_used": question.model_used,
            "credit_deducted": question.credit_deducted,
            "streaming_completed": question.streaming_completed,
            "latency_ms": question.latency_ms,
            "feedback": None,
            "created_at": question.created_at.isoformat(),
        },
    )

    return QuestionResponse(
        data=QuestionDetail.model_validate(question),
        credit_balance=new_balance,
    )


async def _stream_response(
    *,
    request: Request,
    question_text: str,
    chunks: list,
    llm: LLMService,
    rag: RAGService,
    db: AsyncSession,
    user: User,
    start_time: float,
):
    """SSE generator for streaming responses."""
    full_text = ""
    metadata = {}
    model_used = None

    try:
        async for event_type, data in llm.generate_stream(question_text, chunks):
            if event_type == "token":
                token_data = json.loads(data)
                full_text += token_data.get("token", "")
                yield f"event: token\ndata: {data}\n\n"
            elif event_type == "citations":
                metadata = json.loads(data)
                model_used = metadata.get("model_used")
                yield f"event: citations\ndata: {data}\n\n"

        # Save question + deduct credit
        latency_ms = int((time.perf_counter() - start_time) * 1000)
        question_embedding = await _maybe_embed_question(request, question_text)
        question = Question(
            id=uuid.uuid4(),
            user_id=user.id,
            question_text=question_text,
            question_embedding=question_embedding,
            answer_text=full_text,
            quick_answer=metadata.get("quick_answer"),
            risk_level=metadata.get("risk_level"),
            confidence_score=metadata.get("confidence_score"),
            consult_expert=bool(metadata.get("consult_expert", False)),
            affected_teams=metadata.get("affected_teams", []),
            citations=metadata.get("citations", []),
            recommended_actions=metadata.get("recommended_actions", []),
            chunks_used=[c.to_dict() for c in chunks],
            model_used=model_used,
            credit_deducted=True,
            streaming_completed=True,
            latency_ms=latency_ms,
        )
        db.add(question)
        new_balance = await deduct_credit(db, user.id)
        await db.commit()

        # Low-credit notification at thresholds 5 or 2
        if new_balance in (5, 2):
            try:
                email_svc = EmailService()
                await email_svc.send_low_credits_email(user.email, new_balance)
            except Exception:
                logger.warning("low_credit_email_failed", user_id=str(user.id))

        done_data = json.dumps(
            {
                "question_id": str(question.id),
                "credit_balance": new_balance,
            }
        )
        yield f"event: done\ndata: {done_data}\n\n"

        # Cache
        await rag.cache_answer(
            question_text,
            {
                "id": str(question.id),
                "question_text": question.question_text,
                "answer_text": question.answer_text,
                "quick_answer": metadata.get("quick_answer"),
                "risk_level": metadata.get("risk_level"),
                "confidence_score": metadata.get("confidence_score"),
                "consult_expert": bool(metadata.get("consult_expert", False)),
                "affected_teams": metadata.get("affected_teams", []),
                "citations": metadata.get("citations", []),
                "recommended_actions": metadata.get("recommended_actions", []),
                "model_used": model_used,
                "credit_deducted": True,
                "streaming_completed": True,
                "latency_ms": latency_ms,
                "feedback": None,
                "created_at": question.created_at.isoformat(),
            },
        )

    except Exception:
        logger.error("stream_error", exc_info=True)
        error_data = json.dumps({"error": "An error occurred during streaming"})
        yield f"event: error\ndata: {error_data}\n\n"


# ---------------------------------------------------------------------------
# GET /questions — history
# ---------------------------------------------------------------------------


@router.get("", response_model=QuestionListResponse)
async def list_questions(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user: User = Depends(require_verified_user),
    db: AsyncSession = Depends(get_db),
) -> QuestionListResponse:
    """Get paginated question history for the current user."""
    count_stmt = select(func.count(Question.id)).where(Question.user_id == user.id)
    total_result = await db.execute(count_stmt)
    total = total_result.scalar() or 0

    stmt = select(Question).where(Question.user_id == user.id).order_by(desc(Question.created_at)).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(stmt)
    questions = list(result.scalars().all())

    return QuestionListResponse(
        data=[QuestionSummary.model_validate(q) for q in questions],
        total=total,
        page=page,
        page_size=page_size,
    )


# ---------------------------------------------------------------------------
# GET /questions/suggestions — similar past questions for autocomplete
# ---------------------------------------------------------------------------


@router.get("/suggestions", response_model=QuestionSuggestionListResponse)
async def question_suggestions(
    request: Request,
    q: str = Query(..., min_length=1, max_length=500),
    limit: int = Query(default=5, ge=1, le=20),
    user: User = Depends(require_verified_user),
    db: AsyncSession = Depends(get_db),
) -> QuestionSuggestionListResponse:
    """Return up to ``limit`` of the current user's past questions most
    similar to ``q`` by cosine distance on ``question_embedding``.

    Returns an empty list when the partial query is shorter than 5 chars
    (noise floor) or when embeddings aren't available.
    """
    if len(q.strip()) < 5:
        return QuestionSuggestionListResponse(data=[])

    embedding = await _maybe_embed_question(request, q.strip())
    if embedding is None:
        return QuestionSuggestionListResponse(data=[])

    # pgvector cosine distance operator: <=>.
    # This query is Postgres/pgvector-only — callers in SQLite-based unit tests
    # should mock the endpoint rather than hit this path.
    dialect = db.bind.dialect.name if db.bind is not None else ""
    if dialect != "postgresql":
        return QuestionSuggestionListResponse(data=[])

    embedding_str = "[" + ",".join(str(v) for v in embedding) + "]"
    sql = text("""
        SELECT id, question_text, quick_answer
        FROM questions
        WHERE user_id = :user_id
          AND question_embedding IS NOT NULL
          AND streaming_completed = TRUE
        ORDER BY question_embedding <=> CAST(:vec AS vector)
        LIMIT :limit
        """)
    rows = (
        await db.execute(
            sql,
            {"user_id": user.id, "vec": embedding_str, "limit": limit},
        )
    ).all()

    items = [
        QuestionSuggestionItem(
            id=row[0],
            question_text=row[1],
            quick_answer_preview=(row[2] or "")[:120] if row[2] else None,
        )
        for row in rows
    ]
    return QuestionSuggestionListResponse(data=items)


# ---------------------------------------------------------------------------
# GET /questions/{id} — detail
# ---------------------------------------------------------------------------


@router.get("/{question_id}", response_model=QuestionResponse)
async def get_question(
    question_id: uuid.UUID,
    user: User = Depends(require_verified_user),
    db: AsyncSession = Depends(get_db),
) -> QuestionResponse:
    """Get question detail. Only accessible by the question's owner."""
    stmt = select(Question).where(
        Question.id == question_id,
        Question.user_id == user.id,
    )
    result = await db.execute(stmt)
    question = result.scalar_one_or_none()

    if question is None:
        from app.exceptions import RegPulseException

        class QuestionNotFoundError(RegPulseException):
            http_status = 404
            error_code = "QUESTION_NOT_FOUND"

        raise QuestionNotFoundError("Question not found")

    return QuestionResponse(
        data=QuestionDetail.model_validate(question),
        credit_balance=user.credit_balance,
    )


# ---------------------------------------------------------------------------
# GET /questions/{id}/export — compliance brief export
# ---------------------------------------------------------------------------


@router.get("/{question_id}/export")
async def export_question(
    question_id: uuid.UUID,
    user: User = Depends(require_verified_user),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Export a question as a downloadable PDF compliance brief.

    Citations in the PDF include a QR code pointing to the underlying
    RBI circular URL (Sprint 8, G-09).
    """
    stmt = select(Question).where(
        Question.id == question_id,
        Question.user_id == user.id,
    )
    result = await db.execute(stmt)
    question = result.scalar_one_or_none()

    if question is None:
        from app.exceptions import RegPulseException

        class QuestionNotFoundError(RegPulseException):
            http_status = 404
            error_code = "QUESTION_NOT_FOUND"

        raise QuestionNotFoundError("Question not found")

    from app.models.circular import CircularDocument
    from app.services.pdf_export_service import PDFExportService

    # Resolve rbi_url for each cited circular_number (a single IN query).
    raw_citations = list(question.citations or [])
    nums = [c.get("circular_number") for c in raw_citations if c.get("circular_number")]
    url_map: dict[str, str] = {}
    if nums:
        url_rows = await db.execute(
            select(CircularDocument.circular_number, CircularDocument.rbi_url).where(CircularDocument.circular_number.in_(nums))
        )
        url_map = {row[0]: row[1] for row in url_rows.all() if row[0]}

    citations_with_urls = [{**c, "rbi_url": url_map.get(c.get("circular_number") or "")} for c in raw_citations]

    pdf_bytes = PDFExportService.generate_pdf_brief(
        question_text=question.question_text,
        answer_text=question.answer_text,
        quick_answer=question.quick_answer,
        risk_level=question.risk_level,
        affected_teams=question.affected_teams,
        citations=citations_with_urls,
        recommended_actions=question.recommended_actions,
        created_at=question.created_at.isoformat() if question.created_at else None,
    )

    return StreamingResponse(
        iter([pdf_bytes]),
        media_type="application/pdf",
        headers={
            "Content-Disposition": (f'attachment; filename="regpulse_brief_{question_id}.pdf"'),
        },
    )


# ---------------------------------------------------------------------------
# PATCH /questions/{id}/feedback
# ---------------------------------------------------------------------------


@router.patch("/{question_id}/feedback")
async def submit_feedback(
    question_id: uuid.UUID,
    body: FeedbackRequest,
    user: User = Depends(require_verified_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Submit thumbs up/down feedback on a question."""
    stmt = select(Question).where(
        Question.id == question_id,
        Question.user_id == user.id,
    )
    result = await db.execute(stmt)
    question = result.scalar_one_or_none()

    if question is None:
        from app.exceptions import RegPulseException

        class QuestionNotFoundError(RegPulseException):
            http_status = 404
            error_code = "QUESTION_NOT_FOUND"

        raise QuestionNotFoundError("Question not found")

    question.feedback = body.feedback
    question.feedback_comment = body.comment
    await db.commit()

    return {"success": True, "message": "Feedback recorded"}
