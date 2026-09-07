"""Celery tasks for the RegPulse scraper pipeline.

Standalone scraper module. NEVER imports from backend/app/.

Tasks:
- daily_scrape: Full crawl of all RBI sections
- priority_scrape: Crawl Circulars + Master Directions only (every 4h)
- process_document: Full pipeline for a single document URL
- generate_summary: AI summary stub (future prompt)

All tasks are idempotent, use bind=True, and have task_soft_time_limit=300.
"""

from __future__ import annotations

import asyncio
import json
import uuid

import structlog
from celery import shared_task
from scraper.celery_app import app
from celery.exceptions import SoftTimeLimitExceeded
from sqlalchemy import text

from scraper.config import get_scraper_settings
from scraper.crawler.rbi_crawler import RBI_SECTIONS, RBICrawler
from scraper.crawler.rss_fetcher import fetch_all_sources
from scraper.db import get_db_session
from scraper.extractor.metadata_extractor import MetadataExtractor
from scraper.extractor.pdf_extractor import PDFExtractor
from scraper.processor.chunker import TextChunker
from scraper.processor.embedder import Embedder
from scraper.processor.entity_extractor import Entity, EntityExtractor, Triple
from scraper.processor.impact_classifier import ImpactClassifier
from scraper.processor.news_relevance import score_and_link
from scraper.processor.supersession_resolver import SupersessionResolver

logger: structlog.stdlib.BoundLogger = structlog.get_logger("regpulse.tasks")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


_SYSTEM_USER_ID = "00000000-0000-0000-0000-000000000001"


def _audit_log(
    action: str,
    target_table: str | None = None,
    target_id: str | None = None,
    new_value: dict | None = None,
) -> None:
    """Write an admin_audit_log entry attributed to the system user (TD-04)."""
    with get_db_session() as db:
        db.execute(
            text("""
                INSERT INTO admin_audit_log
                    (id, actor_id, action, target_table, target_id, new_value)
                VALUES (:id, :actor_id, :action, :target_table, :target_id, :new_value)
            """),
            {
                "id": str(uuid.uuid4()),
                "actor_id": _SYSTEM_USER_ID,
                "action": action,
                "target_table": target_table,
                "target_id": target_id,
                "new_value": json.dumps(new_value) if new_value else None,
            },
        )
        db.commit()


def _get_seen_urls() -> set[str]:
    """Fetch all rbi_url values already in circular_documents."""
    with get_db_session() as db:
        rows = db.execute(text("SELECT rbi_url FROM circular_documents")).fetchall()
        return {row[0] for row in rows}


