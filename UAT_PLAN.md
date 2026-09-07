# RegPulse — Full UAT Plan

> **Scope:** End-to-end validation of all features built across 50 prompts + Sprints 1–7.
> **Environment:** `docker compose up --build -d` with `DEMO_MODE=true`.
> **Pre-requisite:** Seed demo data via `docker exec regpulse-backend python scripts/seed_demo.py`.
>
> Status key: **[ ]** = not tested, **[P]** = passed, **[F]** = failed, **[S]** = skipped (N/A in demo)

---

## 0. Environment Setup

| # | Check | Steps | Expected | Status |
|---|-------|-------|----------|--------|
| 0.1 | Docker services running | `docker compose ps` | 6 containers: postgres, redis, backend, scraper, celery-beat, frontend — all "Up" | [ ] |
| 0.2 | Backend health | `curl http://localhost:8000/api/v1/health` | `{"status": "healthy"}` | [ ] |
| 0.3 | Backend readiness | `curl http://localhost:8000/api/v1/health/ready` | `{"status": "ready"}` (DB + Redis OK) | [ ] |
| 0.4 | Frontend loads | Open `http://localhost:3000` | Landing page renders | [ ] |
| 0.5 | API docs | Open `http://localhost:8000/api/v1/docs` | Swagger UI with all endpoints | [ ] |
| 0.6 | Demo data seeded | Check library page has circulars | 5+ circulars visible in `/library` | [ ] |
| 0.7 | pgvector enabled | `docker exec regpulse-postgres psql -U regpulse -c "SELECT extname FROM pg_extension WHERE extname='vector'"` | Returns `vector` | [ ] |

---

## 1. Landing Page & Public Routes

| # | Scenario | Steps | Expected | Status |
|---|----------|-------|----------|--------|
| 1.1 | Landing page renders | Navigate to `/` | Hero section, feature cards, CTAs visible | [ ] |
| 1.2 | CTA → Register | Click "Start for Free" | Navigates to `/register` | [ ] |
| 1.3 | CTA → Library | Click "Browse Circulars" | Navigates to `/library` | [ ] |
| 1.4 | Library browsable without auth | Navigate to `/library` (not logged in) | Circulars list loads, filters work | [ ] |
| 1.5 | Circular detail without auth | Click a circular in library | Detail page loads with chunks | [ ] |
| 1.6 | Filter facets load | Check department, tags, doc-type dropdowns | Dropdown options populated from DB | [ ] |
| 1.7 | Autocomplete works | Type in search bar on library | Suggestions appear | [ ] |
| 1.8 | Plans page public | `GET /api/v1/subscriptions/plans` | Returns monthly + annual plans with pricing | [ ] |

---

## 2. Registration Flow

| # | Scenario | Steps | Expected | Status |
|---|----------|-------|----------|--------|
| 2.1 | Register form renders | Navigate to `/register` | Email, name, org fields visible | [ ] |
| 2.2 | Register with valid email | Enter `testuser@bigbank.com`, name, org → Submit | "OTP sent" message, redirect to verify | [ ] |
| 2.3 | OTP verification (demo) | Enter `123456` on `/verify` | Login succeeds, redirect to `/dashboard` | [ ] |
| 2.4 | User created with 5 credits | Check account page | Plan = "free", Credits = 5 | [ ] |
| 2.5 | Duplicate email rejected | Register same email again | Error: "User already exists" | [ ] |
| 2.6 | Invalid OTP rejected | Enter `000000` on verify | Error: "Invalid OTP; N attempt(s) remaining" | [ ] |
| 2.7 | OTP max attempts lockout | Enter wrong OTP 5 times | Error: "Maximum verification attempts exceeded" | [ ] |
| 2.8 | Honeypot field blocks bots | Fill hidden honeypot field (dev tools) | Silently accepts but does NOT create user | [ ] |

---

## 3. Login Flow

| # | Scenario | Steps | Expected | Status |
|---|----------|-------|----------|--------|
| 3.1 | Login form renders | Navigate to `/login` | Email field visible | [ ] |
| 3.2 | Login existing user | Enter registered email → Submit | "OTP sent" message | [ ] |
| 3.3 | Verify OTP → Dashboard | Enter `123456` | Logged in, redirect to `/dashboard` | [ ] |
| 3.4 | Login non-existent email | Enter unregistered email | Error message | [ ] |
| 3.5 | Login deactivated user | Deactivate via admin, try login | Error: "Account has been deactivated" | [ ] |

