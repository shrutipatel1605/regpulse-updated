# RegPulse

## RBI Regulatory Intelligence Platform

### PRODUCT REQUIREMENTS DOCUMENT (PRD) --- v3.0

Supersedes PRD v2.0 | Reflects actual build state through Sprints 1–8 (all pre-launch code work complete, 2026-04-14)

| Field | Value |
|---|---|
| **Product Name** | RegPulse --- RBI Regulatory Intelligence Platform |
| **Version** | 3.0 (Post-Build Reconciliation; Sprint 8 addendum) |
| **Supersedes** | PRD v2.0 |
| **Regulatory Scope** | Reserve Bank of India (RBI) Directives (schema pre-built for multi-regulator expansion) |
| **Primary Revenue** | SaaS Subscription + Per-question Credits |
| **Compliance Scope** | India Digital Personal Data Protection Act 2023 (DPDP), RBI IT Guidelines |
| **Deployment Target** | Google Cloud Platform (asia-south1) --- Cloud Run, Cloud SQL, Memorystore |
| **Status** | 50/50 build prompts + Sprints 1--8 complete. 10/12 PRD v3.0 gaps closed. GCP deployment (Phases A--C) is the remaining critical path to v1.0.0. |

---

## 1. Executive Summary

RegPulse is a B2B SaaS platform purpose-built for professionals in the Indian Banking and Credit industry. It delivers instant, factual, and cited answers to compliance questions grounded exclusively in the Reserve Bank of India's official corpus of Circulars, Master Directions, and Notifications.

Every answer the platform generates: (a) cites exact RBI circular numbers with links to rbi.org.in; (b) includes a Quick Answer executive summary and Detailed Interpretation; (c) classifies the compliance risk level (High / Medium / Low); (d) computes a multi-signal confidence score (0.0--1.0) with a "Consult an Expert" fallback when confidence is insufficient; (e) auto-generates team-tagged action items for implementation. No LLM hallucination of circular references is tolerated under any circumstances.

**v3.0 additions over v2.0:** Anti-hallucination guardrails with confidence scoring, public safe snippet sharing, RSS/news ingest with embedding-based circular linking, knowledge graph extraction with KG-driven RAG expansion, dark mode (WCAG-AA), skeleton loaders, PostHog event analytics with feature flags, admin manual PDF upload pipeline, semantic clustering heatmaps for question analytics, golden dataset evaluation pipeline, k6 load testing suite, GCP deployment target (replacing AWS).

---

## 2. Problem Statement & Market Opportunity

### 2.1 The Compliance Research Problem

The RBI issues hundreds of circulars, master directions, and notifications annually. Compliance officers, credit officers, risk managers, and banking executives must track, interpret, and action these directives under significant time pressure. Current research workflows are broken:

- Manual search on rbi.org.in returns unranked PDFs with no contextual Q&A.
- Circulars are frequently amended or superseded --- interpretation without expert guidance is hazardous.
- Legal and compliance teams are overwhelmed --- hiring regulatory specialists is expensive and slow.
- Generic LLMs (ChatGPT, Claude.ai) hallucinate circular numbers, dates, and provisions.
- No existing tool translates regulatory language into actionable team tasks automatically.

### 2.2 The Opportunity

India has 12 public sector banks, 21 private banks, 1,500+ urban cooperative banks, 100,000+ NBFCs, and a fast-growing fintech sector --- all mandatorily subject to RBI regulation. A focused, authoritative regulatory intelligence platform represents a compelling opportunity in the Indian RegTech market, currently dominated by expensive manual advisory services.

---

## 3. Goals & Success Metrics

### 3.1 Product Goals

- Deliver factually accurate, cited answers to RBI regulatory questions with zero hallucination of circular references.
- Maintain a continuously updated corpus --- new RBI documents indexed within 24 hours of publication with impact classification.
- Enforce multi-signal confidence scoring on every answer; fall back to "Consult an Expert" when confidence < 0.5 or zero valid citations.
- Auto-generate structured action items from every answer, tagged by responsible team and priority.
- Alert users when saved interpretations become stale due to regulatory amendments.
- Convert free users to paid subscribers at >= 15% within 30 days of first use.
- Achieve a thumbs-up satisfaction rate of >= 80% on all AI-generated answers.
- Comply fully with India's Digital Personal Data Protection Act 2023.

### 3.2 Key Metrics (OKRs)

