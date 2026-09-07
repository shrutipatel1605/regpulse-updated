# RegPulse — Test Case Inventory

> Living inventory of all test scenarios — functional, technical, AI eval, load, and stress.
> Status key: **A** = automated, **M** = manual/UAT, **P** = planned (not yet implemented).
>
> Updated: 2026-04-14 (Sprint 7). See also `UAT_PLAN.md` (208 scenarios) and `UAT_RESULTS.md` (81/81 automated UAT).

---

## 1. Existing Test Summary

| Category | File | Tests | Type | Runs in CI |
|----------|------|-------|------|------------|
| Unit — RAG | `backend/tests/unit/test_rag_service.py` | 10 | Unit | Yes |
| Unit — LLM | `backend/tests/unit/test_llm_service.py` | 13 | Unit | Yes |
| Unit — LLM Exceptions | `backend/tests/unit/test_llm_exceptions.py` | 10 | Unit | Yes |
| Unit — PII Exclusion | `backend/tests/unit/test_pii_exclusion.py` | 5 | Unit | Yes |
| Unit — Snippets | `backend/tests/unit/test_snippet_service.py` | 13 | Unit | Yes |
| Unit — Subscriptions | `backend/tests/unit/test_subscriptions.py` | 10 | Unit | Yes |
| Unit — Circulars Router | `backend/tests/unit/test_circulars_router.py` | 17 | Unit | Yes |
| Unit — Library Service | `backend/tests/unit/test_circular_library_service.py` | 12 | Unit | Yes |
| Integration — Auth | `backend/tests/integration/test_auth_flow.py` | 10 | Integration | Yes |
| Unit — RSS Fetcher | `scraper/tests/test_rss_fetcher.py` | 14 | Unit | No |
| Unit — Entity Extractor | `scraper/tests/test_entity_extractor.py` | 14+ | Unit | No |
| Unit — Audit Log | `scraper/tests/test_audit_log.py` | 4 | Unit | No |
| Eval — Hallucination | `backend/tests/evals/test_hallucination.py` | 21 | Eval | No |
| Eval — Retrieval | `backend/tests/evals/test_retrieval.py` | 8 | Integration/Eval | No |
| Load — k6 | `tests/load/k6_load_test.js` | 3 scenarios | Load | No |
| Smoke — Launch | `scripts/launch_check.sh` | 10 checks | Smoke | No |
| Unit — Account (DPDP) | `backend/tests/unit/test_account.py` | 6 | Unit | Yes |
| **Total** | | **~170+** | | |

---

## 2. Functional Test Cases

### 2.1 Authentication & Authorization

| ID | Scenario | Precondition | Steps | Expected | Status | File |
|----|----------|-------------|-------|----------|--------|------|
| F-AUTH-01 | Register with valid work email | None | POST `/auth/register` with work email | 201, OTP sent | A | `test_auth_flow.py` |
| F-AUTH-02 | Register with personal email | None | POST `/auth/register` with gmail.com | 400, INVALID_EMAIL | P | |
| F-AUTH-03 | Verify OTP success | Registered user | POST `/auth/verify-otp` with correct OTP | 200, access_token + refresh cookie | P | |
| F-AUTH-04 | Verify OTP wrong code | Registered user | POST `/auth/verify-otp` with wrong OTP | 401 | P | |
| F-AUTH-05 | Verify OTP expired | Registered, OTP older than 10m | POST `/auth/verify-otp` | 401, OTP_EXPIRED | P | |
| F-AUTH-06 | Verify OTP max attempts | 5 failed attempts | POST `/auth/verify-otp` | 429, MAX_ATTEMPTS | P | |
| F-AUTH-07 | Login with verified email | Verified user | POST `/auth/login` | 200, OTP sent | P | |
| F-AUTH-08 | Refresh token rotation | Valid refresh cookie | POST `/auth/refresh` | 200, new access_token, new refresh cookie | P | |
| F-AUTH-09 | Refresh with revoked token | Revoked session | POST `/auth/refresh` | 401 | A | `test_auth_flow.py` |
| F-AUTH-10 | Logout clears cookie | Authenticated | POST `/auth/logout` | 200, refresh cookie cleared, jti blacklisted | P | |
| F-AUTH-11 | Token issued before password change | Password changed after token mint | Any authenticated request | 401, TOKEN_STALE | A | `test_auth_flow.py` |
| F-AUTH-12 | Deactivated user rejected | is_active=false | Any authenticated request | 401 | A | `test_auth_flow.py` |
| F-AUTH-13 | Unverified user blocked from protected routes | email_verified=false | GET `/questions` | 403 | A | `test_auth_flow.py` |
| F-AUTH-14 | Non-admin blocked from admin routes | is_admin=false | GET `/admin/dashboard` | 403 | A | `test_auth_flow.py` |
| F-AUTH-15 | Zero credits blocked from ask | credit_balance=0 | POST `/questions` | 402 | A | `test_auth_flow.py` |
| F-AUTH-16 | DEMO_MODE fixed OTP | DEMO_MODE=true | Register + verify with 123456 | 200 | M | UAT-6 |
| F-AUTH-17 | Rate limit OTP sends | 3 sends in 1 hour | POST `/auth/register` 4th time | 429 | P | |

