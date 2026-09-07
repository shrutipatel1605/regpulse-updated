# RegPulse

## RBI Regulatory Intelligence Platform

### FUNCTIONAL SPECIFICATION DOCUMENT (FSD) --- v4.0

Supersedes FSD v3.0 | Reflects actual build state through Frontend v2 redesign (2026-04-22)

| Field | Value |
|---|---|
| Document Type | Functional Specification Document (FSD) |
| Version | 4.0 |
| Supersedes | FSD v3.0 |
| Related | RegPulse PRD v4.0, MEMORY.md, PRODUCTION_PLAN.md |
| Scope | Module 1 (Scraper) + Module 2 (Web App) + Module 3 (Team Collaboration) --- Full Stack |
| Stack | Python 3.11 / FastAPI / Next.js 14 / PostgreSQL 16+pgvector / Redis 7 |
| LLM Primary | Anthropic claude-sonnet-4-20250514 (extended thinking, 10k budget) |
| LLM Fallback | GPT-4o (try/catch fallback on Anthropic failure) |
| LLM (Summaries/KG) | Claude Haiku (claude-haiku-4-5-20251001) --- summaries, impact, KG extraction, cluster labels |
| Embeddings | OpenAI text-embedding-3-large (3072-dim, configurable to 1536) |
| Payments | Razorpay (INR) |
| Auth | OTP, RS256 JWT, refresh token rotation, jti Redis blacklist |
| Compliance | India DPDP Act 2023, RBI IT Guidelines |
| Deployment | GCP asia-south1 --- Cloud Run, Cloud SQL, Memorystore, Artifact Registry |

---

## 1. System Architecture Overview

RegPulse is a multi-module system communicating via a shared PostgreSQL+pgvector database. All backend API routes are prefixed /api/v1/.

**v4.0 change:** Added Module 3 (Team Collaboration) covering Learnings, Debates, Annotations, and Structured Feedback. Frontend redesigned with terminal-modern v2 design system. Backend unchanged except for planned new tables and endpoints.

| Component | Role |
|---|---|
| RBI Scraper (M1) | *Unchanged from FSD v3.0.* Cron-triggered Python/Celery service. |
| Impact Classifier (M1) | *Unchanged.* Claude Haiku classifies HIGH/MEDIUM/LOW. |
| Knowledge Graph Extractor (M1) | *Unchanged.* Regex + Claude Haiku LLM pass. |
| RSS/News Ingestor (M1) | *Unchanged.* Celery Beat every 30 min. |
| PostgreSQL+pgvector | 19 tables (current) + 4 planned (learnings, debates, debate_replies, annotations). |
| EmbeddingService (M2) | *Unchanged.* Standalone async service. |
| RAGService (M2) | *Unchanged.* Hybrid BM25+vector with KG expansion. |
| LLMService (M2) | *Unchanged.* Injection guard → Anthropic → GPT-4o fallback. |
| FastAPI Backend (M2) | ~65 endpoints (current) + ~15 planned for M3. All at /api/v1/. |
| Next.js Frontend (M2) | **v4: 27 routes.** Terminal-modern v2 design system (CSS tokens, serif editorial, AppShell). TanStack Query, Zustand, SSE streaming, dark mode. |
| Team Collaboration (M3) [NEW v4] | **Planned backend.** Learnings CRUD, Debates CRUD + voting, Annotations CRUD, Structured Feedback. Frontend already shipped. |
| Celery + Celery Beat | *Unchanged.* 10 tasks, 6 beat schedules. |
| Redis | *Unchanged.* Answer cache, embedding cache, OTP, JWT blacklist, rate limits. |
| Razorpay | *Unchanged.* INR payments, HMAC-SHA256 webhook. |
| Nginx | *Unchanged.* TLS 1.3, HSTS, CSP, rate limiting. |

---

## 2. Database Schema (v4)

### 2.1--2.14 Existing Tables

*All 19 tables from FSD v3.0 remain unchanged.* Key corrections to v3.0 documentation:

