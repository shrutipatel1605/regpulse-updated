**RegPulse**

RBI Regulatory Intelligence Platform

**PRODUCT REQUIREMENTS DOCUMENT (PRD) --- v2.0**

Supersedes PRD v1.0 \| Incorporates gap analysis and 9-category
improvement review

  ------------------ ----------------------------------------------------
  **Product Name**   RegPulse --- RBI Regulatory Intelligence Platform

  **Version**        2.0 (Revised)

  **Document Type**  Product Requirements Document (PRD)

  **Supersedes**     PRD v1.0

  **Regulatory       Reserve Bank of India (RBI) Directives (v2 schema
  Scope**            pre-built for multi-regulator expansion)

  **Primary          SaaS Subscription + Per-question Credits
  Revenue**          

  **Compliance       India Digital Personal Data Protection Act 2023
  Scope**            (DPDP), RBI IT Guidelines

  **Status**         Approved for Development
  ------------------ ----------------------------------------------------

  -----------------------------------------------------------------------
  **1. Executive Summary**

  -----------------------------------------------------------------------

RegPulse is a B2B SaaS platform purpose-built for professionals in the
Indian Banking and Credit industry. It delivers instant, factual, and
cited answers to compliance questions grounded exclusively in the
Reserve Bank of India\'s official corpus of Circulars, Master
Directions, and Notifications.

Every answer the platform generates: (a) cites exact RBI circular
numbers with links to rbi.org.in; (b) includes a Quick Answer executive
summary and Detailed Interpretation; (c) classifies the compliance risk
level (High / Medium / Low); (d) auto-generates team-tagged action items
for implementation. No LLM hallucination of circular references is
tolerated under any circumstances.

v2.0 additions over v1.0: Action Items module (originally in brief,
omitted from v1), Saved Interpretations with regulatory staleness
detection, dedicated Regulatory Updates Feed, impact classification on
every indexed circular, hybrid BM25+vector RAG retrieval with SSE
streaming, DPDP Act data rights, and subscription auto-renewal.

  -----------------------------------------------------------------------
  **2. Problem Statement & Market Opportunity**

  -----------------------------------------------------------------------

**2.1 The Compliance Research Problem**

The RBI issues hundreds of circulars, master directions, and
notifications annually. Compliance officers, credit officers, risk
managers, and banking executives must track, interpret, and action these
directives under significant time pressure. Current research workflows
are broken:

-   Manual search on rbi.org.in returns unranked PDFs with no contextual
    Q&A.

-   Circulars are frequently amended or superseded --- interpretation
    without expert guidance is hazardous.

-   Legal and compliance teams are overwhelmed --- hiring regulatory
    specialists is expensive and slow.

-   Generic LLMs (ChatGPT, Claude.ai) hallucinate circular numbers,
    dates, and provisions.

-   No existing tool translates regulatory language into actionable team
    tasks automatically.

**2.2 The Opportunity**

India has 12 public sector banks, 21 private banks, 1,500+ urban
cooperative banks, 100,000+ NBFCs, and a fast-growing fintech sector ---
all mandatorily subject to RBI regulation. A focused, authoritative
regulatory intelligence platform represents a compelling opportunity in
the Indian RegTech market, currently dominated by expensive manual
advisory services.

  -----------------------------------------------------------------------
  **3. Goals & Success Metrics**

  -----------------------------------------------------------------------

**3.1 Product Goals**

-   Deliver factually accurate, cited answers to RBI regulatory
    questions with zero hallucination of circular references.

-   Maintain a continuously updated corpus --- new RBI documents indexed
    within 24 hours of publication with impact classification.

-   Auto-generate structured action items from every answer, tagged by
    responsible team and priority.

-   Alert users when saved interpretations become stale due to
    regulatory amendments.

-   Convert free users to paid subscribers at ≥ 15% within 30 days of
    first use.

-   Achieve a thumbs-up satisfaction rate of ≥ 80% on all AI-generated
    answers.

-   Comply fully with India\'s Digital Personal Data Protection Act
    2023.