### 2.2 Circular Library

| ID | Scenario | Precondition | Steps | Expected | Status | File |
|----|----------|-------------|-------|----------|--------|------|
| F-LIB-01 | List circulars (paginated) | Seeded circulars | GET `/circulars?page=1&page_size=10` | 200, paginated results | A | `test_circulars_router.py` |
| F-LIB-02 | Filter by doc_type | Seeded circulars | GET `/circulars?doc_type=Circular` | Only Circular type returned | A | `test_circulars_router.py` |
| F-LIB-03 | Filter by status | Seeded circulars | GET `/circulars?status=ACTIVE` | Only ACTIVE docs | A | `test_circulars_router.py` |
| F-LIB-04 | Hybrid search | Seeded circulars | GET `/circulars/search?q=KYC` | Relevant results ranked by RRF | A | `test_circulars_router.py` |
| F-LIB-05 | Autocomplete | Seeded circulars | GET `/circulars/autocomplete?q=kno` | Matching titles/numbers | A | `test_circulars_router.py` |
| F-LIB-06 | Circular detail | Seeded circular | GET `/circulars/{id}` | 200, full detail with chunks | A | `test_circulars_router.py` |
| F-LIB-07 | Circular not found | None | GET `/circulars/{bad-uuid}` | 404 | A | `test_circulars_router.py` |
| F-LIB-08 | Facets — departments | Seeded circulars | GET `/circulars/facets/departments` | List of departments | A | `test_circulars_router.py` |
| F-LIB-09 | Facets — tags | Seeded circulars | GET `/circulars/facets/tags` | List of tags | A | `test_circulars_router.py` |
| F-LIB-10 | Library browsable without auth | Not logged in | GET `/circulars` | 200 (no auth required) | A | `test_circulars_router.py` |
| F-LIB-11 | Search requires auth | Not logged in | GET `/circulars/search?q=test` | 403 | A | `test_circulars_router.py` |

### 2.3 RAG Q&A

| ID | Scenario | Precondition | Steps | Expected | Status | File |
|----|----------|-------------|-------|----------|--------|------|
| F-QA-01 | Ask question (JSON response) | Verified user, credits > 0 | POST `/questions` Accept: application/json | 200, answer with citations + confidence | P | |
| F-QA-02 | Ask question (SSE stream) | Verified user, credits > 0 | POST `/questions` Accept: text/event-stream | SSE tokens + citations event | P | |
| F-QA-03 | Credit deducted on success | credit_balance=5 | POST `/questions` (successful answer) | credit_balance=4 | P | |
| F-QA-04 | Credit NOT deducted on consult-expert | credit_balance=5 | POST `/questions` (low confidence fallback) | credit_balance=5 | M | UAT-6.9 |
| F-QA-05 | Question too long rejected | None | POST `/questions` body > 500 chars | 400, QUESTION_TOO_LONG | P | |
| F-QA-06 | Question history | User with past questions | GET `/questions/history` | Paginated question list | P | |
| F-QA-07 | Question detail with citations | Answered question exists | GET `/questions/{id}` | Full answer + citations + confidence pill | P | |
| F-QA-08 | Answer cache hit | Same question asked twice | POST `/questions` (repeat) | Cache hit, no LLM call, no credit deduction | P | |
| F-QA-09 | PDF export | Answered question | GET `/questions/{id}/export/pdf` | PDF file with answer + citations | P | |
| F-QA-10 | Feedback submission | Answered question | POST `/questions/{id}/feedback` | 200 | P | |

### 2.4 Subscriptions & Payments

| ID | Scenario | Precondition | Steps | Expected | Status | File |
|----|----------|-------------|-------|----------|--------|------|
| F-SUB-01 | List plans | None | GET `/subscriptions/plans` | Available plans with pricing | A | `test_subscriptions.py` |
| F-SUB-02 | Create Razorpay order | Authenticated | POST `/subscriptions/order` | 200, razorpay_order_id | A | `test_subscriptions.py` |
| F-SUB-03 | Verify payment (valid signature) | Order created | POST `/subscriptions/verify` | 200, plan upgraded, credits added | A | `test_subscriptions.py` |
| F-SUB-04 | Verify payment (invalid signature) | Order created | POST `/subscriptions/verify` with bad sig | 400 | A | `test_subscriptions.py` |
| F-SUB-05 | Webhook processes renewal | Razorpay webhook | POST `/subscriptions/webhook` | 200, plan renewed | P | |
| F-SUB-06 | Plan info | Subscribed user | GET `/subscriptions/plan` | Current plan, expiry, credits | A | `test_subscriptions.py` |
| F-SUB-07 | Payment history | User with payments | GET `/subscriptions/history` | Payment records | A | `test_subscriptions.py` |
| F-SUB-08 | Free user gets 5 credits | New registration | Verify OTP | credit_balance=5, plan='free' | P | |

