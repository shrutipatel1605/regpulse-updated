---
name: rebuild
description: "Resurrects stalled projects. Reads entire repo forensically, audits 7 dimensions, classifies files as keep/rewrite/discard, produces corrected one-shot build plan with prompt pack. Use when a project is stuck."
---

# ReBuild — Project Resurrection from Stalled Repos

## Principles

1. Never re-decide what was correctly decided. Salvage good decisions; reverse bad ones.
2. The stall point always has a root cause. Find it before replanning.
3. The rebuild plan must encode lessons from what went wrong — not just restart.
4. The plan must be executable from cold — no assumed context from prior sessions.

**ReBuild does not write code. It writes the plan that writes the code.**

## Four phases — strict order, confirmation gate between each

```
PHASE 1: INGEST  → Read entire repo, build state snapshot → confirm with user
PHASE 2: AUDIT   → Score 7 dimensions, name failure mode   → confirm with user
PHASE 3: SALVAGE → Classify every file and decision         → confirm with user
PHASE 4: REPLAN  → Produce corrected plan + prompt pack     → commit as rebuild foundation
```

---

## PHASE 1: INGEST

### 1.1 — Repo Structure Scan

Read directory tree. Report status of each artifact:

| Artifact | Check for | Report |
|----------|-----------|--------|
| README.md, CLAUDE.md, MEMORY.md, SPEC.md, TOOLING.md | exists / missing / stale | last modified date |
| Source code (src/ or app/) | file count + total lines | complete / partial / skeleton |
| Tests (tests/) | run `pytest -v --tb=short` | pass count / fail count / error count |
| Migrations (alembic/ or migrations/) | exists / partial | migration count |
| Git history | `git log --oneline -20` | commit count, last date, gaps, reverts |
| Config (.env.example, requirements.txt) | exists / missing | dependency count, pinned? |

### 1.2 — Artifact Deep Read

Read in order: MEMORY.md (ADRs, changelog, blockers) → SPEC.md (data models, endpoints, NFRs)
→ CLAUDE.md (stack, session plan, conventions) → git log → test results → source code inventory.

For source code: list all files with line counts. Flag imports that reference nonexistent modules.

### 1.3 — Intent Reconstruction

Answer in 1–2 sentences each:
1. What was this product supposed to do?
2. What was the build plan?
3. How far did it get? (specific milestone + percentage)
4. When and why did it stall?

**Present to user. Wait for confirmation before Phase 2.**

---

## PHASE 2: AUDIT

Score each dimension 1–5 (1 = critical failure, 5 = no issues).
For any ≤2: state the specific failure with evidence from Phase 1.

### The 7 Dimensions

**D1. Spec Completeness** — Are all features specified with acceptance criteria?
Data models typed or prose? API endpoints documented with schemas? NFRs quantified?
Scope boundary explicit? _Failure: "The spec was a wish list, not a build specification."_

**D2. Architecture Soundness** — Do ADRs match actual code? Are there missing ADRs
(no auth strategy, no async pattern)? Is code layered correctly (API/Service/Repository)?
Coupling violations (frontend importing backend models, service querying DB directly)?
_Failure: "Architecture was decided implicitly by code, not explicitly by design."_

**D3. Interface Contract** — Was there a formal API contract before code? Does frontend
consume the contract or hit ad-hoc endpoints? Drift between SPEC.md and actual routes?
Mocks available for external dependencies? _Failure: "The API evolved by accretion."_

**D4. Test Health** — Test count vs endpoint count? Unit vs integration? Are failing tests
genuine regressions or tests for unbuilt features? Pytest gates defined per session?
_Failure: "Tests were written to pass, not to catch regressions."_

**D5. Session & Prompt Quality** — Sessions scoped to 3–5 prompts? Clear deliverable and
test gate per session? Sessions too broad ("implement the backend")? Missing MEMORY.md updates?
Sessions that produced code but no tests? _Failure: "Prompts were vague; context was lost."_

**D6. Dependencies & Environment** — All dependencies pinned? Conflicts in error logs?
External credentials documented? Does `pip install && pytest` work locally?
_Failure: "The project works on one machine and nobody wrote down why."_

