-- Phase 4 (revision): stabilize personality DIMENSIONS instead of the derived
-- archetype label. Adds conversations.dimension_counts.
--
-- Replaces the role of conversations.archetype_counts (added in 002). On DBs
-- that already ran 002, archetype_counts is now UNUSED — left in place
-- (harmless) rather than dropped. Fresh/recreated tables get dimension_counts
-- from the model via create_all and never have archetype_counts.
--
-- Idempotent. Apply (dev):
--   docker compose exec -T postgres psql -U cookd -d cookd \
--     < docker/migrations/003_dimension_counts.sql

ALTER TABLE conversations
    ADD COLUMN IF NOT EXISTS dimension_counts TEXT NOT NULL DEFAULT '{}';
