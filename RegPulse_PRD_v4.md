# RegPulse

## RBI Regulatory Intelligence Platform

### PRODUCT REQUIREMENTS DOCUMENT (PRD) --- v4.0

Supersedes PRD v3.0 | Reflects actual build state through Frontend v2 redesign (2026-04-22)

| Field | Value |
|---|---|
| **Product Name** | RegPulse --- RBI Regulatory Intelligence Platform |
| **Version** | 4.0 (Frontend v2 Redesign + New Feature Modules) |
| **Supersedes** | PRD v3.0 |
| **Regulatory Scope** | Reserve Bank of India (RBI) Directives (schema pre-built for multi-regulator expansion) |
| **Primary Revenue** | SaaS Subscription + Per-question Credits |
| **Compliance Scope** | India Digital Personal Data Protection Act 2023 (DPDP), RBI IT Guidelines |
| **Deployment Target** | Google Cloud Platform (asia-south1) --- Cloud Run, Cloud SQL, Memorystore |
| **Status** | 50/50 build prompts + Sprints 1--8 + Frontend v2 complete. 10/12 PRD v3.0 gaps closed. Frontend v2 introduces 5 new feature modules requiring backend work. GCP deployment (Phases A--C) is the remaining critical path to v1.0.0. |

---

## 1. Executive Summary

RegPulse is a B2B SaaS platform purpose-built for professionals in the Indian Banking and Credit industry. It delivers instant, factual, and cited answers to compliance questions grounded exclusively in the Reserve Bank of India's official corpus of Circulars, Master Directions, and Notifications.

Every answer the platform generates: (a) cites exact RBI circular numbers with links to rbi.org.in; (b) includes a Quick Answer executive summary and Detailed Interpretation; (c) classifies the compliance risk level (High / Medium / Low); (d) computes a multi-signal confidence score (0.0--1.0) with a "Consult an Expert" fallback when confidence is insufficient; (e) auto-generates team-tagged action items for implementation. No LLM hallucination of circular references is tolerated under any circumstances.

**v4.0 additions over v3.0:**

- **Frontend v2 redesign** ("terminal-modern"): Bloomberg-terminal-meets-editorial design system with CSS custom-property tokens, serif typography, executive dashboard, 2-column editorial Ask briefs with right-rail citations/debate/confidence radial. All 12 app pages rewritten. 2 new routes (/learnings, /debate). 27 frontend routes total.
- **Team Learnings module** (UI shipped, backend planned): Capture one-line takeaways from briefs, tag, share with team, pin for institutional memory.
- **Debates module** (UI shipped, backend planned): Threaded team disagreements on regulatory interpretations with agree/disagree voting and resolution tracking.
- **Annotations module** (UI shipped, backend planned): Inline margin notes on brief text, visible only to the user's team.
- **Structured Feedback** (UI shipped, backend planned): Checkbox-chip categories ("Missing a relevant circular", "Misinterpreted a citation", etc.) replacing simple thumbs-up/down.
- **Save-as-Learning flow** (UI shipped, backend planned): One-click capture from Ask page to team learning library.
- **DPDP compliance** (now fully implemented): Account deletion + data export endpoints, closed in Sprint 7.
- **Subscription auto-renewal** (now fully implemented): Toggle + Celery reminder, closed in Sprint 7.

---

## 2. Problem Statement & Market Opportunity

*Unchanged from PRD v3.0 --- see Section 2 of that document.*

---

## 3. Goals & Success Metrics

### 3.1 Product Goals

