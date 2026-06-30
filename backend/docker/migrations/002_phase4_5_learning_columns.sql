-- Phase 4 + 5 learning columns (and a backfill of the prior session's
-- vision_output_json column).
--
-- This project manages schema via SQLAlchemy `Base.metadata.create_all`, which
-- creates MISSING TABLES but never ADDS COLUMNS to existing tables. Fresh DB
-- volumes pick these up automatically; existing dev/prod databases need this
-- one-off, idempotent ALTER. Safe to re-run.
--
-- Apply (dev):
--   docker compose exec -T postgres psql -U cookd -d cookd \
--     < docker/migrations/002_phase4_5_learning_columns.sql

-- Phase 4: running tally of archetypes observed across scans.
ALTER TABLE conversations
    ADD COLUMN IF NOT EXISTS archetype_counts TEXT NOT NULL DEFAULT '{}';

-- Phase 5: per-strategy outcome stats {label: {shown, copied, landed, flopped}}.
ALTER TABLE conversations
    ADD COLUMN IF NOT EXISTS strategy_stats TEXT NOT NULL DEFAULT '{}';

-- Prior session: cached VisionNodeOutput on pending resolutions (was never
-- migrated for existing DBs since create_all can't add columns).
ALTER TABLE pending_resolutions
    ADD COLUMN IF NOT EXISTS vision_output_json TEXT;
