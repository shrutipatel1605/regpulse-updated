# ReBuild — Artifact Templates

Read this file only when producing output artifacts. Not needed at session start.

## State Snapshot (Phase 1 output)

```
STATE SNAPSHOT: {{PRODUCT_NAME}}
Repo: {{REPO_URL}} | Scanned: {{DATE}}

ARTIFACT STATUS:
| Artifact    | Status         | Last updated | Notes                         |
|-------------|----------------|--------------|-------------------------------|
| README.md   | exists/missing | {{date}}     | {{observation}}               |
| MEMORY.md   | exists/missing | {{date}}     | {{N}} ADRs, {{M}} open Qs    |
| SPEC.md     | exists/missing | {{date}}     | {{N}} entities, {{M}} endpoints|
| CLAUDE.md   | exists/missing | {{date}}     | {{N}}-session plan defined    |
| Source code  | complete/partial| {{date}}    | {{N}} files, {{M}} lines      |
| Tests        | passing/failing | {{date}}    | {{pass}}/{{total}} passing    |

GIT: {{total}} commits | Last: {{date}} — {{message}} | Longest gap: {{N}} days | Reverts: {{count}}

INTENT RECONSTRUCTION:
1. Purpose: {{1–2 sentences}}
2. Build plan: {{1–2 sentences}}
3. Progress: {{milestone + percentage}}
4. Stall cause: {{1–2 sentences}}
```

## Audit Scorecard (Phase 2 output)

```
AUDIT SCORECARD: {{PRODUCT_NAME}}

| # | Dimension              | Score | Finding                |
|---|------------------------|-------|------------------------|
| 1 | Spec completeness      | [1-5] | {{1-sentence finding}} |
| 2 | Architecture soundness | [1-5] | {{1-sentence finding}} |
| 3 | Interface contract     | [1-5] | {{1-sentence finding}} |
| 4 | Test health            | [1-5] | {{1-sentence finding}} |
| 5 | Session/prompt quality  | [1-5] | {{1-sentence finding}} |
| 6 | Dependencies/env       | [1-5] | {{1-sentence finding}} |
| 7 | Scope discipline       | [1-5] | {{1-sentence finding}} |

OVERALL: {{sum}}/35 — {{Critical / Troubled / Salvageable / Healthy}}
PRIMARY FAILURE MODE: {{1 sentence}}
SECONDARY FACTORS: {{1–2 sentences}}
REBUILD ESTIMATE: {{N}} sessions | KEEP: {{N}} files | REWRITE: {{N}} | DISCARD: {{N}}
```

## Salvage Inventory (Phase 3 output)

```
SALVAGE INVENTORY: {{PRODUCT_NAME}}

KEEP ({{N}} files, {{M}} lines):
| File | Lines | Reason | Depends on |

REWRITE ({{N}} files, {{M}} lines):
| File | Lines | Fix required | Rebuild session |

DISCARD ({{N}} files, {{M}} lines):
| File | Lines | Lesson learned |

DECISION REVERSAL REGISTER:
| ADR   | Original decision | Status    | New decision (if changed) | Rationale |
```