- Deliver factually accurate, cited answers to RBI regulatory questions with zero hallucination of circular references.
- Maintain a continuously updated corpus --- new RBI documents indexed within 24 hours of publication with impact classification.
- Enforce multi-signal confidence scoring on every answer; fall back to "Consult an Expert" when confidence < 0.5 or zero valid citations.
- Auto-generate structured action items from every answer, tagged by responsible team and priority.
- Alert users when saved interpretations become stale due to regulatory amendments.
- **NEW v4:** Enable teams to build institutional compliance memory through shared learnings, threaded debates, and inline annotations.
- **NEW v4:** Provide structured, categorised feedback on AI answers to drive continuous quality improvement.
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
| **NEW v4:** Team Learnings Captured / Month | 100 | 500 |
| **NEW v4:** Debate Threads Opened / Month | 30 | 150 |
| Avg. Answer Latency (P50) | < 4 seconds | < 3 seconds |
| RAG Retrieval Hit Rate | >= 80% | >= 88% |
| Confidence Score (median) | >= 0.65 | >= 0.75 |
| Circulars Indexed | All historical + live | All historical + live |

---

## 4. User Personas

### 4.1--4.5

*Unchanged from PRD v3.0.* Personas: Priya (Compliance Officer), Rahul (Credit Risk Analyst), Ananya (RegTech Founder), Deepak (Compliance Manager), Internal Admin.

### 4.6 Team Lead --- Raghav [NEW v4]

Head of Risk at a mid-size NBFC. Manages a 5-person compliance team. Primary need: ensure the team's regulatory interpretations are consistent, disagreements are documented, and institutional knowledge persists when team members rotate. Uses Learnings to pin takeaways, Debates to resolve interpretation conflicts, and Annotations to leave margin notes on briefs for his team.

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
| US-12 | Subscriber | export an AI compliance brief as a PDF with action items and QR codes | P2 | Implemented |
| US-13 | All Users | ask a follow-up question in context of the previous answer | P2 | Roadmap |
| US-14 | Enterprise Team | share question history and action items across team members | P2 | Roadmap |
| US-15 | All Users | request deletion of my personal data (DPDP compliance) | P0 Legal | ✅ Implemented (Sprint 7) |
| US-16 | All Users | export all my data in machine-readable format (DPDP portability) | P0 Legal | ✅ Implemented (Sprint 7) |
| US-17 | Analyst | share a safe, redacted preview of any answer via public link | P1 | Implemented |
| US-18 | Admin | upload a PDF circular manually when the scraper misses it | P1 | Implemented |
| US-19 | Admin | view semantic clusters of user questions to identify trending topics | P2 | Implemented |
| US-20 | All Users | use the platform comfortably in dark mode | P2 | Implemented |
| **US-21** | Team Lead | **capture a one-line takeaway from any brief as a team learning** | **P1** | **NEW v4 --- UI only** |
| **US-22** | Team Lead | **tag, pin, and share learnings with team members** | **P1** | **NEW v4 --- UI only** |
| **US-23** | Team Member | **open a debate thread when I disagree with a brief's interpretation** | **P1** | **NEW v4 --- UI only** |
| **US-24** | Team Lead | **resolve debate threads with a final ruling and see agree/disagree tally** | **P1** | **NEW v4 --- UI only** |
| **US-25** | Team Member | **annotate specific passages in a brief with margin notes for my team** | **P2** | **NEW v4 --- UI only** |
| **US-26** | Analyst | **give structured feedback on an answer (categories + freetext)** | **P1** | **NEW v4 --- UI only** |
| **US-27** | Compliance Officer | **save any answer as a team learning directly from the Ask page** | **P1** | **NEW v4 --- UI only** |

---

## 6. Feature Requirements

### 6.1--6.15

*Unchanged from PRD v3.0.* All previously specified features remain implemented as documented. Key corrections from v3.0:

- **F2.8 Subscriptions:** Auto-renewal toggle and low-credit notifications are now ✅ Implemented (Sprint 7). Remove v3.0 deviation note.
- **F2.9 PDF Export:** QR codes per citation are now ✅ Implemented (Sprint 8). Remove v3.0 deviation note.
- **F2.10 Admin Console:** Q&A Sandbox is now ✅ Implemented (Sprint 8). Remove v3.0 deviation note.
- **F2.12 DPDP Act Compliance:** Account deletion and data export are now ✅ Implemented (Sprint 7). Remove "NOT IMPLEMENTED" status.
- **F2.6 Regulatory Updates:** Unread tracking, mark-seen, and filter tabs are now ✅ Implemented (Sprint 8). Remove v3.0 deviation note.