| Metric | Target Month 6 | Target Month 12 |
|---|---|---|
| Registered Users | 500 | 2,000 |
| Paid Subscribers | 75 | 400 |
| Monthly Active Users | 300 | 1,200 |
| Questions per Month | 3,000 | 15,000 |
| Thumbs-Up Rate | >= 75% | >= 85% |
| Action Items Created / Month | 1,500 | 8,000 |
| Avg. Answer Latency (P50) | < 4 seconds | < 3 seconds |
| RAG Retrieval Hit Rate | >= 80% | >= 88% |
| Confidence Score (median) | >= 0.65 | >= 0.75 |
| Circulars Indexed | All historical + live | All historical + live |

---

## 4. User Personas

### 4.1 Compliance Officer --- Priya
Mid-size private bank. Ensures bank policies align with RBI directives. Spends 3--4 hours weekly reviewing new circulars. Primary need: rapid circular lookup, impact assessment, and trackable implementation actions.

### 4.2 Credit Risk Analyst --- Rahul
NBFC. Verifies lending norms, fair practices code, asset classification. Primary need: specific clause interpretation with citations and risk level clarity.

### 4.3 RegTech / Fintech Founder --- Ananya
Building a lending product. Needs to understand digital lending guidelines, KYC norms, data localisation. Primary need: comprehensive regulatory scoping without a legal team.

### 4.4 Compliance Manager --- Deepak
Large public sector bank. Manages a team across Risk, Operations, Legal. Primary need: distribute regulatory action items to the right team members and track completion.

### 4.5 Admin / Platform Curator --- Internal
Reviews thumbs-down answers, fine-tunes prompts, approves AI summaries, monitors question clustering heatmaps. Primary need: fast turnaround on quality issues, clear admin tools.

---

## 5. User Stories

| ID | As a... | I want to... | Priority | Status |
|---|---|---|---|---|
| US-01 | Compliance Officer | search and read any RBI circular with full metadata and impact level | P0 | Implemented |
| US-02 | Bank Executive | ask a question and get a cited answer with risk level, confidence score, and action items | P0 | Implemented |
| US-03 | New User | register with my work email and get 5 free questions immediately | P0 | Implemented |
| US-04 | Paid Subscriber | ask questions within my credit allowance after upgrading | P0 | Implemented |
| US-05 | Compliance Officer | see team-tagged action items auto-generated from every answer | P0 | Implemented |
| US-06 | Compliance Manager | track action item status (Pending/In Progress/Done) | P0 | Implemented |
| US-07 | Analyst | save a Q&A interpretation with a name and tags for future reference | P1 | Implemented |
| US-08 | Compliance Officer | be alerted when a saved interpretation's source circular is amended | P1 | Implemented |
| US-09 | Compliance Officer | browse a dedicated feed of new regulatory changes and market news | P1 | Implemented |
| US-10 | Analyst | rate the quality of each answer to improve the platform | P1 | Implemented |
| US-11 | Admin | review thumbs-down answers and override them with corrections | P0 | Implemented |
| US-12 | Subscriber | export an AI compliance brief as a PDF with action items | P2 | Implemented |
| US-13 | All Users | ask a follow-up question in context of the previous answer | P2 | Roadmap |
| US-14 | Enterprise Team | share question history and action items across team members | P2 | Roadmap |
| US-15 | All Users | request deletion of my personal data (DPDP compliance) | P0 Legal | **Not Implemented** |
| US-16 | All Users | export all my data in machine-readable format (DPDP portability) | P0 Legal | **Not Implemented** |
| US-17 | Analyst | share a safe, redacted preview of any answer via public link | P1 | NEW v3 --- Implemented |
| US-18 | Admin | upload a PDF circular manually when the scraper misses it | P1 | NEW v3 --- Implemented |
| US-19 | Admin | view semantic clusters of user questions to identify trending topics | P2 | NEW v3 --- Implemented |
| US-20 | All Users | use the platform comfortably in dark mode | P2 | NEW v3 --- Implemented |

---

## 6. Feature Requirements

### 6.1 Module 1 --- Reference Library Data Scraper

**F1.1 --- Scheduled Crawling** --- IMPLEMENTED

- Daily cron at 02:00 IST for all sections; priority crawl every 4h (06:00--22:00 UTC) for Circulars + Master Directions.
- Crawls: Notifications/Circulars, Master Directions, Press Releases, FAQs.
- PDF download -> pdfplumber text extraction -> pytesseract OCR fallback for scanned documents.