def _run_async(coro):  # noqa: ANN001, ANN202
    """Run an async coroutine from sync Celery task context."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Shouldn't happen in Celery, but handle gracefully
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor() as pool:
                return pool.submit(asyncio.run, coro).result()
        return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------


@app.task(bind=True, soft_time_limit=300, max_retries=1, name="scraper.tasks.daily_scrape")
def daily_scrape(self):  # noqa: ANN001, ANN201
    """Full crawl of all RBI sections. Discovers new URLs and enqueues process_document."""
    logger.info("daily_scrape_started")

    # Create a scraper_run record
    run_id = str(uuid.uuid4())
    with get_db_session() as db:
        db.execute(
            text("INSERT INTO scraper_runs (id, status) VALUES (:id, 'RUNNING')"),
            {"id": run_id},
        )
        db.commit()

    try:
        seen_urls = _get_seen_urls()
        crawler = RBICrawler()
        # new_docs = _run_async(crawler.get_new_documents(seen_urls=seen_urls)
        all_docs = _run_async(crawler.crawl())
        new_docs = [doc for doc in all_docs if doc.url not in seen_urls]

        enqueued = 0
        for doc_link in new_docs:
            process_document.delay(
                url=doc_link.url,
                title=doc_link.title,
                doc_type=doc_link.doc_type,
                scraper_run_id=run_id,
            )
            enqueued += 1

        _set_run_enqueued(run_id, enqueued)

        logger.info(
            "daily_scrape_enqueued",
            new_documents=enqueued,
            run_id=run_id,
        )

        _audit_log(
            action="daily_scrape_completed",
            target_table="scraper_runs",
            target_id=run_id,
            new_value={"documents_enqueued": enqueued},
        )

    except SoftTimeLimitExceeded:
        logger.error("daily_scrape_timeout", run_id=run_id)
        _mark_run_failed(run_id, "Soft time limit exceeded")
        raise
    except Exception as exc:
        logger.error("daily_scrape_failed", error=str(exc), run_id=run_id, exc_info=True)
        _mark_run_failed(run_id, str(exc))
        raise


@app.task(bind=True, soft_time_limit=300, max_retries=1, name="scraper.tasks.priority_scrape")
def priority_scrape(self):  # noqa: ANN001, ANN201
    """Priority crawl — Circulars + Master Directions only (every 4h)."""
    logger.info("priority_scrape_started")

    priority_sections = {
        k: v for k, v in RBI_SECTIONS.items() if k in ("Notifications", "Master Directions")
    }

    run_id = str(uuid.uuid4())
    with get_db_session() as db:
        db.execute(
            text("INSERT INTO scraper_runs (id, status) VALUES (:id, 'RUNNING')"),
            {"id": run_id},
        )
        db.commit()

    try:
        seen_urls = _get_seen_urls()
        crawler = RBICrawler()

        all_docs = _run_async(crawler.crawl())
        new_docs = [doc for doc in all_docs if doc.url not in seen_urls]

        enqueued = 0
        for doc_link in new_docs:
            process_document.delay(
                url=doc_link.url,
                title=doc_link.title,
                doc_type=doc_link.doc_type,
                scraper_run_id=run_id,
            )
            enqueued += 1

        _set_run_enqueued(run_id, enqueued)

        logger.info(
            "priority_scrape_enqueued",
            new_documents=enqueued,
            run_id=run_id,
        )

    except SoftTimeLimitExceeded:
        logger.error("priority_scrape_timeout", run_id=run_id)
        _mark_run_failed(run_id, "Soft time limit exceeded")
        raise
    except Exception as exc:
        logger.error("priority_scrape_failed", error=str(exc), run_id=run_id, exc_info=True)
        _mark_run_failed(run_id, str(exc))
        raise


@app.task(
    bind=True,
    soft_time_limit=300,
    max_retries=2,
    default_retry_delay=30,
    name="scraper.tasks.process_document",
)
def process_document(
    self,  # noqa: ANN001
    url: str,
    title: str = "",
    doc_type: str = "OTHER",
    scraper_run_id: str | None = None,
) -> dict:
    """Full pipeline for a single document.

    Pipeline: download → extract text → metadata → chunk → embed → classify impact
    → save to DB → supersession resolution → enqueue generate_summary stub.

    Idempotent: checks if rbi_url already exists before processing.
    """

    doc_type = (doc_type or "OTHER").upper()

    logger.info("process_document_started", url=url, title=title[:80])

    # Idempotency check: skip if URL already indexed
    with get_db_session() as db:
        existing = db.execute(
            text("SELECT id FROM circular_documents WHERE rbi_url = :url"),
            {"url": url},
        ).fetchone()
        if existing:
            logger.info("process_document_skipped_duplicate", url=url)
            if scraper_run_id:
                _increment_run_processed(scraper_run_id)
            return {"status": "skipped", "reason": "duplicate", "url": url}

    try:
        # Step 1: Download + extract text
        pdf_extractor = PDFExtractor()
        extracted = _run_async(pdf_extractor.extract(url))

        if not extracted.raw_text.strip():
            logger.warning(
                "process_document_empty_text",
                url=url,
                extraction_method=extracted.extraction_method,
                warnings=extracted.warnings,
            )
            # Increment failed_extractions counter on the scraper run
            if scraper_run_id:
                _increment_failed_extractions(scraper_run_id, url, extracted.warnings)
                _increment_run_failed(
                    scraper_run_id,
                    url,
                    "Document extraction returned empty text",
                )
            return {"status": "skipped", "reason": "empty_text", "url": url}

        # Step 2: Extract metadata
        metadata_extractor = MetadataExtractor()
        metadata = metadata_extractor.extract(extracted.raw_text, source_url=url)

        # Use extracted title if not provided by crawler
        effective_title = title or metadata.circular_number or url.split("/")[-1]

        # Step 3: Chunk text
        chunker = TextChunker()
        chunks = chunker.chunk(extracted.raw_text)

        if not chunks:
            logger.warning("process_document_no_chunks", url=url)
            if scraper_run_id:
                _increment_run_failed(
                    scraper_run_id,
                    url,
                    "No chunks produced from extracted document text",
                )
            return {"status": "skipped", "reason": "no_chunks", "url": url}

        # Step 4: Generate embeddings
        embedder = Embedder()
        chunk_texts = [c.text for c in chunks]
        embeddings = embedder.embed_chunks(chunk_texts)

        # Step 5: Classify impact level
        summary_excerpt = extracted.raw_text[:500]
        classifier = ImpactClassifier()
        impact_level = classifier.classify(
            title=effective_title,
            summary=summary_excerpt,
            department=metadata.department or "",
        )

        # Step 6: Save to database (single transaction)
        doc_id = str(uuid.uuid4())
        # In DEMO_MODE the admin-review queue would never be drained — auto-approve so
        # the Library and search surfaces actually show ingested circulars.
        pending_review = not get_scraper_settings().DEMO_MODE
        with get_db_session() as db:
            # Insert circular_documents row
            db.execute(
                text("""
                    INSERT INTO circular_documents (
                        id, circular_number, title, doc_type, department,
                        issued_date, effective_date, rbi_url, status,
                        impact_level, action_deadline, affected_teams, tags,
                        pending_admin_review, scraper_run_id
                    ) VALUES (
                        :id, :circular_number, :title, :doc_type, :department,
                        :issued_date, :effective_date, :rbi_url, 'ACTIVE',
                        :impact_level, :action_deadline, :affected_teams, :tags,
                        :pending_admin_review, :scraper_run_id
                    )
                """),
                {
                    "id": doc_id,
                    "circular_number": metadata.circular_number,
                    "title": effective_title,
                    "doc_type": doc_type,
                    "department": metadata.department,
                    "issued_date": metadata.issued_date,
                    "effective_date": metadata.effective_date,
                    "rbi_url": url,
                    "impact_level": impact_level,
                    "action_deadline": metadata.action_deadline,
                    "affected_teams": json.dumps(metadata.affected_teams),
                    "tags": json.dumps([]),
                    "pending_admin_review": pending_review,
                    "scraper_run_id": scraper_run_id,
                },
            )

            # Insert document_chunks rows with embeddings (TD-08)
            for i, chunk in enumerate(chunks):
                emb = embeddings[i] if i < len(embeddings) else None
                emb_str = "[" + ",".join(str(x) for x in emb) + "]" if emb else None
                db.execute(
                    text("""
                        INSERT INTO document_chunks (
                            id, document_id, chunk_index, chunk_text, token_count, embedding
                        ) VALUES (
                            :id, :document_id, :chunk_index, :chunk_text, :token_count,
                            CAST(:embedding AS vector)
                        )
                    """),
                    {
                        "id": str(uuid.uuid4()),
                        "document_id": doc_id,
                        "chunk_index": chunk.chunk_index,
                        "chunk_text": chunk.text,
                        "token_count": chunk.token_count,
                        "embedding": emb_str,
                    },
                )

            db.commit()

        logger.info(
            "process_document_saved",
            url=url,
            doc_id=doc_id,
            circular_number=metadata.circular_number,
            impact_level=impact_level,
            chunks=len(chunks),
        )

        # Step 6.5: Knowledge graph extraction (Sprint 3 Pillar A)
        try:
            extractor = EntityExtractor()
            entities, triples = extractor.extract(
                extracted.raw_text,
                circular_number=metadata.circular_number,
                title=effective_title,
            )
            if entities or triples:
                with get_db_session() as db:
                    persist_kg(
                        db,
                        entities=entities,
                        triples=triples,
                        source_document_id=doc_id,
                    )
                    db.commit()
        except Exception:
            logger.exception("kg_extraction_failed_for_document", doc_id=doc_id)

        # Step 7: Supersession resolution
        if metadata.supersession_refs:
            resolver = SupersessionResolver()
            with get_db_session() as db:
                resolved = resolver.resolve(db, doc_id, metadata.supersession_refs)
                if resolved > 0:
                    db.commit()
                logger.info(
                    "supersession_resolved",
                    doc_id=doc_id,
                    refs=metadata.supersession_refs,
                    resolved_count=resolved,
                )

        # Step 8: Enqueue AI summary generation (stub task)
        generate_summary.delay(document_id=doc_id)

        # The document has completed the main ingestion pipeline.
        if scraper_run_id:
            _increment_run_processed(scraper_run_id)

        return {
            "status": "success",
            "document_id": doc_id,
            "circular_number": metadata.circular_number,
            "impact_level": impact_level,
            "chunks": len(chunks),
            "url": url,
        }

    except SoftTimeLimitExceeded as exc:
        logger.error("process_document_timeout", url=url)

        # Treat a timeout like any other transient failure. Only count it
        # against the scraper run after all retries have been exhausted.
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc)

        logger.error("process_document_max_retries", url=url)

        if scraper_run_id:
            _increment_run_failed(
                scraper_run_id,
                url,
                "Soft time limit exceeded",
            )

        return {
            "status": "failed",
            "url": url,
            "error": "Soft time limit exceeded",
        }

    except Exception as exc:
        logger.error(
            "process_document_failed",
            url=url,
            error=str(exc),
            exc_info=True,
        )

        # Retry transient failures. Do not increment documents_failed on
        # intermediate attempts because the document may still succeed.
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc)

        logger.error("process_document_max_retries", url=url)

        if scraper_run_id:
            _increment_run_failed(
                scraper_run_id,
                url,
                str(exc),
            )

        return {
            "status": "failed",
            "url": url,
            "error": str(exc),
        }


@app.task(bind=True, soft_time_limit=300, name="scraper.tasks.generate_summary")
def generate_summary(self, document_id: str) -> dict:  # noqa: ANN001
    """Generate AI summary for a circular document using Claude Haiku.

    Minimal inline implementation — fetches chunks, concatenates up to 4,000 chars,
    calls Haiku for a 3-sentence summary, saves ai_summary, sets pending_admin_review=TRUE.
    Full SummaryService class replaces this in REG-169 (Prompt 42).
    """
    import anthropic

    from scraper.config import get_scraper_settings

    logger.info("generate_summary_started", document_id=document_id)

    try:
        # Fetch chunk texts ordered by chunk_index
        with get_db_session() as db:
            rows = db.execute(
                text(
                    "SELECT chunk_text FROM document_chunks "
                    "WHERE document_id = :doc_id ORDER BY chunk_index"
                ),
                {"doc_id": document_id},
            ).fetchall()

        if not rows:
            logger.warning("generate_summary_no_chunks", document_id=document_id)
            return {"status": "skipped", "reason": "no_chunks", "document_id": document_id}

        # Concatenate chunks up to 4,000 chars
        combined = ""
        for row in rows:
            if len(combined) + len(row[0]) > 4000:
                remaining = 4000 - len(combined)
                if remaining > 0:
                    combined += " " + row[0][:remaining]
                break
            combined += " " + row[0] if combined else row[0]

        # Call Claude Haiku
        settings = get_scraper_settings()
        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        response = client.messages.create(
            model=settings.LLM_SUMMARY_MODEL,
            max_tokens=300,
            system=(
                "You are an RBI regulatory document summariser. "
                "Produce exactly 3 concise sentences summarising the key points, "
                "requirements, and impact of the circular. No preamble."
            ),
            messages=[{"role": "user", "content": combined}],
        )
        summary_text = response.content[0].text.strip()

        # Save summary; mark for admin review unless we're in DEMO_MODE.
        pending_review = not get_scraper_settings().DEMO_MODE
        with get_db_session() as db:
            db.execute(
                text(
                    "UPDATE circular_documents SET ai_summary = :summary, "
                    "pending_admin_review = :pending_admin_review, updated_at = now() "
                    "WHERE id = :doc_id"
                ),
                {
                    "summary": summary_text,
                    "pending_admin_review": pending_review,
                    "doc_id": document_id,
                },
            )
            db.commit()

        logger.info(
            "generate_summary_completed",
            document_id=document_id,
            summary_length=len(summary_text),
        )
        return {"status": "success", "document_id": document_id, "summary": summary_text}

    except SoftTimeLimitExceeded:
        logger.error("generate_summary_timeout", document_id=document_id)
        raise
    except Exception as exc:
        logger.error(
            "generate_summary_failed", document_id=document_id, error=str(exc), exc_info=True
        )
        return {"status": "failed", "document_id": document_id, "error": str(exc)}


@app.task(bind=True, soft_time_limit=300, name="scraper.tasks.send_staleness_alerts")
def send_staleness_alerts(self, circular_id: str) -> dict:  # noqa: ANN001
    """Send staleness alert emails to users with saved interpretations citing a superseded circular.

    Fetches affected users via saved_interpretations → questions → citations JSONB,
    then sends staleness_alert.html email to each user.
    """
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    from scraper.config import get_scraper_settings

    logger.info("send_staleness_alerts_started", circular_id=circular_id)

    try:
        # Get the superseded circular's number
        with get_db_session() as db:
            circ_row = db.execute(
                text("SELECT circular_number FROM circular_documents WHERE id = :cid"),
                {"cid": circular_id},
            ).fetchone()

        if not circ_row or not circ_row[0]:
            return {"status": "skipped", "reason": "no_circular_number"}

        circular_number = circ_row[0]

        # Find saved_interpretations citing this circular (via questions.citations JSONB)
        pattern = json.dumps([{"circular_number": circular_number}])
        with get_db_session() as db:
            rows = db.execute(
                text("""
                    SELECT DISTINCT u.email, si.name
                    FROM saved_interpretations si
                    JOIN questions q ON si.question_id = q.id
                    JOIN users u ON si.user_id = u.id
                    WHERE q.citations @> :pattern::jsonb
                      AND si.needs_review = TRUE
                      AND u.is_active = TRUE
                """),
                {"pattern": pattern},
            ).fetchall()

        if not rows:
            logger.info("send_staleness_alerts_no_affected_users", circular_id=circular_id)
            return {"status": "skipped", "reason": "no_affected_users"}

        settings = get_scraper_settings()
        sent = 0

        for row in rows:
            email_addr = row[0]
            interpretation_name = row[1]
            try:
                msg = MIMEMultipart("alternative")
                msg["Subject"] = "RegPulse: A regulation you saved has been updated"
                msg["From"] = settings.SMTP_FROM
                msg["To"] = email_addr

                html_body = (
                    "<html><body>"
                    "<p>A regulation you saved has been updated.</p>"
                    f"<p>Your interpretation <strong>{interpretation_name}</strong> "
                    f"references circular <strong>{circular_number}</strong>, "
                    "which has been superseded by a newer circular.</p>"
                    "<p>Your interpretation may need review. Please log in to RegPulse "
                    "to check for updates.</p>"
                    "</body></html>"
                )
                msg.attach(MIMEText(html_body, "html"))

                with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                    server.starttls()
                    server.login(settings.SMTP_USER, settings.SMTP_PASS)
                    server.sendmail(settings.SMTP_FROM, email_addr, msg.as_string())
                sent += 1
            except Exception:
                logger.warning(
                    "staleness_alert_send_failed",
                    email=email_addr,
                    exc_info=True,
                )

        logger.info(
            "send_staleness_alerts_completed",
            circular_id=circular_id,
            circular_number=circular_number,
            affected_users=len(rows),
            emails_sent=sent,
        )
        return {"status": "success", "emails_sent": sent, "circular_number": circular_number}

    except SoftTimeLimitExceeded:
        logger.error("send_staleness_alerts_timeout", circular_id=circular_id)
        raise
    except Exception as exc:
        logger.error(
            "send_staleness_alerts_failed",
            circular_id=circular_id,
            error=str(exc),
            exc_info=True,
        )
        return {"status": "failed", "circular_id": circular_id, "error": str(exc)}


# ---------------------------------------------------------------------------
# Sprint 5 Pillar B: Semantic question clustering
# ---------------------------------------------------------------------------


@app.task(
    bind=True,
    soft_time_limit=600,
    name="scraper.tasks.run_question_clustering",
)
def run_question_clustering(
    self,  # noqa: ANN001
    period_days: int = 30,
) -> dict:
    """Cluster user questions semantically and label each cluster.

    Fetches question embeddings from the last N days, runs k-means with PCA
    dimensionality reduction, generates human-readable labels via Claude Haiku,
    and stores results in question_clusters + questions.cluster_id.

    Runs daily at 03:00 UTC via Celery Beat.
    """
    import numpy as np
    from sklearn.cluster import KMeans
    from sklearn.decomposition import PCA
    from sklearn.metrics import silhouette_score

    import anthropic

    logger.info("run_question_clustering_started", period_days=period_days)
    settings = get_scraper_settings()

    try:
        # Step 1: Fetch questions with embeddings from the period
        with get_db_session() as db:
            rows = db.execute(
                text("""
                    SELECT id, question_text, question_embedding::text
                    FROM questions
                    WHERE question_embedding IS NOT NULL
                      AND created_at >= now() - interval ':days days'
                    ORDER BY created_at DESC
                """.replace(":days", str(int(period_days)))),
            ).fetchall()

        if len(rows) < 15:
            logger.info(
                "run_question_clustering_skipped",
                reason="not_enough_questions",
                count=len(rows),
            )
            return {"status": "skipped", "reason": "fewer_than_15_questions", "count": len(rows)}

        question_ids = [str(r[0]) for r in rows]
        question_texts = [r[1] for r in rows]

        # Parse embedding vectors from PostgreSQL text representation
        embeddings = []
        for r in rows:
            vec_str = r[2]  # "[0.1,0.2,...]"
            vec = [float(x) for x in vec_str.strip("[]").split(",")]
            embeddings.append(vec)

        X = np.array(embeddings, dtype=np.float32)

        # Step 2: PCA to reduce dimensionality (3072 → 50)
        n_components = min(50, X.shape[0] - 1, X.shape[1])
        pca = PCA(n_components=n_components)
        X_reduced = pca.fit_transform(X)

        # Step 3: Find best k via silhouette score
        max_k = min(12, len(rows) // 3)
        min_k = min(5, max_k)

        if min_k < 2:
            min_k = 2
        if max_k < min_k:
            max_k = min_k

        best_k = min_k
        best_score = -1.0

        for k in range(min_k, max_k + 1):
            km = KMeans(n_clusters=k, n_init=10, random_state=42)
            labels = km.fit_predict(X_reduced)
            score = silhouette_score(X_reduced, labels)
            if score > best_score:
                best_score = score
                best_k = k

        # Step 4: Final clustering with best k
        km = KMeans(n_clusters=best_k, n_init=10, random_state=42)
        labels = km.fit_predict(X_reduced)

        # Step 5: For each cluster, find representative questions and generate label
        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        from datetime import date, timedelta

        period_end = date.today()
        period_start = period_end - timedelta(days=period_days)

        cluster_records = []
        for cluster_idx in range(best_k):
            member_indices = [i for i, lbl in enumerate(labels) if lbl == cluster_idx]
            member_texts = [question_texts[i] for i in member_indices]

            # Pick up to 5 representative questions (closest to centroid)
            centroid = km.cluster_centers_[cluster_idx]
            distances = [np.linalg.norm(X_reduced[i] - centroid) for i in member_indices]
            sorted_indices = sorted(range(len(member_indices)), key=lambda x: distances[x])
            rep_indices = sorted_indices[:5]
            rep_questions = [member_texts[i] for i in rep_indices]

            # Generate label via Claude Haiku
            try:
                label_resp = client.messages.create(
                    model=settings.LLM_SUMMARY_MODEL,
                    max_tokens=30,
                    system=(
                        "You label clusters of banking regulatory questions. "
                        "Given sample questions, produce a 3-5 word label. "
                        "No preamble, just the label."
                    ),
                    messages=[
                        {
                            "role": "user",
                            "content": "Questions:\n" + "\n".join(f"- {q}" for q in rep_questions),
                        }
                    ],
                )
                cluster_label = label_resp.content[0].text.strip()[:200]
            except Exception:
                cluster_label = f"Cluster {cluster_idx + 1}"
                logger.exception("cluster_labeling_failed", cluster_idx=cluster_idx)

            # Compute centroid in original embedding space for storage
            original_centroid = X[member_indices].mean(axis=0).tolist()

            cluster_records.append(
                {
                    "cluster_idx": cluster_idx,
                    "label": cluster_label,
                    "rep_questions": rep_questions[:5],
                    "centroid": original_centroid,
                    "count": len(member_indices),
                    "member_question_ids": [question_ids[i] for i in member_indices],
                }
            )

        # Step 6: Persist to database
        with get_db_session() as db:
            # Delete old clusters for overlapping period
            db.execute(
                text("""
                    DELETE FROM question_clusters
                    WHERE period_start = :ps AND period_end = :pe
                """),
                {"ps": str(period_start), "pe": str(period_end)},
            )
            db.commit()

            # Clear old cluster assignments
            db.execute(
                text("""
                    UPDATE questions SET cluster_id = NULL
                    WHERE cluster_id IS NOT NULL
                      AND created_at >= :start
                """),
                {"start": str(period_start)},
            )
            db.commit()

            # Insert new clusters and assign questions
            for rec in cluster_records:
                cluster_id = str(uuid.uuid4())
                centroid_str = "[" + ",".join(str(x) for x in rec["centroid"]) + "]"
                rep_q_sql = (
                    "{"
                    + ",".join(
                        '"' + q.replace('"', '\\"').replace("\\", "\\\\") + '"'
                        for q in rec["rep_questions"]
                    )
                    + "}"
                )

                db.execute(
                    text("""
                        INSERT INTO question_clusters
                            (id, cluster_label, representative_questions, centroid,
                             question_count, period_start, period_end)
                        VALUES
                            (CAST(:id AS uuid), :label, :reps,
                             CAST(:centroid AS vector),
                             :count, :ps, :pe)
                    """),
                    {
                        "id": cluster_id,
                        "label": rec["label"],
                        "reps": rep_q_sql,
                        "centroid": centroid_str,
                        "count": rec["count"],
                        "ps": str(period_start),
                        "pe": str(period_end),
                    },
                )

                # Assign questions to this cluster
                for qid in rec["member_question_ids"]:
                    db.execute(
                        text("""
                            UPDATE questions SET cluster_id = CAST(:cid AS uuid)
                            WHERE id = CAST(:qid AS uuid)
                        """),
                        {"cid": cluster_id, "qid": qid},
                    )

            db.commit()

        logger.info(
            "run_question_clustering_completed",
            period_days=period_days,
            best_k=best_k,
            silhouette=round(best_score, 3),
            total_questions=len(rows),
        )
        return {
            "status": "success",
            "clusters": best_k,
            "silhouette": round(best_score, 3),
            "total_questions": len(rows),
        }

    except SoftTimeLimitExceeded:
        logger.error("run_question_clustering_timeout")
        raise
    except Exception as exc:
        logger.error("run_question_clustering_failed", error=str(exc), exc_info=True)
        return {"status": "failed", "error": str(exc)}


# ---------------------------------------------------------------------------
# Sprint 3 Pillar A: Knowledge graph persistence helper
# ---------------------------------------------------------------------------


def persist_kg(
    db,  # noqa: ANN001
    *,
    entities: list[Entity],
    triples: list[Triple],
    source_document_id: str | None = None,
) -> tuple[int, int]:
    """Upsert entities and insert relationships into kg_entities/kg_relationships.

    Idempotent: entity unique key is (entity_type, canonical_name); relationship
    unique key is (source_entity_id, target_entity_id, relation_type, source_document_id).

    Returns (inserted_entities, inserted_edges).
    """
    inserted_entities = 0
    inserted_edges = 0

    name_to_id: dict[tuple[str, str], str] = {}

    for ent in entities:
        # Upsert: insert if missing, otherwise refresh last_seen_at and merge aliases
        row = db.execute(
            text("""
                INSERT INTO kg_entities (entity_type, canonical_name, aliases, metadata)
                VALUES (CAST(:etype AS kg_entity_type_enum), :name, CAST(:aliases AS jsonb), '{}'::jsonb)
                ON CONFLICT (entity_type, canonical_name) DO UPDATE
                    SET last_seen_at = now()
                RETURNING id
                """),
            {
                "etype": ent.entity_type,
                "name": ent.canonical_name,
                "aliases": json.dumps(list(ent.aliases)),
            },
        ).first()
        if row is not None:
            entity_id = str(row[0])
            name_to_id[(ent.entity_type, ent.canonical_name)] = entity_id
            inserted_entities += 1

    for tr in triples:
        subj_id = name_to_id.get((tr.subject.entity_type, tr.subject.canonical_name))
        obj_id = name_to_id.get((tr.obj.entity_type, tr.obj.canonical_name))
        if subj_id is None or obj_id is None:
            continue
        try:
            db.execute(
                text("""
                    INSERT INTO kg_relationships
                        (source_entity_id, target_entity_id, relation_type,
                         source_document_id, confidence)
                    VALUES
                        (CAST(:s AS uuid), CAST(:t AS uuid),
                         CAST(:r AS kg_relation_type_enum),
                         CAST(:doc AS uuid), 1.0)
                    ON CONFLICT (source_entity_id, target_entity_id, relation_type, source_document_id)
                        DO NOTHING
                    """),
                {
                    "s": subj_id,
                    "t": obj_id,
                    "r": tr.predicate,
                    "doc": source_document_id,
                },
            )
            inserted_edges += 1
        except Exception:
            logger.exception("kg_edge_insert_failed", subject=tr.subject.canonical_name)

    logger.info(
        "kg_persisted",
        entities=inserted_entities,
        edges=inserted_edges,
        document_id=source_document_id,
    )
    return inserted_entities, inserted_edges


# ---------------------------------------------------------------------------
# Sprint 3: News ingest task
# ---------------------------------------------------------------------------


@app.task(
    bind=True,
    name="scraper.tasks.ingest_news",
    queue="scraper",
    max_retries=2,
    default_retry_delay=120,
)
def ingest_news(self, sources: list[str] | None = None) -> dict:  # noqa: ANN001, ARG001
    """Fetch RSS feeds, dedupe, score relevance, persist news_items.

    Sprint 3 Pillar B. Idempotent: skips items already present by
    (source, external_id). Each new item is embedded and matched
    against active circulars; high-confidence matches set
    linked_circular_id.
    """
    settings = get_scraper_settings()
    if not settings.RSS_INGEST_ENABLED:
        logger.info("rss_ingest_disabled")
        return {"status": "skipped", "reason": "RSS_INGEST_ENABLED=false"}

    requested = sources or [s.strip() for s in settings.RSS_SOURCES.split(",") if s.strip()]
    logger.info("ingest_news_start", sources=requested)

    items = fetch_all_sources(requested)
    inserted = 0
    skipped = 0
    linked = 0

    if not items:
        logger.info("ingest_news_no_items")
        return {"status": "success", "inserted": 0, "skipped": 0, "linked": 0}

    embedder: Embedder | None = None
    try:
        embedder = Embedder()
    except Exception:
        logger.exception("embedder_init_failed_news")

    with get_db_session() as db:
        existing_rows = db.execute(
            text("SELECT source::text, external_id FROM news_items")
        ).fetchall()
        existing = {(r[0], r[1]) for r in existing_rows}

        for item in items:
            key = (item.source, item.external_id)
            if key in existing:
                skipped += 1
                continue

            # Each item runs in its own savepoint so a single failure
            # (relevance query, insert, etc.) does not poison the rest.
            try:
                with db.begin_nested():
                    score: float | None = None
                    linked_id: str | None = None
                    if embedder is not None:
                        try:
                            score, linked_id = score_and_link(
                                db,
                                title=item.title,
                                summary=item.summary,
                                embedder=embedder,
                            )
                        except Exception:
                            logger.exception("news_scoring_failed")
                            # Reset the savepoint state for the insert below
                            score, linked_id = None, None

                    db.execute(
                        text("""
                            INSERT INTO news_items
                                (id, source, external_id, title, url, published_at,
                                 summary, raw_html_hash, linked_circular_id,
                                 linked_entity_ids, relevance_score, status, created_at)
                            VALUES
                                (gen_random_uuid(), CAST(:source AS news_source_enum),
                                 :external_id, :title, :url, :published_at, :summary,
                                 :raw_html_hash, CAST(:linked_circular_id AS uuid),
                                 '[]'::jsonb, :relevance_score,
                                 'NEW'::news_status_enum, now())
                            ON CONFLICT (source, external_id) DO NOTHING
                            """),
                        {
                            "source": item.source,
                            "external_id": item.external_id,
                            "title": item.title,
                            "url": item.url,
                            "published_at": item.published_at,
                            "summary": item.summary,
                            "raw_html_hash": item.raw_html_hash,
                            "linked_circular_id": linked_id,
                            "relevance_score": score,
                        },
                    )
                inserted += 1
                if linked_id:
                    linked += 1
            except Exception:
                logger.exception(
                    "news_insert_failed",
                    source=item.source,
                    external_id=item.external_id,
                )

        db.commit()

    logger.info(
        "ingest_news_complete",
        inserted=inserted,
        skipped=skipped,
        linked=linked,
        total_seen=len(items),
    )
    return {
        "status": "success",
        "inserted": inserted,
        "skipped": skipped,
        "linked": linked,
        "total_seen": len(items),
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


@app.task(
    bind=True,
    soft_time_limit=300,
    max_retries=1,
    name="scraper.tasks.process_uploaded_pdf",
)
def process_uploaded_pdf(
    self,  # noqa: ANN001
    upload_id: str,
    title: str = "",
    doc_type: str = "OTHER",
    admin_id: str | None = None,
) -> dict:
    """Process a manually uploaded PDF through the full pipeline.

    Reads PDF bytes from Redis (stored by the backend upload endpoint),
    then runs: text extraction → metadata → chunk → embed → classify →
    save to DB → KG extraction → supersession → summary.

    Unlike process_document, embeddings ARE wired into the chunk INSERT.
    """
    import redis as sync_redis

    logger.info("process_uploaded_pdf_started", upload_id=upload_id)

    settings = get_scraper_settings()

    def _update_upload_status(
        status: str,
        document_id: str | None = None,
        error_message: str | None = None,
    ) -> None:
        with get_db_session() as db:
            params: dict = {"status": status, "uid": upload_id}
            set_parts = ["status = :status"]
            if document_id:
                set_parts.append("document_id = CAST(:doc_id AS uuid)")
                params["doc_id"] = document_id
            if error_message:
                set_parts.append("error_message = :err")
                params["err"] = error_message[:2000]
            if status in ("COMPLETED", "FAILED"):
                set_parts.append("completed_at = now()")
            db.execute(
                text(
                    f"UPDATE manual_uploads SET {', '.join(set_parts)} WHERE id = CAST(:uid AS uuid)"
                ),  # noqa: S608
                params,
            )
            db.commit()

    try:
        # Step 0: Fetch PDF bytes from Redis
        r = sync_redis.from_url(settings.REDIS_URL.replace("/1", "/0"))
        pdf_bytes = r.get(f"upload_pdf:{upload_id}")
        r.close()

        if not pdf_bytes:
            _update_upload_status("FAILED", error_message="PDF bytes not found in Redis (expired?)")
            return {"status": "failed", "upload_id": upload_id, "error": "bytes_not_found"}

        _update_upload_status("PROCESSING")

        # Step 1: Extract text from PDF bytes
        pdf_extractor = PDFExtractor()
        raw_text, page_count = pdf_extractor.extract_pdfplumber(pdf_bytes)

        if not raw_text.strip():
            # Try OCR fallback
            try:
                raw_text, page_count = pdf_extractor.extract_ocr(pdf_bytes)
            except Exception:
                _update_upload_status("FAILED", error_message="PDF text extraction failed (empty)")
                return {"status": "failed", "upload_id": upload_id, "error": "empty_text"}

        if not raw_text.strip():
            _update_upload_status("FAILED", error_message="PDF text extraction returned empty text")
            return {"status": "failed", "upload_id": upload_id, "error": "empty_text"}

        # Step 2: Extract metadata
        source_url = f"upload://{upload_id}"
        metadata_extractor = MetadataExtractor()
        metadata = metadata_extractor.extract(raw_text, source_url=source_url)

        effective_title = title or metadata.circular_number or f"Uploaded PDF {upload_id[:8]}"

        # Step 3: Chunk text
        chunker = TextChunker()
        chunks = chunker.chunk(raw_text)

        if not chunks:
            _update_upload_status("FAILED", error_message="No chunks produced from PDF")
            return {"status": "failed", "upload_id": upload_id, "error": "no_chunks"}

        # Step 4: Generate embeddings (wired into INSERT — fixes TD-08 for uploads)
        embedder = Embedder()
        chunk_texts = [c.text for c in chunks]
        embeddings = embedder.embed_chunks(chunk_texts)

        # Step 5: Classify impact level
        summary_excerpt = raw_text[:500]
        classifier = ImpactClassifier()
        impact_level = classifier.classify(
            title=effective_title,
            summary=summary_excerpt,
            department=metadata.department or "",
        )

        # Step 6: Save to database
        doc_id = str(uuid.uuid4())
        with get_db_session() as db:
            db.execute(
                text("""
                    INSERT INTO circular_documents (
                        id, circular_number, title, doc_type, department,
                        issued_date, effective_date, rbi_url, status,
                        impact_level, action_deadline, affected_teams, tags,
                        pending_admin_review, scraper_run_id, upload_source
                    ) VALUES (
                        :id, :circular_number, :title, :doc_type, :department,
                        :issued_date, :effective_date, :rbi_url, 'ACTIVE',
                        :impact_level, :action_deadline, :affected_teams, :tags,
                        TRUE, NULL, 'manual_upload'
                    )
                """),
                {
                    "id": doc_id,
                    "circular_number": metadata.circular_number,
                    "title": effective_title,
                    "doc_type": doc_type,
                    "department": metadata.department,
                    "issued_date": metadata.issued_date,
                    "effective_date": metadata.effective_date,
                    "rbi_url": source_url,
                    "impact_level": impact_level,
                    "action_deadline": metadata.action_deadline,
                    "affected_teams": json.dumps(metadata.affected_teams),
                    "tags": json.dumps([]),
                },
            )

            # Insert chunks WITH embeddings
            for i, chunk in enumerate(chunks):
                emb = embeddings[i] if i < len(embeddings) else None
                emb_str = "[" + ",".join(str(x) for x in emb) + "]" if emb else None
                db.execute(
                    text("""
                        INSERT INTO document_chunks (
                            id, document_id, chunk_index, chunk_text, token_count, embedding
                        ) VALUES (
                            :id, :document_id, :chunk_index, :chunk_text, :token_count,
                            CAST(:embedding AS vector)
                        )
                    """),
                    {
                        "id": str(uuid.uuid4()),
                        "document_id": doc_id,
                        "chunk_index": chunk.chunk_index,
                        "chunk_text": chunk.text,
                        "token_count": chunk.token_count,
                        "embedding": emb_str,
                    },
                )

            db.commit()

        logger.info(
            "process_uploaded_pdf_saved",
            upload_id=upload_id,
            doc_id=doc_id,
            circular_number=metadata.circular_number,
            impact_level=impact_level,
            chunks=len(chunks),
        )

        # Step 7: Knowledge graph extraction
        try:
            extractor = EntityExtractor()
            entities, triples = extractor.extract(
                raw_text,
                circular_number=metadata.circular_number,
                title=effective_title,
            )
            if entities or triples:
                with get_db_session() as db:
                    persist_kg(
                        db,
                        entities=entities,
                        triples=triples,
                        source_document_id=doc_id,
                    )
                    db.commit()
        except Exception:
            logger.exception("kg_extraction_failed_for_upload", doc_id=doc_id)

        # Step 8: Supersession resolution
        if metadata.supersession_refs:
            resolver = SupersessionResolver()
            with get_db_session() as db:
                resolved = resolver.resolve(db, doc_id, metadata.supersession_refs)
                if resolved > 0:
                    db.commit()

        # Step 9: Enqueue summary generation
        generate_summary.delay(document_id=doc_id)

        # Step 10: Mark upload as completed
        _update_upload_status("COMPLETED", document_id=doc_id)

        # Clean up Redis key
        r = sync_redis.from_url(settings.REDIS_URL.replace("/1", "/0"))
        r.delete(f"upload_pdf:{upload_id}")
        r.close()

        return {
            "status": "success",
            "upload_id": upload_id,
            "document_id": doc_id,
            "circular_number": metadata.circular_number,
            "impact_level": impact_level,
            "chunks": len(chunks),
        }

    except SoftTimeLimitExceeded:
        logger.error("process_uploaded_pdf_timeout", upload_id=upload_id)
        _update_upload_status("FAILED", error_message="Processing timed out")
        raise
    except Exception as exc:
        logger.error(
            "process_uploaded_pdf_failed", upload_id=upload_id, error=str(exc), exc_info=True
        )
        _update_upload_status("FAILED", error_message=str(exc))
        return {"status": "failed", "upload_id": upload_id, "error": str(exc)}


def _mark_run_failed(run_id: str, error_msg: str) -> None:
    """Mark a scraper run as FAILED."""
    try:
        with get_db_session() as db:
            db.execute(
                text(
                    "UPDATE scraper_runs SET completed_at = now(), status = 'FAILED', "
                    "error_message = :error WHERE id = :id"
                ),
                {"error": error_msg[:1000], "id": run_id},
            )
            db.commit()
    except Exception:
        logger.error("mark_run_failed_error", run_id=run_id, exc_info=True)

def _increment_run_processed(run_id: str) -> None:
    """Atomically increment documents_processed and finalize the run if complete."""
    try:
        with get_db_session() as db:
            db.execute(
                text(
                    """
                    UPDATE scraper_runs
                    SET documents_processed = documents_processed + 1
                    WHERE id = :id
                    """
                ),
                {"id": run_id},
            )

            db.execute(
                text(
                    """
                    UPDATE scraper_runs
                    SET completed_at = now(),
                        status = 'COMPLETED'
                    WHERE id = :id
                      AND status = 'RUNNING'
                      AND documents_processed + documents_failed >= documents_enqueued
                    """
                ),
                {"id": run_id},
            )
            db.commit()

        logger.info("run_document_processed", run_id=run_id)

    except Exception:
        logger.error("increment_run_processed_error", run_id=run_id, exc_info=True)


def _increment_run_failed(run_id: str, url: str, error: str) -> None:
    """Atomically increment documents_failed and finalize the run if complete."""
    try:
        with get_db_session() as db:
            db.execute(
                text(
                    """
                    UPDATE scraper_runs
                    SET documents_failed = documents_failed + 1
                    WHERE id = :id
                    """
                ),
                {"id": run_id},
            )

            db.execute(
                text(
                    """
                    UPDATE scraper_runs
                    SET completed_at = now(),
                        status = 'COMPLETED'
                    WHERE id = :id
                      AND status = 'RUNNING'
                      AND documents_processed + documents_failed >= documents_enqueued
                    """
                ),
                {"id": run_id},
            )
            db.commit()

        logger.info(
            "run_document_failed",
            run_id=run_id,
            url=url,
            error=error[:500],
        )

    except Exception:
        logger.error("increment_run_failed_error", run_id=run_id, exc_info=True)


def _set_run_enqueued(run_id: str, count: int) -> None:
    """Record how many document tasks were enqueued for a scraper run."""
    try:
        with get_db_session() as db:
            db.execute(
                text(
                    """
                    UPDATE scraper_runs
                    SET documents_enqueued = :count
                    WHERE id = :id
                    """
                ),
                {"count": count, "id": run_id},
            )

            # A run with zero documents has nothing to wait for.
            if count == 0:
                db.execute(
                    text(
                        """
                        UPDATE scraper_runs
                        SET completed_at = now(),
                            status = 'COMPLETED'
                        WHERE id = :id
                        """
                    ),
                    {"id": run_id},
                )

            db.commit()

        logger.info(
            "run_documents_enqueued",
            run_id=run_id,
            count=count,
        )

    except Exception:
        logger.error("set_run_enqueued_error", run_id=run_id, exc_info=True)

def _increment_failed_extractions(
    run_id: str, url: str, warnings: list[str] | None = None
) -> None:
    """Atomically increment failed_extractions counter on a scraper run."""
    try:
        reason = "; ".join(warnings) if warnings else "unknown"
        with get_db_session() as db:
            db.execute(
                text(
                    "UPDATE scraper_runs SET failed_extractions = failed_extractions + 1 "
                    "WHERE id = :id"
                ),
                {"id": run_id},
            )
            db.commit()
        logger.info(
            "failed_extraction_recorded",
            run_id=run_id,
            url=url,
            reason=reason[:200],
        )
    except Exception:
        logger.error("increment_failed_extractions_error", run_id=run_id, exc_info=True)


# ---------------------------------------------------------------------------
# Subscription renewal check (Gap G-04)
# ---------------------------------------------------------------------------


@app.task(
    bind=True,
    soft_time_limit=300,
    name="scraper.tasks.subscription_renewal_check",
)
def subscription_renewal_check(self) -> dict:  # noqa: ANN001, ARG001
    """Check for expiring subscriptions and send renewal reminders.

    Runs daily at 08:00 IST. For users with plan_auto_renew=TRUE and
    plan_expires_at < now() + 3 days, send a renewal reminder email.
    v1: reminder only — auto-charge requires Razorpay Subscriptions API.
    """
    log = logger.bind(task="subscription_renewal_check")
    log.info("renewal_check_started")

    try:
        with get_db_session() as db:
            rows = db.execute(
                text(
                    "SELECT id, email, plan, plan_expires_at "
                    "FROM users "
                    "WHERE plan != 'free' "
                    "AND plan_auto_renew = TRUE "
                    "AND is_active = TRUE "
                    "AND plan_expires_at IS NOT NULL "
                    "AND plan_expires_at < now() + interval '3 days' "
                    "AND plan_expires_at > now()"
                )
            ).fetchall()

        reminded = 0
        for row in rows:
            try:
                _send_renewal_reminder(row.email, row.plan, row.plan_expires_at)
                reminded += 1
            except Exception:
                log.error(
                    "renewal_reminder_failed",
                    user_id=str(row.id),
                    exc_info=True,
                )

        log.info("renewal_check_completed", reminded=reminded, total_expiring=len(rows))
        return {"status": "ok", "reminded": reminded}
    except Exception as exc:
        log.error("renewal_check_error", exc_info=True)
        return {"status": "error", "error": str(exc)}


def _send_renewal_reminder(email: str, plan: str, expires_at: object) -> None:
    """Send a renewal reminder email via SMTP."""
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    settings = get_scraper_settings()
    subject = "RegPulse — Your subscription is expiring soon"
    html = (
        f"<p>Your <strong>{plan}</strong> plan is expiring on "
        f"<strong>{expires_at}</strong>.</p>"
        "<p>Log in to RegPulse to renew your subscription and continue "
        "accessing regulatory intelligence.</p>"
        '<p><a href="https://regpulse.in/account">Renew Now</a></p>'
    )
    plain = (
        f"Your {plan} plan is expiring on {expires_at}. "
        "Log in to RegPulse to renew: https://regpulse.in/account"
    )

    msg = MIMEMultipart("alternative")
    msg["From"] = settings.SMTP_FROM
    msg["To"] = email
    msg["Subject"] = subject
    msg.attach(MIMEText(plain, "plain", "utf-8"))
    msg.attach(MIMEText(html, "html", "utf-8"))

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
        server.starttls()
        server.login(settings.SMTP_USER, settings.SMTP_PASS)
        server.send_message(msg)

    logger.info("renewal_reminder_sent", domain=email.rsplit("@", 1)[-1])


# ---------------------------------------------------------------------------
# Low-credit notification check (Gap G-05)
# ---------------------------------------------------------------------------


@app.task(
    bind=True,
    soft_time_limit=300,
    name="scraper.tasks.credit_notifications",
)
def credit_notifications(self) -> dict:  # noqa: ANN001, ARG001
    """Check for users with low credit balance and send notification emails.

    Runs daily at 09:00 IST. For free-plan users with credits <= 10
    who haven't been alerted in 7 days, send a low-credit email.
    """
    log = logger.bind(task="credit_notifications")
    log.info("credit_notifications_started")

    try:
        with get_db_session() as db:
            rows = db.execute(
                text(
                    "SELECT id, email, credit_balance "
                    "FROM users "
                    "WHERE credit_balance <= 10 "
                    "AND is_active = TRUE "
                    "AND (last_credit_alert_sent IS NULL "
                    "     OR last_credit_alert_sent < now() - interval '7 days')"
                )
            ).fetchall()

        notified = 0
        for row in rows:
            try:
                _send_low_credit_email(row.email, row.credit_balance)
                # Update last_credit_alert_sent
                with get_db_session() as db:
                    db.execute(
                        text(
                            "UPDATE users SET last_credit_alert_sent = now() "
                            "WHERE id = :id"
                        ),
                        {"id": str(row.id)},
                    )
                    db.commit()
                notified += 1
            except Exception:
                log.error(
                    "credit_notification_failed",
                    user_id=str(row.id),
                    exc_info=True,
                )

        log.info("credit_notifications_completed", notified=notified, total_low=len(rows))
        return {"status": "ok", "notified": notified}
    except Exception as exc:
        log.error("credit_notifications_error", exc_info=True)
        return {"status": "error", "error": str(exc)}


def _send_low_credit_email(email: str, remaining_credits: int) -> None:
    """Send a low-credit warning email via SMTP."""
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    settings = get_scraper_settings()
    subject = "RegPulse — Low credit balance"
    html = (
        f"<p>You have <strong>{remaining_credits}</strong> credit(s) remaining "
        "on RegPulse.</p>"
        "<p>Upgrade your plan to continue asking regulatory questions.</p>"
        '<p><a href="https://regpulse.in/upgrade">Upgrade Now</a></p>'
    )
    plain = (
        f"You have {remaining_credits} credit(s) remaining on RegPulse. "
        "Upgrade to continue: https://regpulse.in/upgrade"
    )

    msg = MIMEMultipart("alternative")
    msg["From"] = settings.SMTP_FROM
    msg["To"] = email
    msg["Subject"] = subject
    msg.attach(MIMEText(plain, "plain", "utf-8"))
    msg.attach(MIMEText(html, "html", "utf-8"))

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
        server.starttls()
        server.login(settings.SMTP_USER, settings.SMTP_PASS)
        server.send_message(msg)

    logger.info("low_credit_email_sent", domain=email.rsplit("@", 1)[-1])