### 6.16 Frontend v2 Design System [NEW v4] --- IMPLEMENTED

Terminal-modern aesthetic: "Bloomberg terminal meets editorial print."

- **Design tokens** in CSS custom properties (`globals.css`): paper/ink/amber palette (light + dark), 3 typefaces (Inter Tight sans, Source Serif 4 serif, JetBrains Mono), shadows, radii, grid patterns.
- **Dark mode** via `html.dark` class (not `[data-theme]`). Pre-hydration script prevents flash. WCAG-AA contrast maintained.
- **Component primitives** (`Primitives.tsx`): Pill (7 tones), Btn (4 variants × 2 sizes), Icon (20+ hand-rolled SVGs), Avatar, Sparkline, MiniStat, Kbd, ToastProvider/useToast, Panel.
- **Application shell** (`AppShell`): TopBar (logo + nav links + credits + avatar), Sidebar (NAV items with live badges + keyboard hints), Ticker (auto-scroll regulatory marquee), CommandPalette (⌘K), TweaksPanel (gear toggle for dev/demo settings).
- **Mock data fallback** (`mockData.ts`): Plausible Indian banking scenarios. Pages degrade gracefully to mock data when backend returns empty lists — the terminal stays alive in demo/dev. Never show empty zero-states on executive surfaces.
- **27 routes total** (25 existing + 2 new: `/learnings`, `/debate`).

### 6.17 Team Learnings Module [NEW v4] --- UI ONLY (Backend Planned)

One-line takeaways captured from briefs, forming the team's institutional regulatory memory.

**Frontend (implemented):**
- `/learnings` page: 3 MiniStats (CAPTURED · TOTAL / THIS WEEK / CONTRIBUTORS) + card list.
- Each learning card: avatar, serif takeaway with spark icon, italic note, tag pills, source circular link, Pin/Edit buttons.
- "Save as team learning" modal on Ask page: source question, one-line takeaway input, notes textarea, tag management, "Notify team" checkbox.
- Toast notification on save.

**Backend (planned --- Sprint 10+):**
- `learnings` table: id, user_id, question_id, title (takeaway), note, tags JSONB, pinned BOOLEAN, source_circular_id, created_at.
- CRUD endpoints: `POST /learnings`, `GET /learnings`, `PATCH /learnings/{id}`, `DELETE /learnings/{id}`.
- `POST /learnings/{id}/pin` — toggle pin status.
- Team notification via existing email infrastructure.
- Stats endpoint: `GET /learnings/stats` — total, this_week, contributors.

### 6.18 Debates Module [NEW v4] --- UI ONLY (Backend Planned)

Threaded team disagreements on regulatory interpretations, with agree/disagree voting and resolution.

**Frontend (implemented):**
- `/debate` page: 2-col card grid with OPEN/RESOLVED pill, replies count, title, mono source reference, agree/disagree stacked bar, "Open thread" button.
- Debate section in Ask page right rail with reply input.

**Backend (planned --- Sprint 10+):**
- `debates` table: id, user_id, question_id, title, source_circular_id, status (OPEN/RESOLVED), resolution_text, resolved_by, created_at.
- `debate_replies` table: id, debate_id, user_id, text, stance (AGREE/DISAGREE/NEUTRAL), created_at.
- CRUD endpoints: `POST /debates`, `GET /debates`, `GET /debates/{id}`, `POST /debates/{id}/reply`, `PATCH /debates/{id}/resolve`.
- Sidebar badge for open debates (already wired in nav.ts: `badgeKey: "debate"`).

### 6.19 Annotations Module [NEW v4] --- UI ONLY (Backend Planned)

Inline margin notes on specific passages within AI briefs, visible only to the user's team.

**Frontend (implemented):**
- `<mark class="annot">` spans in rp-prose body with `§` superscript indicator.
- Click to open AnnotPopover: avatar, timestamp, note text, Reply/Resolve buttons.
- "Annotations" hint block in right rail.