---

## 4. Token & Session Management

| # | Scenario | Steps | Expected | Status |
|---|----------|-------|----------|--------|
| 4.1 | Access token in memory only | Check browser DevTools (Application → Cookies, Storage) | No access token in cookies or localStorage | [ ] |
| 4.2 | Refresh token is HttpOnly | Check cookies in DevTools | `refresh_token` cookie: HttpOnly=true, SameSite=lax | [ ] |
| 4.3 | Silent refresh on 401 | Wait for access token expiry (15m) or manually expire | Frontend auto-refreshes, no redirect to login | [ ] |
| 4.4 | Logout clears session | Click logout | Redirect to `/login`, refresh_token cookie cleared | [ ] |
| 4.5 | Revoked token rejected | After logout, replay old access token via curl | 401: "Token has been revoked" | [ ] |
| 4.6 | Concurrent sessions | Login from two browsers | Both work independently | [ ] |
| 4.7 | Logout one session | Logout from browser A | Browser B still works (independent sessions) | [ ] |

---

## 5. Dashboard

| # | Scenario | Steps | Expected | Status |
|---|----------|-------|----------|--------|
| 5.1 | Dashboard loads | Navigate to `/dashboard` after login | Page renders with user greeting | [ ] |
| 5.2 | Credit balance visible | Check dashboard | Shows current credit balance | [ ] |
| 5.3 | Recent questions shown | After asking questions, check dashboard | Recent Q&A listed | [ ] |

---

## 6. Q&A — Ask Flow (Core RAG Pipeline)

| # | Scenario | Steps | Expected | Status |
|---|----------|-------|----------|--------|
| 6.1 | Ask page renders | Navigate to `/ask` | Textarea + credit balance visible | [ ] |
| 6.2 | Ask a valid question | Type "What are the KYC requirements for banks?" → Submit | Streaming answer with citations appears | [ ] |
| 6.3 | Answer has citations | Check response | Citations reference actual circular numbers from retrieved chunks | [ ] |
| 6.4 | Credit deducted | Check credit balance after answer | Balance decreased by 1 | [ ] |
| 6.5 | Quick answer shown | Check answer structure | Quick answer + detailed interpretation visible | [ ] |
| 6.6 | Risk level present | Check answer metadata | Risk level (HIGH/MEDIUM/LOW) shown | [ ] |
| 6.7 | Confidence meter | Check answer display | Confidence score bar (0-1.0) visible | [ ] |
| 6.8 | Consult Expert fallback | Ask a question with no relevant circulars (e.g., "What is the weather?") | "Consult an Expert" message, no credit charged | [ ] |
| 6.9 | No chunks → no credit | Ask completely off-topic question | "No relevant circulars found", credit NOT deducted | [ ] |
| 6.10 | Cache hit → no credit | Ask the exact same question again | Same answer returned, credit NOT deducted | [ ] |
| 6.11 | SSE streaming | Set Accept: text/event-stream | Tokens stream in real-time via SSE | [ ] |
| 6.12 | Zero credits blocked | Exhaust all credits, try to ask | 402: "Insufficient credits" | [ ] |
| 6.13 | Recommended actions | Check answer for action items | `recommended_actions` array present | [ ] |
| 6.14 | Affected teams | Check answer metadata | `affected_teams` array present | [ ] |
| 6.15 | Low-credit email at 5 | Ask questions until balance = 5 | Low-credit email sent (check logs in DEMO_MODE) | [ ] |
| 6.16 | Low-credit email at 2 | Continue until balance = 2 | Second low-credit email triggered | [ ] |

---

## 7. Question History