- **users.plan_auto_renew:** Now wired via `PATCH /subscriptions/auto-renew` (Sprint 7).
- **users.last_credit_alert_sent:** Now wired via Celery `credit_notifications` task (Sprint 7).
- **users.last_seen_updates:** Now wired via `POST /circulars/updates/mark-seen` (Sprint 8).
- **users.deletion_requested_at:** Now wired via `PATCH /account/delete` (Sprint 7).
- **questions.question_embedding:** New column (Sprint 8), vector(3072), populated on every INSERT via `_maybe_embed_question()`.

See FSD v3.0 Sections 2.1--2.14 for full column definitions.

### 2.15 learnings [NEW v4 --- PLANNED]

| Column | Type | Null | Description |
|---|---|---|---|
| id | UUID PK | NO | gen_random_uuid() |
| user_id | UUID FK | NO | -> users.id (creator) |
| question_id | UUID FK | YES | -> questions.id (source brief) |
| source_circular_id | UUID FK | YES | -> circular_documents.id |
| title | TEXT | NO | One-line takeaway |
| note | TEXT | YES | Extended context |
| tags | JSONB | YES | e.g. ["SBR", "Tier-1", "FY27"] |
| pinned | BOOLEAN | NO | Default FALSE |
| created_at | TIMESTAMPTZ | NO | Default now() |

**Indexes:** btree on user_id, btree on question_id, GIN on tags.

### 2.16 debates [NEW v4 --- PLANNED]

| Column | Type | Null | Description |
|---|---|---|---|
| id | UUID PK | NO | gen_random_uuid() |
| user_id | UUID FK | NO | -> users.id (opener) |
| question_id | UUID FK | YES | -> questions.id (source brief) |
| source_circular_id | UUID FK | YES | -> circular_documents.id |
| title | TEXT | NO | Debate topic |
| status | VARCHAR(20) | NO | OPEN \| RESOLVED. Default OPEN. |
| resolution_text | TEXT | YES | Final ruling (set on resolve) |
| resolved_by | UUID FK | YES | -> users.id |
| resolved_at | TIMESTAMPTZ | YES | |
| created_at | TIMESTAMPTZ | NO | Default now() |

**Indexes:** btree on status, btree on user_id.

### 2.17 debate_replies [NEW v4 --- PLANNED]

| Column | Type | Null | Description |
|---|---|---|---|
| id | UUID PK | NO | gen_random_uuid() |
| debate_id | UUID FK | NO | -> debates.id |
| user_id | UUID FK | NO | -> users.id |
| text | TEXT | NO | Reply content |
| stance | VARCHAR(10) | NO | AGREE \| DISAGREE \| NEUTRAL |
| created_at | TIMESTAMPTZ | NO | Default now() |

**Indexes:** btree on debate_id.

### 2.18 annotations [NEW v4 --- PLANNED]

| Column | Type | Null | Description |
|---|---|---|---|
| id | UUID PK | NO | gen_random_uuid() |
| question_id | UUID FK | NO | -> questions.id |
| user_id | UUID FK | NO | -> users.id (author) |
| text_selection | TEXT | NO | Selected text passage |
| note | TEXT | NO | Annotation content |
| resolved | BOOLEAN | NO | Default FALSE |
| created_at | TIMESTAMPTZ | NO | Default now() |

**Indexes:** btree on question_id, btree on user_id.

### 2.19 Structured Feedback [NEW v4 --- PLANNED]

Two options under consideration:

**Option A — Expand existing column:** Change `questions.feedback` from SMALLINT to JSONB: `{score: 1|-1, categories: ["Missing a relevant circular", ...], note: "..."}`. Simpler, no migration needed beyond column type change.

**Option B — New table:** `feedback_responses` (id, question_id, user_id, score, categories JSONB, note TEXT, created_at). Cleaner separation, supports multiple feedback entries per question. Recommended.

Decision deferred to implementation sprint.

### 2.20 Indexes (additions to v3)

