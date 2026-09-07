# RegPulse — Project Memory

> **Read this file before every Claude Code task.** Read `LEARNINGS.md` before starting any sprint.

---

## Product

B2B SaaS for Indian banking professionals. RAG-powered Q&A over RBI Circulars with cited answers. Work-email-gated, subscription-based, 5 free lifetime credits.

**Status:** Phase 2 (Sprints 1–8) shipped, CI green, v1.0.0-rc. MVP live on GCP in DEMO_MODE since 2026-05-14. Phase D.1/D.2/D.3 (Frontend v2 collaboration backend integration) complete (2026-05-15) — Pulse Dashboard, Team Learnings, Debates all on live persistent backend. SCR-1 (scraper PDF extraction) resolved 2026-05-15 — 93 circulars / 1,208 chunks ingested.

**Strict invariants:**
- Zero-hallucination: multi-signal confidence (0.0–1.0), "Consult Expert" fallback when < 0.5 or zero valid citations.
- HTTPOnly cookie refresh tokens (XSS-resistant). RS256 JWT + jti blacklist.
- RAG corpus = circulars only. News (RSS) and KG entities never enter retrieval.
- KG-driven RAG expansion ON by default (`RAG_KG_EXPANSION_ENABLED=true`).
- Public snippet sharing must NEVER expose `detailed_interpretation` — only `quick_answer` (truncated) + 1 citation, or consult-expert fallback.
- DPDP-compliant: account deletion (OTP-verified, PII anonymisation, cascade) + JSON export at `/api/v1/account`.

---

## Architecture

**Scraper** (`/scraper`): Celery + Python. Crawls rbi.org.in daily → PDF extract → chunk → embed → pgvector. Supersession + impact classification. **Sync** code — never `await`. Standalone — never imports from `backend/`.

**Backend** (`/backend`): FastAPI, SQLAlchemy 2.0 async, Pydantic v2. All endpoints at `/api/v1/`. ~70 endpoints, 12 services, 21 tables.

**Frontend** (`/frontend`): Next.js 14, TypeScript strict, terminal-modern v2 design system (CSS custom-property tokens, Inter Tight + Source Serif 4 + JetBrains Mono), TanStack Query, Zustand. 27 routes. Design source in `files/design-v2/`.

**LLM:** claude-sonnet-4-20250514 + extended thinking (10k budget) primary, gpt-4o fallback. Embeddings: text-embedding-3-large (3072-dim). Reranker: ms-marco-MiniLM-L-6-v2 (skipped in DEMO_MODE).

---

## Schema (21 tables)

Ground truth: `backend/migrations/001`–`006*.sql` + Alembic `c202ee0a4986` (learnings) + `1066cb96e57c` (debates) + `a3f7e2b1c4d0` (failed_extractions).

| Table | Model | Key columns |
|-------|-------|-------------|
| users | `user.py` | email, credits, plan, is_admin, email_verified, password_changed_at |
| sessions | `user.py` | token_hash, expires_at, revoked |
| circular_documents | `circular.py` | title, status, impact_level, affected_teams, tags |
| document_chunks | `circular.py` | chunk_text, embedding vector(3072) |
| questions | `question.py` | answer_text, quick_answer, risk_level, **confidence_score**, **consult_expert**, citations JSONB, question_embedding |
| action_items | `question.py` | title, assigned_team, priority, status, due_date |
| saved_interpretations | `question.py` | name, tags, needs_review |
| prompt_versions | `admin.py` | version_tag, prompt_text, is_active |
| subscription_events | `subscription.py` | order_id, plan, amount_paise, status |
| scraper_runs | `scraper.py` | status, documents_processed/failed, failed_extractions |
| admin_audit_log | `admin.py` | actor_id, action, target_table, old/new_value |
| analytics_events | `admin.py` | user_hash, event_type, event_data |
| pending_domain_reviews | `user.py` | domain, mx_valid, approved |
| kg_entities (S3) | `kg.py` | entity_type, canonical_name, aliases JSONB |
| kg_relationships (S3) | `kg.py` | source/target_entity_id, relation_type, source_document_id |
| news_items (S3) | `news.py` | source, external_id, title, url, linked_circular_id, relevance_score |
| public_snippets (S3) | `snippet.py` | slug, question_id, snippet_text, top_citation, consult_expert |
| manual_uploads (S5) | `admin.py` | admin_id, filename, status, document_id, error_message |
| question_clusters (S5) | `admin.py` | cluster_label, representative_questions, centroid, period_start/end |
| learnings (D.2) | `learning.py` | user_id, title, note, source_type, source_id, source_ref, tags |
| debate_threads (D.3) | `debate.py` | title, source_circular_id, created_by, stats JSONB |
| debate_replies (D.3) | `debate.py` | thread_id, user_id, content, stance enum (AGREE/DISAGREE/NEUTRAL) |

