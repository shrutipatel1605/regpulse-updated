# RegPulse v2 Frontend Handover — Terminal-Modern Redesign

> **For a fresh Claude Code CLI session.** Pick up where the previous session paused.

**Branch:** `claude/implement-regpulse-frontend-7pNk8`
**Status:** Chunk 1/5 shipped, pushed. Build green (`pnpm -C frontend build`, 24/24 pages, no type errors).

---

## What's done — Chunk 1

Terminal-modern design system + shell + Dashboard. See commit on the branch.

Files written:
- `frontend/src/app/globals.css` — full token system (paper/ink/amber palette, serif editorial, mono data, `html.dark` overrides keyed to existing theme store). Replaces old minimal Tailwind-only globals.
- `frontend/src/components/design/Primitives.tsx` — `Pill, Tick, Btn, Kbd, Icon (full set), Sparkline, Avatar, ToastProvider/useToast, MiniStat, cn`.
- `frontend/src/components/shell/` — `TopBar, Ticker, Sidebar, CommandPalette, TweaksPanel, AppShell, nav.ts`.
- `frontend/src/app/(app)/layout.tsx` — now mounts `AppShell` (replaced the old `AppSidebar`).
- `frontend/src/app/(app)/dashboard/page.tsx` — full executive command center (hero + 4 metric tiles + This-Week + 7×7 heatmap + activity + exposure + debates).
- `frontend/src/lib/mockData.ts` — ported design fixtures (ticker, heatmap, activity, debates, featured answer, learnings, saved).
- `frontend/src/app/layout.tsx` — body className stripped of fixed greys so tokens own background/foreground.

Built-in live wiring preserved: `useAuthStore` drives topbar user + credits; `useQuery` drives sidebar badges (`/circulars/updates`, `/action-items/stats`).

---

## What's pending

### Chunk 2 — Ask editorial brief
Rewrite `frontend/src/app/(app)/ask/page.tsx` to match `files/design-v2/project/src/ask.jsx`. Keep the existing live SSE wiring (`fetch` + `ReadableStream` against `POST /questions`). Add:
- question bar (`tick`: "ASK · RETRIEVAL FROM 4,821 CIRCULARS · KG-EXPANSION ON") with textarea + `1 credit` label + Ask button
- byline row: `BRIEF · <q-id>` + avatar + askedBy + askedAt + risk pill + `ConfBadge`
- big serif question headline
- `rp-prose` body with `.dek` deck; support inline `<mark class="annot">` for annotations (mock only — real SSE text has no annot spans)
- Recommended-actions list (grid `56px 120px 1fr 70px auto`)
- Feedback bar with thumbs + structured `FeedbackForm` (checkbox chips: "Missing a relevant circular" / "Misinterpreted a citation" / etc.) + save/export/save-as-learning buttons
- `LearningModal` — one-line takeaway + notes + tags + Notify team checkbox
- Right rail: `ConfidenceRadial` (SVG donut) → `CITATIONS · N` list (click to select) → `DEBATE · N` thread → Annotations hint block
- When no question submitted yet: render `RP_DATA.featuredAnswer` so the page isn't empty.

Toast notifications (use `useToast`) for: feedback-submit, save-as-learning, export-PDF, assign-action.

### Chunk 3 — List pages
Rewrite in place, matching `files/design-v2/project/src/pages.jsx`:
- `frontend/src/app/(app)/library/page.tsx` — 240px filter aside + search + 2-col card grid (`CircCard`)
- `frontend/src/app/(app)/updates/page.tsx` — h1 + `LAST SCAN · 2m AGO` + tabs [Circulars | News | Consultations] with table for circulars, relevance cards for news
- `frontend/src/app/(app)/history/page.tsx` — table (Question / When / Risk / Confidence bar / Teams)
- `frontend/src/app/(app)/saved/page.tsx` — 2-col card grid with serif italic question quote
- `frontend/src/app/(app)/action-items/page.tsx` — header with MiniStats (OPEN/HIGH/OVERDUE) + tabbed filters + full `dtable`

Keep existing TanStack Query hooks (`useQuestionHistory`, etc.); the new layouts render live data but degrade to `RP_DATA` when lists are empty.

