-- RegPulse Sprint 4 Migration
-- Persist confidence_score + consult_expert on questions so that
-- the Confidence Meter UI in /history/[id] survives a refresh.
-- Idempotent (safe to re-run on dev DBs).

ALTER TABLE questions
    ADD COLUMN IF NOT EXISTS confidence_score REAL,
    ADD COLUMN IF NOT EXISTS consult_expert BOOLEAN NOT NULL DEFAULT FALSE;

-- Btree index — admin "low confidence" review queue can scan this cheaply.
CREATE INDEX IF NOT EXISTS idx_questions_confidence_score
    ON questions(confidence_score)
    WHERE confidence_score IS NOT NULL;
