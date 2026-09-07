---
name: archforge
description: "Architecture resilience for new products and mid-build features. Prevents cascade failures via interface contracts, change profiles, and stack decisions. Use before code starts or when features break things."
---

# ArchForge — Architecture Resilience for UX-First Builders

## Why builds break mid-flight

Three root causes cover almost every cascade failure:
1. **No interface contract** — API surface undefined before build starts; UX changes → API changes → tests break
2. **No change profile** — architecture built for today, not for the 5–8 changes likely in Year 1
3. **Coupling without boundaries** — modules share state they shouldn't; a change in one bleeds into another

The stack question is secondary. Python/FastAPI + PostgreSQL + Next.js is the default for
Think360 products. ArchForge tells you when to deviate and why.

## Three modes — state the mode explicitly when invoking

| Mode | When | Output |
|------|------|--------|
| INCEPTION | New product, before code | Interface Contract + Change Profile + Stack Decision Record |
| EVOLUTION | Adding a feature mid-build | Change Impact Report (5 questions) |
| DIAGNOSIS | Tests failing, unclear cause | Cascade Trace + fix sequence |

---

## MODE 1: INCEPTION

Run after PRD exists, before T11 Scaffolding Gate 3.

### Step 1 — Change Profile (ask the user these questions, document answers)

**Q1. What are the 5–8 things most likely to change in 12 months?**
Probe: data model (new entities/fields), business rules (thresholds/formulas),
integrations (new sources/channels), user personas (new roles/permissions),
regulatory (compliance shifts), scale (10× volume).

**Q2. Which change is most likely to cascade if architecture isn't designed for it?**
This becomes the primary seam to design around.

**Q3. What is the frontend's primary data need?**
Format: "The frontend needs to [display/allow/search X] and the data comes from [source]."

**Q4. Non-negotiable performance SLAs?** (latency, throughput, availability — quantified)

Output: Change Profile in MEMORY.md (use template from TEMPLATES.md).

### Step 2 — Stack Decision (run this checklist, document as ADR-001)

| Question | Answers → recommendation |
|----------|------------------------|
| Primary data type | Structured relational → PostgreSQL. Documents/PDFs → PostgreSQL + pgvector or S3. Time-series → PostgreSQL + partitioning. |
| Computation pattern | CRUD → FastAPI sync. Heavy processing/ML/scraping → FastAPI + Celery worker queue. Real-time → FastAPI + SSE/websockets. |
| Integration type | REST APIs → httpx. File ingestion → worker queue + storage. Webhooks → FastAPI endpoints + queue. Browser automation → Playwright in separate service. |
| Frontend pattern | Forms/dashboards → Next.js. Real-time → Next.js + SSE. Heavy viz → Next.js + Recharts/D3. |
| Scale in 12 months | <10K users → single server. 10K–50K → connection pooling, horizontal scale. >50K → read replicas + Redis cache. |

**Default:** Python 3.11 + FastAPI + PostgreSQL + Next.js + Celery (if async needed).
**Deviate only when:** Go (>10k req/s), MongoDB (truly schema-less by design), pgvector (semantic search core).
**Never for these products:** Java (no team depth), C++ (wrong domain).

Output: ADR-001 in MEMORY.md — must include decision, alternatives, rationale, and change condition.

### Step 3 — Interface Contract Lock (most important step)

Lock the API surface BEFORE frontend or backend is built. Both sides conform to it.

**Per endpoint, specify:**
- `[METHOD] /api/v1/[resource]/[action]` — purpose (one sentence, which UI action triggers it)
- Request: typed schema (field: type, required/optional)
- Response 200: typed schema
- Errors: 400/401/404/422/500 with meaning
- Side effects: DB writes, events emitted
- Evolution notes: what is likely to change about this endpoint

**Rules:**
1. Every UI screen/action maps to at least one contract endpoint
2. Contract complete before any backend code — frontend builds against mocks
3. If frontend needs something not in contract: update contract first, then build
4. Contract lives in SPEC.md "API Surface" — single source of truth

**Mock layer rule:** Every external dependency gets a mock interface returning realistic
test data. Real implementation swappable behind the same interface. Tests never need live credentials.

Output: Interface Contract in SPEC.md (use template from TEMPLATES.md).

### Step 4 — Coupling Boundaries

State for each module: what data it owns, what it exposes, what it consumes.
Standard layer stack:

```
Frontend (Next.js)     → consumes API Contract only, never DB
API Layer (FastAPI)     → validates requests, shapes responses, calls Service Layer only
Service Layer           → business logic, calls Repository Layer only
Repository Layer        → database queries, exposes typed functions
Database (PostgreSQL)   → persistence only
```

**Rule:** A change to an existing feature should touch ONE layer. Two layers = proceed with care.
Three layers = stop, this is architecture work, not a feature.

---

## MODE 2: EVOLUTION

Run before writing any code for a new feature. Takes 5 minutes.

### Change Impact Assessment — 5 questions

**Q1. New data?** New tables, columns, relationships? → Update SPEC.md data model first.
**Q2. API changes?** New endpoints → add to contract first. Changed endpoints → versioning needed?
**Q3. Which service functions change?** New cross-service dependencies = high risk.
**Q4. How many layers touched?** 1 = go. 2 = care. 3+ = STOP, re-run INCEPTION for this feature.
**Q5. Which tests will break?** Name them. State: updated (scope changed) or fixed (genuine regression).

**Seam-first rule for new endpoints:**
1. Write endpoint definition in SPEC.md
2. Write the test (will fail)
3. Write mock implementation (test passes with mock data)
4. Confirm frontend works against mock
5. Build real implementation — tests pass without modification

Output: Change Impact Report in MEMORY.md (use template from TEMPLATES.md).

---

## MODE 3: DIAGNOSIS

Run when tests fail and cause is unclear.

**Step 1:** Name the failing tests exactly (file, function, error message). No fix attempts yet.
**Step 2:** `git diff HEAD~1 HEAD --name-only` — list every changed file.
**Step 3:** Map each changed file to its layer (Frontend / API / Service / Repository / Data / Config / Test).
**Step 4:** Trace each failing test backward through the call stack to where a changed file appears. State the cascade path.
**Step 5:** Classify the failure:
- Contract violation (changed signature broke caller) → restore contract or update callers
- Data model drift (changed schema broke query) → update migration + repository
- Business rule regression (changed logic, wrong output) → restore logic or update test if rule genuinely changed
- Missing mock update (changed interface, old mock) → update mock

**Step 6:** Fix bottom-up: Data Model → Repository → Service → API → Frontend → Tests.
Never fix a test to make a cascade pass.

---

## Anti-Patterns

- **Building frontend against a live, evolving backend** — always build against mocks first
- **Designing API to match database structure** — API matches frontend needs; service layer translates
- **Skipping Change Impact Assessment because feature seems small** — small features cascade most
- **Using Claude Code to "just try something" without updating contract** — code that diverges from SPEC.md creates drift
- **Choosing a stack because it's theoretically superior** — team familiarity + good structure beats unfamiliar + perfect every time