### Chunk 4 — New routes
- `frontend/src/app/(app)/learnings/page.tsx` — `Team Learnings` with 3 MiniStats (CAPTURED · TOTAL / THIS WEEK / CONTRIBUTORS) + card list (avatar + serif takeaway + note + tag pills + "Source: <circ>" + Pin/Edit buttons). Mock data only for now — no backend yet.
- `frontend/src/app/(app)/debate/page.tsx` — 2-col debate cards (OPEN/RESOLVED pill + replies count + title + src mono + agree/disagree bar + "Open thread"). Mock only.

Add to `NAV` in `frontend/src/components/shell/nav.ts`? They're already there (`learnings`, `debate`).

### Chunk 5 — Upgrade + Account
- `frontend/src/app/(app)/upgrade/page.tsx` — 3-col plan cards, "MOST CHOSEN" amber ribbon on Pro card; serif editorial headline above.
- `frontend/src/app/(app)/account/page.tsx` — PROFILE panel (Name/Email/Role/Org/Plan grid) + TEAM · N MEMBERS panel (avatar rows) + DATA · DPDP COMPLIANCE panel with Export/Delete buttons. Wire real `/account/export` + `/account/delete` flows (preserved from existing page).

---

## How to run

```
cd frontend
pnpm install                 # first time
pnpm type-check              # tsc --noEmit
pnpm build                   # full next build
pnpm dev                     # localhost:3000
```

Visual testing: log in (DEMO_MODE fixed OTP `123456`), land on `/dashboard`. Toggle the amber gear (bottom-right) for the Tweaks panel. ⌘K for the command palette.

---

## Design source

Full prototype stashed at `files/design-v2/`:
- `files/design-v2/README.md` — handoff instructions from claude.ai/design
- `files/design-v2/project/RegPulse.html` — entry HTML
- `files/design-v2/project/styles/tokens.css` — reference tokens (already ported)
- `files/design-v2/project/src/{app,primitives,shell,dashboard,ask,pages}.jsx` — source of truth for layout, inline styles, interaction logic
- `files/design-v2/project/data/mock.js` — source of truth for the mock data (already ported to TS)
- `files/design-v2/chats/chat1.md` — original user intent ("Bloomberg terminal meets modern editorial", executive CCO, debate/annotation, save-as-learning, live pulse)

---

## Hard constraints (do not break)

1. `html.dark` class-based dark mode — the pre-hydration script in `app/layout.tsx` already runs; do NOT add `[data-theme]` selectors.
2. Design tokens live in `globals.css` as CSS custom properties — read via `var(--signal)` etc. Do NOT move them into `tailwind.config.ts`.
3. Access token stays in Zustand memory only — never `localStorage`. Refresh token is an HTTPOnly cookie. `withCredentials: true` in axios handles it.
4. `<Link>` + `<button>` child is invalid HTML — use the `LinkBtn` helper pattern (router.push in onClick) or render the link as a styled `<a>`.
5. When a page's backend returns empty lists, degrade gracefully to `RP_DATA` so the terminal stays alive. Don't show "no data yet" zero-states on the executive surfaces — it kills the sensibility.
6. Toasts via `useToast().push({ tag: "LEARNING", text: "..." })` — already wired globally by `ToastProvider` in `AppShell`.

---

## One-line prompts for a fresh CLI session

Paste one of these to resume:

> **Chunk 2:** Implement the Ask page editorial brief per `files/design-v2/project/src/ask.jsx`. Preserve the live SSE wiring in `frontend/src/app/(app)/ask/page.tsx`. See `HANDOVER_DESIGN_V2.md` Chunk 2. Build green before committing.

> **Chunk 3:** Implement list-page redesigns (Library, Updates, History, Saved, Action Items) per `files/design-v2/project/src/pages.jsx`. Keep existing TanStack hooks as live data sources. See `HANDOVER_DESIGN_V2.md` Chunk 3. Build green before committing.

> **Chunk 4:** Add `/learnings` and `/debate` routes per `files/design-v2/project/src/pages.jsx`. Mock data only — no backend yet. See `HANDOVER_DESIGN_V2.md` Chunk 4. Build green before committing.

> **Chunk 5:** Redesign Upgrade + Account per `files/design-v2/project/src/pages.jsx`. Preserve real account export/delete flows. See `HANDOVER_DESIGN_V2.md` Chunk 5. Build green before committing.

Each chunk: write code → `pnpm build` → commit with `feat(frontend): ...(chunk N/5)` → `git push origin claude/implement-regpulse-frontend-7pNk8`.