| Index | Table | Type | Purpose |
|---|---|---|---|
| idx_learnings_user | learnings | btree | User's learnings list |
| idx_learnings_tags | learnings | GIN | Tag-based filtering |
| idx_debates_status | debates | btree | Open/resolved filter |
| idx_debate_replies_debate | debate_replies | btree | Thread loading |
| idx_annotations_question | annotations | btree | Annotations per brief |

---

## 3--5. Module 1 (Scraper) + Authentication + Q&A Engine

*Unchanged from FSD v3.0.* See Sections 3--5 of that document.

Key corrections to v3.0 gap notes:
- **§5 Q&A Engine:** pybreaker circuit breaker still deferred to Sprint 9. Current try/catch fallback is acceptable for v1.0.0.
- **§5.4 SSE Streaming:** Frontend now uses terminal-modern v2 design (rp-prose body with serif typography, live-dot streaming indicator, editorial 2-column layout). SSE protocol unchanged.

---

## 6. Action Items Module

*Unchanged from FSD v3.0.* Correction: `GET /action-items/stats` is now ✅ Implemented (Sprint 8). `is_overdue` computed field on list items.

---

## 7. Saved Interpretations & Staleness Detection

*Unchanged from FSD v3.0.*

---

## 8. Public Snippet Sharing

*Unchanged from FSD v3.0.*

---

## 9. Regulatory Updates & News Feed

*Unchanged from FSD v3.0.* Correction: Unread tracking, mark-seen, filter tabs are now ✅ Implemented (Sprint 8).

---

## 10. Admin Console

*Unchanged from FSD v3.0.* Correction: Admin Q&A Sandbox (`GET /admin/prompts/test-question`) is now ✅ Implemented (Sprint 8).

---

## 11. Subscriptions & Credits

*Unchanged from FSD v3.0.* Correction: Auto-renewal toggle and low-credit notifications are now ✅ Implemented (Sprint 7).

---

## 12. DPDP Act 2023 Compliance --- ✅ IMPLEMENTED

*Previously "NOT IMPLEMENTED" in FSD v3.0.* Now fully implemented (Sprint 7):

| Endpoint | Method | Description |
|---|---|---|
| POST /api/v1/account/request-deletion-otp | POST | Send deletion verification OTP to user's email |
| PATCH /api/v1/account/delete | PATCH | OTP-verified account deletion: PII anonymisation → cascade delete → nullify questions.user_id |
| GET /api/v1/account/export | GET | JSON export of user's questions, saved_interpretations, action_items |

**v4 note:** When M3 tables (learnings, debates, annotations) are implemented, their data MUST be:
1. Included in the `GET /account/export` payload.
2. Deleted/anonymised on `PATCH /account/delete`.

---

## 13. Module 3 --- Team Collaboration [NEW v4]

### 13.1 Team Learnings

**Purpose:** Institutional compliance memory. Teams capture one-line takeaways from briefs, tag them, and share across the team.

#### 13.1.1 API Endpoints (Planned)

| Endpoint | Method | Auth | Description |
|---|---|---|---|
| POST /api/v1/learnings | POST | Verified | Create learning. Body: `{question_id?, title, note?, tags?, source_circular_id?, notify_team?}` |
| GET /api/v1/learnings | GET | Verified | List team's learnings. Filters: tags, pinned, date range. Pagination. |
| GET /api/v1/learnings/stats | GET | Verified | `{total, this_week, contributors}` |
| PATCH /api/v1/learnings/{id} | PATCH | Owner | Update title, note, tags. |
| POST /api/v1/learnings/{id}/pin | POST | Verified | Toggle pinned status. |
| DELETE /api/v1/learnings/{id} | DELETE | Owner | Hard delete. |

#### 13.1.2 Business Rules
- Any verified user can create a learning.
- Learnings are visible to all users in the same org (team-scoped, not user-scoped).
- `notify_team=true` triggers email to all team members via existing SMTP infrastructure.
- Tag format: freetext strings, stored as JSONB array. Frontend renders as pills.
- Pinned learnings sort to top of list.

### 13.2 Debates