| # | Scenario | Steps | Expected | Status |
|---|----------|-------|----------|--------|
| 7.1 | History list loads | Navigate to `/history` | Paginated list of past questions | [ ] |
| 7.2 | Pagination works | Ask 25+ questions, check pagination | Page 1/2 navigation works | [ ] |
| 7.3 | Question detail | Click a question in history | Full answer, citations, metadata displayed | [ ] |
| 7.4 | Confidence meter on detail | Check detail page | Confidence score bar rendered | [ ] |
| 7.5 | Skeleton loaders | Navigate to history (slow network via DevTools) | Skeleton placeholders shown during load | [ ] |
| 7.6 | Feedback — thumbs up | Click thumbs up on a question | Feedback recorded, UI updates | [ ] |
| 7.7 | Feedback — thumbs down | Click thumbs down on a question | Feedback recorded | [ ] |
| 7.8 | Export compliance brief | Click export on a question | Text file downloads with formatted answer | [ ] |
| 7.9 | Other user's question hidden | Try `GET /questions/{other_user_id}` via curl | 404: "Question not found" | [ ] |

---

## 8. Circular Library (Authenticated)

| # | Scenario | Steps | Expected | Status |
|---|----------|-------|----------|--------|
| 8.1 | Hybrid search | Search "KYC requirements" while logged in | Results ranked by vector + BM25 RRF fusion | [ ] |
| 8.2 | Filter by department | Select a department filter | Results filtered correctly | [ ] |
| 8.3 | Filter by impact level | Select HIGH impact | Only high-impact circulars shown | [ ] |
| 8.4 | Filter by date range | Set date_from and date_to | Results within range | [ ] |
| 8.5 | Filter by tags | Select specific tags | Tagged circulars shown | [ ] |
| 8.6 | Combined filters | Apply multiple filters + search | Intersection of all filters | [ ] |
| 8.7 | Circular detail with chunks | Click a circular | Full text + document chunks displayed | [ ] |

---

## 9. Saved Interpretations

| # | Scenario | Steps | Expected | Status |
|---|----------|-------|----------|--------|
| 9.1 | Save an interpretation | From question detail, click "Save" | Save dialog with name + tags | [ ] |
| 9.2 | List saved items | Navigate to `/saved` | Saved interpretations listed | [ ] |
| 9.3 | View saved detail | Click a saved item | Full question + answer + tags shown | [ ] |
| 9.4 | Update name/tags | Edit name or tags on a saved item | Updates persisted | [ ] |
| 9.5 | Delete saved item | Delete a saved interpretation | Removed from list | [ ] |
| 9.6 | Other user's saved hidden | Try `GET /saved/{other_user_id}` via curl | 404 | [ ] |

---

## 10. Action Items

| # | Scenario | Steps | Expected | Status |
|---|----------|-------|----------|--------|
| 10.1 | Auto-generated from Q&A | Ask a question with recommended actions | Action items auto-created | [ ] |
| 10.2 | List action items | Navigate to `/action-items` | Items listed with status badges | [ ] |
| 10.3 | Filter by status | Filter PENDING / IN_PROGRESS / COMPLETED | Correct items shown | [ ] |
| 10.4 | Filter by team | Filter by assigned_team | Correct items shown | [ ] |
| 10.5 | Filter by priority | Filter HIGH / MEDIUM / LOW | Correct items shown | [ ] |
| 10.6 | Create manually | Click "Add Action Item" | Form appears, item created | [ ] |
| 10.7 | Update status | Change status from PENDING → IN_PROGRESS | Status updated | [ ] |
| 10.8 | Update priority | Change priority | Priority updated | [ ] |
| 10.9 | Delete action item | Delete an item | Removed from list | [ ] |
| 10.10 | Pagination | Create 25+ items | Pagination works | [ ] |

---

## 11. Public Snippet Sharing

| # | Scenario | Steps | Expected | Status |
|---|----------|-------|----------|--------|
| 11.1 | Create snippet | From question detail, click "Share" | Snippet dialog with generated URL | [ ] |
| 11.2 | Public URL works | Open `/s/{slug}` in incognito | Snippet visible (quick_answer + 1 citation) | [ ] |
| 11.3 | Detailed interpretation hidden | Check public snippet | `detailed_interpretation` NOT exposed | [ ] |
| 11.4 | Consult Expert snippet | Share a consult-expert answer | Shows fallback message, no detailed answer | [ ] |
| 11.5 | OG image renders | Check `/api/v1/snippets/{slug}/og` | PNG image returned (cached 24h) | [ ] |
| 11.6 | View count increments | Load snippet URL twice | `view_count` increases | [ ] |
| 11.7 | Rate limiting | Hit snippet URL > 60 times/min | 429: rate limited | [ ] |
| 11.8 | Revoke snippet | Delete snippet as owner | Public URL returns 404 | [ ] |
| 11.9 | List user's snippets | `GET /api/v1/snippets` | Only user's snippets returned | [ ] |

