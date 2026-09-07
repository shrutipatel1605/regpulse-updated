# LEARNINGS — RegPulse Phase 2

> Mistakes, surprises, and gotchas that cost us time during Phase 2 (Sprints 1–7). Each entry is a guard against repeating the same loss in future iterations. Read this before starting any sprint.
>
> Format per entry: **what bit us**, **root cause**, **fix or guard**, **how to prevent**.

---

## Sprint 1 — Hardening, Analytics, Embedder, Landing Page

### L1.1 — DEMO_MODE branches must be wired everywhere they matter
**What bit us:** First demo trial failed because the cross-encoder reranker hung downloading from HuggingFace inside Docker for Mac (SSL timeout), and the OTP rate limit (`OTP_MAX_SENDS_PER_HOUR=3`) was so low we couldn't iterate during testing.
**Root cause:** `DEMO_MODE` was treated as a single boolean but actually needs to gate several independent code paths (OTP, email, payment, expensive model loads, rate limits).
**Fix:** Explicit `if settings.DEMO_MODE:` branches in `main.py` (skip cross-encoder), `otp_service.py` (fixed OTP `123456`), `auth.py` (skip MX check), and per-feature documentation in `CLAUDE.md` § DEMO_MODE.
**Prevention:** When adding any feature that calls an external service, makes a slow startup decision, or charges money — add an explicit DEMO_MODE branch and document it in the DEMO_MODE table.

### L1.2 — `.env` multiline PEM keys break Docker's env parser
**What bit us:** JWT_PRIVATE_KEY pasted as a multi-line PEM into `.env` caused Docker Compose to silently truncate the value at the first newline.
**Root cause:** `.env` files are line-oriented; embedded `\n` literals are accepted but real newlines aren't.
**Fix:** `_expand_pem_newlines` field validator in `app/config.py` converts literal `\n` to real newlines on load. Document the encoding in `.env.example`.
**Prevention:** Any multi-line secret in `.env` must use `\n` literals. Add a validator at the config layer if you ever introduce another.

### L1.3 — `pydantic-settings` v2 wants JSON for list-typed env vars
**What bit us:** `ADMIN_EMAIL_ALLOWLIST=admin@x.com,foo@y.com` failed to parse because pydantic-settings v2 expects JSON array syntax.
**Root cause:** v2 dropped the implicit CSV parsing that v1 supported.
**Fix:** `_parse_admin_allowlist` field validator accepts both CSV and JSON, normalising to a list. Same pattern works for any list-typed env var.
**Prevention:** Any new `list[str]` setting needs a `mode="before"` validator that handles strings.

### L1.4 — Frontend Docker build needs `frontend/public/` to exist
**What bit us:** Next.js standalone build failed because the `public/` directory didn't exist (we hadn't checked anything in there yet).
**Root cause:** Next.js build copies `public/` and errors if it's missing, even if empty.
**Fix:** Commit an empty `public/` directory (use `.gitkeep`).
**Prevention:** When scaffolding a new Next.js project in this repo, always create `public/` even if empty.

### L1.5 — Celery scrapper task routing to a queue the worker doesn't consume
**What bit us:** Scraper tasks were enqueued to the `scraper` queue (per `task_routes` in `celery_app.py`), but the worker started with default `-Q celery`, so tasks sat unconsumed.
**Root cause:** `task_routes` is independent of which queues the worker subscribes to. Two different concepts that must agree.
**Fix:** Worker started with `-Q celery,scraper` in `docker-compose.yml`.
**Prevention:** Whenever you add a new `task_routes` entry, audit the worker command in compose/k8s to make sure it consumes that queue. Consider a startup-time assertion.

### L1.6 — `refresh_token` cookie behaviour invariants
**What bit us:** Sprint 1 refactor moved refresh tokens to HttpOnly cookies but the frontend kept reading from `document.cookie`. Middleware then redirected every protected route to `/login` because the cookie wasn't there client-side.
**Root cause:** HttpOnly cookies are deliberately invisible to JavaScript. The previous architecture relied on client-side cookie reads.
**Fix:** Frontend `axios` uses `withCredentials: true` and trusts the browser to send the cookie automatically. `authStore.setAuth(user, accessToken)` no longer accepts a refresh token. Middleware checks the cookie via `request.cookies.get`, which works server-side.
**Prevention:** When introducing HttpOnly cookies, audit every consumer for `document.cookie` reads and `localStorage` fallbacks. Codified as Rule 11/12 in `CLAUDE.md`.

### L1.7 — Scraper embedder was a stub for ages because nothing failed loudly
**What bit us:** The embedder wrote empty vectors `[]` into `document_chunks.embedding`, so RAG retrieval silently returned zero results until someone noticed in the demo.
**Root cause:** The stub was committed as a placeholder with the intent to fix in a "future prompt" — and the future prompt never came. Tests didn't cover the embedder because the rest of the pipeline tolerated empty vectors.
**Fix:** Sprint 1 replaced the stub with the real OpenAI batched call.
**Prevention:** Stubs must either (a) raise NotImplementedError, or (b) have a tracking task with a deadline. Never leave a "returns empty" stub in a code path that other components consume.

### L1.8 — `password_changed_at` ORM column was missing from the SQL schema
**What bit us:** The `User` ORM declared `password_changed_at` but the migration never created the column. SELECTs failed with "column does not exist" only at runtime.
**Root cause:** ORM and migration drifted because we don't use Alembic autogenerate. Manual SQL migration missed the field added later in the model.
**Fix:** Patched migration `001_initial_schema.sql` directly. Documented as a known issue.
**Prevention:** When you add a column to an ORM model, the same commit MUST update the migration SQL. Add a CI check that diffs `Base.metadata.create_all` against the migration if this happens twice.

---

## Sprint 2 — Anti-Hallucination, Evals, Load Tests

### L2.1 — Both `generate()` and `generate_stream()` must enforce identical safety
**What bit us:** Initial Sprint 2 patch added the insufficient-context guard only to `generate()`. The streaming path bypassed it, so live SSE answers could still hallucinate.
**Root cause:** Two near-duplicate code paths in `llm_service.py` for streaming vs non-streaming, both reachable from `/ask`.
**Fix:** Extracted the safety checks (insufficient-context guard, citation validation, confidence computation, consult-expert fallback) into shared helpers called by both paths.
**Prevention:** Any change to LLM safety logic must touch both `generate` and `generate_stream`. Codified in the eval test suite — both paths are tested.

### L2.2 — Citation validation must report a count, not just a filtered list
**What bit us:** Initial confidence formula divided `valid_citations / total_attempted`, but `total_attempted` was lost after `_validate_citations` returned only the filtered list. We were computing confidence from `valid/valid = 1.0` always.
**Root cause:** Throwing away the pre-filter count.
**Fix:** `_validate_citations` now writes `_stripped_citation_count` back into the response dict so the confidence computer can read it.
**Prevention:** When a function filters a list and a downstream caller needs to know the original size, return the count alongside the filtered result — don't make the caller re-derive it.

### L2.3 — Changing the LLM response schema breaks the frontend silently
**What bit us:** Sprint 2 added `confidence_score`, `consult_expert`, and changed `risk_level` to nullable. The frontend `/ask` page assumed `risk_level` was always a string and crashed in dev.
**Root cause:** No type contract synced between backend Pydantic schemas and frontend TypeScript types.
**Fix:** Frontend hotfix to handle null. The longer-term plan is OpenAPI codegen (TD-03).
**Prevention:** Whenever you add or nullable-ify a field in the LLM response schema, grep the frontend for every consumer of that field and update the type definitions. Codified for Sprint 4 — Confidence Meter UI is the deliberate landing zone for the new fields.

### L2.4 — < 2 chunks short-circuit saves cost AND prevents hallucination
**What bit us:** Early Sprint 2 builds called the LLM even when retrieval returned 0–1 chunks. The LLM filled the gap from training data (hallucinated).
**Root cause:** No quantitative threshold for "enough context".
**Fix:** Insufficient-context guard in `llm_service.generate` returns a `consult_expert` response immediately when `len(chunks) < 2`. No LLM call.
**Prevention:** Treat retrieval depth as a first-class safety signal. Any future RAG-style feature should have an analogous "minimum evidence" check.

---

## Sprint 3 — KG, News Ingest, Public Snippets