Indexes: ivfflat on embeddings (lists=100; **disabled on Cloud SQL — pgvector 2000-dim cap, see LEARNINGS LGCP.5**), GIN on FTS + citations JSONB + tags JSONB, btree on FKs/status/timestamps.

---

## Business Rules

1. RAG-only answers — no training knowledge. Injection guard layered on top.
2. Citation validation — strip circular numbers not in retrieved chunks.
3. Credits deducted only on success (`SELECT FOR UPDATE`). Cache hits free.
4. Work email only — 250+ domain blocklist + MX check.
5. No PDF hosting — `rbi_url` links to rbi.org.in only.
6. Superseded circulars excluded from RAG (`WHERE status='ACTIVE'`).
7. AI summaries need admin approval before display.
8. PII never reaches LLM.
9. Action items auto-generated from `recommended_actions`.
10. Re-indexed circular → `saved_interpretations.needs_review=TRUE`.

---

## RAG Pipeline

```
1. Normalise + SHA256 hash → Redis cache check (24h TTL, no credit)
2. Embed question → Redis-cached
3. PARALLEL: pgvector cosine ANN + PostgreSQL FTS (WHERE status='ACTIVE')
4. RRF fusion: score = Σ 1/(60 + rank_i)
5. Dedup: max RAG_MAX_CHUNKS_PER_DOC per document
6. Cross-encoder rerank (ProcessPoolExecutor, 30s timeout) → top K
7. < 2 chunks → "Consult Expert" fallback (no LLM call)
8. Injection guard + XML wrapping → LLM (Anthropic, GPT-4o fallback)
9. Validate citations → compute confidence (3 signals)
10. Confidence < 0.5 or zero citations → "Consult Expert" fallback
11. INSERT + deduct credit → cache → SSE/JSON
```

LLM returns: `{quick_answer, detailed_interpretation, risk_level, confidence_score, consult_expert, affected_teams, citations[], recommended_actions[]}`

---

## Patterns (Hard Constraints)

**Backend:**
- Never import from `scraper/` — use `embedding_service.py`
- `app.state.cross_encoder` may be None — check before use
- Exception classes in `app.exceptions` only (7 subclasses)
- Auth chain: get_current_user → require_active → require_verified → require_admin/credits
- Admin mutations write to `admin_audit_log`. Admin read-only/sandbox actions log to `analytics_events` (e.g. `admin_test_question`).
- Subscription plans defined in `PLANS` dict in `subscription_service.py`.
- Razorpay webhook at `/subscriptions/webhook` — excluded from CORS, verified via HMAC-SHA256.
- `POST /questions` uses `response_model=None` (Union: JSON or StreamingResponse).
- `questions.question_embedding` persisted on every new row — fed by `_maybe_embed_question()`, hits EmbeddingService Redis cache.
- Shared RAG/LLM wiring in `app/dependencies/rag.py` (`build_rag_service`, `build_llm_service`).
- **Route ordering:** `/foo/stats`, `/foo/suggestions`, `/foo/updates` MUST be declared BEFORE any `/foo/{id}` path-param route.
- pgvector-only SQL must check `db.bind.dialect.name == 'postgresql'` and short-circuit for SQLite unit tests.
- User mutations from routes (e.g. `last_seen_updates = now()`) must use `UPDATE users SET ... WHERE id = :id` — the user ORM object may be attached to a different session than the route's `db`.
- TIMESTAMPTZ columns must declare `DateTime(timezone=True)` or asyncpg rejects naive datetimes.
- Config: `from app.config import get_settings` (@lru_cache singleton). All errors: `{"success": false, "error": "...", "code": "..."}`.
- All ORM enums use `enum.StrEnum`. ruff B008 + E402 (conftest) suppressed in pyproject.
- reportlab `Paragraph` treats `&`, `<`, `>` as markup — always pass user-facing strings through `pdf_export_service._escape()`.