**Backend (planned --- Sprint 11+):**
- `annotations` table: id, question_id, user_id, text_selection, note, resolved BOOLEAN, created_at.
- `annotation_replies` table: id, annotation_id, user_id, text, created_at.
- CRUD endpoints: `POST /questions/{id}/annotations`, `GET /questions/{id}/annotations`, `PATCH /annotations/{id}`, `DELETE /annotations/{id}`.
- Team-scoped visibility: annotations visible to all users in the same org.

### 6.20 Structured Feedback [NEW v4] --- UI ONLY (Backend Planned)

Categorised feedback replacing simple thumbs-up/down, feeding into a quality review pipeline.

**Frontend (implemented):**
- Feedback bar on Ask page: "Accurate" / "Needs work" buttons.
- On click: FeedbackForm expands with checkbox chip options:
  - Thumbs down: "Missing a relevant circular", "Misinterpreted a citation", "Risk level too low/high", "Actions not aligned with our structure", "Stale — superseded circular cited".
  - Thumbs up: "Exactly what I needed", "Cited the right sections", "Actions are actionable", "Confidence feels right".
- Optional freetext note.
- "Send to review queue" button.

**Backend (planned --- Sprint 10+):**
- Expand `questions.feedback` from SMALLINT to structured JSONB: `{score: 1|-1, categories: string[], note: string}`.
- Or new `feedback_responses` table: id, question_id, user_id, score, categories JSONB, note TEXT, created_at.
- Admin review queue updated to surface category aggregates.

### 6.21 Save-as-Learning Flow [NEW v4] --- UI ONLY (Backend Planned)

One-click capture from the Ask page to the team learning library.

**Frontend (implemented):**
- LearningModal: triggered from feedback bar "Save as team learning" button.
- Fields: source question (auto-populated), one-line takeaway, notes, tags, "Notify team" checkbox.
- On save: toast notification.

**Backend (planned):**
- `POST /learnings` — accepts `{question_id, title, note, tags, notify_team}`.
- Wired to the Learnings module (§6.17).

---

## 7. Non-Functional Requirements

*Unchanged from PRD v3.0.* All NFRs remain as specified.

---

## 8. Subscription Plans & Pricing

| Feature | Free | Professional | Enterprise |
|---|---|---|---|
| Price | Rs 0 | Rs 2,999/month | Custom (annual contract) |
| Question Credits | 5 (lifetime) | 250 / month | Unlimited |
| Action Items | 5 max | Unlimited | Unlimited |
| Saved Interpretations | 3 max | Unlimited | Unlimited |
| Team Learnings [v4] | 5 max | Unlimited | Unlimited |
| Debates [v4] | View only | Create + vote | Create + vote + resolve |
| Annotations [v4] | No | Yes | Yes |
| Public Snippet Sharing | Yes | Yes | Yes |
| Staleness Alerts | No | Yes | Yes |
| PDF Export (with QR codes) | No | Yes | Yes |
| Dark Mode | Yes | Yes | Yes |
| Priority RAG (fresh cache) | No | No | Yes |
| Team Seats | No | No | Yes (roadmap) |
| API Access | No | No | Yes (roadmap) |
| SLA | None | Email support 48h | Dedicated 4h SLA |
| Auto-renewal | N/A | ✅ Implemented | ✅ Implemented |
| Credit rollover | No | No | Yes |

---

## 9. Security & Privacy Requirements

### 9.1--9.2

*Unchanged from PRD v3.0.*

### 9.3 Data Privacy (DPDP Act 2023) --- ✅ IMPLEMENTED

- Work email gated --- no consumer personal accounts.
- Account deletion: OTP-verified → PII anonymisation (email, name, org) → cascade delete (sessions, saved_interpretations, action_items) → nullify questions.user_id.
- Data export: `GET /account/export` returns JSON with questions, saved_interpretations, action_items.
- **v4 note:** When Learnings, Debates, and Annotations modules are built, their data must be included in the export payload and deleted/anonymised on account deletion.

### 9.4 Infrastructure Security

*Unchanged from PRD v3.0.*

---