**F1.2 --- Metadata Extraction (Enhanced)** --- IMPLEMENTED

- Circular number, issuing department, issued date, effective date via regex + constants taxonomy.
- Action Deadline: extracted from compliance phrases ('submit by', 'implement by', 'on or before').
- Affected Teams: keyword classification against 6-team taxonomy (Compliance, Risk Management, Operations, Legal, IT Security, Finance).
- Topic tags: classified against taxonomy (KYC, Digital Lending, FEMA, Priority Sector, etc.).

**F1.3 --- Impact Classification** --- IMPLEMENTED

- Every indexed circular receives an impact_level: HIGH / MEDIUM / LOW.
- Classification by Claude Haiku during ingestion. HIGH: new requirements, penalties, prohibitions; MEDIUM: amendments; LOW: informational.
- Admin can override classification. Displayed as coloured badge throughout the platform.

**F1.4 --- Supersession Resolution + Staleness Detection** --- IMPLEMENTED

- Pattern matching for supersession language, status='SUPERSEDED' on matched circulars.
- When a circular is marked superseded, all saved_interpretations citing that circular are flagged needs_review=TRUE.
- Affected users receive a staleness alert email.
- Redis answer cache invalidated for affected questions.

**F1.5 --- AI Summary Generation** --- IMPLEMENTED

- Claude Haiku generates a 3-sentence AI summary per circular.
- Summaries require admin approval before being displayed to users (pending_admin_review flag).

**F1.6 --- Knowledge Graph Extraction [NEW v3]** --- IMPLEMENTED

- Each indexed circular runs a regex pre-pass (circular numbers, sections, amounts, dates) plus a Claude Haiku LLM pass for organisations/regulations/teams + relationship triples.
- Stored in `kg_entities` + `kg_relationships` tables.
- KG-driven RAG expansion enabled by default (`RAG_KG_EXPANSION_ENABLED=true`): related entities from the knowledge graph are injected into retrieval queries, improving recall for cross-circular questions.
- Backfill script: `python /scraper/backfill_kg.py` walks every active circular.

### 6.2 Module 2 --- Web Application

**F2.1 --- Authentication** --- IMPLEMENTED

- Work email only --- 250+ domain blocklist + async MX record verification.
- OTP-only login (no passwords). 6-digit OTP, 10-minute TTL, 3 OTPs/hour rate limit.
- RS256 JWT access tokens (1h TTL), refresh tokens in httpOnly cookie (7d TTL).
- Refresh token rotation: every refresh revokes old session and issues a new token.
- JWT blacklist: on logout, jti stored in Redis (TTL = remaining token lifetime).
- Honeypot field on registration form. Bot suspects flagged, not onboarded.

**F2.2 --- Q&A Engine (Enhanced)** --- IMPLEMENTED

The Q&A engine uses a hybrid BM25+vector RAG pipeline with SSE streaming and multi-layer anti-hallucination guardrails.

- User question -> injection guard check -> hybrid retrieval -> KG expansion -> reranking -> insufficient context guard -> LLM generation -> citation validation -> confidence scoring -> structured response.
- Prompt injection defense: regex detection of 20+ injection patterns. Detected questions return 400, no credit charge.
- Hybrid retrieval: parallel pgvector cosine ANN + PostgreSQL full-text search, merged via Reciprocal Rank Fusion.
- KG-driven RAG expansion [NEW v3]: knowledge graph entities related to the query are used to broaden retrieval, improving recall for cross-circular questions.
- Cross-encoder reranking in ProcessPoolExecutor --- never blocks the API event loop.
- SSE streaming: tokens stream to frontend in real time via fetch + ReadableStream with rAF-buffered rendering. Credit deducted only on successful completion.
- LLM fallback: GPT-4o if Anthropic unavailable (try/catch fallback pattern).
- Cache hits are free: identical questions (SHA256 on normalised text) served from Redis (24h TTL).
- Anti-hallucination guardrails [NEW v3]:
  - Insufficient context guard: < 2 chunks after retrieval -> "Consult Expert" fallback (no LLM call, no credit charge).
  - Citation validation: every citation.circular_number validated against retrieved chunks; hallucinated numbers stripped.
  - Confidence scoring: 3-signal composite (LLM self-reported confidence, citation survival ratio, retrieval depth). Score 0.0--1.0.
  - Confidence < 0.5 or zero valid citations -> "Consult an Expert" fallback response.