### L3.1 — TIMESTAMPTZ columns require `DateTime(timezone=True)` in SQLAlchemy
**What bit us:** First snippet POST returned 500. The error was `can't subtract offset-naive and offset-aware datetimes`. The migration created `expires_at TIMESTAMPTZ`, but the ORM declared `Mapped[datetime | None] = mapped_column()`, which defaults to `TIMESTAMP WITHOUT TIME ZONE`. asyncpg refused to bind a tz-aware datetime to a naive column type.
**Root cause:** SQLAlchemy's `DateTime` type defaults to `timezone=False`. The bare `mapped_column()` infers a type from the Python annotation, which is `datetime` — without timezone hints.
**Fix:** Every TIMESTAMPTZ column in the new models (`kg.py`, `news.py`, `snippet.py`) explicitly declares `mapped_column(DateTime(timezone=True), …)`. Codified as Rule 8 in `CLAUDE.md`.
**Prevention:** Any new ORM model touching a TIMESTAMPTZ Postgres column must use `DateTime(timezone=True)`. If you find yourself writing `mapped_column(server_default="now()")` for a timestamp, ask yourself whether the column is timezone-aware in the migration — it almost always is for this codebase.

### L3.2 — `Limiter` instantiated in `main.py` causes a circular import the moment a router uses it
**What bit us:** Adding `@limiter.limit("60/minute")` to the snippets router required `from app.main import limiter`. But `app/main.py` already imports the snippets router. Circular import → ImportError at startup.
**Root cause:** `main.py` is the wrong home for shared infrastructure singletons. Anything routers need must live in a module that does NOT import routers.
**Fix:** Extracted `limiter = Limiter(...)` into `app/rate_limit.py`. Both `main.py` and any router import from there.
**Prevention:** Any new singleton that routers will consume (limiters, metrics registries, feature flags) belongs in its own module under `app/`, never in `app/main.py`. The same rule applies to redis clients, anthropic clients, etc. — the lifespan context wires them up, but the *type definitions* live elsewhere.

### L3.3 — Container backend has no bind mount; `docker cp` is the only way to iterate live
**What bit us:** Edited `backend/app/models/snippet.py` on the host, restarted the backend, and the change wasn't picked up. The container has the code baked into the image.
**Root cause:** `docker-compose.yml` bind-mounts the database init SQL but not the backend source. Production parity was prioritised over dev iteration speed.
**Fix:** Use `docker cp file regpulse-backend:/app/...` after each edit, then `docker restart regpulse-backend`. For the scraper container the path is `/scraper/...`.
**Prevention:** Document the live-iteration commands at the top of any sprint that touches backend or scraper. Or — better — add an opt-in `docker-compose.dev.yml` overlay with bind mounts. Tracked as a future improvement.

### L3.4 — Sprint 1 fixed the embedder in the repo but not in the running scraper image
**What bit us:** Pillar B (RSS news ingest) failed on first run with "vector must have at least 1 dimension" because the scraper container was still running the old stub embedder image. The repo had the real embedder since `363b1ef`, but the scraper container had been built before that commit.
**Root cause:** Long-running container plus in-place edits via `docker cp` had been syncing only the files I'd touched. The unrelated `embedder.py` was stale.
**Fix:** `docker cp scraper/processor/embedder.py regpulse-scraper:...` and the bug went away.
**Prevention:** When you start work on any sprint, rebuild the relevant containers from source first: `docker compose build backend scraper && docker compose up -d backend scraper`. Don't trust that a running container reflects the current `main`.

### L3.5 — pgvector cosine query against an empty embedding vector errors hard
**What bit us:** During the first ingest_news run, the embedder returned `[[]]` (one item, empty vector) — but my check was `if not vectors: return None, None`, which only catches the outer empty list. We then formatted `'[]'` as a vector literal and pgvector raised "vector must have at least 1 dimension".
**Root cause:** Insufficient empty-check.
**Fix:** `if not vectors or not vectors[0]: return None, None`.
**Prevention:** When defending against "embedder returned nothing", check both the outer list AND the first inner element. Same pattern applies to any external service that returns nested data.

### L3.6 — psycopg2 transaction abort poisons subsequent queries in the same session
**What bit us:** Pillar B's first run inserted 0/60 news items. The first failing INSERT (caused by L3.5) aborted the transaction, then every subsequent INSERT in the same `with get_db_session():` block failed with "current transaction is aborted, commands ignored until end of transaction block".
**Root cause:** Postgres transactions are atomic — one failure aborts the whole TX until rollback. Iterating a loop inside a single TX without per-item isolation is a footgun.
**Fix:** Each loop iteration runs inside `with db.begin_nested():` (a SAVEPOINT). One failure rolls back its own savepoint without affecting siblings.
**Prevention:** Any batch loop that does multiple writes inside one outer TX should wrap each iteration in `begin_nested()`. Treat this as the default for batch ingest.

### L3.7 — Frontend uses pnpm; running `npm install` produces a stray `package-lock.json`
**What bit us:** I needed `tsc` to type-check the new frontend pages, `frontend/node_modules` didn't exist, and I ran `npm install`. That created `frontend/package-lock.json`. Almost committed it.
**Root cause:** Repo standard is pnpm (`pnpm-lock.yaml` is in git history). I didn't check before installing.
**Fix:** Removed `package-lock.json` before staging. Should have used `pnpm install` from the start.
**Prevention:** Before installing frontend deps, run `git log --all --diff-filter=A --name-only -- 'frontend/*lock*'` to check which lockfile the repo expects. Add a `frontend/.npmrc` with `package-lock=false` as a guard.