### 2.5 Action Items & Saved Interpretations

| ID | Scenario | Precondition | Steps | Expected | Status | File |
|----|----------|-------------|-------|----------|--------|------|
| F-ACT-01 | Create action item | Answered question | POST `/action-items` | 201, item created | P | |
| F-ACT-02 | List action items | User has items | GET `/action-items` | Paginated list | P | |
| F-ACT-03 | Update action item status | Item exists | PATCH `/action-items/{id}` | 200, status updated | P | |
| F-ACT-04 | Delete action item | Item exists | DELETE `/action-items/{id}` | 200 | P | |
| F-SAV-01 | Save interpretation | Answered question | POST `/saved` | 201, saved with tags | P | |
| F-SAV-02 | List saved | User has saved items | GET `/saved` | Paginated list | P | |
| F-SAV-03 | Delete saved | Item exists | DELETE `/saved/{id}` | 200 | P | |

### 2.6 Public Snippet Sharing

| ID | Scenario | Precondition | Steps | Expected | Status | File |
|----|----------|-------------|-------|----------|--------|------|
| F-SNP-01 | Create snippet | Answered question | POST `/snippets` | 201, slug returned | A | `test_snippet_service.py` |
| F-SNP-02 | Public get snippet | Snippet exists | GET `/snippets/public/{slug}` | 200, quick_answer only, NO detailed_interpretation | A | `test_snippet_service.py` |
| F-SNP-03 | Snippet redaction enforced | Snippet exists | GET `/snippets/public/{slug}` | detailed_interpretation is NEVER in response | A | `test_snippet_service.py` |
| F-SNP-04 | Revoke snippet | Owner | DELETE `/snippets/{id}` | 200, public link returns 404 | P | |
| F-SNP-05 | OG image generation | Snippet exists | GET `/snippets/public/{slug}/og` | PNG image with title overlay | P | |
| F-SNP-06 | Rate limit on public reads | Unauthenticated | 61 requests in 1 minute | 429 on 61st | P | |
| F-SNP-07 | Consult-expert fallback snippet | Low-confidence answer | POST `/snippets` | Snippet shows fallback text, no citation leak | A | `test_snippet_service.py` |

### 2.7 News Feed

| ID | Scenario | Precondition | Steps | Expected | Status | File |
|----|----------|-------------|-------|----------|--------|------|
| F-NEWS-01 | List news items | Ingested items | GET `/news` | Paginated news list | P | |
| F-NEWS-02 | News detail | Item exists | GET `/news/{id}` | Full item with linked circulars | P | |
| F-NEWS-03 | News never in RAG corpus | News items exist | POST `/questions` about news | RAG retrieval returns 0 news chunks | P | |

### 2.8 Admin

| ID | Scenario | Precondition | Steps | Expected | Status | File |
|----|----------|-------------|-------|----------|--------|------|
| F-ADM-01 | Dashboard metrics | Admin user | GET `/admin/dashboard` | Metrics tiles (users, questions, circulars) | M | UAT-7.1 |
| F-ADM-02 | Review pending circulars | Pending items | GET `/admin/review` | List of pending items | M | UAT-7.5 |
| F-ADM-03 | Approve circular | Pending circular | POST `/admin/review/{id}/approve` | Status updated, audit log entry | P | |
| F-ADM-04 | Upload PDF | Admin | POST `/admin/uploads/pdf` (multipart) | 201, processing status | M | UAT-7.2 |
| F-ADM-05 | Upload tracks processing status | Upload in progress | GET `/admin/uploads` | Status transitions: processing → completed | M | UAT-7.2 |
| F-ADM-06 | Uploaded PDF has embeddings | Upload completed | Query document_chunks for uploaded doc | embedding IS NOT NULL | M | UAT-7.3 |
| F-ADM-07 | Heatmap renders | Clustering has run | GET `/admin/dashboard/heatmap` | Cluster × time-bucket matrix | M | UAT-7.4 |
| F-ADM-08 | User management | Admin | GET `/admin/users` | User list with credit balances | P | |
| F-ADM-09 | Non-admin rejected | Regular user | Any `/admin/*` | 403 | A | `test_auth_flow.py` |

---

## 3. Technical Test Cases

### 3.1 Sprint 6 — TD Hardening