- Confidence Meter UI [NEW v3]: visual indicator on ask page, history detail, and history list.

**F2.3 --- Structured Answer Format** --- IMPLEMENTED

Every Q&A answer returns a structured response with:
- Quick Answer: 80-word executive summary.
- Detailed Interpretation: full markdown analysis with structured sections.
- Risk Level: HIGH / MEDIUM / LOW badge.
- Confidence Score [NEW v3]: 0.0--1.0 with visual meter.
- Consult Expert flag [NEW v3]: boolean indicating the system defers to human expertise.
- Affected Teams: list of teams identified as responsible for implementation.
- Source Citations: each citation includes circular number, title, date, verbatim supporting quote, and section reference where determinable.
- Recommended Actions: list of {team, action_text, priority} items structured by team.

**F2.4 --- Action Items Module** --- IMPLEMENTED

Every answer's Recommended Actions can be saved as trackable action items.
- 'Add to Action Items' button on each Recommended Action row.
- Action items have: title, description, assigned_team, priority (High/Medium/Low), due_date (auto-suggested: +7d High, +30d Medium, +90d Low), status (Pending / In Progress / Completed).
- Dedicated /action-items page: tabbed by status, priority badges, source interpretation link.
- Dashboard shows pending action item count.

**F2.5 --- Saved Interpretations Library** --- IMPLEMENTED

- Users can save any Q&A result as a named, tagged interpretation.
- Saved items show Quick Answer, Risk Level, source citations, and current/stale status.
- Staleness detection: when a cited circular is amended or superseded, items with needs_review=TRUE show 'Update Available' badge.
- Staleness alert email sent automatically to the user.

**F2.6 --- Regulatory Updates & News Feed** --- IMPLEMENTED (MODIFIED)

- Dedicated /updates page showing recently indexed circulars and market news.
- RSS/news ingest [NEW v3]: Celery Beat task runs every 30 min, pulls from RBI Press, Business Standard, LiveMint, ET Banking via RSS. Items embedded and linked to active circulars by cosine similarity above NEWS_RELEVANCE_THRESHOLD (default 0.75).
- "Market News" tab alongside regulatory updates.
- News items are **never** mixed into the RAG retrieval corpus (RAG-only-from-circulars is invariant).

> **Deviation from v2.0 spec:** The unread count badge, `last_seen_updates` tracking, mark-seen endpoint, and filter tabs (All/High Impact/My Department/This Week) specified in PRD v2.0 are not implemented. The `last_seen_updates` column exists in the schema but is unused. See Section 12 (Gaps).

**F2.7 --- Circular Library** --- IMPLEMENTED

- Browse, search, and filter all indexed RBI circulars.
- Hybrid search (BM25 + vector) with Reciprocal Rank Fusion.
- Filters: doc_type, department, impact_level, tags, date range, status.
- Each circular card: circular_number, title, doc_type badge, impact_level badge, department, date, status.
- Detail page: full metadata, action_deadline with urgency highlight, affected_teams pills, AI summary (approved only), supersession banner.

**F2.8 --- Subscriptions & Credits** --- PARTIALLY IMPLEMENTED

- Plans: Free (5 lifetime credits), Professional (Rs 2,999/month, 250 credits), Enterprise (custom, unlimited).
- Credits deducted atomically on successful answer delivery only (SELECT FOR UPDATE).
- Razorpay (INR) for all payments. HMAC-SHA256 webhook signature verification.

> **Deviation from v2.0 spec:** Subscription auto-renewal Celery task, low-credit notification Celery task, and PATCH /auto-renew toggle endpoint are not implemented. The `plan_auto_renew` and `last_credit_alert_sent` columns exist in the schema but are unused.

**F2.9 --- PDF Export** --- IMPLEMENTED

- Professional plan users can export any answer as a formatted PDF compliance brief.
- PDF includes: RegPulse header, question, Quick Answer, full interpretation, risk level, citations, action items section, disclaimer.

> **Deviation from v2.0 spec:** QR codes linking to rbi.org.in are not included in the PDF. Citations link as text URLs only.

**F2.10 --- Admin Console** --- IMPLEMENTED (ENHANCED)