**3.2 Key Metrics (OKRs)**

  ---------------------------- --------------------- ---------------------
  **Metric**                   **Target Month 6**    **Target Month 12**

  Registered Users             500                   2,000

  Paid Subscribers             75                    400

  Monthly Active Users         300                   1,200

  Questions per Month          3,000                 15,000

  Thumbs-Up Rate               ≥ 75%                 ≥ 85%

  Action Items Created / Month 1,500                 8,000

  Avg. Answer Latency (P50)    \< 4 seconds          \< 3 seconds

  RAG Retrieval Hit Rate       ≥ 80%                 ≥ 88%

  Circulars Indexed            All historical + live All historical + live
  ---------------------------- --------------------- ---------------------

  -----------------------------------------------------------------------
  **4. User Personas**

  -----------------------------------------------------------------------

**4.1 Compliance Officer --- Priya**

Mid-size private bank. Ensures bank policies align with RBI directives.
Spends 3--4 hours weekly reviewing new circulars. Primary need: rapid
circular lookup, impact assessment, and trackable implementation
actions.

**4.2 Credit Risk Analyst --- Rahul**

NBFC. Verifies lending norms, fair practices code, asset classification.
Primary need: specific clause interpretation with citations and risk
level clarity.

**4.3 RegTech / Fintech Founder --- Ananya**

Building a lending product. Needs to understand digital lending
guidelines, KYC norms, data localisation. Primary need: comprehensive
regulatory scoping without a legal team.

**4.4 Compliance Manager --- Deepak**

Large public sector bank. Manages a team across Risk, Operations, Legal.
Primary need: distribute regulatory action items to the right team
members and track completion.

**4.5 Admin / Platform Curator --- Internal**

Reviews thumbs-down answers, fine-tunes prompts, approves AI summaries.
Primary need: fast turnaround on quality issues, clear admin tools.

  -----------------------------------------------------------------------
  **5. User Stories**

  -----------------------------------------------------------------------

  -------- ---------------- -------------------------- -------------- -----------
  **ID**   **As a\...**     **I want to\...**          **Priority**   **v2
                                                                      Status**

  US-01    Compliance       search and read any RBI    P0 --- Must    Enhanced
           Officer          circular with full         Have           
                            metadata and impact level                 

  US-02    Bank Executive   ask a question and get a   P0 --- Must    Enhanced
                            cited answer with risk     Have           
                            level and action items                    

  US-03    New User         register with my work      P0 --- Must    Unchanged
                            email and get 5 free       Have           
                            questions immediately                     

  US-04    Paid Subscriber  ask questions within my    P0 --- Must    Unchanged
                            credit allowance after     Have           
                            upgrading                                 

  US-05    Compliance       see team-tagged action     P0 --- Must    NEW v2
           Officer          items auto-generated from  Have           
                            every answer                              

  US-06    Compliance       track action item status   P0 --- Must    NEW v2
           Manager          (Pending/In                Have           
                            Progress/Done/Overdue)                    

  US-07    Analyst          save a Q&A interpretation  P1 --- Should  NEW v2
                            with a name and tags for   Have           
                            future reference                          

  US-08    Compliance       be alerted when a saved    P1 --- Should  NEW v2
           Officer          interpretation\'s source   Have           
                            circular is amended                       

  US-09    Compliance       browse a dedicated feed of P1 --- Should  NEW v2
           Officer          new regulatory changes     Have           
                            filtered by impact                        

  US-10    Analyst          rate the quality of each   P1 --- Should  Unchanged
                            answer to improve the      Have           
                            platform                                  

  US-11    Admin            review thumbs-down answers P0 --- Must    Unchanged
                            and override them with     Have           
                            corrections                               

  US-12    Subscriber       export an AI compliance    P2 --- Nice to Enhanced
                            brief as a PDF with action Have           
                            items                                     

  US-13    All Users        ask a follow-up question   P2 --- Nice to v2 Roadmap
                            in context of the previous Have           
                            answer                                    

  US-14    Enterprise Team  share question history and P2 --- Nice to v2 Roadmap
                            action items across team   Have           
                            members                                   

  US-15    All Users        request deletion of my     P0 --- Legal   NEW v2
                            personal data (DPDP        Req.           
                            compliance)                               

  US-16    All Users        export all my data in      P0 --- Legal   NEW v2
                            machine-readable format    Req.           
                            (DPDP portability)                        
  -------- ---------------- -------------------------- -------------- -----------

  -----------------------------------------------------------------------
  **6. Feature Requirements**

  -----------------------------------------------------------------------