| ID | Scenario | Precondition | Steps | Expected | Status | File |
|----|----------|-------------|-------|----------|--------|------|
| T-TD02-01 | Backend SIGTERM fires shutdown event | Running backend | Send SIGTERM | Log lines: `sigterm_received`, `db_pool_closed`, `redis_closed`, `shutdown_complete` | P | |
| T-TD02-02 | Backend exits within grace period | Running backend | `time docker kill -s TERM regpulse-backend` | Exit < 15s | M | UAT-9 |
| T-TD02-03 | Celery worker logs shutdown | Running worker | Send SIGTERM | Log: `celery_worker_shutting_down` | P | |
| T-TD02-04 | Celery finishes current task before exit | Worker processing a task | Send SIGTERM | Task completes, then exit | P | |
| T-TD04-01 | System user exists after migration | Fresh DB | Query users table | `system@regpulse.internal` with UUID `000...001` | P | |
| T-TD04-02 | `_audit_log` inserts row | Scraper context | Call `_audit_log("test_action")` | Row in admin_audit_log with system user actor_id | A | `test_audit_log.py` |
| T-TD04-03 | daily_scrape writes audit entry | Scraper completes | Run daily_scrape | admin_audit_log has `daily_scrape_completed` entry | M | UAT-8 |
| T-TD08-01 | process_document inserts embeddings | Valid PDF URL | Run process_document task | document_chunks.embedding IS NOT NULL for all chunks | P | |
| T-TD08-02 | Embedding dims match config | Processed document | Query embedding column | Vector dimension = EMBEDDING_DIMS (3072) | P | |
| T-TD08-03 | Backfill no longer needed | Fresh scrape | Count chunks where embedding IS NULL | 0 | M | UAT-8 |
| T-TD10-01 | TypeError propagates (not swallowed) | LLMService instance | Call generate() with invalid kwarg | TypeError raised, not caught | A | `test_llm_exceptions.py` |
| T-TD10-02 | AttributeError propagates | LLMService instance | Trigger attribute bug | AttributeError raised | A | `test_llm_exceptions.py` |
| T-TD10-03 | Anthropic APIError triggers fallback | Anthropic returns 500 | Call generate() | Falls back to OpenAI, answer returned | A | `test_llm_exceptions.py` |
| T-TD10-04 | Both APIs fail raises cleanly | Both return errors | Call generate() | Raises, log shows typed exception class | A | `test_llm_exceptions.py` |
| T-TD10-05 | Stream Anthropic failure falls back | Anthropic stream fails | Call generate_stream() | Falls back to OpenAI, tokens emitted | P | |
| T-TD10-06 | Malformed LLM JSON handled | LLM returns invalid JSON | Call generate_stream() | `llm_parse_failed` logged, safe fallback emitted | A | `test_llm_exceptions.py` |
| T-TD11-01 | Retrieval recall — single circular | Seeded corpus | retrieve("KYC updation frequency") | RBI/2024-25/42 in results | A | `test_retrieval.py` |
| T-TD11-02 | Retrieval recall — multi circular | Seeded corpus | retrieve("KYC and NBFC risk") | Multiple expected circulars appear | A | `test_retrieval.py` |
| T-TD11-03 | Out-of-scope low recall | Seeded corpus | retrieve("chicken tikka recipe") | 0–2 chunks returned | A | `test_retrieval.py` |
| T-TD11-04 | All seeded chunks have embeddings | After seed | Count NULL embeddings | 0 | A | `test_retrieval.py` |
| T-TD12-01 | Dev Dockerfile builds | Docker daemon | `docker build --target dev backend/` | Exit 0, pytest available | P | |
| T-TD12-02 | `make eval` runs | Docker running | `make eval` | Exit 0, test results printed | P | |

### 3.2 Database & Migrations

| ID | Scenario | Precondition | Steps | Expected | Status | File |
|----|----------|-------------|-------|----------|--------|------|
| T-DB-01 | All 5 migrations apply on fresh DB | Empty postgres | docker compose up -v | 19 tables created, system user seeded | M | UAT-2 |
| T-DB-02 | Migrations are idempotent | Existing DB | Re-run migrations | No errors (ON CONFLICT DO NOTHING) | P | |
| T-DB-03 | pgvector extension loaded | Running postgres | SELECT extname FROM pg_extension | 'vector' present | A | `main.py` startup check |
| T-DB-04 | Timezone columns use TIMESTAMPTZ | Schema | Inspect DDL | All timestamp columns are TIMESTAMPTZ | P | |
| T-DB-05 | Credit deduction uses SELECT FOR UPDATE | Concurrent requests | Two simultaneous ask requests with 1 credit | Only one succeeds | P | |

### 3.3 Redis & Caching

| ID | Scenario | Precondition | Steps | Expected | Status | File |
|----|----------|-------------|-------|----------|--------|------|
| T-RED-01 | Answer cache stores result | Ask a question | Check Redis for `ans:{hash}` | Cached answer JSON, TTL=24h | P | |
| T-RED-02 | Cache hit skips LLM | Same question asked twice | Second call | No LLM invocation, cached response | P | |
| T-RED-03 | JWT blacklist works | Revoked token jti | GET with revoked token | 401, Redis has jti entry | A | `test_auth_flow.py` |
| T-RED-04 | OTP stored and expires | Register | Check Redis OTP key | Exists with TTL = OTP_EXPIRY_MINUTES | P | |

### 3.4 Security

