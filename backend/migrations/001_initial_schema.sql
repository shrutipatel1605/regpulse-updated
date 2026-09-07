-- RegPulse Initial Schema
-- PostgreSQL 15 + pgvector
-- All UUID PKs default to gen_random_uuid()
-- All timestamps are TIMESTAMPTZ defaulting to now()

-- =============================================================================
-- Extensions
-- =============================================================================
CREATE EXTENSION IF NOT EXISTS "pgcrypto";      -- gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS "vector";         -- pgvector

-- =============================================================================
-- ENUMs
-- =============================================================================
CREATE TYPE org_type_enum AS ENUM (
    'BANK', 'NBFC', 'COOPERATIVE', 'PAYMENT_BANK',
    'SMALL_FINANCE_BANK', 'FINTECH', 'INSURANCE', 'OTHER'
);

CREATE TYPE doc_type_enum AS ENUM (
    'CIRCULAR', 'MASTER_DIRECTION', 'NOTIFICATION',
    'PRESS_RELEASE', 'GUIDELINE', 'OTHER'
);

CREATE TYPE circular_status_enum AS ENUM ('ACTIVE', 'SUPERSEDED', 'DRAFT');

CREATE TYPE impact_level_enum AS ENUM ('HIGH', 'MEDIUM', 'LOW');

CREATE TYPE action_item_status_enum AS ENUM ('PENDING', 'IN_PROGRESS', 'COMPLETED');