**6.1 Module 1 --- Reference Library Data Scraper**

**F1.1 --- Scheduled Crawling**

-   Daily cron at 02:00 IST for all sections; priority crawl every 4h
    (06:00--22:00 UTC) for Circulars + Master Directions.

-   Crawls: Notifications/Circulars, Master Directions, Press Releases,
    FAQs.

-   PDF download → pdfplumber text extraction → pytesseract OCR fallback
    for scanned documents.

**F1.2 --- Metadata Extraction (Enhanced)**

-   Circular number, issuing department, issued date, effective date via
    regex + constants taxonomy.

-   Action Deadline \[NEW v2\]: separate from effective_date ---
    extracted from compliance phrases (\'submit by\', \'implement by\',
    \'on or before\').

-   Affected Teams \[NEW v2\]: keyword classification against
    \[\'Compliance\', \'Risk Management\', \'Operations\', \'Legal\',
    \'IT Security\', \'Finance\'\].

-   Topic tags \[NEW v2\]: AI-classified against 20-term taxonomy (KYC,
    Digital Lending, FEMA, Priority Sector, etc.).

**F1.3 --- Impact Classification \[NEW v2\]**

-   Every indexed circular receives an impact_level: HIGH / MEDIUM /
    LOW.

-   Classification by Claude Haiku during ingestion (cost-efficient).
    HIGH: new requirements, penalties, prohibitions; MEDIUM: amendments;
    LOW: informational.

-   Admin can override classification. Displayed as coloured badge
    throughout the platform.

**F1.4 --- Supersession Resolution + Staleness Detection \[Enhanced\]**

-   Existing: pattern matching for supersession language,
    status=\'SUPERSEDED\' on matched circulars.

-   New \[v2\]: when a circular is marked superseded, all
    saved_interpretations citing that circular are flagged
    needs_review=TRUE. Affected users receive a staleness alert email.

**F1.5 --- AI Summary Generation**

-   Claude Haiku generates a 3-sentence AI summary per circular.

-   Summaries require admin approval before being displayed to users
    (pending_admin_review flag).

**6.2 Module 2 --- Web Application**

**F2.1 --- Authentication**

-   Work email only --- 250+ domain blocklist + async MX record
    verification.

-   OTP-only login (no passwords). 6-digit OTP, 10-minute TTL, 3
    OTPs/hour rate limit.

-   RS256 JWT access tokens (1h TTL), refresh tokens in httpOnly cookie
    (7d TTL).

-   Refresh token rotation \[v2 security\]: every refresh revokes old
    session and issues a new token.

-   JWT blacklist \[v2 security\]: on logout, jti stored in Redis (TTL =
    remaining token lifetime). Deactivated users immediately locked out.

**F2.2 --- Q&A Engine (Enhanced)**

The Q&A engine uses a hybrid BM25+vector RAG pipeline with SSE
streaming.

-   User question → optional context selectors (Department, Use Case) →
    injection guard check → hybrid retrieval → reranking → LLM
    generation → structured response.

-   Prompt injection defense \[v2\]: regex detection of 20+ injection
    patterns. Detected questions return 400, no credit charge.

-   Hybrid retrieval \[v2\]: parallel pgvector cosine ANN + PostgreSQL
    full-text search, merged via Reciprocal Rank Fusion.

-   Query expansion \[v2 optional\]: Claude Haiku generates 2
    alternative phrasings before retrieval (RAG_QUERY_EXPANSION=false by
    default).

-   Cross-encoder reranking in ProcessPoolExecutor --- never blocks the
    API event loop.

-   SSE streaming \[v2\]: tokens stream to frontend in real time. Credit
    deducted only on successful completion.

-   LLM fallback \[v2\]: GPT-4o via pybreaker circuit breaker if
    Anthropic unavailable.

-   Cache hits are free: identical questions (SHA256 on normalised text)
    served from Redis (24h TTL).

**F2.3 --- Structured Answer Format \[NEW v2\]**

Every Q&A answer returns a structured response with the following
fields:

-   Quick Answer: 80-word executive summary.

-   Detailed Interpretation: full markdown analysis with structured
    sections.

-   Risk Level: HIGH / MEDIUM / LOW badge.

-   Affected Teams: list of teams identified as responsible for
    implementation.

-   Source Citations: each citation includes circular number, title,
    date, verbatim supporting quote, and section reference where
    determinable.

-   Recommended Actions: list of {team, action_text, priority} items
    structured by team.

**F2.4 --- Action Items Module \[NEW v2 --- was in original brief\]**

Every answer\'s Recommended Actions can be saved as trackable action
items.

-   \'Add to Action Items\' button on each Recommended Action row.

-   Action items have: title, description, assigned_team, priority
    (High/Medium/Low), due_date (auto-suggested: +7d High, +30d Medium,
    +90d Low), status (Pending / In Progress / Completed).

-   Overdue items computed automatically (due_date \< today, status !=
    Completed).

-   Dedicated /action-items page: tabbed by status, priority badges,
    days-remaining countdown, source interpretation link.

-   Dashboard shows pending action item count and top overdue items.

**F2.5 --- Saved Interpretations Library \[NEW v2\]**

-   Users can save any Q&A result as a named, tagged interpretation.

-   Saved items show Quick Answer, Risk Level, source citations, and
    current/stale status.

-   Staleness detection: when a cited circular is amended or superseded,
    items with needs_review=TRUE show \'Update Available\' badge.

-   Staleness alert email sent automatically to the user when their
    saved item becomes stale.

-   Users mark items as reviewed after reading the update.

**F2.6 --- Regulatory Updates Feed \[NEW v2\]**

-   Dedicated /updates page showing recently indexed circulars sorted by
    indexed_at DESC.

-   Filter tabs: All Updates / High Impact / My Department / This Week.

-   Each card shows: title, circular number, impact badge, summary
    preview, action_deadline if present, affected teams, and direct
    \'Ask a Question\' link.

-   Unread count badge on Updates nav item (based on last_seen_updates
    timestamp on user).

**F2.7 --- Circular Library**

-   Browse, search, and filter all indexed RBI circulars.

-   Hybrid search (BM25 + vector) with Reciprocal Rank Fusion.

-   Filters: doc_type, department, impact_level \[v2\], tags \[v2\],
    date range, status.

-   Each circular card: circular_number, title, doc_type badge,
    impact_level badge \[v2\], department, date, status.

-   Detail page: full metadata, action_deadline \[v2\] with urgency
    highlight, affected_teams pills \[v2\], AI summary (approved only),
    supersession banner, citations.

**F2.8 --- Subscriptions & Credits**

-   Plans: Free (5 lifetime credits), Professional (₹2,999/month, 250
    credits), Enterprise (custom, unlimited).

-   Credits deducted atomically on successful answer delivery only
    (SELECT FOR UPDATE).

-   Subscription auto-renewal \[v2\]: Celery Beat task checks 3 days
    before expiry and attempts Razorpay charge.

-   Low-credit notifications \[v2\]: email alerts at balance thresholds
    10, 5, and 2 (max 1/week per user).

-   Razorpay (INR) for all payments. HMAC-SHA256 webhook signature
    verification.

**F2.9 --- PDF Export**

-   Professional plan users can export any answer as a formatted PDF
    compliance brief.

-   PDF includes: RegPulse letterhead, question, Quick Answer, full
    interpretation, risk level, citations with QR codes to rbi.org.in,
    action items section, disclaimer.

**F2.10 --- Admin Console**

-   Review Queue: thumbs-down answers surfaced for manual review and
    override.

-   Override workflow: admin edits answer inline, override cached in
    Redis, logged in admin_audit_log.

-   Prompt Management: create, activate, and rollback system prompt
    versions. Admin Q&A Sandbox for testing new prompts without charging
    credits.

-   Circular Management: approve AI summaries, edit metadata
    (impact_level, action_deadline, affected_teams, tags).

-   User Management: view users, adjust credits, change plan, deactivate
    accounts.

-   Scraper Controls: view run history, trigger manual crawl, live log
    streaming.

-   Analytics: question volume trends, top queries, top circulars,
    conversion funnel, injection detection rate.

**F2.11 --- DPDP Act Compliance \[NEW v2 --- Legal Requirement\]**

-   Account deletion: PATCH /api/v1/account/delete --- soft delete with
    PII anonymisation (email→hashed placeholder, name→\'Deleted User\').
    Requires OTP re-confirmation.

-   Data portability: GET /api/v1/account/export --- all questions,
    saved interpretations, action items as JSON download. Requires OTP
    re-confirmation.

-   Retention policy: question content retained for admin analytics with
    user_id nullified; personal data (name, email) deleted immediately
    on request.

-   Basis: India\'s Digital Personal Data Protection Act 2023 ---
    applicable to all Indian SaaS handling personal data.

  -----------------------------------------------------------------------
  **7. Non-Functional Requirements**

  -----------------------------------------------------------------------

  --------------- ---------------------------------- ---------------------
  **Category**    **Requirement**                    **Target**

  Performance     API P50 latency --- circular       \< 200ms
                  browse                             

  Performance     API P95 latency --- hybrid search  \< 800ms

  Performance     API P50 latency --- question       \< 4 seconds
                  answer                             

  Performance     API P95 latency --- question       \< 8 seconds
                  answer                             

  Scalability     Concurrent users                   10,000

  RAG Quality     Retrieval hit rate (golden eval    ≥ 85%
                  suite)                             

  RAG Quality     Mean Reciprocal Rank (MRR)         ≥ 0.70

  Availability    Platform uptime                    ≥ 99.5% monthly

  Security        JWT access token TTL               1 hour

  Security        Refresh token rotation             On every
                                                     /auth/refresh call

  Security        Prompt injection detection         \< 200ms (regex,
                                                     before LLM call)

  Security        DPDP data deletion SLA             Within 30 days of
                                                     request

  Data freshness  New RBI circular indexed           Within 24 hours of
                                                     publication

  Cache hit rate  Identical questions served from    ≥ 30% of all Q&A
                  Redis                              requests

  LLM accuracy    Thumbs-up rate                     ≥ 80%

  Cost            LLM cost per question (median)     \< ₹2 (Sonnet) via
                                                     caching & chunking
  --------------- ---------------------------------- ---------------------

  -----------------------------------------------------------------------
  **8. Subscription Plans & Pricing**

  -----------------------------------------------------------------------

  --------------------------- -------------- ------------------ ----------------
  **Feature**                 **Free**       **Professional**   **Enterprise**

  Price                       ₹0             ₹2,999/month       Custom (annual
                                                                contract)

  Question Credits            5 (lifetime)   250 / month        Unlimited

  Action Items                5 max          Unlimited          Unlimited

  Saved Interpretations       3 max          Unlimited          Unlimited

  Staleness Alerts            No             Yes                Yes

  PDF Export                  No             Yes                Yes

  Priority RAG (fresh cache)  No             No                 Yes

  Team Seats                  No             No                 Yes (v2 roadmap)

  API Access                  No             No                 Yes (v2 roadmap)

  SLA                         None           Email support 48h  Dedicated 4h SLA

  Auto-renewal                N/A            Yes (configurable) Yes

  Credit rollover             No             No                 Yes
  --------------------------- -------------- ------------------ ----------------

  -----------------------------------------------------------------------
  **9. Security & Privacy Requirements**

  -----------------------------------------------------------------------

**9.1 Authentication Security**

-   OTP-only --- no passwords stored.

-   RS256 JWT with 1h access token and 7d refresh token (httpOnly
    cookie).

-   Refresh token rotation: each /auth/refresh revokes old session and
    issues new token pair.

-   JWT blacklist: logout/deactivation adds jti to Redis with TTL equal
    to remaining token lifetime.

**9.2 LLM Security**

-   Prompt injection detection before every LLM call --- 20+ patterns,
    400 response on detection.

-   User input wrapped in XML tags in LLM prompt. System prompt
    instructs model to ignore instructions inside tags.

-   PII (name, email, org) never sent to any LLM.

-   DEMO_MODE=true blocked from running in ENVIRONMENT=prod by startup
    validator.

**9.3 Data Privacy (DPDP Act 2023)**

-   Work email gated --- no consumer personal accounts.

-   PII fields anonymised on account deletion request within 30 days.

-   Data portability export (JSON) available on request.

-   Question logs retained for platform analytics with user_id nullified
    post-deletion.

**9.4 Infrastructure Security**

-   TLS 1.3 only. HSTS, CSP, X-Frame-Options, X-Content-Type-Options
    headers on all responses.

-   Razorpay webhook excluded from CORS. HMAC-SHA256 signature
    verification on all webhook calls.

-   XSS defense: admin override content rendered as markdown only with
    rehype-sanitize --- no raw HTML.

-   Rate limiting: registration 5/hour, OTP verify 10/hour, questions
    10/minute per user.

-   Honeypot field on registration form. Bot suspects flagged, not
    onboarded.

  -----------------------------------------------------------------------
  **10. Out of Scope for v1 (v2 Roadmap)**

  -----------------------------------------------------------------------

  ------------------------ ------------------------------- --------------
  **Feature**              **Reason Deferred**             **v2
                                                           Priority**

  Team Seats / Workspace   Requires multi-user org model   HIGH
                           and shared state                

  Share Interpretation     Requires team workspace         HIGH
  with Team                                                

  Comment Threads on       Requires team workspace         MEDIUM
  Interpretations                                          

  Conversational Q&A       Requires parent_question_id     HIGH
  Threading                model + context mgmt            

  SEBI / MeitY / RBI-NBFC  Multi-regulator expansion ---   HIGH
  Notifications            schema pre-built                

  Version Diff / Compare   Requires version history        MEDIUM
  Circulars                storage and diff rendering      

  Mobile App (iOS /        Web PWA covers mobile in v1     LOW
  Android)                                                 

  Razorpay Subscriptions   v1 sends renewal email only;    MEDIUM
  API (auto-charge)        auto-charge in v2               

  Saved Payment Methods    Requires Razorpay Cards/Tokens  MEDIUM
                           API                             

  OpenAPI SDK / API Access Enterprise plan feature in v2   MEDIUM
  ------------------------ ------------------------------- --------------

  -----------------------------------------------------------------------
  **11. Technical Architecture Summary**

  -----------------------------------------------------------------------

  ------------------ ----------------------------- -------------------------
  **Layer**          **Technology**                **Notes**

  Backend API        FastAPI (Python 3.11),        All endpoints at /api/v1/
                     Pydantic v2, SQLAlchemy 2.0   
                     async                         

  Frontend           Next.js 14, TypeScript        SSR + ISR; PWA manifest
                     strict, Tailwind CSS,         
                     Zustand, pnpm                 

  Database           PostgreSQL 16 + pgvector      Shared by scraper and
                     (ivfflat index)               backend

  Cache / Queue      Redis 7, Celery, Celery Beat  Answer cache, task queue,
                                                   JWT blacklist

  LLM (Primary)      Anthropic                     Q&A answers
                     claude-sonnet-4-20250514      

  LLM (Fallback)     GPT-4o via pybreaker circuit  Activates on Anthropic
                     breaker                       5xx/timeout

  LLM (Summaries)    Claude Haiku                  Lower cost; summaries +
                     (claude-haiku-4-5-20251001)   impact classification

  Embeddings         OpenAI text-embedding-3-large Configurable to 1536-dim
                     (3072-dim)                    to halve storage cost

  Reranking          ms-marco-MiniLM-L-6-v2        Loaded in backend only
                     (sentence-transformers)       --- not scraper image

  Payments           Razorpay (INR only)           HMAC-SHA256 webhook
                                                   verification

  CI/CD              GitHub Actions → AWS ECR →    Blue-green via AWS
                     AWS ECS (ap-south-1)          CodeDeploy for backend

  Proxy              Nginx (TLS 1.3, HSTS, CSP)    Rate limiting zones per
                                                   endpoint class

  Monitoring         structlog, Prometheus,        RAG hit rate as
                     Sentry, CloudWatch            CloudWatch custom metric
  ------------------ ----------------------------- -------------------------

*--- RegPulse PRD v2.0 --- All rights reserved ---*