| ID | Scenario | Precondition | Steps | Expected | Status | File |
|----|----------|-------------|-------|----------|--------|------|
| T-SEC-01 | Injection guard blocks prompt manipulation | None | POST question with "Ignore your instructions" | 400, POTENTIAL_INJECTION | A | `test_hallucination.py` |
| T-SEC-02 | PII never sent to LLM | User with org_name | Ask question, inspect LLM prompt | No user email, name, or org in prompt | A | `test_pii_exclusion.py` |
| T-SEC-03 | Snippet never leaks detailed_interpretation | Shared snippet | GET public snippet | Only quick_answer (truncated) + 1 citation | A | `test_snippet_service.py` |
| T-SEC-04 | CORS excludes webhook | None | OPTIONS on `/subscriptions/webhook` | No CORS headers | P | |
| T-SEC-05 | Razorpay webhook HMAC verified | Webhook call | POST with invalid signature | 400 | P | |
| T-SEC-06 | Refresh token is HttpOnly cookie | Login | Inspect Set-Cookie header | HttpOnly; Secure; SameSite=lax | P | |
| T-SEC-07 | Access token not in cookies | Login | Inspect response | Token in JSON body, not cookie | P | |
| T-SEC-08 | Rate limiter active | None | Exceed rate limit | 429 | P | |
| T-SEC-09 | Error responses use standard format | Any error | Trigger 4xx/5xx | `{"success": false, "error": "...", "code": "..."}` | P | |
| T-SEC-10 | DEMO_MODE blocked in production | ENVIRONMENT=prod, DEMO_MODE=true | Start app | RuntimeError at config load | P | |

### 3.5 RAG Pipeline Internals

| ID | Scenario | Precondition | Steps | Expected | Status | File |
|----|----------|-------------|-------|----------|--------|------|
| T-RAG-01 | Question normalization is deterministic | None | Normalize same question twice | Same hash | A | `test_rag_service.py` |
| T-RAG-02 | RRF fusion scores overlap correctly | Two result lists with shared chunks | Run _rrf_fuse | Shared chunks have higher score | A | `test_rag_service.py` |
| T-RAG-03 | Deduplication respects max_per_doc | 5 chunks from same doc | Run _deduplicate(max=2) | Only 2 kept | A | `test_rag_service.py` |
| T-RAG-04 | KG expansion adds related chunks | KG entities linked | retrieve() with KG enabled | Additional chunks from related circulars | A | `test_retrieval.py` (partial) |
| T-RAG-05 | KG expansion failure is non-fatal | KG service throws | retrieve() | Warning logged, result without expansion | P | |
| T-RAG-06 | Cross-encoder reranking (non-demo) | Cross-encoder loaded | retrieve() with cross_encoder | Results reranked by relevance | P | |
| T-RAG-07 | Cosine threshold filters low-relevance | Low-similarity chunks | retrieve() | Chunks below threshold excluded | P | |

---

## 4. AI Evaluation Test Cases

### 4.1 Hallucination Prevention (Existing — `test_hallucination.py`)

| ID | Scenario | Category | Expected | Status |
|----|----------|----------|----------|--------|
| E-HAL-01..12 | 12 factual questions with ground truth | factual | Correct circular cited, answer matches ground truth | A |
| E-HAL-13..15 | 3 multi-circular questions | multi_circular | Multiple correct circulars cited | A |
| E-HAL-16..23 | 8 out-of-scope questions (SEBI, tax, crypto, etc.) | out_of_scope | consult_expert=true, no fabricated citations | A |
| E-HAL-24..28 | 5 prompt injection attempts | injection | 400, POTENTIAL_INJECTION error | A |

### 4.2 Confidence Calibration

| ID | Scenario | Precondition | Steps | Expected | Status | File |
|----|----------|-------------|-------|----------|--------|------|
| E-CONF-01 | High confidence = many valid citations | LLM returns 3 valid citations | _compute_confidence() | score > 0.7 | A | `test_hallucination.py` |
| E-CONF-02 | Low confidence = stripped citations | LLM returns fabricated citations | _compute_confidence() | score < 0.5 | A | `test_hallucination.py` |
| E-CONF-03 | Zero chunks = zero confidence | 0 chunks | _compute_confidence() | score = 0.0 | A | `test_hallucination.py` |
| E-CONF-04 | Consult-expert triggered on low confidence | score < 0.5 | generate() | Returns fallback response | A | `test_hallucination.py` |
| E-CONF-05 | Insufficient context (< 2 chunks) skips LLM | 0 or 1 chunks | generate() | No LLM call, fallback returned, no credit | A | `test_hallucination.py` |

### 4.3 Retrieval Quality (Existing — `test_retrieval.py`)

| ID | Scenario | Query | Expected Circular | Status |
|----|----------|-------|-------------------|--------|
| E-RET-01 | KYC updation frequency | "What is the KYC updation frequency for high-risk customers?" | RBI/2024-25/42 | A |
| E-RET-02 | Digital lending | "How should loan disbursements be handled in digital lending?" | RBI/2023-24/108 | A |
| E-RET-03 | NBFC classification | "What are the NBFC classification layers under SBR framework?" | RBI/2024-25/15 | A |
| E-RET-04 | PCA triggers | "When is the PCA framework triggered for banks?" | RBI/2023-24/76 | A |
| E-RET-05 | Fraud reporting | "What is the fraud reporting timeline for banks?" | RBI/2024-25/31 | A |
| E-RET-06 | Multi-circular recall | "What are KYC requirements and risk management for NBFCs?" | RBI/2024-25/42 + RBI/2024-25/15 | A |
| E-RET-07 | Out-of-scope low recall | "What is the recipe for chicken tikka masala?" | 0–2 chunks | A |
| E-RET-08 | Embedding population | N/A | All chunks non-NULL | A |