- Review Queue: thumbs-down answers surfaced for manual review and override.
- Override workflow: admin edits answer inline, override cached in Redis, logged in admin_audit_log.
- Prompt Management: create, activate, and rollback system prompt versions.
- Circular Management: approve AI summaries, edit metadata (impact_level, action_deadline, affected_teams, tags).
- User Management: view users, adjust credits, change plan, deactivate accounts.
- Scraper Controls: view run history, trigger manual crawl.
- Admin Dashboard: aggregate stats.
- Manual PDF Upload [NEW v3]: drag-drop PDF -> Celery processing -> full pipeline (extract, chunk, embed, classify, KG, summary).
- Semantic Clustering Heatmap [NEW v3]: daily Celery task runs k-means on question embeddings with PCA + silhouette-based k selection, labels clusters via Haiku. CSS-grid heatmap with period/bucket controls.
- Admin News Management [NEW v3]: view and manage RSS-ingested news items.

> **Deviation from v2.0 spec:** Admin Q&A Sandbox (test-question endpoint) and standalone /analytics endpoint are not implemented.

**F2.11 --- Public Snippet Sharing [NEW v3]** --- IMPLEMENTED

- Any signed-in user can share a redacted preview of any of their answers via `/s/[slug]`.
- The full `detailed_interpretation` is enforced never to leave the snippet service --- only `quick_answer` (truncated to 80 words) + 1 citation, or the consult-expert fallback.
- Open Graph image rendered server-side via Pillow for social card previews.
- Rate limited per IP.
- Snippets can be revoked by the owner.

**F2.12 --- DPDP Act Compliance** --- NOT IMPLEMENTED

> **Critical gap:** The DPDP Act 2023 compliance endpoints (account deletion, data export) specified in PRD v2.0 are not implemented. The `deletion_requested_at` column exists in the users table schema, but no API endpoints expose this functionality. This is a legal requirement that must be addressed before production launch. See Section 12 (Gaps).

**F2.13 --- Dark Mode [NEW v3]** --- IMPLEMENTED

- Class-based dark mode (`darkMode: "class"` in Tailwind config) with system-preference bootstrap.
- WCAG-AA compliant colour palette.
- Toggle persisted in localStorage with PostHog analytics event (`dark_mode_toggled`).

**F2.14 --- Skeleton Loaders [NEW v3]** --- IMPLEMENTED

- Skeleton loading states on library, history, and updates pages for perceived performance.

**F2.15 --- Analytics & Feature Flags [NEW v3]** --- IMPLEMENTED

- PostHog adopted for event/journey analytics (first-party, no lock-in).
- Feature flag infrastructure via `useFeatureFlag` hook.
- Events tracked: `confidence_meter_viewed`, `dark_mode_toggled`, `share_snippet_dialog_opened`, `ask_question_submitted`.
- A/B UX flag scaffolding for future experiments.

---

## 7. Non-Functional Requirements

| Category | Requirement | Target |
|---|---|---|
| Performance | API P50 latency --- circular browse | < 200ms |
| Performance | API P95 latency --- hybrid search | < 800ms |
| Performance | API P50 latency --- question answer | < 4 seconds |
| Performance | API P95 latency --- question answer | < 8 seconds |
| Scalability | Concurrent users | 10,000 |
| RAG Quality | Retrieval hit rate (golden eval suite) | >= 85% |
| RAG Quality | Mean Reciprocal Rank (MRR) | >= 0.70 |
| RAG Quality | Confidence score median | >= 0.65 |
| Availability | Platform uptime | >= 99.5% monthly |
| Security | JWT access token TTL | 1 hour |
| Security | Refresh token rotation | On every /auth/refresh call |
| Security | Prompt injection detection | < 200ms (regex, before LLM call) |
| Security | DPDP data deletion SLA | Within 30 days of request |
| Data freshness | New RBI circular indexed | Within 24 hours of publication |
| Cache hit rate | Identical questions served from Redis | >= 30% of all Q&A requests |
| LLM accuracy | Thumbs-up rate | >= 80% |
| Anti-hallucination | Confidence < 0.5 -> "Consult Expert" | 100% enforcement |
| Anti-hallucination | Golden dataset eval pass rate | >= 95% (21/21 current) |
| Cost | LLM cost per question (median) | < Rs 2 (Sonnet) via caching & chunking |

---

## 8. Subscription Plans & Pricing