---

## 12. Updates / News Feed

| # | Scenario | Steps | Expected | Status |
|---|----------|-------|----------|--------|
| 12.1 | Updates page loads | Navigate to `/updates` | News items listed | [ ] |
| 12.2 | News items displayed | Check feed | Title, source, date, linked circular (if any) | [ ] |
| 12.3 | Filter by source | Filter dropdown | Correct items shown | [ ] |
| 12.4 | Linked circulars | Click on a linked circular | Navigates to circular detail | [ ] |
| 12.5 | News NOT in RAG corpus | Ask a question about a news headline | Answer uses circulars, not news items | [ ] |
| 12.6 | Skeleton loaders | Navigate with slow network | Skeleton placeholders shown | [ ] |

---

## 13. Subscriptions & Payments

| # | Scenario | Steps | Expected | Status |
|---|----------|-------|----------|--------|
| 13.1 | Upgrade page loads | Navigate to `/upgrade` | Plan cards with pricing shown | [ ] |
| 13.2 | Monthly plan details | Check monthly card | ₹2,999, 250 credits, 30 days | [ ] |
| 13.3 | Annual plan details | Check annual card | ₹29,999, 3,000 credits, 365 days | [ ] |
| 13.4 | Create order (API) | `POST /subscriptions/order` with plan="monthly" | Returns order_id + amount | [S] |
| 13.5 | Razorpay checkout | Click "Subscribe" on a plan | Razorpay modal opens (test mode) | [S] |
| 13.6 | Payment verification | Complete test payment | Credits added, plan activated | [S] |
| 13.7 | Payment history | Check `/account` → Payment History | Transaction listed with status | [ ] |
| 13.8 | Webhook idempotency | Replay webhook payload | No double-credit, 200 response | [S] |

> **Note:** Razorpay tests marked [S] require test API keys. In DEMO_MODE, the order creation will fail unless Razorpay test keys are configured.

---

## 14. Account Management

| # | Scenario | Steps | Expected | Status |
|---|----------|-------|----------|--------|
| 14.1 | Account page loads | Navigate to `/account` | Profile, plan, payment history, data management | [ ] |
| 14.2 | Profile info correct | Check displayed info | Name, email match registration | [ ] |
| 14.3 | Plan info correct | Check subscription section | Plan, credits, expiry shown | [ ] |
| 14.4 | Auto-renew toggle | Toggle auto-renew switch | State persists on page reload | [ ] |
| 14.5 | Export data | Click "Export My Data" | JSON file downloads | [ ] |
| 14.6 | Export contains questions | Open exported JSON | `questions` array with text + answers | [ ] |
| 14.7 | Export contains saved | Check JSON | `saved_interpretations` array | [ ] |
| 14.8 | Export contains actions | Check JSON | `action_items` array | [ ] |
| 14.9 | Export excludes admin fields | Check JSON → user object | No `is_admin`, `bot_suspect`, `password_changed_at` | [ ] |
| 14.10 | Delete account — OTP sent | Click "Delete Account" → "Send OTP" | OTP sent (demo: 123456) | [ ] |
| 14.11 | Delete account — confirm | Enter OTP → Confirm | Account deleted, redirected to `/login` | [ ] |
| 14.12 | Deleted user can't login | Try to login with deleted email | Fails (email anonymised) | [ ] |
| 14.13 | PII anonymised in DB | Query DB for deleted user | email = `deleted_*@deleted.regpulse.com`, full_name = "Deleted User" | [ ] |
| 14.14 | Questions preserved | Check questions table | user_id = NULL, question text preserved for analytics | [ ] |
| 14.15 | Sessions deleted | Check sessions table | No sessions for deleted user | [ ] |
| 14.16 | Invalid OTP rejected | Enter wrong OTP during deletion | Error: "Invalid OTP" | [ ] |