**Frontend:**
- Access token in Zustand memory only — NEVER localStorage. Refresh token via backend `Set-Cookie HttpOnly; Secure; SameSite=lax`. Frontend NEVER touches `document.cookie`.
- `authStore.setAuth(user, accessToken)` — 2 args. `clearAuth` calls `/api/v1/auth/logout`.
- Credit balance updates without re-auth: `useAuthStore.setState({user: {...user, credit_balance: n}})`.
- TanStack Query for data; `QueryProvider` wraps app in root layout.
- SSE via `fetch` + `ReadableStream` (not EventSource).
- **Frontend v2 design system**: tokens in `globals.css` — `var(--ink)`, `var(--signal)`, `var(--panel)`. Dark mode via `html.dark` class. Tokens NEVER in `tailwind.config.ts`.
- **Primitives** (`components/design/Primitives.tsx`): `Pill`, `Btn`, `Icon`, `Avatar`, `Sparkline`, `MiniStat`, `ToastProvider`/`useToast`, `Panel`, `cn`.
- **AppShell** (`components/shell/`): `TopBar`, `Sidebar`, `Ticker`, `CommandPalette` (⌘K), `TweaksPanel`.
- Mock fallback: pages degrade to `RP_DATA` from `lib/mockData.ts` when backend returns empty — never show "no data" zero-states.
- `<Link>` + `<button>` child is invalid HTML — use `router.push` in onClick or styled `<a>`.

---

## DEMO_MODE

When `DEMO_MODE=true` (blocked in prod):
- OTP fixed `123456` (no email sent). Work email validation skipped. Cross-encoder skipped (fast startup). Razorpay/SMTP use dummy keys.
- `OTP_MAX_SENDS_PER_HOUR` should be raised (default 3 too low).
- Scraper auto-approves new circulars (`pending_admin_review=FALSE` on INSERT + AI-summary UPDATE) so the Library and RAG surfaces actually show them. See `scraper/tasks.py:process_document` + `generate_summary`. Prod keeps the admin gate.
- Backend cookie needs `COOKIE_SECURE=true, COOKIE_SAMESITE=none` while frontend + backend live on different `*.run.app` subdomains. Switch back to `lax` once custom domain (Phase 5) lands. Wired via `config.py:COOKIE_SECURE/COOKIE_SAMESITE`.

## Localhost

```bash
cp .env.example .env   # set DEMO_MODE=true
docker compose up --build -d
# Frontend: http://localhost:3000  |  API docs: http://localhost:8000/api/v1/docs
```

Scraper tasks route to `scraper` queue — worker must consume with `-Q celery,scraper`.

---

## Technical Debt (open)