**Purpose:** Structured disagreement on regulatory interpretations. When a team member disagrees with a brief, they open a debate thread. Others vote AGREE/DISAGREE. A team lead resolves with a final ruling.

#### 13.2.1 API Endpoints (Planned)

| Endpoint | Method | Auth | Description |
|---|---|---|---|
| POST /api/v1/debates | POST | Verified | Open debate. Body: `{question_id?, title, source_circular_id?}` |
| GET /api/v1/debates | GET | Verified | List debates. Filters: status (OPEN/RESOLVED), source_circular_id. Pagination. |
| GET /api/v1/debates/{id} | GET | Verified | Debate detail with all replies. |
| POST /api/v1/debates/{id}/reply | POST | Verified | Add reply. Body: `{text, stance: AGREE|DISAGREE|NEUTRAL}` |
| PATCH /api/v1/debates/{id}/resolve | PATCH | Verified | Resolve debate. Body: `{resolution_text}`. Sets status=RESOLVED, resolved_by, resolved_at. |
| GET /api/v1/debates/stats | GET | Verified | `{open, resolved, total}` for sidebar badge. |

#### 13.2.2 Business Rules
- Any verified user can open a debate or reply.
- Only the debate opener or an admin can resolve.
- Stance tallies (agree/disagree counts) computed from replies, not stored separately.
- Resolved debates are read-only (no new replies).
- Sidebar badge shows open debate count (nav.ts already has `badgeKey: "debate"`).

### 13.3 Annotations

**Purpose:** Inline margin notes on specific passages within AI-generated briefs. Visible only to the user's team.

#### 13.3.1 API Endpoints (Planned)

| Endpoint | Method | Auth | Description |
|---|---|---|---|
| POST /api/v1/questions/{id}/annotations | POST | Verified | Create annotation. Body: `{text_selection, note}` |
| GET /api/v1/questions/{id}/annotations | GET | Verified | List annotations for a question. Team-scoped. |
| PATCH /api/v1/annotations/{id} | PATCH | Owner | Update note text. |
| PATCH /api/v1/annotations/{id}/resolve | PATCH | Verified | Mark resolved. |
| DELETE /api/v1/annotations/{id} | DELETE | Owner | Hard delete. |

#### 13.3.2 Business Rules
- Annotations are team-scoped: visible to all users sharing the same `org_name`.
- `text_selection` is the verbatim text passage the annotation is attached to. Frontend uses this to re-anchor the `<mark>` span on re-render.
- Resolved annotations are greyed out but not hidden.
- PII note: annotation text may reference regulatory positions — excluded from public snippet sharing.

### 13.4 Structured Feedback

**Purpose:** Replace simple thumbs-up/down with categorised feedback feeding into a quality improvement pipeline.

#### 13.4.1 API Change (Planned)

Expand `POST /api/v1/questions/{id}/feedback`:

**Current:** `{feedback: 1|-1, comment?: string}`

**Proposed:** `{score: 1|-1, categories: string[], note?: string}`

Categories (thumbs down):
- `missing_circular` — "Missing a relevant circular"
- `misinterpreted_citation` — "Misinterpreted a citation"
- `risk_too_low` — "Risk level too low"
- `risk_too_high` — "Risk level too high"
- `actions_misaligned` — "Actions not aligned with our structure"
- `stale_citation` — "Stale — superseded circular cited"

Categories (thumbs up):
- `exactly_right` — "Exactly what I needed"
- `right_sections` — "Cited the right sections"
- `actionable` — "Actions are actionable"
- `confidence_right` — "Confidence feels right"

#### 13.4.2 Admin Review Queue Enhancement
- Review queue groups feedback by category.
- Dashboard shows category distribution chart.
- "Missing a relevant circular" and "stale_citation" categories auto-flag for RAG pipeline review.

---

## 14. Frontend Route Map (v4)

