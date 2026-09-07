# ArchForge — Artifact Templates

Read this file only when producing output artifacts. Not needed at session start.

## Change Profile (store in MEMORY.md)

```
CHANGE PROFILE: {{PRODUCT_NAME}} | Updated: {{DATE}}

| Axis          | Anticipated change               | Likelihood | Seam needed          |
|---------------|----------------------------------|------------|----------------------|
| Data model    | {{description}}                  | High/Med   | {{seam}}             |
| Business rule | {{description}}                  | High/Med   | {{seam}}             |
| Integration   | {{description}}                  | High/Med   | {{seam}}             |
| User persona  | {{description}}                  | High/Med   | {{seam}}             |
| Regulatory    | {{description}}                  | High/Med   | {{seam}}             |
| Scale         | {{description}}                  | High/Med   | {{seam}}             |

HIGHEST RISK CHANGE: {{the one most likely to cascade}}
PRIMARY SEAM: {{the architectural decision made to absorb this}}
```

## Stack Decision Record (store in MEMORY.md as ADR-001)

```
ADR-001: Technology Stack
Decision:         {{backend / database / frontend / queue / infra}}
Alternatives:     {{considered and rejected, with reasons}}
Rationale:        {{which decision-tree answers drove each choice}}
Change condition: {{what would cause this to be revisited}}
```

## Interface Contract — Per Endpoint (store in SPEC.md under "API Surface")

```
ENDPOINT: {{METHOD}} /api/v1/{{resource}}/{{action}}
UI trigger:      {{what user action calls this}}
Auth:            {{Bearer JWT / API key / public}}
Request body:    {{field: type (required|optional) — description}}
Response 200:    {{field: type — description}}
Errors:          400: {{when}} | 401: {{when}} | 404: {{when}} | 422: {{fields}} | 500: {{when}}
Side effects:    {{DB writes, events, external calls}}
Mock available:  {{yes/no — path}}
Evolution notes: {{what will likely change}}
```

## Change Impact Report (store in MEMORY.md, one per feature)

```
CHANGE IMPACT: {{FEATURE_NAME}} — {{DATE}}
Data model changes:   {{yes/no — description}}
API contract changes: {{yes/no — new/modified endpoints}}
Service layer changes:{{yes/no — functions affected}}
Layers touched:       {{count — names}}
Assessment:           {{proceed / proceed with care / STOP}}
Tests expected to break: {{list}}
```