| Feature | Free | Professional | Enterprise |
|---|---|---|---|
| Price | Rs 0 | Rs 2,999/month | Custom (annual contract) |
| Question Credits | 5 (lifetime) | 250 / month | Unlimited |
| Action Items | 5 max | Unlimited | Unlimited |
| Saved Interpretations | 3 max | Unlimited | Unlimited |
| Public Snippet Sharing [v3] | Yes | Yes | Yes |
| Staleness Alerts | No | Yes | Yes |
| PDF Export | No | Yes | Yes |
| Dark Mode [v3] | Yes | Yes | Yes |
| Priority RAG (fresh cache) | No | No | Yes |
| Team Seats | No | No | Yes (roadmap) |
| API Access | No | No | Yes (roadmap) |
| SLA | None | Email support 48h | Dedicated 4h SLA |
| Auto-renewal | N/A | Planned (not yet built) | Planned |
| Credit rollover | No | No | Yes |

---

## 9. Security & Privacy Requirements

### 9.1 Authentication Security
- OTP-only --- no passwords stored.
- RS256 JWT with 1h access token and 7d refresh token (httpOnly cookie).
- Refresh token rotation: each /auth/refresh revokes old session and issues new token pair.
- JWT blacklist: logout/deactivation adds jti to Redis with TTL equal to remaining token lifetime.

### 9.2 LLM Security
- Prompt injection detection before every LLM call --- 20+ patterns, 400 response on detection.
- User input wrapped in XML tags in LLM prompt. System prompt instructs model to ignore instructions inside tags.
- PII (name, email, org) never sent to any LLM.
- DEMO_MODE=true blocked from running in ENVIRONMENT=prod by startup validator.
- Anti-hallucination: 3-layer protection (injection guard -> insufficient context guard -> confidence scoring with "Consult Expert" fallback).

### 9.3 Data Privacy (DPDP Act 2023)
- Work email gated --- no consumer personal accounts.
- Schema supports PII anonymisation on account deletion (columns exist).
- **Endpoints not yet implemented** --- must be built before production launch.

### 9.4 Infrastructure Security
- TLS via Google-managed certificates on Cloud Run.
- Razorpay webhook excluded from CORS. HMAC-SHA256 signature verification.
- XSS defense: admin override content rendered as markdown only with rehype-sanitize --- no raw HTML.
- Rate limiting: registration 5/hour, OTP verify 10/hour, questions 10/minute per user.
- Honeypot field on registration form.

---

## 10. Out of Scope (Roadmap)

| Feature | Reason Deferred | Priority |
|---|---|---|
| Team Seats / Workspace | Requires multi-user org model and shared state | HIGH |
| Share Interpretation with Team | Requires team workspace | HIGH |
| Comment Threads on Interpretations | Requires team workspace | MEDIUM |
| Conversational Q&A Threading | Requires parent_question_id model + context mgmt | HIGH |
| SEBI / MeitY / RBI-NBFC Notifications | Multi-regulator expansion --- schema pre-built | HIGH |
| Version Diff / Compare Circulars | Requires version history storage and diff rendering | MEDIUM |
| Mobile App (iOS / Android) | Web PWA covers mobile in v1 | LOW |
| Razorpay Subscriptions API (auto-charge) | v1 sends renewal email only; auto-charge in v2 | MEDIUM |
| Saved Payment Methods | Requires Razorpay Cards/Tokens API | MEDIUM |
| OpenAPI SDK / API Access | Enterprise plan feature | MEDIUM |
| Query Expansion (RAG_QUERY_EXPANSION) | Deferred --- KG expansion provides similar recall benefit | LOW |

---

## 11. Technical Architecture Summary

| Layer | Technology | Notes |
|---|---|---|
| Backend API | FastAPI (Python 3.11), Pydantic v2, SQLAlchemy 2.0 async | All endpoints at /api/v1/ |
| Frontend | Next.js 14, TypeScript strict, Tailwind CSS, Zustand, TanStack Query, pnpm | Dark mode (WCAG-AA), skeleton loaders |
| Database | PostgreSQL 16 + pgvector (ivfflat index) | 19 tables, shared by scraper and backend |
| Cache / Queue | Redis 7, Celery, Celery Beat | Answer cache, task queue, JWT blacklist |
| LLM (Primary) | Anthropic claude-sonnet-4-20250514 | Extended thinking (10k budget), Q&A answers |
| LLM (Fallback) | GPT-4o | Activates on Anthropic failure |
| LLM (Summaries) | Claude Haiku (claude-haiku-4-5-20251001) | Summaries, impact classification, KG extraction, cluster labelling |
| Embeddings | OpenAI text-embedding-3-large (3072-dim) | Configurable to 1536-dim |
| Reranking | ms-marco-MiniLM-L-6-v2 (sentence-transformers) | Loaded in backend only (skipped in DEMO_MODE) |
| Payments | Razorpay (INR only) | HMAC-SHA256 webhook verification |
| CI/CD | GitHub Actions (WIF) -> Artifact Registry -> Cloud Run | Tag-triggered deployment |
| Analytics | PostHog (self-hosted compatible) | Event tracking + feature flags |
| Monitoring | structlog JSON -> Cloud Logging / Cloud Monitoring | Zero-config log ingestion |