-- =============================================================================
-- users
-- =============================================================================
CREATE TABLE users (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email                   VARCHAR(255) NOT NULL UNIQUE,
    email_verified          BOOLEAN NOT NULL DEFAULT FALSE,
    full_name               VARCHAR(255) NOT NULL,
    designation             VARCHAR(255),
    org_name                VARCHAR(255),
    org_type                org_type_enum,
    credit_balance          INTEGER NOT NULL DEFAULT 0,
    plan                    VARCHAR(50) NOT NULL DEFAULT 'free',
    plan_expires_at         TIMESTAMPTZ,
    plan_auto_renew         BOOLEAN NOT NULL DEFAULT TRUE,
    is_admin                BOOLEAN NOT NULL DEFAULT FALSE,
    is_active               BOOLEAN NOT NULL DEFAULT TRUE,
    bot_suspect             BOOLEAN NOT NULL DEFAULT FALSE,
    last_login_at           TIMESTAMPTZ,
    last_credit_alert_sent  TIMESTAMPTZ,
    last_seen_updates       TIMESTAMPTZ,
    deletion_requested_at   TIMESTAMPTZ,
    password_changed_at     TIMESTAMPTZ,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- =============================================================================
-- sessions (refresh token store + jti blacklist)
-- =============================================================================
CREATE TABLE sessions (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash  VARCHAR(512) NOT NULL,
    expires_at  TIMESTAMPTZ NOT NULL,
    revoked     BOOLEAN NOT NULL DEFAULT FALSE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- =============================================================================
-- scraper_runs (must exist before circular_documents FK)
-- =============================================================================
CREATE TABLE scraper_runs (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    started_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at         TIMESTAMPTZ,
    status               VARCHAR(20) NOT NULL DEFAULT 'RUNNING',
    documents_processed  INTEGER NOT NULL DEFAULT 0,
    documents_failed     INTEGER NOT NULL DEFAULT 0,
    error_message        TEXT,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- =============================================================================
-- circular_documents
-- =============================================================================
CREATE TABLE circular_documents (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    circular_number       VARCHAR(100),
    title                 TEXT NOT NULL,
    doc_type              doc_type_enum NOT NULL,
    department            VARCHAR(255),
    issued_date           DATE,
    effective_date        DATE,
    rbi_url               TEXT NOT NULL,
    status                circular_status_enum NOT NULL DEFAULT 'ACTIVE',
    superseded_by         UUID REFERENCES circular_documents(id) ON DELETE SET NULL,
    ai_summary            TEXT,
    pending_admin_review  BOOLEAN NOT NULL DEFAULT TRUE,
    impact_level          impact_level_enum,
    action_deadline       DATE,
    affected_teams        JSONB DEFAULT '[]'::jsonb,
    tags                  JSONB DEFAULT '[]'::jsonb,
    regulator             VARCHAR(20) NOT NULL DEFAULT 'RBI',
    scraper_run_id        UUID REFERENCES scraper_runs(id) ON DELETE SET NULL,
    indexed_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- =============================================================================
-- document_chunks
-- =============================================================================
CREATE TABLE document_chunks (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id   UUID NOT NULL REFERENCES circular_documents(id) ON DELETE CASCADE,
    chunk_index   INTEGER NOT NULL,
    chunk_text    TEXT NOT NULL,
    embedding     vector(3072),
    token_count   INTEGER NOT NULL DEFAULT 0,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- =============================================================================
-- prompt_versions (must exist before questions FK)
-- =============================================================================
CREATE TABLE prompt_versions (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    version_tag  VARCHAR(50) NOT NULL UNIQUE,
    prompt_text  TEXT NOT NULL,
    is_active    BOOLEAN NOT NULL DEFAULT FALSE,
    created_by   UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- =============================================================================
-- questions
-- =============================================================================
CREATE TABLE questions (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id               UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    question_text         TEXT NOT NULL,
    question_embedding    vector(3072),
    answer_text           TEXT,
    quick_answer          TEXT,
    risk_level            VARCHAR(10),
    recommended_actions   JSONB DEFAULT '[]'::jsonb,
    affected_teams        JSONB DEFAULT '[]'::jsonb,
    citations             JSONB DEFAULT '[]'::jsonb,
    chunks_used           JSONB DEFAULT '[]'::jsonb,
    model_used            VARCHAR(50),
    prompt_version        VARCHAR(50),
    feedback              SMALLINT,
    feedback_comment      TEXT,
    admin_override        TEXT,
    reviewed              BOOLEAN NOT NULL DEFAULT FALSE,
    reviewed_at           TIMESTAMPTZ,
    credit_deducted       BOOLEAN NOT NULL DEFAULT FALSE,
    streaming_completed   BOOLEAN NOT NULL DEFAULT TRUE,
    latency_ms            INTEGER,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- =============================================================================
-- action_items
-- =============================================================================
CREATE TABLE action_items (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    source_question_id  UUID REFERENCES questions(id) ON DELETE SET NULL,
    source_circular_id  UUID REFERENCES circular_documents(id) ON DELETE SET NULL,
    title               VARCHAR(500) NOT NULL,
    description         TEXT,
    assigned_team       VARCHAR(100),
    priority            VARCHAR(10) NOT NULL DEFAULT 'MEDIUM',
    due_date            DATE,
    status              action_item_status_enum NOT NULL DEFAULT 'PENDING',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- =============================================================================
-- saved_interpretations
-- =============================================================================
CREATE TABLE saved_interpretations (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id       UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    question_id   UUID NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
    name          VARCHAR(255) NOT NULL,
    tags          JSONB DEFAULT '[]'::jsonb,
    needs_review  BOOLEAN NOT NULL DEFAULT FALSE,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- =============================================================================
-- subscription_events
-- =============================================================================
CREATE TABLE subscription_events (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    order_id            VARCHAR(255),
    razorpay_event_id   VARCHAR(255) UNIQUE,
    plan                VARCHAR(50) NOT NULL,
    amount_paise        INTEGER NOT NULL,
    status              VARCHAR(50) NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- =============================================================================
-- admin_audit_log
-- =============================================================================
CREATE TABLE admin_audit_log (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    actor_id      UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    action        VARCHAR(100) NOT NULL,
    target_table  VARCHAR(100),
    target_id     UUID,
    old_value     JSONB,
    new_value     JSONB,
    ip_address    VARCHAR(45),
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- =============================================================================
-- analytics_events
-- =============================================================================
CREATE TABLE analytics_events (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_hash       VARCHAR(64) NOT NULL,
    event_type      VARCHAR(100) NOT NULL,
    event_data      JSONB DEFAULT '{}'::jsonb,
    session_id      VARCHAR(100),
    ip_address      VARCHAR(45),
    user_agent      TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- =============================================================================
-- pending_domain_reviews
-- =============================================================================
CREATE TABLE pending_domain_reviews (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain      VARCHAR(255) NOT NULL UNIQUE,
    email       VARCHAR(255) NOT NULL,
    mx_valid    BOOLEAN,
    reviewed    BOOLEAN NOT NULL DEFAULT FALSE,
    approved    BOOLEAN,
    reviewed_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- =============================================================================
-- Indexes
-- =============================================================================

-- Foreign key indexes
CREATE INDEX idx_sessions_user_id ON sessions(user_id);
CREATE INDEX idx_sessions_expires_at ON sessions(expires_at);
CREATE INDEX idx_circular_documents_scraper_run_id ON circular_documents(scraper_run_id);
CREATE INDEX idx_circular_documents_superseded_by ON circular_documents(superseded_by);
CREATE INDEX idx_document_chunks_document_id ON document_chunks(document_id);
CREATE INDEX idx_questions_user_id ON questions(user_id);
CREATE INDEX idx_action_items_user_id ON action_items(user_id);
CREATE INDEX idx_action_items_source_question_id ON action_items(source_question_id);
CREATE INDEX idx_action_items_source_circular_id ON action_items(source_circular_id);
CREATE INDEX idx_saved_interpretations_user_id ON saved_interpretations(user_id);
CREATE INDEX idx_saved_interpretations_question_id ON saved_interpretations(question_id);
CREATE INDEX idx_subscription_events_user_id ON subscription_events(user_id);
CREATE INDEX idx_admin_audit_log_actor_id ON admin_audit_log(actor_id);
CREATE INDEX idx_prompt_versions_created_by ON prompt_versions(created_by);

-- Status indexes
CREATE INDEX idx_circular_documents_status ON circular_documents(status);
CREATE INDEX idx_questions_feedback ON questions(feedback);
CREATE INDEX idx_questions_reviewed ON questions(reviewed);
CREATE INDEX idx_action_items_status ON action_items(status);
CREATE INDEX idx_scraper_runs_status ON scraper_runs(status);

-- Timestamp indexes
CREATE INDEX idx_users_created_at ON users(created_at);
CREATE INDEX idx_circular_documents_indexed_at ON circular_documents(indexed_at);
CREATE INDEX idx_questions_created_at ON questions(created_at);
CREATE INDEX idx_action_items_created_at ON action_items(created_at);
CREATE INDEX idx_analytics_events_created_at ON analytics_events(created_at);
CREATE INDEX idx_subscription_events_created_at ON subscription_events(created_at);

-- pgvector ANN indexes — DEFERRED until pgvector >=0.7.0 on the Postgres host.
-- text-embedding-3-large is 3072-dim; current Cloud SQL Postgres 16 ships pgvector that caps
-- both ivfflat AND hnsw at 2000 dimensions. Sequential scan is acceptable for first deploy
-- (small corpus). Upgrade path: switch to `halfvec(3072)` + ivfflat, or wait for pgvector 0.7.
-- See LEARNINGS.md LGCP.5.
-- CREATE INDEX idx_document_chunks_embedding ON document_chunks
--     USING hnsw (embedding vector_cosine_ops);
-- CREATE INDEX idx_questions_embedding ON questions
--     USING hnsw (question_embedding vector_cosine_ops);

-- Full-text search (BM25 hybrid retrieval)
CREATE INDEX idx_circular_documents_fts ON circular_documents
    USING GIN (to_tsvector('english', title || ' ' || COALESCE(circular_number, '')));

-- JSONB indexes
CREATE INDEX idx_questions_citations ON questions USING GIN (citations);
CREATE INDEX idx_circular_documents_tags ON circular_documents USING GIN (tags);
CREATE INDEX idx_circular_documents_affected_teams ON circular_documents USING GIN (affected_teams);

-- Analytics
CREATE INDEX idx_analytics_events_type ON analytics_events(event_type);
CREATE INDEX idx_analytics_events_user_hash ON analytics_events(user_hash);
