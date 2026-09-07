-- Sprint 5: Manual PDF uploads + Semantic clustering
-- Applied after 003_sprint4_confidence.sql

-- ============================================================
-- Pillar A: Manual PDF Upload
-- ============================================================

-- Track upload source on circular_documents
ALTER TABLE circular_documents
    ADD COLUMN IF NOT EXISTS upload_source VARCHAR(20) NOT NULL DEFAULT 'scraper';

-- Upload tracking table
CREATE TABLE IF NOT EXISTS manual_uploads (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    admin_id        UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    filename        VARCHAR(500) NOT NULL,
    file_size_bytes INTEGER NOT NULL,
    status          VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    document_id     UUID REFERENCES circular_documents(id) ON DELETE SET NULL,
    error_message   TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at    TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_manual_uploads_admin_id ON manual_uploads(admin_id);
CREATE INDEX IF NOT EXISTS idx_manual_uploads_status ON manual_uploads(status);

-- ============================================================
-- Pillar B: Semantic Clustering Heatmaps
-- ============================================================

CREATE TABLE IF NOT EXISTS question_clusters (
    id                        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cluster_label             VARCHAR(200) NOT NULL,
    representative_questions  TEXT[] NOT NULL DEFAULT '{}',
    centroid                  vector(3072),
    question_count            INTEGER NOT NULL DEFAULT 0,
    period_start              DATE NOT NULL,
    period_end                DATE NOT NULL,
    created_at                TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_question_clusters_period
    ON question_clusters(period_start, period_end);

-- Cluster assignment FK on questions
ALTER TABLE questions
    ADD COLUMN IF NOT EXISTS cluster_id UUID REFERENCES question_clusters(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_questions_cluster_id ON questions(cluster_id);