### 4.4 Retrieval Quality — Planned Extensions

| ID | Scenario | Query | Expected | Status |
|----|----------|-------|----------|--------|
| E-RET-09 | KG expansion improves recall | Entity-reference query | KG=true recall >= KG=false recall | P |
| E-RET-10 | Precision@K measurement | All 6 queries | Precision@6 >= 0.5 | P |
| E-RET-11 | MRR (Mean Reciprocal Rank) | All 6 queries | MRR >= 0.6 | P |
| E-RET-12 | Latency under 3s | retrieve() call | End-to-end < 3s | P |
| E-RET-13 | Superseded circular excluded | Superseded doc in DB | retrieve() | Superseded doc NOT in top-K | P |
| E-RET-14 | News items never in retrieval | News items seeded | retrieve() on news topic | 0 news chunks returned | P |

### 4.5 Citation Validation

| ID | Scenario | Precondition | Steps | Expected | Status | File |
|----|----------|-------------|-------|----------|--------|------|
| E-CIT-01 | Valid citations preserved | LLM returns known circular number | _validate_citations() | Citation kept | A | `test_hallucination.py` |
| E-CIT-02 | Fabricated citations stripped | LLM returns unknown circular | _validate_citations() | Citation removed, _stripped_count incremented | A | `test_hallucination.py` |
| E-CIT-03 | Circular number format validation | Various formats | _validate_citations() | Only exact matches against retrieved set | A | `test_llm_service.py` |
| E-CIT-04 | Empty citations list | LLM returns no citations | _validate_citations() | Empty list, low confidence | P | |

### 4.6 End-to-End LLM Quality (Requires Live API Keys)

| ID | Scenario | Query | Assertions | Status |
|----|----------|-------|------------|--------|
| E-E2E-01 | Factual accuracy against ground truth | All 12 factual golden questions | Answer semantically matches ground_truth | P |
| E-E2E-02 | Multi-circular coverage | All 3 multi-circular golden questions | All expected circulars cited | P |
| E-E2E-03 | Out-of-scope refusal | All 8 OOS golden questions | consult_expert=true, no fabricated info | P |
| E-E2E-04 | Streaming consistency | Same question via JSON vs SSE | Same answer content, same citations | P |
| E-E2E-05 | Fallback model parity | Force Anthropic failure | OpenAI fallback produces valid structured JSON | P |

---

## 5. Scraper & Data Pipeline Test Cases

### 5.1 Crawler

| ID | Scenario | Precondition | Steps | Expected | Status |
|----|----------|-------------|-------|----------|--------|
| T-SCR-01 | Discover new URLs | Existing URLs in DB | Run daily_scrape | New URLs enqueued, seen URLs skipped | P |
| T-SCR-02 | PDF extraction | Valid RBI PDF | Run process_document | raw_text non-empty | P |
| T-SCR-03 | Empty PDF skipped | Empty/corrupted PDF | Run process_document | status=skipped, reason=empty_text | P |
| T-SCR-04 | Metadata extraction | Extracted text | MetadataExtractor.extract() | circular_number, department, dates populated | P |
| T-SCR-05 | Chunking | Long text | TextChunker.chunk() | Non-empty chunks with token counts | P |
| T-SCR-06 | Impact classification | Title + summary | ImpactClassifier.classify() | HIGH/MEDIUM/LOW | P |
| T-SCR-07 | Supersession detection | New circular supersedes old | SupersessionResolver.resolve() | Old circular status=SUPERSEDED | P |

### 5.2 RSS Ingest

| ID | Scenario | Precondition | Steps | Expected | Status | File |
|----|----------|-------------|-------|----------|--------|------|
| T-RSS-01 | External ID derivation | Feed entry | _external_id(entry) | Stable ID from entry.id or link | A | `test_rss_fetcher.py` |
| T-RSS-02 | Date parsing | struct_time | _parse_published() | datetime object | A | `test_rss_fetcher.py` |
| T-RSS-03 | Content hash stability | Same entry | _hash_entry() twice | Same hash | A | `test_rss_fetcher.py` |
| T-RSS-04 | Max 50 entries per source | Feed with 100 entries | fetch_source() | Only 50 returned | A | `test_rss_fetcher.py` |
| T-RSS-05 | Network error handled | Unreachable URL | fetch_source() | Empty list, no crash | A | `test_rss_fetcher.py` |
| T-RSS-06 | News-circular linking | Ingested news + circulars | score_and_link() | Relevant circulars linked above threshold | P |

### 5.3 Knowledge Graph