---

## 15. Dark Mode

| # | Scenario | Steps | Expected | Status |
|---|----------|-------|----------|--------|
| 15.1 | System preference bootstrap | Set OS to dark mode → load app | Dark mode active automatically | [ ] |
| 15.2 | Toggle via UI | Click theme toggle (sun/moon icon) | Mode switches immediately | [ ] |
| 15.3 | Persists on reload | Toggle, reload page | Same mode active | [ ] |
| 15.4 | WCAG-AA contrast | Inspect text/background in dark mode | Contrast ratio ≥ 4.5:1 for normal text | [ ] |
| 15.5 | All pages support dark mode | Navigate through all app pages | No white-flash or unthemed elements | [ ] |

---

## 16. Admin — Dashboard

| # | Scenario | Steps | Expected | Status |
|---|----------|-------|----------|--------|
| 16.1 | Admin login | Login with admin email (in ADMIN_EMAIL_ALLOWLIST) | Access to `/admin` | [ ] |
| 16.2 | Dashboard stats | Navigate to `/admin` | User count, questions, circulars, pending reviews | [ ] |
| 16.3 | Non-admin blocked | Login as regular user, navigate to `/admin` | 403 or redirect | [ ] |
| 16.4 | Heatmap loads | Navigate to `/admin/heatmap` | Clustering heatmap with period controls | [ ] |
| 16.5 | Refresh clustering | Click "Refresh" on heatmap | Celery task enqueued, heatmap updates | [ ] |

---

## 17. Admin — User Management

| # | Scenario | Steps | Expected | Status |
|---|----------|-------|----------|--------|
| 17.1 | User list loads | Navigate to `/admin/users` | Paginated user list | [ ] |
| 17.2 | Search by email | Type in search box | Filtered results | [ ] |
| 17.3 | Filter by plan | Select plan filter | Correct users shown | [ ] |
| 17.4 | Update credits | Edit user's credit_balance | Balance updated | [ ] |
| 17.5 | Deactivate user | Set is_active = false | User can't login | [ ] |
| 17.6 | Reactivate user | Set is_active = true | User can login again | [ ] |
| 17.7 | Audit log created | After any update | `admin_audit_log` entry with actor_id, old/new values | [ ] |

---

## 18. Admin — Circular Review

| # | Scenario | Steps | Expected | Status |
|---|----------|-------|----------|--------|
| 18.1 | Pending summaries | Navigate to `/admin/circulars` | Circulars with pending AI summaries listed | [ ] |
| 18.2 | Approve summary | Click "Approve" on a circular | Summary becomes public | [ ] |
| 18.3 | Edit metadata | Update title, tags, department | Changes persisted | [ ] |
| 18.4 | Audit log created | After metadata edit | `admin_audit_log` entry | [ ] |

---

## 19. Admin — Q&A Review

| # | Scenario | Steps | Expected | Status |
|---|----------|-------|----------|--------|
| 19.1 | Flagged questions | Navigate to `/admin/review` | Questions with negative feedback listed | [ ] |
| 19.2 | Override answer | Enter corrected text → Save | `admin_override` field populated | [ ] |
| 19.3 | Mark reviewed | Click "Mark Reviewed" without override | Removed from review queue | [ ] |
| 19.4 | Audit log created | After override | `admin_audit_log` entry | [ ] |

---

## 20. Admin — Scraper Management

| # | Scenario | Steps | Expected | Status |
|---|----------|-------|----------|--------|
| 20.1 | Scraper runs list | Navigate to `/admin/scraper` | Past runs with status, counts | [ ] |
| 20.2 | Trigger priority scrape | Click "Priority Scrape" | Celery task enqueued, new run appears | [ ] |
| 20.3 | Trigger full scrape | Click "Full Scrape" | Celery task enqueued | [ ] |
| 20.4 | Run status updates | Watch scraper run | Status progresses: RUNNING → COMPLETED/FAILED | [ ] |

---

## 21. Admin — PDF Upload