### L3.8 — Pytest inside the backend container has unrecoverable sys.path collisions
**What bit us:** Tried to run new unit tests via `pytest` inside the backend container. Pytest auto-prepends `/` to `sys.path` (because `tests/__init__.py` exists but `/app/__init__.py` doesn't), which makes Python treat `/app/` as the `app` namespace package — shadowing the real `app` package living at `/app/app/`. Every conftest import of `from app.cache import get_redis` then failed.
**Root cause:** The backend container's `WORKDIR=/app` collides with the package name `app`. Pytest's rootdir-based collection assumes the parent of the package is on sys.path, but in this layout the parent is `/`, which Python treats as a namespace package source.
**Fix:** I tried multiple workarounds (custom conftest at /app, pytest.ini with `pythonpath=.`, `--rootdir`, `--confcutdir`) — none of them worked because the conftest at `/app/tests/conftest.py` loads BEFORE my conftest's sys.path repair code, and once `app` is cached as a namespace package, deleting it from `sys.modules` mid-import breaks the loading conftest itself.
**Workaround used:** Run new unit tests as plain python scripts that import the module directly. CI runs them properly via `PYTHONPATH=backend pytest backend/tests/unit/` from the project root, where this collision doesn't exist.
**Prevention:** Never try to run pytest from `/app` inside the backend container. Always run from outside with `PYTHONPATH=backend pytest backend/tests/...`. If you absolutely need in-container pytest, the proper fix is to rename the package from `app` to `regpulse_backend` — out of scope for one sprint.

### L3.9 — Celery broker URL DB number matters
**What bit us:** First `celery call scraper.tasks.ingest_news` returned a task ID but the worker never executed it. The CLI used `-b redis://redis:6379/0` (default), but the scraper worker is configured to consume from `/1` (set via `REDIS_URL` in `.env`). Tasks landed in db 0; worker watched db 1.
**Root cause:** Redis db number is part of the broker identity. Two clients pointing at the same host but different db numbers might as well be different brokers.
**Fix:** `celery -A celery_app -b redis://redis:6379/1 call ...` matches the worker's actual broker.
**Prevention:** Always pass `-b $REDIS_URL` (or omit `-b` and let celery_app's defaults take over) when triggering tasks manually. Document the broker URL alongside the docker exec snippet in `CLAUDE.md`.

### L3.10 — Public snippet redaction must be enforced at the SERVICE layer, not the router
**What bit us (could have):** It's tempting to build the snippet payload in the router by reading fields off the question record and packing them into the response. That puts the redaction guarantee one `model_dump()` away from leaking `detailed_interpretation`.
**Root cause/risk:** Routers are easy to refactor; field expansion is a one-line accident.
**Fix:** `snippet_service._build_safe_snippet` is the ONLY function that reads from a `Question` record on the snippet path. It returns `(snippet_text, top_citation_dict, consult_expert)`. The router never sees the question. Unit test `test_detailed_interpretation_never_leaks` asserts the FULL ANSWER text never appears in the output, including in the citation dict's string repr.
**Prevention:** Any "redacted projection" of a sensitive record belongs in a service function that returns a fully-baked safe payload. Never let a router touch the source record and pick fields.

### L3.11 — News must NEVER end up in the RAG retrieval corpus
**What bit us (could have):** RSS news items contain banking-relevant text. The "obvious" optimisation would be to embed them and add them to `document_chunks` so RAG can find them. That breaks the "answers cite RBI circulars only" guarantee.
**Root cause/risk:** Loose framing of "anything regulation-relevant goes in the RAG store" would corrupt the cite-worthy corpus with un-vetted news content.
**Fix:** News lives in `news_items`, surfaced only in `/updates`. The embeddings used to LINK news to circulars (`news_relevance.py`) are computed on the fly and discarded — they never persist into `document_chunks`. Documented as Rule 12 in `CLAUDE.md`.
**Prevention:** Treat `document_chunks` as sacred. Anything that ends up there can be cited by the LLM as authoritative. If a future ingest source isn't RBI, it goes in its own table.

### L3.12 — KG-driven RAG expansion must default OFF
**What bit us (could have):** The KG expansion path in `rag_service._kg_expand` adds chunks from graph-neighbour circulars with a small RRF boost. Enabling this silently changes retrieval precision and recall in production. Without the Confidence Meter UI (Sprint 4), users have no way to see when an answer drew on expanded context.
**Root cause/risk:** "Built and merged" easily becomes "rolled out" if the rollout gate isn't explicit.
**Fix:** `RAG_KG_EXPANSION_ENABLED` defaults to `false` in both `app/config.py` and `.env.example`. The check is at the top of `_kg_expand`; the function is a no-op when the flag is off.
**Prevention:** Any new optional retrieval / scoring tweak ships as `_ENABLED=false`. Operators flip it deliberately AFTER (a) the golden dataset eval still passes with the flag on, and (b) the UI surfaces the new signal.

### L3.13 — OG image URL must point at the backend host, not the frontend
**What bit us:** First implementation generated `og_image_url = f"{FRONTEND_URL}/api/v1/snippets/{slug}/og"`, which was wrong on two counts: (a) LinkedIn/X fetch the OG image from whatever URL we emit, and the frontend doesn't proxy `/api/v1/*` to the backend; (b) in production these are different domains entirely.
**Root cause:** Conflating "where the user lands" (`FRONTEND_URL`) with "where the public API lives" (`BACKEND_PUBLIC_URL`).
**Fix:** Added `BACKEND_PUBLIC_URL` config. `_og_image_url` uses it (falls back to `localhost:8000` for demo).
**Prevention:** Any URL that a third-party crawler must fetch directly should be built from `BACKEND_PUBLIC_URL`, not `FRONTEND_URL`. Webhooks and OG images are the obvious cases; auth callbacks are another.

---

## Sprint 4 — Premium UI Polish, Confidence Meter, Dark Mode

### L4.1 — `confidence_score` was computed but never persisted, so the meter couldn't survive a refresh
**What bit us:** Sprint 2 added confidence scoring + consult_expert fallback in `llm_service.py`, but the values were only ever passed to the SSE `citations` event. The router that saves the question to the DB silently dropped both fields, and the `Question` ORM had no columns for them. Sprint 4's first attempt to render a meter on `/history/[id]` showed nothing because every persisted question had `confidence_score = undefined`.
**Root cause:** Sprint 2 changed the LLM contract but only the live answer path consumed it. The persistence path was never updated, and there was no test that round-tripped a question through `POST /questions` → `GET /questions/{id}` and asserted the new fields.
**Fix:** Migration `003_sprint4_confidence.sql` adds `confidence_score REAL` + `consult_expert BOOLEAN NOT NULL DEFAULT FALSE`. ORM, Pydantic schema, and both router paths (JSON + SSE) now wire the fields end-to-end. The frontend treats `confidence_score === null` as "no signal" and renders nothing rather than fake a value for pre-Sprint-4 questions.
**Prevention:** Whenever a service returns a new field, audit *both* the live consumer (the SSE event in this case) AND the persistence layer (ORM column + INSERT + cache payload) in the same commit. Add a contract test that posts a question and re-reads it to assert the round trip.

### L4.2 — Class-based Tailwind dark mode needs a pre-hydration script or every page flashes light
**What bit us:** First dark-mode pass set the `dark` class via the React `useEffect` in `ThemeBootstrap`. Result: every page load painted light, then flipped to dark a few hundred ms later — a visible white flash for any user whose OS preference is dark.
**Root cause:** Next.js renders the HTML on the server with no `dark` class, the browser paints that, *then* React hydrates and `useEffect` runs. The script timing is fundamentally wrong for a body-class theme switch.
**Fix:** Inline `<script dangerouslySetInnerHTML>` in the root layout `<head>` reads `localStorage` + `prefers-color-scheme` and toggles `document.documentElement.classList.add('dark')` BEFORE React hydrates. The `ThemeBootstrap` React component is still mounted to take over for runtime switching, but the first-paint correctness comes from the inline script.
**Prevention:** Any class-based theme strategy (`darkMode: "class"` in Tailwind, or equivalent) requires a synchronous pre-hydration script. SSR + `useEffect` is always too late. The script must live in `<head>` so it runs before the body paints.

### L4.3 — `useState`/`localStorage`-derived store causes hydration mismatch on the toggle
**What bit us:** The first `ThemeToggle` component read `useThemeStore((s) => s.theme)` and rendered "Light" or "Dark" directly. On dark-OS users this caused a hydration mismatch: server rendered "Light" (because `localStorage` doesn't exist server-side and the store's `initial.theme` defaults to `"light"`), client immediately rendered "Dark", and React threw the warning.
**Root cause:** Any component that depends on browser-only state (localStorage, matchMedia, window dimensions) cannot render that state on the first hydration without a mismatch.
**Fix:** `ThemeToggle` keeps a `mounted` state that flips on `useEffect` and renders a same-size placeholder until then. The actual toggle markup only appears post-mount.
**Prevention:** For any UI that mirrors persisted/system state, adopt the "render placeholder until mounted" pattern. The placeholder must occupy the same physical space so the layout doesn't shift when it swaps in.

### L4.4 — SSE token rendering jitter comes from per-token React re-renders, not from the network
**What bit us:** During Anthropic's streaming response, every 1–3 character delta caused `setState((prev) => ({...prev, answer: prev.answer + token}))`. React re-rendered the entire `/ask` page on every event — visible jitter, especially when ReactMarkdown re-parsed mid-stream.
**Root cause:** The naive "append on every event" pattern. Network arrival is not the right cadence for UI updates; the display refresh rate is.
**Fix:** Tokens accumulate in a `useRef` buffer; a `requestAnimationFrame`-scheduled `flushTokens` drains the buffer into state at most once per frame. The buffer is also flushed before swapping in the citations metadata so the citations panel never appears ahead of its prose.
**Prevention:** Never feed network events directly into React state at the network's rate. Buffer to a ref and flush on a steady cadence (rAF for visual smoothness, setTimeout for non-critical updates). Especially important for SSE/WebSocket streams where event frequency can be hundreds per second.

### L4.5 — Stable layout containers prevent the citations panel from "punching" the prose down
**What bit us:** Once the buffered token rendering was smooth, the next jank source was the citations event arriving mid-stream — the page suddenly grew a confidence meter + Quick Answer card *above* the in-flight prose, shoving the user's reading position downward.
**Root cause:** The conditional render `{state.confidenceScore !== null && <ConfidenceMeter ... />}` had no reserved space, so the prose layout shifted the moment the metadata arrived.
**Fix:** Wrap the conditional in a `<div className="min-h-[1px]">` that always exists during streaming. The meter snaps in without growing the parent container until its actual height is needed, and even then the visual displacement is at the top of the answer (above the prose) where it doesn't disrupt the active reading region.
**Prevention:** Any element that appears mid-stream needs a stable container. Either reserve space with min-height, or place the new element below the in-flight content rather than above it. Layout shift is always perceptible — design for it.

### L4.6 — Sprint 1 fixed `posthog-js/react` hooks but `onFeatureFlags` returns shape varies between minor versions
**What bit us:** The first `useFeatureFlag` hook called `posthog.onFeatureFlags(handler)` and stored the returned value as `unsub`. Some versions of `posthog-js` return a function (the unsubscribe), others return undefined. Calling `unsub()` unconditionally would crash on the older shape.
**Root cause:** The library's API contract for `onFeatureFlags` is inconsistent across minor versions, and we can't pin both posthog-js *and* posthog-js/react to a known-good combination without auditing every other consumer.
**Fix:** `if (typeof unsub === "function") unsub();` — defensive cleanup that tolerates either shape.
**Prevention:** When subscribing to any third-party event hook, validate the return type before invoking it as a cleanup. Library minor versions silently change these contracts; defensive type checks are cheaper than version pins.

### L4.7 — `docker cp` after schema changes still requires the migration to be applied separately
**What bit us:** First post-Sprint-4 backend restart after `docker cp`'ing the new ORM threw `column "confidence_score" of relation "questions" does not exist` on the very first answer write. The ORM expected the column; the running database didn't have it.
**Root cause:** L3.3 documented the `docker cp` workflow for code changes. It does NOT auto-apply migrations — those still need an explicit `psql < migration.sql`.
**Fix:** `docker exec -i regpulse-postgres psql -U regpulse -d regpulse < backend/migrations/003_sprint4_confidence.sql` *before* restarting the backend.
**Prevention:** Sprint exit checklist now includes "applied any new SQL migrations against the running demo DB" as a pre-restart step. Code-only `docker cp` is fine for service code; schema changes need a database write.

### L4.8 — `docker compose up -d backend` recreates the container and wipes every `docker cp`'d file
**What bit us:** During the post-Sprint-4 KG-flag verification, I needed the backend to reload `.env` to pick up `RAG_KG_EXPANSION_ENABLED=true`. I ran `docker compose up -d backend` (not `docker restart`), which **recreated** the container from the baked-in image. The image was multiple sprints stale — no Sprint 3 KG settings, no Sprint 4 confidence columns, no `tests/evals/` directory. Every code edit I'd applied via `docker cp` over the previous sprints was gone.
**Root cause:** Two compose verbs that look similar do very different things. `docker restart` keeps the container's filesystem (so `docker cp`'d edits survive). `docker compose up -d` (without `--no-recreate`) destroys and recreates if anything in the service definition changed — and reloading `.env` counts as a change.
**Fix:** After the recreate, I had to `docker cp` the *entire* `backend/app/` and `backend/tests/` trees back into the new container, then `docker restart`. Or — the better fix — `docker compose build backend && docker compose up -d --force-recreate backend` so the image ITSELF reflects the source.
**Prevention:** Two rules. (1) For env-var changes, `docker compose up -d backend` is correct, but you MUST also rebuild the image first if you've been hot-patching with `docker cp`. (2) At sprint close, run `docker compose build backend scraper && docker compose up -d --force-recreate backend scraper` so the running containers match the committed source. Treat `docker cp` as a strictly-temporary mid-iteration shortcut, not a deployment mechanism.

### L4.9 — `anthropic==0.42.0` silently rejects the `thinking={"type": "enabled"}` kwarg, masking the real Anthropic call
**What bit us:** First end-to-end smoke test after the Sprint 4 fix returned `INTERNAL_ERROR`. The logs showed `TypeError: AsyncMessages.create() got an unexpected keyword argument 'thinking'` from the primary path, then fell through to the OpenAI fallback (which then failed for an unrelated reason — see L4.10). Sprint 1 had wired extended thinking into `llm_service._call_anthropic` but the SDK pinned in `requirements.txt` predated the parameter.
**Root cause:** The `thinking={"type": "enabled", "budget_tokens": ...}` kwarg landed in the Anthropic Python SDK around v0.49. We pinned `anthropic==0.42.0` in `backend/requirements.txt` and never bumped it when Sprint 1 added the kwarg. The TypeError was caught by the broad `except Exception` in `LLMService.generate`, which logged at `warning` level and quietly fell through to the fallback path. Result: no Anthropic call succeeded, ever, on this image — but the error never surfaced because the fallback masked it.
**Fix:** Bumped to `anthropic==0.49.0` in `requirements.txt`, rebuilt the backend image (`docker compose build backend`), recreated the container, and verified `anthropic.__version__ == "0.49.0"` inside the container. End-to-end smoke test then returned `model_used: "claude-sonnet-4-20250514"` on the primary path with no fallback.
**Prevention:** Whenever you add a new kwarg or parameter to a third-party SDK call, audit `requirements.txt` to ensure the pinned version supports it. Better still: have the test suite cover the *exact* code path that uses the new kwarg, so a bump that breaks it surfaces in CI rather than at the demo. Consider tightening the `except Exception` in `LLMService.generate` to log Anthropic-side `TypeError`s at `error` level (they signal a developer bug, not an API failure) so they're not silently absorbed by the fallback path.

### L4.10 — `LLM_FALLBACK_MODEL` was set to a Claude model name in `.env`, so the OpenAI fallback path called OpenAI with an Anthropic model id
**What bit us:** When the L4.9 Anthropic failure cascaded into the fallback path, OpenAI returned `404 The model 'claude-sonnet-4-20250514' does not exist`. The user's `.env` had `LLM_FALLBACK_MODEL=claude-sonnet-4-20250514` (probably copied from `LLM_MODEL` during an earlier debugging session), and `_call_openai` reads `self._settings.LLM_FALLBACK_MODEL` and hands it straight to `openai.chat.completions.create(model=...)`.
**Root cause:** Two failure modes layered. (a) The `.env` was misconfigured — `LLM_FALLBACK_MODEL` is consumed by an OpenAI client and must be an OpenAI model id, but nothing in the codebase enforced that invariant. (b) Because the fallback path was never actually exercised in healthy operation (Anthropic always succeeded in earlier sprints), the bug sat dormant until L4.9 surfaced it.
**Fix:** Added a validator in `Settings.model_post_init` that hard-fails at startup if `LLM_FALLBACK_MODEL.startswith("claude-")`, with a clear message naming the variable and pointing at `.env`. Updated `.env.example` to spell out which client each LLM_* model id is consumed by. Fixed the local `.env` to `LLM_FALLBACK_MODEL=gpt-4o`.
**Prevention:** Any config var that's coupled to a specific provider (model ids, API key prefixes, region codes) deserves a startup-time validator that catches misconfiguration loudly. The cost is a five-line check at config load; the alternative is a 500 in production the first time the feature actually runs. This pattern is now in `app/config.py` `model_post_init` for the LLM model ids — extend it whenever you add another provider-coupled var.

### L4.11 — The golden eval mocks the LLM, so it can NOT verify retrieval-side changes like `RAG_KG_EXPANSION_ENABLED`
**What bit us:** I confidently re-ran the golden eval after flipping `RAG_KG_EXPANSION_ENABLED=true` and reported "28/28 PASS, no regression." Then I read the eval source: it constructs synthetic chunks directly and feeds them to `LLMService.generate()` with a mocked Anthropic client. It never calls `RAGService.retrieve()`, which means it never executes `_kg_expand`. The 28/28 result was true but irrelevant — it proves nothing about whether KG expansion works in production.
**Root cause:** "The eval" was scoped to LLM safety logic (citation validation, confidence scoring, injection guard, consult-expert fallback). Sprint 3 added a retrieval-side feature (KG expansion) but did not extend the eval to cover it. So we have a gap: any change inside `rag_service.py` is unverified by the eval suite, no matter how loudly we re-run it.
**Fix (this run):** I supplemented the eval with a live end-to-end smoke test against `POST /api/v1/questions` using a real demo user, real retrieval, real KG expansion, and a real Anthropic call. That confirmed the path executes and returns a sane answer.
**Prevention:** Add a retrieval-aware integration eval that hits a small fixture DB (or the demo postgres) and asserts (a) `_kg_expand` runs without error when the flag is on, (b) the resulting chunk set is a *superset* of the un-expanded set, and (c) confidence/citation behaviour is unchanged for the existing 28 cases. Until that integration eval exists, the sprint exit checklist must include a manual end-to-end smoke against `/api/v1/questions` whenever a sprint touches retrieval. "Re-run the eval" is necessary but not sufficient.

### L4.12 — `pytest` is not installed in the runtime backend image
**What bit us:** Trying to run `python tests/evals/test_hallucination.py` inside the freshly recreated backend container immediately failed with `ModuleNotFoundError: No module named 'pytest'`. Even though the eval can be invoked as a plain script, it still imports `pytest` at module load time for its fixtures.
**Root cause:** `requirements.txt` is the runtime image's only dependency source, and pytest is (correctly) a dev-only dep that isn't pinned there. The previous container had `pytest` installed from a prior `pip install --quiet pytest` invocation that survived restarts but not recreates.
**Fix (workaround):** `docker exec regpulse-backend pip install --quiet pytest` before each eval run on a freshly recreated container. Acceptable for the demo but fragile.
**Prevention:** Either (a) split into `requirements.txt` (runtime) + `requirements-dev.txt` (adds pytest, ruff, black) and bake the dev deps into a `regpulse-backend:dev` image used for evals; or (b) refactor `test_hallucination.py` to not import `pytest` at module level so the standalone-script invocation Just Works. Option (a) is the cleaner CI story; option (b) is the cheaper one-line fix.

### L4.13 — A broad `except Exception` around an LLM call hides developer bugs by collapsing them into "API failure"
**What bit us:** L4.9 (the SDK kwarg `TypeError`) is a *Python type error* — a developer bug, not an external service failure. But it landed inside the same `except Exception` block in `LLMService.generate` that's meant to catch real Anthropic outages, so the system logged it at `warning` level and tried to recover via the fallback. The fallback then failed for L4.10's reason. The user-visible result was a generic 500, and the diagnosis took multiple log dives.
**Root cause:** Treating `Exception` as the unit of failure handling. `TypeError`, `AttributeError`, and `ImportError` are categorically different from `httpx.ConnectError` or `anthropic.APIStatusError`. Catching them all the same way means real API outages and developer typos look identical at the operations layer.
**Fix:** Not yet applied — flagging as TD-10. The right shape is `except (anthropic.APIError, anthropic.APIConnectionError, anthropic.APIStatusError) as e:` for the fallback trigger, and let `TypeError`/`AttributeError` propagate so they crash loudly during dev/CI. In production they'd 500 with a request id, which is also fine — they're bugs.
**Prevention:** Audit every `except Exception` around external service calls and tighten to the smallest exception family that represents "the external service is unhealthy." Programmer errors should NEVER be in the same catch — they should crash the request and surface a Sentry alert.

---

## Sprint 5 — Admin PDF Upload, Semantic Clustering Heatmaps

### L5.1 — Backend Redis client uses `decode_responses=True`, which breaks raw byte storage
**What bit us:** The upload endpoint needed to store raw PDF bytes in Redis for the scraper Celery task to read. The shared `cache.py` Redis client has `decode_responses=True`, which mangles binary data.
**Root cause:** The cache client was designed for string-based caching (JSON, text). Raw file bytes are a different use case.
**Fix:** Created a separate bytes-mode Redis connection in the upload router (`decode_responses=False`) specifically for PDF byte storage. Used a `upload_pdf:{uuid}` key prefix with 5-minute TTL.
**Prevention:** When adding a new Redis use case that involves binary data, never reuse a `decode_responses=True` client. Create a purpose-specific connection.

### L5.2 — `/app/__init__.py` in the backend container breaks pytest module discovery
**What bit us:** Running `pytest` inside the container failed with `ModuleNotFoundError: No module named 'app.cache'`. The `__init__.py` at `/app/` makes Python treat `/app` as a package, so `from app.cache import ...` requires the *parent* of `/app` to be in `sys.path` — but pytest doesn't set that up.
**Root cause:** The Dockerfile's WORKDIR is `/app`, and there's an `__init__.py` at that level. `uvicorn app.main:app` works because uvicorn adds CWD to `sys.path`, but pytest doesn't.
**Fix (workaround):** Temporarily rename `/app/__init__.py` before running pytest: `mv /app/__init__.py /app/__init__.py.bak`. Install `pytest-asyncio` and `aiosqlite` for async test support. Restore after.
**Prevention:** TD-12 (split `requirements-dev.txt` and bake a dev image) remains the right fix. Additionally, consider removing the root `/app/__init__.py` if it's not needed — uvicorn doesn't require it.

### L5.3 — Docker BuildKit cache corruption causes persistent `COPY` failures
**What bit us:** Frontend Docker builds failed repeatedly with `cannot copy to non-directory: .../node_modules/@eslint/eslintrc` even after `docker builder prune -f` and `docker buildx prune -af`.
**Root cause:** BuildKit's overlay filesystem cache got corrupted (stale symlink or directory/file type mismatch in the `node_modules` cache mount). This is a known Docker Desktop issue.
**Fix:** Fell back to the legacy builder via `DOCKER_BUILDKIT=0 docker compose build --no-cache frontend`. The legacy builder doesn't use cache mounts and completed cleanly.
**Prevention:** If BuildKit COPY fails after cache prune, try `DOCKER_BUILDKIT=0` before investigating further. Consider adding `DOCKER_BUILDKIT=0` as a comment in `docker-compose.yml` for future reference.

### L5.4 — CI ruff config was missing per-file-ignores, so 21 pre-existing errors failed every push
**What bit us:** Sprint 5 push triggered backend-lint CI failure. Investigation revealed 21 ruff errors — all pre-existing (T201 print in scripts, S608 dynamic SQL in kg_service, E501 line-length, B905 zip). The `pyproject.toml` had `select = ["T20", "S", ...]` enabled but no per-file-ignores for scripts and evals that legitimately use `print()`.
**Root cause:** The ruff config was written aspirationally — it enabled strict rules but never tested against the full codebase. Previous pushes likely also failed CI lint, but nobody noticed because backend-test and frontend-build were the focus.
**Fix:** Added `per-file-ignores` in `pyproject.toml` for scripts (`T201`), evals (`T201`), and `kg_service.py` (`S608`). Fixed the 3 code-level issues (E501, B905). `ruff check backend/` now passes with 0 errors.
**Prevention:** After adding or changing ruff rules, always run `ruff check backend/` locally before pushing. Consider adding it to a pre-commit hook.

### L5.5 — `ruff check --fix` modifies files silently — must stage ALL changed files, not just the ones you intended
**What bit us:** Ran `ruff check --fix backend/` to auto-fix lint errors. It fixed files in `snippet_service.py` (UP017: `timezone.utc` → `UTC`) alongside the files I was targeting. I staged only the 4 files I knew about and committed. `snippet_service.py` stayed as an unstaged local change. CI then failed on the very fix I thought I'd already applied.
**Root cause:** `--fix` modifies files in-place across the entire target directory. If you cherry-pick which files to stage, you'll miss silently-fixed files. This cost 3 extra CI-fix commits.
**Fix:** Committed the missed file.
**Prevention:** After `ruff check --fix`, always run `git diff --name-only` to see ALL modified files before staging. Or use `git add -u` for lint-fix commits to catch everything. Better yet: run `ruff check` (without `--fix`) first to see the list, fix manually or with `--fix`, then verify with `git status`.

---

## Cross-Sprint Patterns

### LX.1 — Memory drift between point-in-time notes and live state
**What bit us:** Started a session believing the demo was "awaiting feedback before next dev cycle" (per a 15-day-old memory entry). Reality: Sprint 1 had landed earlier the same day and Sprint 2 was already partly committed. Built a working theory off stale data.
**Fix:** Always run `git log --oneline -10` and `git status` at the start of any session before consulting memory. Treat memory as a starting hypothesis, not ground truth.
**Prevention:** Codified in the memory system rules — "Before recommending from memory, verify against current code." Already documented; this entry is a reminder that the rule is load-bearing.

### LX.2 — Stub fixtures and "future prompt" placeholders accumulate silently
**What bit us:** L1.7 (embedder stub) is the headline example. Other examples: `process_document` Step 6 INSERT discards `_embeddings` (TD-08, found during Sprint 3 backfill); `admin_audit_log.actor_id NOT NULL` blocks scraper writes (TD-04, still open).
**Root cause:** "Done for now, will fix in the next prompt" without a tracking artifact.
**Fix:** Tracked as TD-NN entries in `MEMORY.md` Technical Debt table.
**Prevention:** Every stub or placeholder gets a TD-NN entry with a one-line plan AT THE TIME OF COMMIT. No exceptions.

### LX.3 — Container parity vs dev iteration is a real tradeoff
**What bit us:** L3.3 (no bind mount) and L3.4 (stale baked-in code) both stem from prioritising prod parity in `docker-compose.yml`. The cost is friction every time we touch backend or scraper code mid-session.
**Root cause:** `docker-compose.yml` is doing double duty as a prod-like config and a dev environment.
**Fix:** None yet — just documenting the friction.
**Prevention:** Future work — split into `docker-compose.yml` (prod-parity baseline) and `docker-compose.dev.yml` (overlay with bind mounts and `--reload`). Until then, plan sprint work assuming you'll need `docker cp` + restart for every backend/scraper edit.

### LX.4 — Document changes invalidate the test count in the docs
**What bit us:** Spec said "30 anti-hallucination test cases" but the actual dataset has 28. Both numbers lived in `CLAUDE.md`, `MEMORY.md`, and `spec.md`. None matched the truth.
**Root cause:** Counts duplicated across multiple docs without a single source.
**Fix:** Treat `golden_dataset.json`'s `test_cases` length as the authoritative count. Don't repeat the number in prose.
**Prevention:** Any number that comes from data (test counts, table counts, route counts) should appear in at most one doc, and ideally be derivable from the data itself. When you can't avoid duplicating it, audit all copies in the same commit.

---

## Sprint 6 — Pre-Launch Hardening

### L6.1 — Broad `except Exception` hides programming bugs in LLM code
**What bit us:** TD-10 analysis revealed 4 `except Exception` blocks in `llm_service.py`. A `TypeError` from a wrong kwarg would silently fall through to the OpenAI fallback path (or be swallowed entirely on the streaming parse path), making bugs look like transient API failures.
**Root cause:** Initial implementation prioritised "never crash" over debuggability. API errors and programming errors require different handling.
**Fix:** Replaced with typed exception tuples: `(anthropic.APIError, anthropic.APIConnectionError, anthropic.APITimeoutError)` for the API paths, `(json.JSONDecodeError, KeyError, TypeError, ValueError)` for the parse path.
**Prevention:** Never catch bare `Exception` in API wrapper code. Use the SDK's own exception hierarchy. Let `TypeError`/`AttributeError` propagate.

### L6.2 — Docker migrations must be mounted explicitly
**What bit us:** Only `001_initial_schema.sql` was mounted into the postgres `docker-entrypoint-initdb.d/`. Migrations 002–005 existed on disk but never ran on fresh `docker compose up -v`.
**Root cause:** Each new migration was added to the file system but the `docker-compose.yml` volume mount list was never updated.
**Fix:** Added all 5 migration files as explicit read-only volume mounts in docker-compose.yml.
**Prevention:** Any new migration SQL file must have a corresponding volume mount added in the same commit.

### L6.3 — Retrieval evals need real embeddings; mocks are worthless for recall
**What bit us:** TD-11 — the existing `test_hallucination.py` eval never called `RAGService.retrieve()`. It mocked chunks, so it tested LLM output quality but not whether the retrieval pipeline actually finds the right chunks.
**Root cause:** Unit-test mindset applied to an integration-level concern. Retrieval recall depends on embedding quality, pgvector index, and RRF fusion — none of which are exercisable under mocks.
**Fix:** New `test_retrieval.py` seeds golden dataset circulars with real OpenAI embeddings into the compose Postgres, then calls `retrieve()` and asserts the correct circulars appear in top-K.
**Prevention:** Any retrieval or ranking change must be validated against the retrieval eval, not just the hallucination eval. The hallucination eval tests the LLM; the retrieval eval tests the pipeline.

---

## GCP Deployment — Phase 2 (2026-05-14)

### LGCP.1 — Multi-line `gcloud` commands get mangled when pasted into macOS zsh
**What bit us:** Phase 2A reserved the private-services IP range successfully but the follow-up `vpc-peerings connect` (second command in the same paste) silently never executed. Result: Cloud SQL creation later failed with `NETWORK_NOT_PEERED` because the address range was `RESERVED` but no peering connection existed. Took two failed SQL attempts to diagnose.
**Root cause:** When you paste a multi-line shell command (with `\` line continuations) into Terminal/iTerm with zsh, the paste buffer can drop the trailing `\` or split the command at newlines. Each fragment runs as its own command, and gcloud only sees the first line's arguments.
**Fix:** Write all multi-step provisioning commands to a shell script in `scripts/gcp/` and have the user run `bash scripts/gcp/<script>.sh`. Single-line `gcloud` commands also work but become unreadably long for >5 flags.
**Prevention:** Never document a multi-line `gcloud` command for the user to paste. Either (a) single-line, or (b) script file. The runbook (`GCP_DEPLOY_RUNBOOK.md`) now references scripts rather than inline command blocks for all multi-line gcloud.

### LGCP.2 — `set -u` + `$NNN` in echo strings = unbound variable error
**What bit us:** `phase2_resume.sh` had `echo "==> 2E. Budget alert ($300/mo, ...)"`. With `set -u` (nounset), bash parsed `$300` as `${3}00` — i.e. positional arg 3, which is unset — and aborted the script just before the budget creation. Redis had already dispatched but the budget alert never ran.
**Root cause:** `set -u` is correct discipline (catches typos in variable names), but it makes dollar signs in literal strings dangerous. Bash's `$NNN` form is positional-arg expansion, not "the number $300".
**Fix:** Use single quotes for literals: `echo '==> 2E. Budget alert ($300/mo...)'`. Or escape: `\$300`.
**Prevention:** When writing any bash script with `set -u`, audit `echo` statements for unescaped `$` followed by digits. CI lint with `shellcheck` would catch this — worth adding when we have more scripts.

### LGCP.3 — Cloud SQL on new projects defaults to Enterprise Plus edition
**What bit us:** First Cloud SQL create attempt returned `Invalid Tier (db-custom-2-4096) for (ENTERPRISE_PLUS) Edition`. The project's Cloud SQL default is now Enterprise Plus (introduced 2023), which only accepts predefined `db-perf-optimized-N-*` tiers, not custom machine types.
**Root cause:** Cloud SQL Enterprise Plus is the new premium tier (~3-4x cost). New projects/instances may default to it depending on org policy or project age. `PRODUCTION_PLAN.md` specifies `db-custom-2-4096` which is an Enterprise-edition tier.
**Fix:** Add `--edition=ENTERPRISE` explicitly to the SQL instance create command. Baked into `phase2_resume.sh` and `phase2_retry_sql.sh`.
**Prevention:** Always specify `--edition` explicitly on `gcloud sql instances create` — never rely on the project default. Cost difference between editions is significant ($75/mo vs $300+/mo for the same workload).

### LGCP.5 — Cloud SQL Postgres 16 ships pgvector that caps both ivfflat AND hnsw at 2000 dimensions
**What bit us:** Migration 001 has `CREATE INDEX ... USING ivfflat (embedding vector_cosine_ops)` on `document_chunks.embedding` which is `vector(3072)` (text-embedding-3-large dimensions). Cloud SQL rejected with `column cannot have more than 2000 dimensions for ivfflat index`. Swapped to hnsw — same 2000-dim limit error. Migration partially applied; subsequent migrations chained on partial state. Had to drop the `regpulse` database, comment out the two ANN indexes, and re-run.
**Root cause:** pgvector lifted the 2000-dim limit on hnsw in v0.7.0 (May 2024). Cloud SQL Postgres 16 (as of this deploy, May 2026) still ships an older pgvector that has the cap. Local Docker uses `pgvector/pgvector:pg16` which has a newer pgvector — that's why local works.
**Fix:** Commented out both ANN indexes in `001_initial_schema.sql`. Vector similarity queries now sequential-scan, which is acceptable for the R&D corpus size. Three forward paths when scale matters: (a) wait for Cloud SQL pgvector upgrade; (b) migrate column to `halfvec(3072)` (ivfflat allows 4000-dim on halfvec); (c) reduce embeddings to 1536-dim via text-embedding-3-small (quality regression).
**Prevention:** Before deploying schemas that depend on Postgres extension features, check the target host's extension version with `SELECT extversion FROM pg_extension WHERE extname='vector';`. Cloud-managed Postgres lags upstream by 6-18 months on extension versions.

### LGCP.6 — Cloud SQL Auth Proxy can't connect to private-IP-only instances from outside the VPC
**What bit us:** Created `regpulse-db` with `--no-assign-ip` (private IP only — best practice for fintech). Tried to run migrations from laptop via Cloud SQL Auth Proxy. Proxy authenticated successfully but every connection attempt failed: `instance does not have IP of type "PUBLIC"`. The proxy from outside the VPC needs the instance to have a public endpoint, even though it then uses IAM auth (not network auth) to connect.
**Root cause:** The Cloud SQL Auth Proxy v2 connects via the instance's public IP through Google's edge, with IAM-based TLS at the transport layer. With `--no-assign-ip`, there's no public endpoint to connect to. `--private-ip` flag on the proxy doesn't help — it only changes which IP the proxy returns; the connection still needs network reachability, and a laptop isn't in the VPC.
**Fix:** `gcloud sql instances patch regpulse-db --assign-ip` to add a public endpoint while keeping the private IP. Cloud Run still uses the private IP via VPC Connector. Public IP is safe because Cloud SQL Auth Proxy enforces IAM-based auth — no IP allowlist needed for security.
**Prevention:** Either (a) provision Cloud SQL with public IP from the start (and accept the IAM-auth-only security model), or (b) plan migrations as Cloud Run Jobs that run from inside the VPC. For R&D, (a) is the pragmatic default — public IP + IAM auth is not the same as "publicly accessible Postgres." Document the public IP as "admin path, IAM-gated" in the runbook.

### LGCP.4 — `--labels` is not in the `gcloud sql` GA track
**What bit us:** First SQL create attempt failed with `unrecognized arguments: --labels=...` even though `--labels` is documented on `gcloud sql instances create`.
**Root cause:** The flag is only exposed on the `gcloud beta sql instances create` command, not GA. Other resource types (Redis, Compute) have `--labels` in GA. Inconsistent surface.
**Fix:** Use `gcloud beta sql instances create` for all Cloud SQL provisioning. Beta in gcloud is well-supported, not experimental — the resource created is identical to GA.
**Prevention:** When adding labels (now standard governance on every resource), reach for `gcloud beta` for SQL specifically; GA is fine for everything else.

---

## Process Learnings

### LP.1 — `git push` is not implicit
**What bit us:** Sprint 3 landed locally on `main` with 5 commits. I called the sprint "complete" before pushing. The user had to ask explicitly.
**Fix:** Always confirm push status when wrapping a sprint.
**Prevention:** Per the standing rule, I won't push without authorization, but I should always SURFACE the local-vs-remote gap at sprint completion so the user knows it's the next step.

### LP.2 — "Verified manually" isn't the same as "tests pass"
**What bit us:** I called Pillar C complete after verifying the snippet flow end-to-end with curl, but I never re-ran the existing 28 anti-hallucination tests against the post-Sprint-3 backend. The user asked "all evals tested?" and I had to answer no.
**Fix:** A sprint that touches `rag_service.py`, `llm_service.py`, or any retrieval/answer code MUST end with the golden dataset eval re-run.
**Prevention:** Add an "evals re-run" step to every sprint's exit checklist. Treat it as non-negotiable for any change to retrieval or answer logic.

### LP.3 — Frontend tests need installed deps; the CI environment isn't free
**What bit us:** First attempt to type-check the frontend failed because `frontend/node_modules` didn't exist locally. Had to install everything before I could verify a 5-line change.
**Fix:** Run `pnpm install` once at the start of any session that will touch the frontend.
**Prevention:** Frontend session warmup: `cd frontend && pnpm install` before any TypeScript edits. Shouldn't be necessary for backend-only work.

---

## Sprint 7 — DPDP Compliance, Auto-Renewal, Low-Credit Notifications

### L7.1 — ORM user object detached from test session causes silent no-op updates
**What bit us:** Account deletion test passed the `user` object via dependency override, but `user` was created in a different SQLAlchemy session than the request handler's `db`. Direct attribute mutation (`user.email = "..."`) followed by `db.commit()` silently did nothing because the object wasn't tracked by `db`.
**Root cause:** Test fixtures create users in their own session, but the FastAPI `Depends(get_db)` injects a different session. The user object is detached, so changes aren't flushed.
**Fix:** Use explicit `UPDATE` statements (via `sqlalchemy.update()`) instead of ORM attribute mutation when the entity may come from a different session — which is always the case in test environments and any endpoint where the auth dependency and the DB dependency use separate sessions.
**Prevention:** In routers that modify user state, prefer `UPDATE ... WHERE` over mutating the injected `user` object. This is more robust than relying on the user being attached to the same session. Also catches cases where the user was loaded with `expire_on_commit=False` in middleware.

### L7.2 — SQLite test engine needs type overrides for Vector, JSONB, and Enum columns
**What bit us:** The conftest only created `users` and `sessions` tables (marked as `_AUTH_TABLES`) with SQLite-compatible type overrides. The account router queries `questions`, `saved_interpretations`, and `action_items` which have `Vector(3072)`, `JSONB`, and `Enum` columns — all unsupported in SQLite.
**Root cause:** The original conftest was designed for auth-only tests and intentionally limited scope to avoid JSONB/pgvector compatibility issues.
**Fix:** Created a separate `account_engine` fixture that applies broader type overrides: UUID→String, Vector→String, JSONB→String, Enum→String, and removes `server_default` for `now()` and `'[]'::jsonb`. This fixture creates all 5 tables needed for account tests.
**Prevention:** When adding tests for new routers that touch multiple models, check whether the conftest's `_AUTH_TABLES` includes all required tables. If not, create a route-specific engine fixture with the necessary type overrides.

### L7.3 — `.env` file pollutes test environment via pydantic-settings auto-loading
**What bit us:** Running `pytest` from the project root caused `pydantic-settings` to auto-load `.env` which contained extra vars (`POSTGRES_USER`, `JIRA_*`) not in the `Settings` model. Since `Settings` uses `extra="forbid"` (the default), this caused `ValidationError` at import time.
**Root cause:** `model_config = {"env_file": ".env"}` in `Settings` means any `.env` in the working directory is loaded. The project `.env` has Docker Compose vars and Jira integration vars that aren't in the model.
**Fix:** Run tests from `/tmp` (or any directory without `.env`) so pydantic-settings doesn't find the file. CI already does this implicitly since it checks out a fresh repo without `.env`.
**Prevention:** When running tests locally, always use `cd /tmp && PYTHONPATH=backend pytest ...` or set up a dedicated test runner script that clears the `.env` path.

---

## Sprint 8 — UX Gaps, Admin Tooling, Real PDFs

### L8.1 — FastAPI route ordering: static paths must precede `/{id}` params
**What bit us:** `GET /action-items/stats` returned 422 because `GET /{item_id}` matched first and tried to parse `"stats"` as a UUID. Same hazard: `GET /questions/suggestions` vs `GET /questions/{id}`, and `GET /circulars/updates` vs `GET /circulars/{id}`.
**Root cause:** FastAPI matches routes in registration order. A catch-all path-param route declared before a static sibling captures it.
**Fix:** Register static-path routes BEFORE any `/{id}` route in the same prefix. Checked during implementation; none of Sprint 8's new routes collide.
**Prevention:** When adding an endpoint under an existing prefix, grep the router for `{[a-z_]+}` routes and ensure the new endpoint is registered above them. Add a short comment where the boundary lives: "-- all static /foo/* endpoints above here --".

### L8.2 — pgvector SQL is Postgres-only; SQLite tests must short-circuit
**What bit us:** `GET /questions/suggestions` uses `ORDER BY question_embedding <=> CAST(:vec AS vector)`. SQLite has no `vector` type; unit tests blew up on dialect parse.
**Root cause:** Most unit tests run against `sqlite+aiosqlite://`. pgvector operators and `CAST(... AS vector)` don't exist there.
**Fix:** Check `db.bind.dialect.name == 'postgresql'` at the top of the endpoint and return an empty list otherwise. Keeps the endpoint functional in production without breaking the SQLite-based test harness.
**Prevention:** Any new endpoint using pgvector SQL must include a dialect guard. If the endpoint is core (not optional UX), add a postgres-backed integration test instead of relying on SQLite unit tests.

### L8.3 — MagicMock `__aiter__` is called with `self`; bare async generators break
**What bit us:** `test_stream_parse_failure_emits_safe_fallback` failed with `TypeError: _aiter_events() takes 0 positional arguments but 1 was given` because the code set `mock_stream.__aiter__ = _aiter_events` where `_aiter_events` is a zero-arg async generator.
**Root cause:** Python's magic method protocol calls `__aiter__` with `self`. Assigning a bare function to `mock.__aiter__` means that function is invoked with the mock instance as the first positional arg.
**Fix:** Wrap in a lambda that absorbs the self arg: `mock_stream.__aiter__ = lambda _self: _aiter_events()`.
**Prevention:** When mocking async iterators, always wrap the generator with a one-arg lambda. This applies to `__iter__`, `__enter__`, `__exit__`, etc. too.

### L8.4 — reportlab `Paragraph` treats `& < >` as markup — always escape
**What bit us:** Citation quotes containing `&` characters made `reportlab.platypus.Paragraph` raise XML parse errors mid-PDF generation.
**Root cause:** `Paragraph` uses an XML-lite mini-parser (`<b>`, `<i>`, `<br/>`) so any unescaped ampersand or angle bracket in source text breaks it.
**Fix:** Added `pdf_export_service._escape()` that replaces `&`, `<`, `>` with their HTML entities. Every user-facing string passes through it before being wrapped in a `Paragraph`.
**Prevention:** Any time a string reaches `Paragraph(text, style)` it must have gone through `_escape()`. Keep the helper next to the PDF service so it's hard to miss.

### L8.5 — Pre-existing test failures block new PRs when CI runs the full suite
**What bit us:** The Sprint 7 handover flagged 6 pre-existing unit test failures as "low-impact" known issues. They were tolerated locally but the CI workflow (`ci.yml`) runs `pytest backend/tests/unit/` without filtering, so they failed `backend-test` on Sprint 8's PR.
**Root cause:** "Known failing tests" were never cleaned up; the handover's "CI green" claim was stale vs. what CI actually ran.
**Fix:** Fixed all 6 in the Sprint 8 PR (`65b6872`). Five were `test_circular_library_service` filter counts that needed +1 to account for the always-on `pending_admin_review = False` clause in `_build_filter_conditions`. One was the `__aiter__` mock fix in L8.3.
**Prevention:** Never ship a handover that says "CI green" if any test is red. Known failures create drag — either fix them immediately or mark them `@pytest.mark.skip(reason="...")` with a follow-up issue so CI stays honest.

### L8.6 — EmbeddingService's SHA256 Redis cache means double-embedding is cheap
**What bit us:** Worried that persisting `question_embedding` in the POST /questions handler would add a second OpenAI call on top of the one `RAGService.retrieve()` already made.
**Root cause / observation:** EmbeddingService caches each `generate_single(text)` call in Redis keyed by SHA256(text). The retrieval path and the persistence path both embed the same `question_text` — the second call hits the cache.
**Fix:** No mitigation needed. Just documented in `routers/questions.py::_maybe_embed_question()` so future readers don't "optimise" by plumbing the vector through `RAGService.retrieve()`'s return value.
**Prevention:** When reusing an embedding in the same request, just call `EmbeddingService.generate_single()` again. The cache handles it. Only plumb the vector through if EmbeddingService is bypassed (e.g. raw OpenAI call).

### L8.7 — Backfill scripts should be idempotent and shipped with the PR that needs them
**What bit us:** Sprint 8 started writing `question_embedding` on new rows, but every existing row has NULL — so `GET /questions/suggestions` returns empty for users who asked questions before the deploy.
**Fix:** Shipped `scripts/backfill_question_embeddings.py` in the same PR. Batches 50 rows at a time, skips rows where the column is already set (idempotent), reuses EmbeddingService so Redis caching helps on repeat runs.
**Prevention:** Whenever a schema column goes from "optionally populated" to "always populated", include a backfill script in the same PR and document it in the handover as an operational step. Don't leave the backfill as a follow-up ticket.

---

## Phase D — V2 Integration & Audit (May 2026)

### L9.1 — Automated agents are blocked by strict OTP validation even in DEMO_MODE
**What bit us:** The `browser_subagent` failed to navigate the app beyond the login screen. It correctly entered the fixed `123456` OTP, but the backend returned 400/422 errors or the session cookie wasn't correctly persisted in the agent's headless state.
**Root cause:** Auth gates designed for humans often have session-binding or state-tracking that automated agents fail to mimic perfectly, or the 10-min TTL/3-send-per-hour limit bit the agent during retries.
**Fix:** In `DEMO_MODE`, consider a `?bypass_auth=true` query param or a pre-seeded session cookie for automated audits.
**Prevention:** When building automated UX audits, always verify the "login" path first. If it's a known blocker, provide a bypass for non-production environments.

### L9.2 — Scraper reported success despite zero text extraction from PDFs
**What bit us:** `scraper_runs` showed hundreds of documents "processed", but `circular_documents` remained at 10 rows. Logs showed pervasive "Syntax Error" from poppler/pdftotext.
**Root cause:** The scraper caught the `pdftotext` error but logged it as a warning and moved to the next document without failing the task or the run. The "processed" count in `scraper_runs` was incrementing for every URL visited, not every document landed.
**Fix:** Tighten the `process_document` status logic to distinguish between `skipped` (non-PDF), `failed_extraction`, and `success`. Report these counts separately in `scraper_runs`.
**Prevention:** "Processed" is a vague metric. Always track `success`, `fail`, and `skip` as distinct counters in any pipeline task.

### L9.3 — Crawler dropping image-only links + Extractor crashing on HTML (SCR-1)
**What bit us:** The scraper missed all 76+ Notification PDFs but crashed on 800+ `.aspx` URLs with "Syntax Error: Illegal character".
**Root cause:** Two bugs combined. (1) The RBI Notification page wraps PDF downloads in image icons, which have empty `link_text`. The crawler's `if not link_text: continue` filter silently dropped every real PDF link. (2) The remaining collected URLs were HTML navigation pages, but `pdfplumber` was fed them without validation, causing underlying `poppler` crashes.
**Fix:** (1) In `rbi_crawler.py`, if a link ends with `.pdf` but has no text, use the filename as the fallback `link_text`. (2) In `pdf_extractor.py`, validate the `%PDF-` magic byte before passing content to `pdfplumber`, and reject gracefully via `ExtractionFailure`.
**Prevention:** Never filter purely on anchor text without checking the `href` extension. Never trust `Content-Type` or URLs — always validate magic bytes before passing untrusted files to binary parsers.

### L9.4 — RBI WAF blocks automated PDF downloads (OP-3)
**What bit us:** Even after fixing the crawler, ~373 valid `rbidocs.rbi.org.in` PDF links failed extraction.
**Root cause:** RBI's Web Application Firewall returned HTTP 200 but the body was a 244-byte HTML "Request Rejected" page (`<title>Request Rejected</title>`). Our extraction failed gracefully because of L9.3's magic byte validation, but the documents still couldn't be ingested.
**Fix:** OP-3 created to track. Needs User-Agent spoofing, slower crawl rates, or proxying to bypass the WAF.
**Prevention:** When scraping government or enterprise sites, always test the raw download path with typical scraper User-Agents. If WAF is present, design for it early.

### L9.5 — Admin-review gate silently hides scraper output from the demo
**What bit us:** SCR-1 fix landed 93 circulars + 1,208 embedded chunks in the production DB, but the public `/api/v1/circulars` endpoint returned `total: 0`. We initially mis-diagnosed this as a deploy or DB-pointing bug.
**Root cause:** `circular_documents.pending_admin_review` defaults to `TRUE` (`models/circular.py:63`). `circular_library_service._build_filter_conditions` always appends `pending_admin_review.is_(False)` to every list / search / detail / facet query — so unapproved rows are completely invisible to non-admin users (correct prod behavior; broken UX in DEMO_MODE where no admin will ever review them). RAG retrieval lives in a different service that does NOT apply this filter, so Q&A worked end-to-end against unapproved circulars — which made the gap easy to miss.
**Fix:** Gate `pending_admin_review` on `DEMO_MODE` in the scraper INSERT (`scraper/tasks.py:process_document`) and the AI-summary UPDATE (`generate_summary`). Existing rows were one-shot bulk-approved via `UPDATE circular_documents SET pending_admin_review = FALSE`. Shipped in `scraper:rc4`.
**Prevention:** Any code path that diverges read-from-write filtering between user surfaces (Library = filtered, RAG = unfiltered) is a UX trap. Either pick a single visibility predicate for the whole product or document the divergence prominently. When introducing a "needs admin approval" gate, also wire a DEMO_MODE bypass at the same time.

### L9.6 — Cross-site cookies + Next.js middleware are a fundamental mismatch on `*.run.app` (CORS-DEMO-1)
**What bit us:** After full backend + scraper fix, frontend login flow loops: register → verify-otp → dashboard → bounces back to `/login`. Even after fixing `SameSite=lax` → `SameSite=None; Secure` and a separate CORS preflight 400 from a stale `FRONTEND_URL` placeholder.
**Root cause:** The Public Suffix List treats `*.run.app` subdomains as separate sites. Backend sets the `refresh_token` cookie scoped to `regpulse-backend-…run.app`. Browser does send it to the backend on `withCredentials: true` fetches (good, that part works now). BUT the Next.js middleware runs on `regpulse-frontend-…run.app` — a different host. `request.cookies.get("refresh_token")` is always undefined from the frontend's perspective. Middleware redirects every protected route to `/login`.
**Fix (deferred):** Three options, choose one before resuming demo:
- (A) Next.js rewrites — proxy `/api/*` from frontend origin to backend (cleanest, ~10 min frontend rebuild)
- (B) No-op the middleware redirect, rely on client-side auth state (loses hard-refresh recovery, ~10 min frontend rebuild)
- (C) Phase 5 — custom domain. Map `regpulse.in` and `api.regpulse.in`, set cookie `Domain=.regpulse.in`. ~30–60 min including DNS + Google-managed SSL provisioning. **This is the only real fix.**
**Prevention:** Cookie-based auth across multiple Cloud Run services in `*.run.app` was always going to be brittle. Future projects: ship custom-domain wiring before considering an end-to-end demo "done," or design middleware to read a non-HttpOnly companion cookie set on the frontend origin at login time.

### L9.7 — FastAPI 0.115 strict-asserts 204 routes
**What bit us:** Deploy of `backend:rc3` (first deploy after Phase D.2 was merged) crashed at startup with `AssertionError` in `fastapi/routing.py:507`. Health check failed. Cloud Run kept the previous revision live (no outage, but no new code either).
**Root cause:** FastAPI 0.115.6 added `assert is_body_allowed_for_status_code(...)` in `APIRoute.__init__`. The Phase D.2 DELETE handler in `learnings.py` was declared `status_code=status.HTTP_204_NO_CONTENT` with return annotation `-> None` and no explicit `response_class`. FastAPI inferred a non-empty response model and tripped the new assertion. (Phase D.2 code had been merged days ago but never actually deployed — Cloud Run was still on a pre-D.2 image — so the bug latency was zero between "first deploy" and "discovered.")
**Fix:** `@router.delete("/{learning_id}", status_code=204, response_class=Response)` plus `return Response(status_code=204)`. Imported `Response` from `fastapi`. Shipped in `backend:rc4`.
**Prevention:** For any DELETE / no-body route under FastAPI ≥0.115, always declare `response_class=Response` explicitly. And: **if a feature is merged but not deployed, you don't know whether it works** — the staging deploy IS the test. Treat merged-but-undeployed code as untested.

### L9.8 — Deploy-script placeholders drift silently from live Cloud Run URLs
**What bit us:** After deploying `backend:rc3`, CORS preflight started returning HTTP 400 "Disallowed CORS origin." The frontend / backend URLs are issued by Cloud Run in two forms — project-number form (`regpulse-frontend-822716875639.asia-south1.run.app`) and hash form (`regpulse-frontend-yvigu4ssea-el.a.run.app`). The deploy script `phase4e_deploy_backend.sh` hard-coded the project-number form as `FRONTEND_URL_PLACEHOLDER`, with a `# updated after frontend deploys` comment that nobody acted on. Whatever earlier ad-hoc fix had set the right value on `backend:rc2` was wiped by my redeploy.
**Fix:** Hard-coded the hash-form URL in the script + did a `gcloud run services update --update-env-vars FRONTEND_URL=…` on the live service. Both work, but the next time the frontend is recreated (and gets a new hash) the script will drift again.
**Prevention:** Either (a) read FRONTEND_URL at deploy time via `gcloud run services describe regpulse-frontend --format='value(status.url)'`, or (b) move per-environment URLs to an `.env`-style override file under version control. Don't trust comments-to-self in shell scripts to stay in sync.