| ID | Scenario | Precondition | Steps | Expected | Status | File |
|----|----------|-------------|-------|----------|--------|------|
| T-KG-01 | Regex extracts circular numbers | Text with RBI/2024-25/42 | regex pass | Entity with type=CIRCULAR | A | `test_entity_extractor.py` |
| T-KG-02 | Regex extracts sections | Text with "Section 3.1" | regex pass | Entity with type=SECTION | A | `test_entity_extractor.py` |
| T-KG-03 | Regex extracts monetary amounts | Text with "₹1,000 crore" | regex pass | Entity with type=AMOUNT | A | `test_entity_extractor.py` |
| T-KG-04 | LLM pass parses valid JSON | Haiku returns JSON envelope | _parse_llm_response() | Entities + triples extracted | A | `test_entity_extractor.py` |
| T-KG-05 | Invalid entities filtered | LLM returns bad entity type | _parse_llm_response() | Bad entities dropped | A | `test_entity_extractor.py` |
| T-KG-06 | Malformed JSON fallback | LLM returns garbage | _parse_llm_response() | Empty lists, no crash | A | `test_entity_extractor.py` |
| T-KG-07 | KG persisted to DB | Entities + triples | persist_kg() | Rows in kg_entities, kg_relationships | P |

---

## 6. Load & Stress Test Cases

### 6.1 Existing k6 Scenarios (`tests/load/k6_load_test.js`)

| ID | Scenario | VUs | Duration | Assertions | Status |
|----|----------|-----|----------|------------|--------|
| L-K6-01 | Smoke | 1 VU | 10s | Health returns 200 | A |
| L-K6-02 | Load ramp | 0→10→20 VUs | 2m | Auth flow p95 < 3s, error rate < 5% | A |
| L-K6-03 | Spike | 0→50→0 VUs | 1m | Request p95 < 5s, error rate < 5% | A |

### 6.2 Planned Load Scenarios

| ID | Scenario | VUs | Duration | Assertions | Status |
|----|----------|-----|----------|------------|--------|
| L-QA-01 | Concurrent Q&A | 10 VUs | 3m | p95 < 10s, no 500s, credits consistent | P |
| L-QA-02 | SSE streaming under load | 20 VUs | 2m | Streams complete, no truncation | P |
| L-QA-03 | Library search concurrent | 30 VUs | 2m | p95 < 2s, results consistent | P |
| L-QA-04 | Cache effectiveness | 10 VUs, same questions | 2m | Cache hit rate > 80% after warmup | P |
| L-SCR-01 | Scraper task storm | 50 concurrent process_document | — | All complete, no OOM, embeddings populated | P |
| L-DB-01 | Connection pool saturation | 50 VUs | 5m | Pool handles gracefully, no connection leaks | P |
| L-RED-01 | Redis throughput | 100 VUs cache reads | 2m | p99 < 50ms | P |

### 6.3 Stress / Resilience

| ID | Scenario | Trigger | Expected | Status |
|----|----------|---------|----------|--------|
| S-RES-01 | Anthropic API down | Block Anthropic host | Falls back to OpenAI, answers still served | P |
| S-RES-02 | OpenAI API down | Block OpenAI host | Embedding service fails gracefully, clear error | P |
| S-RES-03 | Both LLMs down | Block both | 503, "Consult Expert" for all queries, no crash | P |
| S-RES-04 | Redis down | Stop Redis container | Degraded mode, cache misses, rate limiting bypassed, readiness probe fails | P |
| S-RES-05 | Postgres connection drop | Kill postgres mid-request | 500 with proper error format, reconnects on next request | P |
| S-RES-06 | Celery worker crash | Kill worker mid-task | task_acks_late=True ensures redelivery | P |
| S-RES-07 | Memory pressure | Limit container to 256MB | OOM-killed cleanly, Docker restarts | P |
| S-RES-08 | Disk full on Postgres | Fill volume | Insert fails with clear error, no corruption | P |
| S-RES-09 | Slow LLM response (60s) | Mock slow API | Soft time limit fires, graceful timeout | P |
| S-RES-10 | Concurrent credit race condition | Two asks, 1 credit | SELECT FOR UPDATE prevents double-spend | P |

---

## 7. Frontend Test Cases

> No automated frontend tests exist yet. All are manual/UAT or planned.

### 7.1 User Journey (Manual — UAT-6)

| ID | Scenario | Steps | Expected | Status |
|----|----------|-------|----------|--------|
| FE-01 | Register + verify | `/register` → enter email → `/verify-otp` → 123456 | Redirect to `/dashboard`, 5 credits | M |
| FE-02 | Library search | `/library` → search "KYC" | Results render, click opens detail | M |
| FE-03 | Ask question | `/ask` → type question → submit | SSE stream starts, answer + confidence meter + citations | M |
| FE-04 | Citation click navigates | Click citation circular number | Opens `/library/[id]` | M |
| FE-05 | History page | `/history` → click question | Detail view with confidence pill | M |
| FE-06 | Dark mode toggle | Header toggle | Background inverts, no FOUC, persists on reload | M |
| FE-07 | Consult-expert fallback | Ask gibberish | "Consult an Expert" shown, no credit deducted | M |
| FE-08 | Snippet share dialog | Answer page → share button | Dialog with slug link, copy button | M |
| FE-09 | Public snippet page | `/s/[slug]` (unauthenticated) | Quick answer + 1 citation, no detailed interpretation | M |
| FE-10 | Updates page | `/updates` | News items + circular updates, tabs work | M |