**D7. Scope Discipline** — Did scope expand during build? Features in code not in spec?
Unfinished branches? New features added without spec updates?
_Failure: "The project tried to do more than planned and finished none of it."_

### Scorecard

Sum scores → tier: Critical (<15) / Troubled (15–24) / Salvageable (25–30) / Healthy (31+).
State: primary failure mode (1 sentence) + secondary factors (1–2 sentences).

**Present Audit Scorecard to user. Wait for confirmation before Phase 3.**

---

## PHASE 3: SALVAGE

### 3.1 — File Classification

For every source file and artifact, classify:

**KEEP** — Correct, tested, aligned with spec. Criteria: passing tests + matches SPEC.md + no coupling violations.
**REWRITE** — Right intent, wrong implementation. Criteria: partially working, structural issues, no tests, hardcoded values. State the specific fix.
**DISCARD** — Wrong, abandoned, or contradicts corrected plan. State the lesson learned.

### 3.2 — Decision Reversal Register

For every ADR in MEMORY.md:
- **CONFIRMED** — still correct, carry forward
- **REVERSED** — wrong; state why + new decision + new rationale
- **MODIFIED** — partially correct; state what changes

This register becomes the foundation of the rebuilt MEMORY.md.

**Present Salvage Inventory + Decision Register to user. Wait for confirmation before Phase 4.**

---

## PHASE 4: REPLAN

### 4.1 — Corrected Architecture

State corrected: stack (confirm or change each component), data model (typed schemas),
Interface Contract (endpoint list), coupling boundaries. If no Interface Contract existed
in original project: run ArchForge INCEPTION now.

### 4.2 — Corrected Build Plan (N-session Claude Code prompt pack)

**Session structure rules:**

| Session | Always contains | Why |
|---------|----------------|-----|
| Session 1 | DB models + migrations + repository + seed data | Everything depends on the data layer |
| Session 2 | FastAPI route skeletons for ALL endpoints, returning mocks | Frontend never blocks on backend |
| Sessions 3–N | One feature per session, built as a vertical slice (repo → service → API → frontend → test) | Every session is testable and demoable |
| Last session | Full test suite + integration fixes + documentation update | Clean close |

**Every session prompt must include:**
- Context: "Project state: [what exists]. This session builds: [deliverable]."
- Pytest gate: specific test names + minimum pass count
- Scope containment: what NOT to touch
- Close: "Update MEMORY.md, commit as '[ID]: [description]', run full pytest."

### 4.3 — KEEP/REWRITE Integration

For KEEP files: state which session they belong to (skip that work), which tests validate them.
For REWRITE files: state which session rewrites them + specific fix instruction from salvage.

### 4.4 — Updated Foundation Artifacts

Produce corrected versions of all four files:
- **MEMORY.md** — Decision Reversal Register + salvage summary + corrected phase state
- **CLAUDE.md** — Updated session protocol + corrected stack + new prompt pack
- **SPEC.md** — Corrected data models + Interface Contract + updated NFRs
- **README.md** — Updated scope and current state

First commit: `REBUILD: Corrected foundation — [N] kept, [M] rewritten, [K] discarded`

---

## Integration

```
[Stalled repo] → ReBuild PHASE 1–3 (diagnose)
    → PHASE 4 REPLAN (produces same artifacts as T01 Repo Foundation Pack)
        → ArchForge INCEPTION (if Interface Contract was missing)
            → T12 Sprint Execution (execute the rebuild)
                ↔ T13 Prompt Optimizer (audit rebuild prompts)
```

---

## Anti-Patterns

- **Skipping Phase 1** — the artifacts contain the diagnosis; even if you think you know what's wrong, read everything
- **Discarding everything** — stalled projects almost always have salvageable code; a rebuild that keeps nothing is a restart that repeats the same mistakes
- **Copying the old prompt pack** — the old pack caused the stall; the new plan must be rewritten from audit findings
- **Skipping the Decision Reversal Register** — silently inherits bad decisions from the original build
- **Skipping user confirmation gates** — Phases 1–3 each require explicit user confirmation; the plan is built on unchecked assumptions otherwise
- **Treating ReBuild as one-time** — the skill is re-entrant; if the rebuild stalls, run ReBuild again on the richer forensic record