| ID | Issue | Plan |
|---|---|---|
| TD-01 | Scraper writes directly to backend DB | API isolation in v2 (Sprint 9+) |
| TD-03 | Manual api.ts client | OpenAPI codegen (Sprint 9) |
| TD-09 | `BACKEND_PUBLIC_URL` unset in demo | Set when GCP custom domain lands |
| G-10 | Simple try/catch LLM fallback — no circuit-open tracking | `pybreaker` in requirements.txt; wire in Sprint 9 |
| OP-1 | `questions.question_embedding` NULL for pre-Sprint 8 rows | Run `scripts/backfill_question_embeddings.py` once in production |
| OP-2 | Admin sandbox doesn't swap `PromptVersion` at LLM call time | Wire `PromptVersion.prompt_text` through `LLMService` in Sprint 9 |
| OP-3 | ~373 rbidocs PDFs blocked by RBI WAF ("Request Rejected") | Add User-Agent header / retry with backoff; or accept lower yield |
| **CORS-DEMO-1** | **Browser-login loops on `*.run.app` demo** — backend cookie is invisible to Next.js middleware running on a different PSL site. Fix: (A) Next.js rewrites proxy `/api/*` through frontend origin, OR (B) Phase 5 custom domain. See LEARNINGS L9.6. | **Top priority next session** |

Resolved: TD-02/04/05/06/07/08/10/11/12 (Sprints 1–6); G-01–G-09, G-12 (Sprints 7–8); scraper `ModuleNotFoundError` (`aed8425`); **SCR-1** (PDF extraction + crawler empty-text links, `16ba70c`); admin-review gate for DEMO (this session, `scraper:rc4`).

---

## GCP Deployment State

**Source of truth: `GCP_DEPLOY_RUNBOOK.md`.** Project `regpulse-495309` (asia-south1, billing `0130B1-10E7BB-34EF9C`).

**Live URLs (Cloud Run auto-generated; custom domain deferred to Phase 5):**
- Frontend: `https://regpulse-frontend-yvigu4ssea-el.a.run.app`
- Backend: `https://regpulse-backend-yvigu4ssea-el.a.run.app`
- API docs: `https://regpulse-backend-yvigu4ssea-el.a.run.app/api/v1/docs`

**Infra:** Cloud SQL `regpulse-db` (Postgres 16 Enterprise HA), Memorystore Redis `regpulse-redis` (Basic 1GB), VPC Connector `regpulse-connector`, 13 Secret Manager secrets, runtime SA `regpulse-runtime@`. Backend `regpulse/backend:rc4` (rev `00009-v8h`), frontend `regpulse/frontend:rc1`, scraper `regpulse/scraper:rc4`. Both services `min-instances=1`. Mode: `ENVIRONMENT=staging, DEMO_MODE=true, FREE_CREDIT_GRANT=999999, COOKIE_SECURE=true, COOKIE_SAMESITE=none`.

**Artifact Registry:** `asia-south1-docker.pkg.dev/regpulse-495309/regpulse` (`backend:rc4`, `frontend:rc1`, `scraper:rc4`)

**Scraper:** Cloud Run Job `regpulse-scraper` (2 vCPU, 2Gi, 1h timeout, `scraper:rc4`). Daily Cloud Scheduler `regpulse-scraper-daily` at 20:30 UTC / 02:00 IST. SCR-1 resolved (`16ba70c`): 93 circulars, 1,208 chunks. Remaining gap: ~373 rbidocs PDFs blocked by RBI WAF (OP-3). Bulk-approve of existing 93 rows done as one-shot SQL UPDATE (2026-05-15).

**Observability:** Log-based metrics (`regpulse_scraper_documents/errors/success`) + Cloud Monitoring Dashboard via `scripts/gcp/phase6_setup_observability.sh`.

**Deferred:**
- Phase 4H (Celery GCE) — only needed when leaving DEMO_MODE.
- Phase 5 (custom domain), Phase 6 (GitHub Actions WIF auto-deploy), Phase 7 (smoke + v1.0.0 cut).
- ANN indexes on embeddings (`halfvec(3072)` migration for ivfflat compatibility).
- 🗓️ **2026-05-16:** Rotate OpenAI + Anthropic API keys (transcript-exposed). Confirm/revoke `shubhamkadam1802@gmail.com` Editor+DevOps access.