| # | Scenario | Steps | Expected | Status |
|---|----------|-------|----------|--------|
| 21.1 | Upload page loads | Navigate to `/admin/uploads` | Drag-drop zone + upload list | [ ] |
| 21.2 | Upload valid PDF | Drag a PDF file | Upload starts, status = PROCESSING | [ ] |
| 21.3 | Processing completes | Wait for Celery task | Status = COMPLETED, circular created | [ ] |
| 21.4 | Uploaded circular searchable | Search in library | Uploaded circular appears in results | [ ] |
| 21.5 | Upload source marked | Check DB | `upload_source = 'manual_upload'` | [ ] |
| 21.6 | Non-PDF rejected | Upload a .txt file | Error: invalid file type | [ ] |
| 21.7 | Oversized file rejected | Upload > 20MB PDF | Error: file too large | [ ] |

---

## 22. Admin — Prompt Management

| # | Scenario | Steps | Expected | Status |
|---|----------|-------|----------|--------|
| 22.1 | Prompt list loads | Navigate to `/admin/prompts` | Prompt versions listed (newest first) | [ ] |
| 22.2 | Create new prompt | Enter new prompt text → Save | New version created, auto-activated | [ ] |
| 22.3 | Activate old version | Click "Activate" on older version | That version becomes active | [ ] |
| 22.4 | Q&A uses active prompt | Ask a question | Response influenced by active prompt version | [ ] |

---

## 23. Admin — News Management

| # | Scenario | Steps | Expected | Status |
|---|----------|-------|----------|--------|
| 23.1 | News list loads | Navigate to `/admin/news` | All news items (including dismissed) | [ ] |
| 23.2 | Dismiss news item | Set status = DISMISSED | Item hidden from user feed | [ ] |
| 23.3 | Reactivate news item | Set status = ACTIVE | Item visible again | [ ] |

---

## 24. Celery Tasks (Background)

| # | Scenario | Steps | Expected | Status |
|---|----------|-------|----------|--------|
| 24.1 | Beat scheduler running | `docker logs regpulse-celery-beat-1 --tail 20` | Heartbeat entries visible | [ ] |
| 24.2 | Worker consuming tasks | `docker logs regpulse-scraper-1 --tail 20` | Task execution logs | [ ] |
| 24.3 | News ingest runs | Wait 30 minutes or trigger manually | `ingest_news` task completes | [ ] |
| 24.4 | Question clustering runs | Trigger via `/admin/heatmap/refresh` | `run_question_clustering` completes | [ ] |
| 24.5 | Worker queues correct | Check worker startup log | Consuming queues: `celery,scraper` | [ ] |
| 24.6 | Graceful shutdown | `docker compose stop scraper` | Worker finishes current task before exit | [ ] |

---

## 25. Security & Edge Cases

| # | Scenario | Steps | Expected | Status |
|---|----------|-------|----------|--------|
| 25.1 | PII not in LLM calls | Check backend logs during Q&A | No email/name in LLM request | [ ] |
| 25.2 | Citation validation | Check answer citations | Only circular numbers from retrieved chunks | [ ] |
| 25.3 | Rate limiting | Hit an endpoint > limit/min | 429: "Too Many Requests" | [ ] |
| 25.4 | SQL injection | Send `'; DROP TABLE users;--` as question | Normal error response, no DB impact | [ ] |
| 25.5 | XSS in question | Enter `<script>alert('xss')</script>` as question | Escaped in response, no script execution | [ ] |
| 25.6 | CORS enforcement | `curl -H "Origin: https://evil.com"` a protected endpoint | No CORS headers for non-allowed origin | [ ] |
| 25.7 | Webhook HMAC | Send fake webhook without valid signature | Rejected (signature mismatch) | [S] |
| 25.8 | Credits via SELECT FOR UPDATE | Concurrent question requests | No double-deduction (atomic) | [ ] |
| 25.9 | Expired token refresh | Use expired access token | Auto-refresh succeeds, request retried | [ ] |
| 25.10 | Snippet redaction | Create snippet for detailed answer | Only `quick_answer` + 1 citation exposed | [ ] |
| 25.11 | Admin audit trail | Perform admin actions | All mutations logged in `admin_audit_log` | [ ] |
| 25.12 | Superseded circular excluded | Mark a circular as superseded | Not returned in RAG retrieval (`WHERE status='ACTIVE'`) | [ ] |
| 25.13 | News not in RAG | Ask about a news headline topic | Answer cites circulars, not news items | [ ] |