## 10. Out of Scope (Roadmap)

| Feature | Reason Deferred | Priority |
|---|---|---|
| Learnings backend | UI shipped; backend schema + endpoints in Sprint 10+ | HIGH |
| Debates backend | UI shipped; backend schema + endpoints in Sprint 10+ | HIGH |
| Annotations backend | UI shipped; backend schema + endpoints in Sprint 11+ | MEDIUM |
| Structured feedback backend | UI shipped; schema expansion in Sprint 10+ | MEDIUM |
| Team Seats / Workspace | Requires multi-user org model and shared state | HIGH |
| Conversational Q&A Threading | Requires parent_question_id model + context mgmt | HIGH |
| SEBI / MeitY / RBI-NBFC Notifications | Multi-regulator expansion --- schema pre-built | HIGH |
| Version Diff / Compare Circulars | Requires version history storage and diff rendering | MEDIUM |
| Mobile App (iOS / Android) | Web PWA covers mobile in v1 | LOW |
| OpenAPI SDK / API Access | Enterprise plan feature | MEDIUM |
| Query Expansion (RAG_QUERY_EXPANSION) | Deferred --- KG expansion provides similar recall benefit | LOW |

---

## 11. Technical Architecture Summary

| Layer | Technology | Notes |
|---|---|---|
| Backend API | FastAPI (Python 3.11), Pydantic v2, SQLAlchemy 2.0 async | All endpoints at /api/v1/ |
| Frontend | Next.js 14, TypeScript strict, CSS custom-property design tokens, TanStack Query, Zustand | Terminal-modern v2 design. 27 routes. |
| Database | PostgreSQL 16 + pgvector (ivfflat index) | 19 tables (+ 3--4 planned for v4 modules), shared by scraper and backend |
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

## 12. Gaps: Status Summary

### 12.1 PRD v3.0 Gaps (10/12 closed)

| Gap ID | Feature | Status |
|---|---|---|
| G-01 | DPDP Account Deletion | ✅ Sprint 7 |
| G-02 | DPDP Data Export | ✅ Sprint 7 |
| G-03 | Updates Feed Tracking | ✅ Sprint 8 |
| G-04 | Subscription Auto-Renewal | ✅ Sprint 7 |
| G-05 | Low-Credit Notifications | ✅ Sprint 7 |
| G-06 | Action Items Stats | ✅ Sprint 8 |
| G-07 | Admin Q&A Sandbox | ✅ Sprint 8 |
| G-08 | Question Suggestions | ✅ Sprint 8 |
| G-09 | PDF QR Codes | ✅ Sprint 8 |
| G-10 | pybreaker Circuit Breaker | ⏳ Sprint 9 |
| G-11 | Query Expansion | ❌ Deferred (KG expansion) |
| G-12 | Overdue Computation | ✅ Sprint 8 |

### 12.2 PRD v4.0 New Gaps (Frontend v2 → Backend)

| Gap ID | Feature | Frontend | Backend | Target |
|---|---|---|---|---|
| G-13 | Team Learnings CRUD + stats | ✅ UI shipped | ❌ Not built | Sprint 10 |
| G-14 | Debates CRUD + voting + resolve | ✅ UI shipped | ❌ Not built | Sprint 10 |
| G-15 | Annotations CRUD + team visibility | ✅ UI shipped | ❌ Not built | Sprint 11 |
| G-16 | Structured Feedback (categories) | ✅ UI shipped | ❌ Not built | Sprint 10 |
| G-17 | Save-as-Learning from Ask page | ✅ UI shipped | ❌ Not built | Sprint 10 |

### 12.3 Residual Tech Debt

| ID | Issue |
|---|---|
| TD-01 | Scraper writes directly to backend DB --- isolate in v2 |
| TD-03 | Manual api.ts client --- replace with OpenAPI codegen |
| TD-09 | BACKEND_PUBLIC_URL unset in demo --- set via Secret Manager |

---

*--- RegPulse PRD v4.0 (Frontend v2 Redesign + New Feature Modules, 2026-04-22) --- All rights reserved ---*
