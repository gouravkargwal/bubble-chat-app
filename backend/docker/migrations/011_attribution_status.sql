-- Attribution-status field: captures the per-interaction verdict for the copied
-- reply's strategy_label, set on the NEXT scan once _find_attributable_response
-- evaluates it against the new transcript.
--
-- The model's `attribution_status` column (`Mapped[str | None]`) was added to
-- the SQLAlchemy Interaction class but `Base.metadata.create_all` cannot add
-- columns to existing tables, so this migration was never auto-applied,
-- causing `column interactions.attribution_status does not exist` errors
-- in production.
--
-- Idempotent. Apply (dev):
--   docker compose exec -T postgres psql -U cookd -d cookd \
--     < docker/migrations/011_attribution_status.sql
--
-- Apply (prod):
--   docker compose exec -T postgres psql -U cookd -d cookd \
--     < docker/migrations/011_attribution_status.sql

ALTER TABLE interactions
    ADD COLUMN IF NOT EXISTS attribution_status VARCHAR(20);
