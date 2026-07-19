-- Archetype snapshot field: captures the detected_archetype at the time each
-- interaction's replies were generated. See the SQLAlchemy model comment for
-- the full rationale (it deliberately isolates the archetype read from the
-- outcome it's meant to predict).
--
-- The model added this column but `Base.metadata.create_all` cannot add
-- columns to existing tables, so this migration was never auto-applied,
-- causing `column interactions.detected_archetype does not exist` errors
-- in production.
--
-- Idempotent. Apply (dev):
--   docker compose exec -T postgres psql -U cookd -d cookd \
--     < docker/migrations/010_detected_archetype.sql
--
-- Apply (prod):
--   docker compose exec -T postgres psql -U cookd -d cookd \
--     < docker/migrations/010_detected_archetype.sql

ALTER TABLE interactions
    ADD COLUMN IF NOT EXISTS detected_archetype VARCHAR(50);