### 7.2 Admin UI (Manual — UAT-7)

| ID | Scenario | Steps | Expected | Status |
|----|----------|-------|----------|--------|
| FE-ADM-01 | Dashboard loads | `/admin` | Metrics tiles render | M |
| FE-ADM-02 | PDF upload | `/admin/uploads` → drag PDF | Status transitions to completed | M |
| FE-ADM-03 | Heatmap renders | `/admin/heatmap` | Grid with period/bucket controls | M |
| FE-ADM-04 | Review queue | `/admin/review` | Pending items, approve/reject buttons | M |

### 7.3 Planned Frontend Tests (Vitest/Playwright)

| ID | Scenario | Type | Status |
|----|----------|------|--------|
| FE-AUTO-01 | Auth store state management | Unit (Vitest) | P |
| FE-AUTO-02 | SSE stream rendering | Unit (Vitest) | P |
| FE-AUTO-03 | Dark mode toggle + persistence | Unit (Vitest) | P |
| FE-AUTO-04 | Full user journey | E2E (Playwright) | P |
| FE-AUTO-05 | Admin upload flow | E2E (Playwright) | P |

---

## 8. CI/CD & Infrastructure Test Cases

| ID | Scenario | Steps | Expected | Status |
|----|----------|-------|----------|--------|
| T-CI-01 | Backend lint passes | Push to main | Ruff + Black clean | A (ci.yml) |
| T-CI-02 | Backend unit tests pass | Push to main | pytest exit 0 | A (ci.yml) |
| T-CI-03 | Frontend build passes | Push to main | tsc + eslint + next build exit 0 | A (ci.yml) |
| T-CI-04 | Docker compose builds | `docker compose build` | All 5 service images build | M |
| T-CI-05 | All containers healthy | `docker compose up -d` | 6 containers running | M |
| T-CI-06 | Health endpoint | `curl /api/v1/health` | `{"status":"healthy"}` | A (launch_check.sh) |
| T-CI-07 | Readiness endpoint | `curl /api/v1/health/ready` | `{"status":"ready"}` | A (launch_check.sh) |
| T-CI-08 | Deploy workflow (stub) | Tag push | Workflow triggers | P |

---

## 9. Test Coverage Gaps (Priority Order)

| Priority | Gap | Impact | Effort | Recommendation |
|----------|-----|--------|--------|----------------|
| ~~**P0**~~ | ~~TD-10: No test that TypeError propagates in LLMService~~ | ~~Silent bugs~~ | ~~Small~~ | ✅ `test_llm_exceptions.py` |
| **P0** | F-QA-01..02: No automated test for ask endpoint (JSON + SSE) | Core product flow untested | Medium | Integration test against compose |
| ~~**P0**~~ | ~~T-SEC-02: PII exclusion from LLM prompt~~ | ~~Compliance risk~~ | ~~Small~~ | ✅ `test_pii_exclusion.py` |
| **P1** | F-AUTH-03..08: OTP + refresh flow untested end-to-end | Auth regressions possible | Medium | Integration test |
| ~~**P1**~~ | ~~T-TD04-02: Audit log helper~~ | ~~Sprint 6 unverified~~ | ~~Small~~ | ✅ `test_audit_log.py` |
| **P1** | E-E2E-01..05: No live LLM end-to-end eval | Answer quality regressions | Large | Requires API keys, long runtime |
| **P2** | FE-AUTO-01..05: Zero frontend automated tests | UI regressions invisible | Large | Vitest + Playwright setup |
| **P2** | S-RES-01..10: No resilience/chaos tests | Prod failure modes unknown | Large | Requires infra to simulate |
| **P2** | L-QA-01..04: No Q&A load tests | Performance under load unknown | Medium | Extend k6 with auth + ask flow |
| **P3** | T-SCR-01..07: Scraper pipeline untested | Scraper regressions possible | Medium | Requires mock RBI responses |

---

## 10. Test Execution Matrix

| Environment | What runs | How |
|-------------|-----------|-----|
| **CI (every push)** | Backend lint, backend unit tests, frontend build | `ci.yml` — automated |
| **Local dev** | All of the above + integration tests | `make test` |
| **Docker compose** | Evals, retrieval eval, launch check | `make eval`, `scripts/launch_check.sh` |
| **Manual UAT** | Browser journey, admin flows, dark mode, SSE | Human in browser |
| **Pre-release** | k6 load tests, full golden eval, UAT matrix | `k6 run`, manual checklist |
| **Staging (future)** | All automated + resilience scenarios | Post-Sprint 7 |