| Route | Component | Notes |
|---|---|---|
| / | (marketing)/page.tsx | Public landing page. JSON-LD schema. |
| /register | register/page.tsx | Multi-step: email+profile -> OTP. |
| /login | login/page.tsx | Email -> OTP -> dashboard. |
| /verify | verify/page.tsx | Standalone OTP entry. |
| /(app)/dashboard | dashboard/page.tsx | **v4:** Executive command center — hero, 4 metric tiles, 7×7 heatmap, activity feed, exposure, debates. |
| /(app)/library | library/page.tsx | **v4:** 240px filter aside + 2-col CircCard grid. |
| /(app)/library/[id] | library/[id]/page.tsx | Circular detail. |
| /(app)/ask | ask/page.tsx | **v4:** 2-col editorial brief (main + 320px right rail). SSE streaming, annotations, feedback bar, learning modal, confidence radial, citations, debate. |
| /(app)/history | history/page.tsx | **v4:** dtable with confidence bars, risk pills, team pills. |
| /(app)/history/[id] | history/[id]/page.tsx | Question detail with confidence meter. |
| /(app)/updates | updates/page.tsx | **v4:** 3-tab (Circulars dtable / News relevance cards / Consultations). Live-dot, filter chips. |
| /(app)/saved | saved/page.tsx | **v4:** 2-col card grid with serif italic question quote. |
| /(app)/action-items | action-items/page.tsx | **v4:** MiniStat header + 5-tab filters + dtable with checkbox toggle. |
| /(app)/learnings [NEW v4] | learnings/page.tsx | 3 MiniStats + learning card list. Mock data (backend planned). |
| /(app)/debate [NEW v4] | debate/page.tsx | 2-col debate cards with agree/disagree bars. Mock data (backend planned). |
| /(app)/upgrade | upgrade/page.tsx | **v4:** 3-col plan cards with MOST CHOSEN ribbon, serif editorial headline. |
| /(app)/account | account/page.tsx | **v4:** PROFILE + TEAM + PAYMENT HISTORY + DPDP panels. Live export/delete/auto-renew. |
| /s/[slug] | s/[slug]/page.tsx | Public snippet view with OG meta. |
| /admin | admin/page.tsx | Stats, charts. |
| /admin/review | admin/review/page.tsx | Thumbs-down review + override. |
| /admin/prompts | admin/prompts/page.tsx | Prompt version management. |
| /admin/circulars | admin/circulars/page.tsx | Pending summaries + metadata edit. |
| /admin/users | admin/users/page.tsx | User management. |
| /admin/scraper | admin/scraper/page.tsx | Scraper controls. |
| /admin/uploads | admin/uploads/page.tsx | Manual PDF upload. |
| /admin/heatmap | admin/heatmap/page.tsx | Semantic clustering heatmap. |

**Total: 27 routes** (25 from v3 + `/learnings` + `/debate`).

---

## 15. Frontend Design System (v4) [NEW]

### 15.1 Design Tokens

CSS custom properties in `frontend/src/app/globals.css`. Two palettes (light + dark via `html.dark`).

| Token group | Examples | Purpose |
|---|---|---|
| Background | `--bg`, `--bg-1`, `--bg-2`, `--panel`, `--panel-2` | Surface layers |
| Ink | `--ink` through `--ink-5` | Text hierarchy (dark to light) |
| Signal | `--signal`, `--signal-2`, `--signal-bg`, `--signal-ink` | Amber accent (CTA, active states) |
| Semantic | `--good`, `--warn`, `--bad` + `-bg` variants | Status indicators |
| Typography | `--font-sans`, `--font-serif`, `--font-mono` | Inter Tight, Source Serif 4, JetBrains Mono |
| Shadow | `--shadow-sm`, `--shadow`, `--shadow-lg` | Elevation |
| Grid | `--grid`, `--grid-strong` | Subtle background gridlines |

### 15.2 Component Primitives

`frontend/src/components/design/Primitives.tsx`:

| Component | Props | Description |
|---|---|---|
| Pill | tone (7 values), children | Status/tag indicator |
| Btn | variant (primary/accent/ghost/""), size (sm/""), icon | Action button |
| Icon | 20+ named SVG components | Hand-rolled 14×14 line icons |
| Avatar | initials, size, tone | Circular monogram |
| Sparkline | data[], width, height, stroke, fill | Inline mini chart |
| MiniStat | label, value, signal?, tone? | Numeric KPI display |
| ToastProvider / useToast | push({tag, text}) | Global toast notifications |
| Panel | className, ...HTMLAttributes | Card container |
| Kbd | children | Keyboard shortcut badge |
| cn | ...parts | Class name joiner |

