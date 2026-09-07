-- RegPulse Sprint 3 Migration
-- Knowledge Graph + News Ingest + Public Snippet Sharing
-- Idempotent (safe to re-run on dev DBs)

-- =============================================================================
-- ENUMs
-- =============================================================================
DO $$ BEGIN
    CREATE TYPE kg_entity_type_enum AS ENUM (
        'CIRCULAR', 'SECTION', 'REGULATION', 'ENTITY_TYPE',
        'AMOUNT', 'DATE', 'TEAM', 'ORG'
    );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE kg_relation_type_enum AS ENUM (
        'SUPERSEDES', 'REFERENCES', 'AMENDS', 'APPLIES_TO',
        'MENTIONS', 'EFFECTIVE_FROM'
    );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE news_source_enum AS ENUM (
        'RBI_PRESS', 'BUSINESS_STANDARD', 'LIVEMINT', 'ET_BANKING'
    );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE news_status_enum AS ENUM ('NEW', 'REVIEWED', 'DISMISSED');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- =============================================================================
-- kg_entities
-- =============================================================================
CREATE TABLE IF NOT EXISTS kg_entities (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_type     kg_entity_type_enum NOT NULL,
    canonical_name  VARCHAR(500) NOT NULL,
    aliases         JSONB NOT NULL DEFAULT '[]'::jsonb,
    metadata        JSONB NOT NULL DEFAULT '{}'::jsonb,
    first_seen_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_seen_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (entity_type, canonical_name)
);

CREATE INDEX IF NOT EXISTS idx_kg_entities_canonical_name
    ON kg_entities (canonical_name);
CREATE INDEX IF NOT EXISTS idx_kg_entities_aliases
    ON kg_entities USING GIN (aliases);
CREATE INDEX IF NOT EXISTS idx_kg_entities_type
    ON kg_entities (entity_type);

-- =============================================================================
-- kg_relationships
-- =============================================================================
CREATE TABLE IF NOT EXISTS kg_relationships (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_entity_id    UUID NOT NULL REFERENCES kg_entities(id) ON DELETE CASCADE,
    target_entity_id    UUID NOT NULL REFERENCES kg_entities(id) ON DELETE CASCADE,
    relation_type       kg_relation_type_enum NOT NULL,
    source_document_id  UUID REFERENCES circular_documents(id) ON DELETE CASCADE,
    confidence          REAL NOT NULL DEFAULT 1.0,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (source_entity_id, target_entity_id, relation_type, source_document_id)
);

CREATE INDEX IF NOT EXISTS idx_kg_rel_source ON kg_relationships(source_entity_id);
CREATE INDEX IF NOT EXISTS idx_kg_rel_target ON kg_relationships(target_entity_id);
CREATE INDEX IF NOT EXISTS idx_kg_rel_type ON kg_relationships(relation_type);
CREATE INDEX IF NOT EXISTS idx_kg_rel_document ON kg_relationships(source_document_id);

-- =============================================================================
-- news_items
-- =============================================================================
CREATE TABLE IF NOT EXISTS news_items (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source              news_source_enum NOT NULL,
    external_id         VARCHAR(500) NOT NULL,
    title               TEXT NOT NULL,
    url                 TEXT NOT NULL,
    published_at        TIMESTAMPTZ,
    summary             TEXT,
    raw_html_hash       VARCHAR(64),
    linked_circular_id  UUID REFERENCES circular_documents(id) ON DELETE SET NULL,
    linked_entity_ids   JSONB NOT NULL DEFAULT '[]'::jsonb,
    relevance_score     REAL,
    status              news_status_enum NOT NULL DEFAULT 'NEW',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (source, external_id)
);

CREATE INDEX IF NOT EXISTS idx_news_items_published_at ON news_items(published_at DESC);
CREATE INDEX IF NOT EXISTS idx_news_items_status ON news_items(status);
CREATE INDEX IF NOT EXISTS idx_news_items_source ON news_items(source);
CREATE INDEX IF NOT EXISTS idx_news_items_linked_circular ON news_items(linked_circular_id);

-- =============================================================================
-- public_snippets
-- =============================================================================
CREATE TABLE IF NOT EXISTS public_snippets (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug            VARCHAR(32) NOT NULL UNIQUE,
    question_id     UUID NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    snippet_text    TEXT NOT NULL,
    top_citation    JSONB,
    consult_expert  BOOLEAN NOT NULL DEFAULT FALSE,
    view_count      INTEGER NOT NULL DEFAULT 0,
    revoked         BOOLEAN NOT NULL DEFAULT FALSE,
    expires_at      TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_public_snippets_slug ON public_snippets(slug);
CREATE INDEX IF NOT EXISTS idx_public_snippets_user ON public_snippets(user_id);
CREATE INDEX IF NOT EXISTS idx_public_snippets_question ON public_snippets(question_id);
CREATE INDEX IF NOT EXISTS idx_public_snippets_created_at ON public_snippets(created_at DESC);