---

## 12. Gaps: PRD v2.0 Features — Closure Status

Originally 12 gaps were identified against PRD v2.0. **10 of 12 are now closed** (Sprints 7 and 8). The table below reflects actual delivery status.

| Gap ID | Feature | Status | Delivered In | Endpoint / Implementation |
|---|---|---|---|---|
| G-01 | DPDP Account Deletion | ✅ Closed | Sprint 7 (`8c9f34b`) | `POST /account/request-deletion-otp`, `PATCH /account/delete` — OTP-gated, PII anonymised, cascade delete |
| G-02 | DPDP Data Export | ✅ Closed | Sprint 7 (`8c9f34b`) | `GET /account/export` — JSON with questions/saved/action_items |
| G-03 | Updates Feed unread tracking | ✅ Closed | Sprint 8 (`56d628f`) | `GET /circulars/updates` + `POST /circulars/updates/mark-seen`; sidebar badge, filter chips |
| G-04 | Subscription auto-renewal | ✅ Closed | Sprint 7 (`8c9f34b`) | `PATCH /subscriptions/auto-renew` + Celery `subscription_renewal_check` (daily 08:00 IST) |
| G-05 | Low-credit email notifications | ✅ Closed | Sprint 7 (`8c9f34b`) | Celery `credit_notifications` (daily 09:00 IST) + in-request BackgroundTask at balance 5 / 2 |
| G-06 | Action items /stats endpoint | ✅ Closed | Sprint 8 (`56d628f`) | `GET /action-items/stats` — GROUP BY status + overdue count |
| G-07 | Admin Q&A Sandbox | ✅ Closed | Sprint 8 (`56d628f`) | `GET /admin/prompts/test-question` — no Question row, no credits, logs `AnalyticsEvent("admin_test_question")` |
| G-08 | Question suggestions | ✅ Closed | Sprint 8 (`56d628f`) | `GET /questions/suggestions` — pgvector ANN on `questions.question_embedding` (now persisted on write) |
| G-09 | PDF QR codes to rbi.org.in | ✅ Closed | Sprint 8 (`56d628f`) | `GET /questions/{id}/export` now returns `application/pdf` built with `reportlab`; per-citation QR via `qrcode[pil]` |
| G-10 | pybreaker circuit breaker for LLM | ⏳ Sprint 9 | — | `pybreaker==1.2.0` already in `requirements.txt`; wire into `llm_service.py` with `fail_max=3`, `reset_timeout=60` |
| G-11 | Query expansion | ❌ Deferred | — | KG-driven RAG expansion (`RAG_KG_EXPANSION_ENABLED=true` default, Sprint 6) serves the same recall benefit at lower cost |
| G-12 | Overdue computation | ✅ Closed | Sprint 8 (`56d628f`) | `is_overdue` computed field on `GET /action-items` items; `/action-items/stats` exposes overdue count |

### Post-Launch Scope

| Sprint | Gap | Rationale |
|---|---|---|
| Sprint 9 | G-10 | Reliability improvement; current try/catch fallback is acceptable for v1.0.0. |
| Deferred | G-11 | KG expansion already addresses the recall gap. |

### Residual Tech Debt (carried into Sprint 9)

| ID | Issue |
|---|---|
| TD-01 | Scraper writes directly to backend DB — acceptable for v1.0.0, isolate in v2 |
| TD-03 | Manual `api.ts` client — replace with OpenAPI codegen |
| TD-09 | `BACKEND_PUBLIC_URL` unset in demo — set via Secret Manager during Phase A |

---

*--- RegPulse PRD v3.0 (Sprint 8 addendum, 2026-04-14) --- All rights reserved ---*