---

## 26. Performance & Load

| # | Scenario | Steps | Expected | Status |
|---|----------|-------|----------|--------|
| 26.1 | k6 smoke test | `k6 run tests/load/k6_load_test.js --env SCENARIO=smoke` | All checks pass, p95 < 2s | [ ] |
| 26.2 | k6 load test | `k6 run tests/load/k6_load_test.js --env SCENARIO=load` | 50 VUs sustained, error rate < 1% | [ ] |
| 26.3 | SSE streaming latency | Measure time-to-first-token | < 3 seconds for cached embeddings | [ ] |
| 26.4 | Library page load | Measure `/library` load time | < 1.5 seconds | [ ] |
| 26.5 | Embedding cache | Ask same question twice, compare latency | Second request significantly faster | [ ] |

---

## 27. Cross-Browser & Responsive

| # | Scenario | Steps | Expected | Status |
|---|----------|-------|----------|--------|
| 27.1 | Chrome | Full flow in Chrome | No visual or functional issues | [ ] |
| 27.2 | Safari | Full flow in Safari | No visual or functional issues | [ ] |
| 27.3 | Firefox | Full flow in Firefox | No visual or functional issues | [ ] |
| 27.4 | Mobile viewport (375px) | Chrome DevTools mobile emulation | Layout doesn't break, content accessible | [ ] |
| 27.5 | Tablet viewport (768px) | Chrome DevTools tablet emulation | Responsive layout works | [ ] |

---

## 28. Error States & Empty States

| # | Scenario | Steps | Expected | Status |
|---|----------|-------|----------|--------|
| 28.1 | New user — empty history | Login as fresh user, go to `/history` | "No questions yet" message | [ ] |
| 28.2 | New user — empty saved | Go to `/saved` | "No saved interpretations" | [ ] |
| 28.3 | New user — empty actions | Go to `/action-items` | "No action items" | [ ] |
| 28.4 | No search results | Search for gibberish in library | "No results found" message | [ ] |
| 28.5 | Backend down | Stop backend container | Frontend shows error state, not crash | [ ] |
| 28.6 | Redis down | Stop Redis container | Backend returns degraded health, graceful errors | [ ] |
| 28.7 | LLM API down | Invalid API key | Fallback model attempted, then graceful error | [ ] |

---

## Test Execution Summary

| Category | Total Tests | Passed | Failed | Skipped |
|----------|-------------|--------|--------|---------|
| 0. Environment | 7 | | | |
| 1. Landing/Public | 8 | | | |
| 2. Registration | 8 | | | |
| 3. Login | 5 | | | |
| 4. Token/Session | 7 | | | |
| 5. Dashboard | 3 | | | |
| 6. Q&A / RAG | 16 | | | |
| 7. History | 9 | | | |
| 8. Library | 7 | | | |
| 9. Saved | 6 | | | |
| 10. Action Items | 10 | | | |
| 11. Snippets | 9 | | | |
| 12. Updates/News | 6 | | | |
| 13. Subscriptions | 8 | | | |
| 14. Account/DPDP | 16 | | | |
| 15. Dark Mode | 5 | | | |
| 16. Admin Dashboard | 5 | | | |
| 17. Admin Users | 7 | | | |
| 18. Admin Circulars | 4 | | | |
| 19. Admin Q&A Review | 4 | | | |
| 20. Admin Scraper | 4 | | | |
| 21. Admin PDF Upload | 7 | | | |
| 22. Admin Prompts | 4 | | | |
| 23. Admin News | 3 | | | |
| 24. Celery Tasks | 6 | | | |
| 25. Security | 13 | | | |
| 26. Performance | 5 | | | |
| 27. Cross-Browser | 5 | | | |
| 28. Error States | 7 | | | |
| **TOTAL** | **208** | | | |

---

## UAT Sign-Off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Product Owner | | | |
| QA Lead | | | |
| Tech Lead | | | |

---

*Generated 2026-04-13. See `TESTCASES.md` for automated test inventory (~170 automated tests).*