### 15.3 Application Shell

`frontend/src/components/shell/`:

| Component | Description |
|---|---|
| AppShell | Root layout — assembles TopBar + Sidebar + Ticker + content area + TweaksPanel |
| TopBar | Logo, nav links, credits badge, user avatar |
| Sidebar | NAV items with live badges (updates/actions/debate), keyboard hints, bottom section (Upgrade/Account/Admin) |
| Ticker | Auto-scrolling regulatory headline marquee |
| CommandPalette | ⌘K search overlay |
| TweaksPanel | Gear-toggle dev/demo settings panel |
| nav.ts | NAV + NAV_BOTTOM route definitions with icons and badge keys |

### 15.4 CSS Utility Classes

| Class | Purpose |
|---|---|
| `.panel` | Card with `var(--panel)` bg + `var(--line)` border |
| `.tick` | Section header — mono, uppercase, with leading dash |
| `.pill.*` | Inline status badge (7 tone variants) |
| `.btn.*` | Button (4 variant × 2 size variants) |
| `.dtable` | Data table with sticky headers |
| `.rp-prose` | Serif editorial body (16.5px, 1.65 line-height) |
| `.rp-prose .dek` | Deck/standfirst (22px italic, border-left accent) |
| `.rp-prose mark.annot` | Annotation highlight (signal-bg, dashed underline) |
| `.bar.*` | Progress bar (4 color variants) |
| `.input` | Text input / textarea |
| `.checkbox` | Custom checkbox |
| `.toast` | Toast notification |
| `.live-dot` | Pulsing "live" indicator |
| `.gridlines` | Subtle background grid |

---

## 16. Environment Variables Reference

*Unchanged from FSD v3.0.* See Section 15 of that document.

---

## 17. Gaps: FSD v4.0 Status

### 17.1 FSD v3.0 Gaps --- All Closed

| Gap | Status |
|---|---|
| DPDP endpoints | ✅ Sprint 7 |
| Updates feed tracking | ✅ Sprint 8 |
| Subscription auto-renewal | ✅ Sprint 7 |
| Low-credit notifications | ✅ Sprint 7 |
| Action items /stats | ✅ Sprint 8 |
| Admin Q&A sandbox | ✅ Sprint 8 |
| Question suggestions | ✅ Sprint 8 |
| PDF QR codes | ✅ Sprint 8 |
| Action items is_overdue | ✅ Sprint 8 |
| pybreaker circuit breaker | ⏳ Sprint 9 |
| RAG_QUERY_EXPANSION | ❌ Deferred (KG expansion) |

### 17.2 FSD v4.0 New Gaps (Frontend v2 → Backend)

| Gap ID | Module | Schema | Endpoints | Target Sprint |
|---|---|---|---|---|
| G-13 | Team Learnings | `learnings` table | 6 endpoints (§13.1.1) | Sprint 10 |
| G-14 | Debates | `debates` + `debate_replies` tables | 6 endpoints (§13.2.1) | Sprint 10 |
| G-15 | Annotations | `annotations` table | 5 endpoints (§13.3.1) | Sprint 11 |
| G-16 | Structured Feedback | `feedback_responses` table or JSONB expansion | 1 endpoint change (§13.4.1) | Sprint 10 |
| G-17 | Save-as-Learning | Wires to G-13 | Covered by `POST /learnings` | Sprint 10 |

**Migration plan:** Single migration `006_sprint10_collaboration.sql` for learnings + debates + debate_replies + feedback_responses. Separate `007_sprint11_annotations.sql` for annotations.

---

*--- RegPulse FSD v4.0 (Frontend v2 Redesign + Team Collaboration Modules, 2026-04-22) --- All rights reserved ---*
